# REFLECTION.md

## US Census Chat Agent — Development Reflection

### Overview

This reflection covers my development process, key architectural decisions, honest assessment of tradeoffs, and what I would do differently with more time.

---

## Development Process

### Phase 1: Data Exploration (3-4 hours)

Before writing a single line of code I spent significant time understanding the actual dataset. This turned out to be the most valuable investment of the entire build.

Key discoveries from data exploration:

**The schema is not what it appears.** The Snowflake Marketplace listing suggests a clean, queryable Census dataset. The reality is 8,120 cryptically-named columns (`B19013e1`, `B27010e17`) spread across 243 physical tables. Column names are completely opaque without the metadata table.

**Case sensitivity is a silent killer.** Snowflake uppercases unquoted identifiers. `SELECT B19013e1` silently becomes `SELECT B19013E1` which errors. Every column name must be double-quoted. I discovered this during exploration and baked it into every prompt as a hard rule. Most agents built without this data exploration step will fail on this alone.

**The FIPS join is non-obvious.** The dataset has no direct join key between block group data and state/county names. The join works via FIPS code prefix matching: `LEFT(CENSUS_BLOCK_GROUP, 2) = STATE_FIPS` and `SUBSTRING(CENSUS_BLOCK_GROUP, 3, 3) = COUNTY_FIPS`. I verified this with actual queries before trusting it.

**Median values cannot be averaged.** Census median columns (income, rent, home value) represent block-group-level medians. Averaging them across block groups is statistically incorrect. The right approach is a population-weighted average: `SUM(median * weight) / SUM(weight)`. I verified the difference: simple AVG gives $84,692 for California median income, weighted average gives $84,261. The weight column varies by metric — households for income, renter units for rent, owner units for home value. I verified each weight column exists before using it.

**B17001 doesn't exist.** An AI-generated database reference document I received claimed B17001 was the primary poverty table. It isn't in our dataset. The actual poverty tables are B17010, B17017, B17021. I caught this by querying the actual schema rather than trusting the documentation.

**Allocation tables are noise.** Tables prefixed B99 are statistical allocation tables, not demographic data. Including them in any schema context confuses the LLM. I exclude them everywhere.

This exploration phase shaped every architectural decision that followed. Candidates who skip this step build agents that work on demos but fail on real queries.

---

### Phase 2: Architecture Design

The core challenge is bridging natural language to accurate SQL on a dataset with 8,120 opaque column names. I considered three approaches:

**Option A: Full schema injection**
Dump all 8,120 column descriptions into every prompt.
- Rejected: ~120,000 tokens per query at ~$0.30/query. More importantly, LLMs have a "lost in the middle" attention problem — they reliably miss information in the middle of very large contexts. Income and poverty columns, which are in the middle of the schema alphabetically, would be systematically less reliable.

**Option B: Keyword/embedding search**
Use fuzzy LIKE search or semantic embeddings to find relevant columns per query.
- Prototyped both. Fuzzy search fails on vocabulary mismatch — users say "rent", Census says "Contract Rent". I built and tested a semantic embedding index over 364 e1 rows. Results were inconsistent: "rent" correctly found B25056, but "poverty" returned B29003 (citizenship by poverty status) instead of B17017. Abandoned as unreliable.

**Option C: Two-step table selection + targeted column lookup (chosen)**
Step 1: Give the LLM all 243 table titles and topics (~5,000 tokens). LLM picks 2-3 relevant tables.
Step 2: Query Snowflake metadata for only those tables' columns (~50-100 rows). LLM picks exact columns.

This directly addresses the assignment hints:
- "Comprehensive mapping" — all 243 tables are visible to the selector
- "Context awareness without hardcoding" — columns are fetched dynamically

Each step gets a small, focused context. The LLM's attention is concentrated where it matters.

---

### Phase 3: Implementation

**Model selection mattered more than expected.**

Initial implementation used GPT-4o throughout. Health insurance queries returned ~54% (wrong) because GPT-4o struggled to identify the correct uninsured columns (e17, e33, e50, e66) from B27010's 66-column structure despite clear field descriptions.

Switching to GPT-4.1 for critical steps (table selection, column selection, SQL generation) fixed this immediately — the model correctly identified the no-insurance columns and computed `1 - (uninsured/total)`. This demonstrates that model selection is an architectural decision with direct correctness implications.

I use different models for different steps based on complexity:
- GPT-4.1 for table selection, column selection, SQL generation — requires complex reasoning
- GPT-4.1-mini for guardrail classification, planning, synthesis — sufficient for simpler tasks

This reduces per-query cost by ~40% while maintaining quality where it matters.

**The guardrail design required careful thought.**

A system-prompt-only guardrail is not robust — clever rephrasing can bypass it. I implemented a dedicated LLM classifier as a hard gate before any expensive operations. Two design decisions worth noting:

*Fails open*: If the classifier errors, it defaults to `allowed: true`. This is deliberate. A guardrail that blocks legitimate Census questions due to infrastructure failure is worse than one that occasionally lets a borderline question through.

*Passes conversation history*: Without history, "What about Texas?" after asking about California gets blocked as "too vague." The guardrail needs context to understand follow-up questions.

**Weighted median implementation.**

The SQL generator prompt includes explicit aggregation rules with verified weight columns:
- Median household income (B19013e1) → weight by B19001e1 (total households)
- Median gross rent (B25064e1) → weight by B25063e1 (total renter units)
- Median home value (B25077e1) → weight by B25075e1 (total owner units)

Every weight column was verified to exist in the actual database before being added to the prompt. The synthesizer always discloses "population-weighted approximation, not a true median."

**Year comparison support.**

The planner produces `year: "2019-2020"` for comparison questions. The metadata lookup normalizes this to use 2019 metadata (schemas are identical) but generates physical table names for both years. The SQL generator then produces UNION ALL queries joining both years. Verified: median income in California went from $84,261 in 2019 to $87,168 in 2020.

---

## Key Architectural Decisions

### Why a separate planning step?

Most text-to-SQL agents go directly from natural language to SQL. I insert a planning step that produces a structured JSON plan first:

```json
{
  "topics": ["income"],
  "geography_type": "state",
  "location": "CA",
  "year": "2019",
  "is_answerable": true,
  "ambiguities": ["user said California — interpreted as CA"]
}
```

Three reasons:
1. **Fast-fail path**: `is_answerable: false` short-circuits the pipeline before expensive metadata lookups and SQL generation. City-level queries fail in ~800ms instead of ~15s.
2. **State normalization in code**: "California" → "CA" happens in a Python dictionary lookup, not inside an LLM. This is 100% reliable. LLMs are unreliable at string transformations inside SQL.
3. **Debuggability**: The plan is a logged artifact. When an answer is wrong, I can inspect the plan to see what the agent thought the question meant.

### Why not Snowflake Cortex Analyst?

Cortex Analyst is available in my region (AWS US East 1) and would be the production direction. It handles text-to-SQL natively within Snowflake using a semantic model, which would eliminate the vocabulary mismatch problem and handle complex tables like B27010 natively.

I chose not to use it for this prototype for two reasons: building a complete semantic model for 243 tables within the time constraint would have compromised the reflection document and deployment testing — both of which I believe are higher-signal deliverables. The production path is clear: replace the dynamic metadata lookup with a Cortex Analyst semantic model.

### Why sqlglot for validation?

Failing fast before hitting Snowflake is cheaper and gives parseable error messages. The retry mechanism feeds the error back to the SQL generator — the second attempt fixes the majority of syntax errors. A try/catch on Snowflake execution gives a worse error message and wastes a round trip.

---

## Testing Strategy

I split testing into three layers:

**Unit tests** (22 tests, ~0.4s): Test deterministic non-LLM code — SQL safety checker, syntax parser, LIMIT injection, state normalization. Fast, zero API cost, run on every change.

**Integration tests** (9 tests, ~16s): Test Snowflake connectivity and known-answer queries. `test_california_income_query` asserts the result is between $80,000 and $90,000 — a range test that catches both connection failures and major regression in the weighted median calculation.

**Behavioral evals** (15 cases, ~3 mins): Test agent behavior not exact answers. Assert properties: "does the SQL contain the California FIPS code 06?", "does the answer mention the state name?", "was this question correctly blocked?". LLM outputs vary slightly between runs — asserting behavior rather than exact strings makes evals robust.

**Current scores**: 22/22 unit tests, 9/9 integration tests, 15/15 behavioral evals.

### What I would add with more time

**LLM-as-judge evaluation**: A second model (Claude, to avoid same-model bias) grades answer quality on dimensions: grounding (did it use only data from the query?), accuracy (is the number plausible?), transparency (did it disclose approximations?). GPT-4o judging GPT-4o outputs introduces systematic bias toward its own outputs.

**Regression tests against deployed URL**: Run evals against the live Railway URL not just local. Catches environment-specific failures — missing env vars, connection pool exhaustion, cold start timeouts.

**Latency benchmarks per query type**: Simple state queries should complete in ~8s. Year comparison queries in ~20s. National queries in ~12s. Automated benchmarks would catch performance regressions.

---

## Edge Cases and Failure Modes

### Identified and addressed

**City-level queries**: Census data is at county/block group level. City boundaries don't map cleanly to CBGs. Handled: planner marks city-level queries as `is_answerable: false` with a helpful message suggesting the user ask about the county instead.

**Wrong year**: User asks about 2015 data. Handled: planner defaults to 2019 and notes the ambiguity. Never returns an error for wrong year.

**Follow-up questions**: "What about Texas?" after asking about California. Handled: guardrail and planner both receive conversation history. Verified working.

**State name variants**: "California", "california", "CA", "ca" — all normalized to "CA" via deterministic Python dictionary before any LLM processing.

**NULL values**: Many block groups have NULL for certain metrics. Handled: SQL generator prompted to use `COALESCE` and `IS NOT NULL` filters. Verified in LA County and California queries.

**SQL injection**: Safety validator blocks DROP, DELETE, INSERT, UPDATE, CREATE, ALTER, TRUNCATE. Tested with 7 unit tests.

### Identified but not fully addressed

**Complex multi-column tables**: B27010 (health insurance, 66 columns) and similar complex tables sometimes produce incorrect SQL when the column structure is ambiguous. With GPT-4.1 this improved significantly — health insurance now returns 91.2% (correct) — but I cannot guarantee correctness for all complex tables across all queries.

**Real production fix**: An exploratory pre-flight step where the agent queries table structure before writing SQL. I prototyped this but removed it when GPT-4.1 made it unnecessary for the tested cases. The pattern is valid for production.

**Aggregation ambiguity**: "What is the average income in California?" — average of what? Per capita income (B19301e1), median household income (B19013e1), or aggregate household income (B19025e1)? The agent picks the most common interpretation (median household) but doesn't always ask for clarification.

**County name matching**: The FIPS table stores counties as "Los Angeles County" with the "County" suffix. User queries like "what about LA?" or "Los Angeles" without "County" may not match. Handled partially with ILIKE matching but edge cases remain.

**Streaming disabled**: The frontend uses `run()` instead of `run_stream()` to preserve SQL in the response. This means users see a spinner for 10-20 seconds instead of progressive output. The fix requires `run_stream()` to yield structured chunks `{"type": "sql/text/status"}` — I designed this but didn't implement it within the time constraint.

---

## What I Would Do Differently

**Start deployment earlier.** I spent significant time on architecture exploration that paid off in correctness, but I should have deployed a working MVP at hour 6 and iterated from a live URL. The assignment explicitly warns about deployment issues that don't surface locally.

**Build the eval suite earlier.** I wrote tests after the core architecture was stable. Writing evals first would have caught the gpt-4o health insurance bug earlier and given me a clearer signal on what was working vs broken.

**Trust the data exploration more.** Every time I assumed something about the schema without verifying it, I was wrong. B17001 doesn't exist. COUNTY_FIPS is 3 digits not 5. The weighted median formula matters. The pattern was consistent: verify in data, then code.

---

## On Using AI Coding Tools

I used Claude extensively throughout this build — for architecture discussion, code generation, debugging, and data exploration queries. Several things are worth noting about how I used it:

I treated Claude as a senior engineering collaborator, not a code generator. I pushed back when suggestions seemed wrong, verified every data claim independently, and made final architectural decisions myself. When Claude suggested an embedding-based metadata lookup, I prototyped it, tested it against actual queries, found it unreliable for "poverty" queries, and rejected it. When Claude suggested the wrong COUNTY_FIPS join (5 digits), I verified against actual data and corrected it.

The most valuable use was data exploration — Claude helped me formulate the right SQL queries to understand the schema, but every query result came from actual Snowflake execution. No schema facts were assumed from Claude's training data.

The least valuable use was when I asked Claude to make architectural decisions without grounding them in data. The embedding vs two-step approach debate went in circles until we actually tested both against real queries.

**The meta-lesson**: AI tools are most valuable when they help you move faster through verified territory, not when they help you move faster through unverified assumptions.

---

## Summary

The core architectural insight of this submission is the two-step metadata lookup: show the LLM all 243 table titles to pick the right table, then query Snowflake for the actual columns of those specific tables. This directly addresses both assignment hints — comprehensive mapping and context awareness without hardcoding — and was discovered through actual data exploration, not assumed.

The hardest problem was vocabulary mismatch between user language and Census terminology. The solution that worked was not embeddings (tried, inconsistent), not a hardcoded map (tried, silent failures), but giving a capable LLM (GPT-4.1) complete and accurate context and letting it reason. The model upgrade from GPT-4o to GPT-4.1 was a meaningful correctness improvement, particularly for complex multi-column tables.

The most honest thing I can say about this submission: it works well for the majority of natural language Census queries, handles failure modes gracefully, and is built on verified data knowledge rather than assumptions. Its limitations — complex aggregation tables, city-level queries, streaming UX — are documented honestly and have clear production solutions.