# app/agent.py
# Orchestrator — ties all layers together

import time
from app.guardrails import check_guardrail
from app.planner import make_plan
from app.metadata import get_metadata_for_question
from app.sql_generator import generate_sql
from app.validator import validate_sql
from app.synthesizer import synthesize, synthesize_stream
from app.db import execute_query

MAX_RETRIES = 1


def run(question: str, history: list = []) -> dict:
    """
    Full agent loop — non-streaming version.
    Returns dict with answer, sql, plan, error fields.
    """
    t_start = time.time()

    # Step 1: Guardrail
    guardrail = check_guardrail(question, history)
    if not guardrail.get("allowed", True):
        return {
            "answer": (
                "I can only answer questions about US Census demographics. "
                "Try asking about population, income, housing, education, "
                "or other demographic topics."
            ),
            "sql": None, "plan": None, "blocked": True, "error": None
        }

    # Step 2: Plan
    plan = make_plan(question, history)

    if not plan.get("is_answerable", True):
        return {
            "answer": (
                "I wasn't able to answer that with the available Census data. "
                "Data is available at the state and county level only — "
                "city-level data is not available. "
                "Try asking about a state or county instead."
            ),
            "sql": None, "plan": plan, "blocked": False, "error": None
        }

    # Step 3: Metadata lookup
    metadata = get_metadata_for_question(question, plan)

    if metadata.get("error") or not metadata.get("columns"):
        return {
            "answer": (
                "I had trouble identifying the right Census data for your question. "
                "Could you try rephrasing it?"
            ),
            "sql": None, "plan": plan, "blocked": False,
            "error": metadata.get("error", "no columns found")
        }

    # Step 4: Generate SQL
    sql = generate_sql(question, plan, metadata)

    # Step 5: Validate + retry once with error context
    for attempt in range(MAX_RETRIES + 1):
        validation = validate_sql(sql)

        if not validation["valid"]:
            if attempt < MAX_RETRIES:
                sql = generate_sql(question, plan, metadata,
                                   error_context=validation["error"])
                continue
            else:
                return {
                    "answer": "I had trouble generating a valid query. Could you try rephrasing?",
                    "sql": sql, "plan": plan, "blocked": False,
                    "error": validation["error"]
                }

        # Step 6: Execute
        sql = validation["sql"]
        result = execute_query(sql)

        # Step 7: Synthesize
        answer = synthesize(question, plan, sql, result)

        print(f"[timing] TOTAL: {time.time()-t_start:.2f}s")

        return {
            "answer": answer,
            "sql": sql,
            "plan": plan,
            "blocked": False,
            "error": result.get("error")
        }


def run_stream(question: str, history: list = []):
    """
    Streaming version. Yields text chunks for frontend.
    """
    # Step 1: Guardrail
    guardrail = check_guardrail(question, history)
    if not guardrail.get("allowed", True):
        yield (
            "I can only answer questions about US Census demographics. "
            f"{guardrail.get('reason', '')}."
        )
        return

    # Step 2: Plan
    plan = make_plan(question, history)

    if not plan.get("is_answerable", True):
        yield (
            "I wasn't able to answer that with the available Census data. "
            "Data is available at the state and county level only — "
            "city-level data is not available."
        )
        return

    # Step 3: Metadata lookup
    metadata = get_metadata_for_question(question, plan)

    if metadata.get("error") or not metadata.get("columns"):
        yield (
            "I had trouble identifying the right Census data for your question. "
            "Could you try rephrasing it?"
        )
        return

    # Step 4: Generate SQL
    sql = generate_sql(question, plan, metadata)

    # Step 5: Validate — retry once with error context
    validation = validate_sql(sql)
    if not validation["valid"]:
        sql = generate_sql(question, plan, metadata,
                           error_context=validation["error"])
        validation = validate_sql(sql)
        if not validation["valid"]:
            yield "I had trouble generating a valid query. Could you try rephrasing?"
            return

    # Step 6: Execute
    sql = validation["sql"]
    result = execute_query(sql)

    # Step 7: Stream synthesis
    yield from synthesize_stream(question, plan, sql, result)