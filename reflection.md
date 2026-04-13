# Reflection — US Census Chat Agent

## Overview

This document covers my development process, key decisions, known limitations, and testing approach. It also covers what works, what doesn't, and the specific tradeoffs I made given the time constraint.

The core insight of this submission is that the vocabulary mismatch problem between natural language and Census terminology can't be solved by keyword search, semantic embeddings, or full schema injection (atleast in 24 hours). It requires showing a capable LLM the complete table catalog at low resolution, letting it reason about relevance, then fetching exact columns dynamically from Snowflake metadata. This approach emerged from testing alternatives against real queries.
---

## Development Process

### Phase 1: Data Exploration (3-4 hours)

Before writing any application code, I spent the first 3-4 hours just understanding the dataset. This turned out to be the most important time I spent.

The Census dataset looks approachable on the surface but is genuinely complex underneath. 8,120 columns with names like `B19013e1` and `B27010e17` are completely opaque without the metadata table. 

A few specific examples out of many I verified before writing any code:

**FIPS join pattern.** There's no direct key between block group data and state/county names. Join using `LEFT(CENSUS_BLOCK_GROUP, 2) = STATE_FIPS` and `SUBSTRING(CENSUS_BLOCK_GROUP, 3, 3) = COUNTY_FIPS`. The FIPS table has no `STATE_NAME` column — early SQL drafts that used `f.STATE_NAME` failed silently, which was annoying to debug.

**Universe mismatches.** Different tables count different things. B19013 counts households, B01001 counts people, B25003 counts occupied housing units. A block group having 400 households and 1,200 people isn't a data error — those are just different universes. Cross-table derived metrics (like income per capita) need to account for this or the denominator is wrong.

**Derived fields don't exist** everything is computed at query time. The dataset contains only raw estimates. There are no pre-computed percentages, rates, or ratios anywhere in the schema. "Percent renter-occupied" is not a column: you compute it as B25003e3 / B25003e1. An agent that searches for a field named something like "renter_rate" or "poverty_percent" will find nothing and either fail or hallucinate a column name.

**Field codes are not human-readable** and the agent cannot guess them. There is no pattern that lets us derive "B19013 = median household income" from first principles. The mapping has to come from metadata. An agent without access to field labels will either hallucinate table codes or query the wrong thing entirely. 

**e/m column distinction.** Every ACS field comes in two versions: estimate (`e` suffix) and margin of error (`m` suffix). MOE columns are statistical uncertainty ranges, not demographic values. The metadata filter excludes all `m` columns — if that filter ever breaks, the agent would silently treat confidence intervals as data.

**Weighted median aggregation.** You can't average block-group medians to get a county or state median: the math doesn't work. Instead: `SUM(median * weight) / NULLIF(SUM(weight), 0)`. This is a population-weighted mean of medians, which is an approximation but the best one available from this data structure. Weight column varies by metric: total households for income, renter-occupied units for gross rent, owner-occupied units for home value. Always disclose this as a "population-weighted approximation."

**ACS 5-year window.** "2019 data" means responses collected 2015–2019, not a 2019 snapshot. Year-over-year comparisons between 2019 and 2020 are comparing overlapping windows (2015–2019 vs 2016–2020), not discrete years. Smaller geographies tend to be more reliable because more pooled responses reduce the standard error.

**B vs C tables** C-tables (e.g. `C19001`) are simplified versions of B-tables that collapse race/ethnicity categories to improve reliability for small geographies. They're not separate concepts — don't treat them as additional variables if your metadata includes both.

---

### Phase 2: Architecture Design

I prototyped and rejected two approaches based on test results before arriving at the one I built.

Full schema injection: injecting all 8,120 columns into a single prompt exceeds reliable attention span and produces hallucinated column names on complex queries. Beyond that, building a correct semantic model for 243 tables with proper hierarchy, universe annotations, and weight column relationships in 24 hours wasn't realistic: correctness would have been assumed, not verified. Rejected without prototyping.

Semantic embedding search: I built an embedding index over all table titles and tested it against real queries. "Poverty" returned B29003 (citizenship by poverty status) instead of B17017 (poverty status of individuals). The Census uses its own terminology that doesn't map to how people ask questions. Fuzzy LIKE search had the same problem. Rejected after testing: the vocabulary mismatch is structural, not fixable by better embeddings.

**Two-step table selection + targeted column lookup** is what I built. Step 1: the LLM sees all 243 table titles at ~5,000 tokens — small enough for reliable attention — and picks relevant tables. Step 2: Snowflake metadata is queried for only those tables' columns (~50 focused rows), and the LLM picks exact columns from that focused context. Nothing is hardcoded except the 243 table titles.

This ensures **"Comprehensive mapping"** — the table selector sees all 243 verified tables, nothing excluded or summarized, including B-series, C-series, metadata tables, and all demographic breakdowns. **"Context awareness without hardcoding"** — columns are fetched dynamically from Snowflake metadata at query time, not from any static list in any prompt. If the Census dataset added a new table tomorrow, the agent would find it automatically without any code change. The two-step approach satisfies both simultaneously: comprehensive at the table level, targeted at the column level. 
---

### Phase 3: Implementation

The full pipeline:

```
User question
    ↓
[1] GUARDRAIL — gpt-4.1-mini classifier, fails open, passes history
    ↓ blocked → helpful rejection
[2] PLANNER — NL to structured JSON plan (gpt-4.1-mini)
    ↓ unanswerable → fast-fail (~800ms)
[3] TABLE SELECTOR — LLM sees all 243 table titles (gpt-4.1)
    ↓
[4] COLUMN LOOKUP — Snowflake metadata query for selected tables only
    ↓
[5] COLUMN SELECTOR — LLM picks exact columns (gpt-4.1)
    ↓
[6] SQL GENERATOR — writes verified SQL (gpt-4.1)
    ↓
[7] VALIDATOR — empty check + safety + syntax + LIMIT (sqlglot, deterministic)
    ↓ retry once with error context
[8] EXECUTOR — Snowflake, 45s timeout
    ↓
[9] SYNTHESIZER — grounded answer (gpt-4.1-mini)
```

**Model selection had a direct impact on correctness.** After researching, I realised that GPT-4.1 is optimized specifically for instruction-following and coding tasks. It's more literal, less likely to editorialize, and better at staying within constraints on long structured outputs. For an agent that needs to generate precise SQL, follow strict metadata rules, and not hallucinate column names, this matters quite a lot.

Claude tends to over-explain and add caveats. Gemini is less predictable on structured outputs. GPT-4.1 just does what it's told with less noise.

I use `gpt-4.1` where the task requires genuine reasoning over structured data, and `gpt-4.1-mini` where the task is well-defined and simpler (classification, planning, synthesis). This reduces per-query cost ~40% without affecting answer quality.

**Average response time: ~25 seconds for most tasks.** 

---

## Other key Architectural Decisions

### Comprehensive mapping and context awareness

The two-step metadata lookup resolves this directly. The table selector receives the complete 243-table registry at every query: no table is excluded, no topic is pre-filtered. The column lookup then queries Snowflake's own metadata table dynamically for the selected tables, returning the exact column IDs, field levels, and descriptions that exist in the actual database at query time. Nothing is hardcoded beyond the table titles.

This means the agent can answer questions about any of the 8,120 columns in the dataset without any of them being explicitly listed in a prompt.

### Why a separate planning step? (json)

Most text-to-SQL agents go directly from question to SQL. I insert a planning step that produces structured JSON first:

```json
{
  "topics": ["income"],
  "geography_type": "state",
  "location": "CA",
  "year": "2019",
  "is_comparison": false,
  "is_answerable": true,
  "ambiguities": ["interpreted California as state CA"]
}
```

Three reasons. First, fast-fail: `is_answerable: false` short-circuits the pipeline before expensive operations — city-level queries fail in ~800ms instead of ~15s. Second, state normalization happens in a Python dictionary lookup, not inside an LLM. "California" → "CA" is deterministic and reliable. Third, every failed query has an inspectable plan, which made debugging dramatically faster throughout development.

### Operational guardrails as a dedicated layer

Before anything expensive runs — metadata lookup, SQL generation, all of it: a separate LLM call (gpt-4.1-mini) checks one thing: is this a legitimate Census data query? It returns {"allowed": bool, "reason": str}. If blocked, the pipeline short-circuits immediately.
Three deliberate design choices: it receives the last conversation turn so follow-up questions aren't incorrectly flagged as out-of-scope. It fails open, an infrastructure error allows the question through, because silently dropping valid queries is the worse failure mode than occasionally passing a bad one. And it's tested against 6 adversarial inputs specifically chosen to probe its edges: recipe request, individual net worth, foreign country, financial advice, prompt injection, and nonsense. All 6 blocked correctly.


### Graceful degradation 

Every step in the pipeline has an explicit failure path that produces a helpful message rather than an empty response or unhandled error:

- Guardrail blocks → explains what the agent does handle, suggests alternatives
- Planner marks unanswerable → explains why (city-level, non-US, post-2020) and suggests what would work
- Metadata lookup fails → asks the user to rephrase
- SQL generation fails (empty string on API error) → clean message, no cryptic error
- SQL validation fails after retry → explains the query couldn't be generated
- Snowflake execution errors → specific messages per error type (invalid identifier, timeout, does not exist)
- Empty results → explains the data isn't available at that level of detail

None of these paths crash the application or return a blank screen.



### Why not Snowflake Cortex Analyst?

Cortex Analyst is available in my region (AWS US East 1) and is a good production direction to explore. It handles text-to-SQL natively within Snowflake, eliminates the vocabulary mismatch problem, and would handle complex hierarchical tables better than our current approach. I verified it was available and chose not to use it.

Building a correct semantic model for 243 tables with 24 hours total was not the right choice because it requires correctness + validation, otherwise the responses could be way worse.
---



## Testing Strategy

Four layers, each catching different failure modes:

**Unit tests (22 tests, ~0.4s):** Deterministic non-LLM code — SQL safety checker, syntax parser, LIMIT injection, empty SQL rejection, state normalization. Zero cost, instant feedback. If the validator breaks, every query is either unsafe or crashes.

**Integration tests (9 tests, ~16s):** Snowflake connectivity and known-answer queries. `test_california_income_query` asserts the weighted median result is between $80,000 and $90,000 — catches both connection failures and regression in the formula simultaneously.

**Behavioral evals (32 cases, ~8 mins):** Agent behavior, not exact answers. LLM outputs vary slightly between runs — behavioral properties are stable. Does "What about Texas?" after a California question resolve correctly? Does a query about Loving County, TX — population ~98 : return a real answer instead of crashing? The 32 cases were chosen to cover the full surface area: happy path queries, US territories, ambiguous geographies, out-of-scope requests, multi-turn follow-ups, and known edge cases.

**Grounding check (15 cases, ~5 mins):** For each question, the agent runs, the generated SQL is executed directly against Snowflake, and the primary number in the answer is compared against the primary number in the SQL result within 5% tolerance. This tests whether the synthesizer used actual query data, not whether the SQL is correct. An agent that passes behavioral evals can still fill gaps from training memory. The grounding check catches that specifically.

**Current scores:** 21/22 unit tests, 9/9 integration tests, 30/32 behavioral evals (94%), 15/15 grounding check (100%).

The honest limitation is that the pipeline degrades on queries that require a very large number of columns across multiple complex tables simultaneously. The column selector runs at max_tokens=1200: sufficient for every tested case, but a query that genuinely needs 40+ columns from 6+ tables will start hitting that ceiling. The fix could be Snowflake-side topic pre-filtering before the column lookup, which would keep the context window focused regardless of query complexity. Not implemented within the time constraint, but the failure mode is understood and bounded.

The grounding check result is the most meaningful signal in the test suite. Across 15 diverse query patterns — state income, national population, county level, territories, housing metrics, year-specific queries, every answer number was within 5% of the actual SQL execution result. The synthesizer never used a number from training memory instead of the query result. Specific examples: US population answer said "328 million" against a SQL result of 328,016,242 (0.005% off); health insurance answer said "91.2%" against SQL result of 91.19% (0.01% off); CA 2020 income answer said "$87,168" against SQL result of $87,168.19 (essentially exact). This confirms the grounding rule in the synthesizer prompt is working as intended.

### What I would explore if I have more time

**Snowflake Cortex Analyst semantic model.** The highest-impact improvement. Replaces the metadata lookup pipeline with native text-to-SQL and fixes vocabulary mismatch at the root.

**Pre-computed schema map with explicit hierarchy encoding.** The current dynamic metadata lookup infers column hierarchy from text descriptions rather than encoding it explicitly. A pre-computed schema map would document every column's parent-child relationships, aggregation type, and weight column in structured JSON — built once from a Snowflake query over all 8,120 columns and verified for complex tables. 

**Prompt versioning.** Prompts are strings in `prompts.py`. Any change is silent. Production needs prompt versioning, rollback, and the ability to correlate a prompt change with a quality regression.

**Query decomposition.** Complex multi-part questions need multiple SQL queries. The current agent tries to answer them in one query and often fails.


---

## Known Edge Cases and Failure Modes

### Identified and handled

**City-level queries** — planner marks `is_answerable: false`, suggests county instead.

**Wrong year** — defaults to 2019 with an ambiguity note. Never errors.

**Multi-turn follow-ups** — "What about Texas?" after California resolves correctly. Guardrail and planner both receive history. Verified working in UI.

**State name variants** — "California", "california", "CA", "ca" all normalize deterministically.

**NULL handling** — `COALESCE` and `IS NOT NULL` filters throughout. Respects Census small cell suppression.

**Prompt injection** — correctly blocked. Verified.

**Ambiguous geography** — "What is the population of New York?" defaults to state, notes the interpretation.

**Tiny county** — Loving County TX (~98 people). FIPS join works correctly. Verified.

**SQL generation failure**  Returns empty string on API error, caught before validation, clean message to user.

### Identified but not fully addressed

**B16004 double-counting.** For "Spanish speakers in California" the agent returns ~57%; the correct answer is ~29% (verified: `(B16004e4 + B16004e26 + B16004e48) / B16004e1`). Root cause: FIELD_LEVEL_7 isn't fetched, so parent and child rows look identical in formatted metadata output. Fix requires fetching deeper field levels and adding hierarchy logic. Not implemented because a partial fix risked regressions in simpler tables.

**Ambiguous county without state.** "Washington County" matches 31 states. Agent returns data for multiple matches rather than asking for clarification. Production fix: detect multi-state matches at the planner and prompt for disambiguation.

**Token budget edge case.** Column selector at `max_tokens=1200`. Sufficient for all tested cases. Production fix: Snowflake-side topic filtering.

**LIMIT constant inconsistency.** The SQL generator prompt instructs `LIMIT 10000` for non-aggregated queries while the validator injects `LIMIT 1000` if no LIMIT clause exists. In practice the SQL generator always adds a LIMIT so the validator injection rarely fires, but the constants are inconsistent. Production would consolidate to a single configurable constant.

**Table selector year instruction for comparisons.** The table selector prompt says "use the year from the query plan" but comparison queries produce `year: "2019-2020"` which doesn't map to a real physical table. This is handled correctly in `metadata.py` which normalizes to 2019 for metadata lookup, but the prompt and actual behavior are slightly inconsistent.


---

## On Using AI Coding Tools

I used Claude throughout: architecture discussion, code generation, debugging, and data exploration.

---

## Summary

The core insight of this submission is that the vocabulary mismatch problem between natural language and Census terminology can't be solved by keyword search, semantic embeddings, or full schema injection. It requires showing a capable LLM the complete table catalog at low resolution, letting it reason about relevance, then fetching exact columns dynamically from Snowflake metadata. This approach emerged from testing alternatives against real queries, not from reasoning about it in the abstract.

The hardest problem wasn't architecture, it was the data. Census column structures are genuinely complex: opaque names, case-sensitive quoting, hierarchical organization, block-group medians that can't be averaged, NULL values that mean suppressed not unknown, ACS 5-year windows that overlap between years. Time spent understanding these specifics before writing code translated directly into correct answers and avoided real bugs.

The honest limitations are documented specifically and have clear production solutions. The agent handles the core use case correctly, degrades gracefully on known edge cases, and is built on verified data knowledge rather than assumptions.
