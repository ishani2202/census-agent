# app/sql_generator.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.prompts import SQL_GENERATOR_PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DB = "US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC"


def format_metadata_for_prompt(metadata: dict) -> str:
    """
    Format metadata lookup results into clear context for SQL generator.
    Includes physical tables, columns, aggregation hints.
    """
    lines = []

    lines.append(f"Physical tables to query: {', '.join(metadata.get('physical_tables', []))}")
    lines.append(f"Table selection reasoning: {metadata.get('table_reasoning', '')}")
    lines.append("")
    lines.append("Verified columns to use:")

    for col in metadata.get("columns", []):
        agg = col.get("aggregation", "SUM")
        table = col.get("physical_table", "")
        desc = col.get("description", "")

        if agg == "weighted_median":
            weight = col.get("weight_column", "")
            lines.append(
                f'  - "{col["table_id"]}" in {table} | {desc} | '
                f'USE WEIGHTED MEDIAN: SUM("{col["table_id"]}" * "{weight}") / NULLIF(SUM("{weight}"), 0)'
            )
        else:
            lines.append(
                f'  - "{col["table_id"]}" in {table} | {desc} | aggregation: {agg}'
            )

    lines.append(f"\nColumn reasoning: {metadata.get('column_reasoning', '')}")
    return "\n".join(lines)


def generate_sql(question: str, plan: dict, metadata: dict, error_context: str = None) -> str:
    """
    Generate Snowflake SQL from a query plan and verified metadata.
    Returns raw SQL string only.
    If error_context provided, includes previous error for retry.
    """
    columns_context = format_metadata_for_prompt(metadata)

    error_note = ""
    if error_context:
        error_note = f"\nPREVIOUS ATTEMPT FAILED WITH ERROR: {error_context}\nFix this error in your new SQL.\n"

    user_message = f"""
User question: {question}

Query plan:
{json.dumps(plan, indent=2)}

{columns_context}

Database prefix: {DB}
{error_note}
Write the Snowflake SQL query. Return raw SQL only — no markdown, no backticks, no explanation.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": SQL_GENERATOR_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=1000
        )
        sql = response.choices[0].message.content.strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()
        return sql

    except Exception as e:
        return f"-- SQL generation error: {str(e)}"