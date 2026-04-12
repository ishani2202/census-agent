# tests/evals/eval_suite.py
# Runs behavioral evals against the agent
# Usage: python tests/evals/eval_suite.py

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.agent import run
from tests.evals.eval_cases import EVAL_CASES


def run_evals():
    results = []
    print(f"Running {len(EVAL_CASES)} evals...\n")

    for eval_case in EVAL_CASES:
        print(f"[{eval_case['id']}] {eval_case['question'][:60]}...")

        try:
            response = run(eval_case["question"])
            answer = response.get("answer", "").lower()
            sql = (response.get("sql") or "").lower()
            blocked = response.get("blocked", False)

            failures = []

            # Check blocked status
            if eval_case.get("should_be_blocked"):
                if not blocked:
                    failures.append("Should have been blocked but wasn't")
            else:
                if blocked and eval_case.get("should_succeed"):
                    failures.append("Should not have been blocked")

            # Check answer contains expected strings
            for term in eval_case.get("answer_should_contain", []):
                if term.lower() not in answer:
                    failures.append(f"Answer missing: '{term}'")

            # Check answer contains any of these
            any_terms = eval_case.get("answer_should_contain_any", [])
            if any_terms and not any(t.lower() in answer for t in any_terms):
                failures.append(f"Answer missing any of: {any_terms}")

            # Check answer does not contain
            for term in eval_case.get("answer_should_not_contain", []):
                if term.lower() in answer:
                    failures.append(f"Answer contains unwanted: '{term}'")

            # Check SQL contains expected strings
            for term in eval_case.get("sql_should_contain", []):
                if term.lower() not in sql:
                    failures.append(f"SQL missing: '{term}'")

            # Check SQL does not contain
            for term in eval_case.get("sql_should_not_contain", []):
                if term.lower() in sql:
                    failures.append(f"SQL contains unwanted: '{term}'")

            passed = len(failures) == 0
            status = "PASS" if passed else "FAIL"
            print(f"  {status}")
            if failures:
                for f in failures:
                    print(f"    - {f}")

            results.append({
                "id": eval_case["id"],
                "passed": passed,
                "failures": failures,
                "answer": response.get("answer", "")[:100]
            })

        except Exception as e:
            print(f"  ERROR: {str(e)}")
            results.append({
                "id": eval_case["id"],
                "passed": False,
                "failures": [f"Exception: {str(e)}"],
                "answer": ""
            })

    # Summary
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    score = (passed / total) * 100

    print(f"\n{'='*50}")
    print(f"Eval score: {passed}/{total} ({score:.0f}%)")
    print(f"{'='*50}")

    if passed < total:
        print("\nFailed evals:")
        for r in results:
            if not r["passed"]:
                print(f"  [{r['id']}]: {r['failures']}")

    return results


if __name__ == "__main__":
    run_evals()