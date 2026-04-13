# US Census Chat Agent

A production-quality chat agent that answers natural language questions about the US population using the ACS 2019 5-year estimates from the Snowflake Marketplace. Built in 24 hours.

**Live demo:** `[https://census-agent-jirdy3dtrgqrxrshpjfshy.streamlit.app/]`  
**Login:** `[credentials if applicable]`

---

## The core problem

The Census dataset has 8,120 columns with names like `B19013e1` and `B27010e17`. They're completely opaque without the metadata table, and the terminology the Census uses doesn't map cleanly to how people ask questions. "Poverty" in natural language maps to B17001 — but a semantic search returns B29003 (citizenship by poverty status) instead. Embeddings don't fix this. Keyword search doesn't fix this.

The only approach that worked: show a capable LLM the complete 243-table catalog at low resolution, let it reason about which tables are relevant, then fetch exact columns dynamically from Snowflake metadata for only those tables. This keeps the context window focused and accurate without hardcoding anything.

---

## Architecture

```
User question
    ↓
[1] GUARDRAIL — gpt-4.1-mini, structured output, fails open
    ↓ blocked → helpful rejection with suggestions
[2] PLANNER — NL → structured JSON plan, fast-fail on unanswerable queries (~800ms)
    ↓ unanswerable → clear explanation of why
[3] TABLE SELECTOR — LLM sees all 243 table titles (gpt-4.1)
    ↓
[4] COLUMN LOOKUP — live Snowflake metadata query for selected tables only
    ↓
[5] COLUMN SELECTOR — LLM picks exact columns from focused context (gpt-4.1)
    ↓
[6] SQL GENERATOR — writes verified SQL (gpt-4.1)
    ↓
[7] VALIDATOR — syntax + safety + LIMIT enforcement (sqlglot, deterministic)
    ↓ fails → retry once with error context
[8] EXECUTOR — Snowflake, 45s timeout
    ↓
[9] SYNTHESIZER — grounded answer, discloses approximations (gpt-4.1-mini)
```

### Why this architecture

**Two-step metadata lookup.** The table selector sees all 243 verified table titles at ~5,000 tokens — small enough for reliable attention — and picks what's relevant. The column lookup then queries Snowflake's live metadata for only those tables, returning ~50 focused rows. The LLM never sees the full 8,120-column schema. Nothing is hardcoded beyond the table titles — if the Census dataset adds a new table tomorrow, the agent finds it automatically.

**Dedicated planning step.** Most text-to-SQL agents go directly from question to SQL. Inserting a structured JSON planning step first gives three things: fast-fail for unanswerable queries before any expensive operations (~800ms instead of ~15s), deterministic state normalization ("California" → "CA" via a Python dictionary, not an LLM), and an inspectable artifact for every query that made debugging dramatically faster.

**Model routing.** `gpt-4.1` for steps requiring genuine reasoning over structured data — table selection, column selection, SQL generation. `gpt-4.1-mini` for well-defined, constrained tasks — guardrail classification, planning, synthesis. GPT-4.1 is optimized for instruction-following and stays within constraints on structured outputs without editorializing. Approximate cost: ~$0.005 per query blended. At 1,000 queries/day that's ~$150/month. The mini routing reduces cost ~40% with no measurable impact on answer quality.

**Graceful degradation on every path.** Every step has an explicit failure path that produces a helpful message:

| Failure point | What the user sees |
|---|---|
| Guardrail blocks | Explains what the agent handles, suggests alternatives |
| Planner marks unanswerable | Explains why (city-level, non-US, post-2020) and what would work |
| Metadata lookup fails | Asks user to rephrase |
| SQL generation fails | Clean message, no stack trace |
| SQL validation fails after retry | Explains the query couldn't be generated safely |
| Snowflake errors | Specific message per error type |
| Empty results | Explains why data isn't available at that granularity |

---

## Key data decisions

These aren't obvious from the schema and each one corresponds to a real bug or wrong answer if ignored.

**Weighted median aggregation.** You cannot average block-group medians to produce a county or state median — the math doesn't work. The correct approach is `SUM(median * weight) / NULLIF(SUM(weight), 0)`. Weight column varies by metric: total households for income, renter-occupied units for gross rent, owner-occupied units for home value. Always disclosed to the user as a "population-weighted approximation."

**NULL means suppressed, not unknown.** NULLs in this dataset mean the block group had too few respondents for the Census Bureau to report reliably — small cell suppression for privacy protection. The `IS NOT NULL` filters are correct, but the reason matters: we're respecting Census disclosure avoidance methodology, not filtering bad data.

**Zero and NULL are different.** Zero means a block group genuinely had none of something. NULL means it was suppressed. The `> 0` filter belongs on weight columns only — applying it to count fields silently undercounts areas that legitimately have zero of a characteristic.

**Universe mismatches.** B19013 counts households, B01001 counts people, B25003 counts occupied housing units. Cross-table derived metrics need to account for this or the denominator is wrong.

**The e/m distinction.** Every ACS field has an estimate (`e` suffix) and a margin of error (`m` suffix). MOE columns are statistical uncertainty ranges, not demographic values. The metadata filter excludes all `m` columns — if that filter breaks, the agent silently treats confidence intervals as data.

**ACS 5-year window.** "2019 data" means responses collected 2015–2019. Year-over-year comparisons between 2019 and 2020 are overlapping windows, not discrete years.

**City-level queries are unanswerable.** City boundaries don't align with Census Block Group boundaries. A question about Austin, TX cannot be answered because Austin's city limits cut across hundreds of CBGs that also include non-Austin areas. Caught at the planning step and returned as a helpful explanation.

---

## Testing

Four layers, each catching different failure modes.

**Unit tests (22 tests, ~0.4s):** The fastest feedback loop — run in under half a second, cost nothing. Cover everything deterministic: SQL safety checker, syntax parser, LIMIT injection, empty SQL rejection, state normalization. If any of these break, the pipeline fails on every query regardless of LLM performance.

**Integration tests (9 tests, ~16s):** Hit the live Snowflake database with real queries and assert real answers. The most important — `test_california_income_query` — asserts the weighted median income for California lands between $80,000 and $90,000. One test that simultaneously catches connection failures, schema changes, and formula regressions.

**Behavioral evals (32 cases, ~8 mins):** LLM outputs aren't deterministic — testing for exact answers produces flaky results. These test what the agent *does*, not what it *says*. Coverage: core demographic queries, national aggregations, county level, US territories (Puerto Rico, DC), edge cases (Loving County TX with ~98 people, ambiguous county names), guardrail probes (prompt injection, nonsense input, financial advice requests), year handling, multi-turn follow-ups, cross-state ranking, and all graceful degradation paths.

**Grounding check (15 cases, ~5 mins):** The most important layer, and the one most agents skip. An agent can pass every behavioral eval while still pulling numbers from training memory rather than actual query results — and you'd never catch it without this. For each question, the primary number in the synthesized answer is compared against the raw SQL execution result from Snowflake directly, within 5% tolerance. It tests synthesizer grounding specifically, not SQL correctness.

Results across 15 diverse queries: US population answer said "328 million" against a SQL result of 328,016,242 (0.005% off). Health insurance coverage said "91.2%" against SQL result of 91.19% (0.01% off). California 2020 income said "$87,168" against SQL result of $87,168.19 (essentially exact). The synthesizer never once used a number from training memory.

**Current scores:** 21/22 unit tests, 9/9 integration tests, 30/32 behavioral evals (94%), 15/15 grounding check (100%).

The 94% behavioral eval figure understates actual reliability. Both failures were transient OpenAI API errors during the eval run — not logic failures. On verified runs the logic failure rate is 0/30. They do expose a real production gap: LLM calls need retry logic with exponential backoff rather than relying solely on fail-open behavior.

---

## Known limitations

**B16004 double-counting.** For "Spanish speakers in California" the agent returns ~57%; the correct answer is ~29%. Root cause: the metadata format doesn't expose hierarchy depth beyond FIELD_LEVEL_6, so parent totals and their breakdowns look identical to the column selector — and it selects both. Fix requires fetching deeper field levels and adding explicit hierarchy logic. Not implemented because a partial fix risked regressions in simpler tables.

**Ambiguous county without state.** "Washington County" matches 31 states. The agent returns data for the first match rather than asking for clarification. Fix: detect multi-state matches at the planning step and prompt for disambiguation.

**Complex multi-table queries near token ceiling.** The column selector runs at `max_tokens=1200` — sufficient for all tested cases. A query genuinely requiring 40+ columns across 6+ tables starts hitting that ceiling. The real fix isn't raising the limit — it's better upstream structure: a pre-computed hierarchy map that documents parent-child relationships and aggregation types explicitly, combined with Snowflake-side topic filtering so the column selector only receives columns relevant to the query. Both would keep the context window focused regardless of query complexity.

---

## What I'd do with more time

**Snowflake Cortex Analyst semantic model.** The highest-impact improvement. Replaces the metadata lookup pipeline with native text-to-SQL inside Snowflake and fixes vocabulary mismatch at the root. Building a correct semantic model for 243 tables in 24 hours wasn't realistic — correctness would have been assumed, not verified. With more time this is the right direction.

**Pre-computed hierarchy map.** Build a structured JSON schema map once from a Snowflake query over all 8,120 columns that explicitly documents every column's parent-child relationships, universe, aggregation type, and weight column. This would fix the B16004 double-counting bug and make the column selector dramatically more reliable on complex tables.

**Query decomposition.** Complex multi-part questions currently get attempted in a single SQL query and sometimes fail. The right approach is decomposing them into multiple queries and synthesizing the results.

**Prompt versioning.** Prompts are strings in `prompts.py`. Any change is silent — there's no way to correlate a prompt edit with a quality regression. Production needs versioning and rollback.

**Retry logic with backoff.** The two behavioral eval failures caused by API errors would be caught by exponential backoff on LLM calls. Currently the pipeline relies on fail-open behavior for error recovery, which is insufficient for production.

---

## Running locally

```bash
git clone [repo]
cd [repo]
pip install -r requirements.txt
```

Set environment variables:
```
OPENAI_API_KEY=
SNOWFLAKE_ACCOUNT=
SNOWFLAKE_USER=
SNOWFLAKE_PASSWORD=
SNOWFLAKE_DATABASE=
SNOWFLAKE_SCHEMA=
SNOWFLAKE_WAREHOUSE=
```

```bash
streamlit run app.py
```

### Running tests

```bash
pytest tests/unit/          # 0.4s, no external dependencies
pytest tests/integration/   # requires Snowflake connection
pytest tests/evals/         # requires OpenAI + Snowflake, ~13 mins total
```
