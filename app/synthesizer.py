# app/synthesizer.py
import os
from openai import OpenAI
from decimal import Decimal
from dotenv import load_dotenv
from app.prompts import SYNTHESIZER_PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_results_for_prompt(columns: list, rows: list) -> str:
    """
    Format raw Snowflake results into a readable table for the LLM.
    Converts Decimal types to float for clean display.
    """
    if not columns or not rows:
        return "No results returned."

    clean_rows = []
    for row in rows:
        clean_row = []
        for val in row:
            if isinstance(val, Decimal):
                clean_row.append(float(round(val, 2)))
            else:
                clean_row.append(val)
        clean_rows.append(clean_row)

    lines = [" | ".join(str(c) for c in columns)]
    lines.append("-" * 60)
    for row in clean_rows[:20]:
        lines.append(" | ".join(str(v) for v in row))

    if len(rows) > 20:
        lines.append(f"... and {len(rows) - 20} more rows")

    return "\n".join(lines)


def synthesize(question: str, plan: dict, sql: str, query_result: dict) -> str:
    """
    Turn raw query results into a natural language answer.
    Strictly grounded — only references numbers from query results.
    """
    if query_result.get("error"):
        error_msg = query_result["error"]
        if "invalid identifier" in error_msg.lower():
            return (
                "I had trouble querying that data — "
                "a column name in the generated SQL was incorrect. "
                "Could you try rephrasing your question?"
            )
        elif "does not exist" in error_msg.lower():
            return (
                "I had trouble finding that data — "
                "the table or column referenced doesn't exist. "
                "Could you try rephrasing your question?"
            )
        elif "timeout" in error_msg.lower():
            return (
                "The query took too long to complete. "
                "Try asking about a more specific region or topic."
            )
        else:
            return (
                f"I had trouble retrieving that data. "
                f"Here's what went wrong: {error_msg}"
            )

    if not query_result.get("rows"):
        return (
            "I couldn't find any data matching your question in the "
            "US Census dataset. This could mean the geographic area "
            "or demographic category isn't available at this level of detail."
        )

    results_text = format_results_for_prompt(
        query_result["columns"],
        query_result["rows"]
    )

    ambiguities = plan.get("ambiguities", [])
    ambiguity_note = ""
    if ambiguities:
        ambiguity_note = f"\nNote: {'; '.join(ambiguities)}"

    user_message = f"""
User question: {question}
{ambiguity_note}

Query results:
{results_text}

Answer the user's question based strictly on these results.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYNTHESIZER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"I found the data but had trouble formatting the response: {str(e)}"


def synthesize_stream(question: str, plan: dict, sql: str, query_result: dict):
    """
    Streaming version. Yields response chunks as they arrive.
    """
    if query_result.get("error") or not query_result.get("rows"):
        yield synthesize(question, plan, sql, query_result)
        return

    results_text = format_results_for_prompt(
        query_result["columns"],
        query_result["rows"]
    )

    ambiguities = plan.get("ambiguities", [])
    ambiguity_note = ""
    if ambiguities:
        ambiguity_note = f"\nNote: {'; '.join(ambiguities)}"

    user_message = f"""
User question: {question}
{ambiguity_note}

Query results:
{results_text}

Answer the user's question based strictly on these results.
"""

    try:
        stream = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYNTHESIZER_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0.3,
            max_tokens=500,
            stream=True
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    except Exception as e:
        yield f"I found the data but had trouble formatting the response: {str(e)}"