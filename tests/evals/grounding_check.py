# tests/evals/grounding_check.py
# Grounding check — verifies the synthesizer used actual SQL results.
# For each question: runs agent, executes the SQL it generated,
# then checks if the answer number matches the SQL result within 5%.
#
# Usage: python tests/evals/grounding_check.py

import sys
import os
import re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent import run
from app.db import execute_query

GROUNDING_CASES = [
    {"id": "CA_median_income",     "question": "What is the median household income in California?"},
    {"id": "TX_median_income",     "question": "What is the median household income in Texas?"},
    {"id": "NY_median_income",     "question": "What is the median household income in New York?"},
    {"id": "US_population",        "question": "What is the total population of the United States?"},
    {"id": "CA_population",        "question": "What is the total population of California?"},
    {"id": "US_health_insurance",  "question": "What percentage of Americans have health insurance?"},
    {"id": "LA_county_pop",        "question": "What is the population of Los Angeles County?"},
    {"id": "NY_median_rent",       "question": "What is the median rent in New York?"},
    {"id": "FL_median_rent",       "question": "What is the median rent in Florida?"},
    {"id": "CA_home_value",        "question": "What is the median home value in California?"},
    {"id": "US_veterans",          "question": "How many veterans are there in the United States?"},
    {"id": "manhattan_income",     "question": "What is the median household income in New York County?"},
    {"id": "CA_income_2020",       "question": "What was the median household income in California in 2020?"},
    {"id": "PR_population",        "question": "What is the population of Puerto Rico?"},
    {"id": "DC_median_income",     "question": "What is the median household income in Washington DC?"},
]


def extract_number(text: str) -> float:
    """Extract primary metric number from text. Excludes years."""
    if not text:
        return None

    t = text.lower()

    # Billions
    m = re.search(r'([\d,]+\.?\d*)\s*billion', t)
    if m:
        try:
            return float(m.group(1).replace(',', '')) * 1_000_000_000
        except: pass

    # Millions
    m = re.search(r'([\d,]+\.?\d*)\s*million', t)
    if m:
        try:
            return float(m.group(1).replace(',', '')) * 1_000_000
        except: pass

    # Dollar amounts
    dollars = re.findall(r'\$([\d,]+(?:\.\d+)?)', text)
    if dollars:
        try:
            return max(float(d.replace(',', '')) for d in dollars)
        except: pass

    # Percentages
    m = re.search(r'([\d,]+\.?\d*)\s*%', text)
    if m:
        try:
            return float(m.group(1).replace(',', ''))
        except: pass

    # Plain numbers — exclude years
    candidates = []
    for n in re.findall(r'[\d,]+(?:\.\d+)?', text):
        try:
            val = float(n.replace(',', ''))
            if val > 10 and not (2015 <= val <= 2025):
                candidates.append(val)
        except: pass

    if not candidates:
        return None
    return max(candidates) if max(candidates) > 100000 else min(candidates)


def extract_from_result(columns, rows) -> float:
    """Extract primary number from SQL result."""
    if not rows or not columns:
        return None

    # Single value
    if len(rows) == 1 and len(rows[0]) == 1:
        try:
            return float(str(rows[0][0]).replace(',', ''))
        except: return None

    # Multiple columns — prefer metric-named columns
    if len(rows) == 1:
        metric_keywords = ["rate", "pct", "percent", "median", "avg",
                          "income", "rent", "value", "age", "poverty"]
        for i, val in enumerate(rows[0]):
            if val is None: continue
            col = columns[i].lower() if i < len(columns) else ""
            if any(k in col for k in metric_keywords):
                try:
                    return float(str(val).replace(',', ''))
                except: pass

        # Fall back to smallest positive number (rates < counts)
        candidates = []
        for val in rows[0]:
            if val is None: continue
            try:
                f = float(str(val).replace(',', ''))
                if f > 0: candidates.append(f)
            except: pass
        return min(candidates) if candidates else None

    return None


def within_tolerance(got, expected, tol=5.0):
    if got is None or expected is None or expected == 0:
        return False
    return abs(got - expected) / abs(expected) * 100 <= tol


def run_grounding_checks():
    print("=" * 65)
    print("  GROUNDING CHECK")
    print("  Does the answer match what the SQL actually returned?")
    print("  Tolerance: 5% | Cases: 15 | Model: gpt-4.1")
    print("=" * 65)
    print()

    results = []

    for case in GROUNDING_CASES:
        print(f"  [{case['id']}]")
        print(f"  {case['question']}")

        passed = False
        reason = ""
        answer_num = None
        sql_num = None

        try:
            # Run agent
            response = run(case["question"])
            answer = response.get("answer", "")
            sql = response.get("sql")

            if response.get("blocked"):
                reason = "SKIP — blocked"
                print(f"  {reason}\n")
                results.append({**case, "passed": False, "reason": reason})
                continue

            if not sql:
                reason = "SKIP — no SQL"
                print(f"  {reason}")
                print(f"  Answer: {answer[:100]}\n")
                results.append({**case, "passed": False, "reason": reason})
                continue

            # Execute agent SQL
            result = execute_query(sql)
            if result.get("error"):
                reason = f"SQL ERROR — {result['error'][:60]}"
                print(f"  {reason}\n")
                results.append({**case, "passed": False, "reason": reason})
                continue

            sql_num = extract_from_result(result["columns"], result["rows"])
            answer_num = extract_number(answer)

            if sql_num is None:
                reason = "SKIP — can't extract number from SQL result"
                print(f"  {reason}\n")
                results.append({**case, "passed": False, "reason": reason})
                continue

            if answer_num is None:
                reason = "FAIL — no number in answer"
                print(f"  SQL result:  N/A")
                print(f"  Answer num:  None")
                print(f"  ❌ {reason}")
                print(f"  Answer: {answer[:120]}\n")
                results.append({**case, "passed": False, "reason": reason})
                continue

            # Compare with scaling fallbacks
            passed = within_tolerance(answer_num, sql_num)
            if not passed:
                passed = within_tolerance(answer_num, sql_num * 100)
            if not passed:
                passed = within_tolerance(answer_num * 1_000_000, sql_num)

            diff = abs(answer_num - sql_num) / abs(sql_num) * 100 if sql_num else 999
            status = "✅ PASS" if passed else "❌ FAIL"
            reason = f"diff {diff:.1f}%" if not passed else "ok"

            print(f"  SQL result:  {sql_num:,.2f}")
            print(f"  Answer num:  {answer_num:,.2f}")
            print(f"  {status}")
            if not passed:
                print(f"  Answer: {answer[:120]}")

        except Exception as e:
            reason = f"ERROR — {str(e)[:60]}"
            print(f"  {reason}")

        print()
        results.append({**case, "passed": passed, "reason": reason,
                       "sql_num": sql_num, "answer_num": answer_num})

    # Summary
    passed_count = sum(1 for r in results if r["passed"])
    total = len(results)

    print("=" * 65)
    print(f"  GROUNDING SCORE: {passed_count}/{total} ({100*passed_count//total if total else 0}%)")
    print()
    print("  Pass = answer number within 5% of actual SQL result")
    print("  Fail = synthesizer may have used training data or wrong SQL")
    print()

    failures = [r for r in results if not r["passed"]]
    if failures:
        print("  Failures:")
        for r in failures:
            print(f"    [{r['id']}] {r.get('reason', '')}")

    print("=" * 65)
    return results


if __name__ == "__main__":
    run_grounding_checks()