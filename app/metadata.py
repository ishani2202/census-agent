# app/metadata.py
# Two-step metadata lookup:
# Step 1: TABLE SELECTOR — LLM picks relevant physical tables from full registry
# Step 2: COLUMN LOOKUP — query metadata for those tables, LLM picks exact columns

import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.db import execute_query
from app.prompts import TABLE_SELECTOR_PROMPT, COLUMN_SELECTOR_PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def select_tables(question: str, plan: dict) -> dict:
    """
    Step 1: LLM picks relevant physical tables from full 243-table registry.
    Returns {"physical_tables": [...], "table_numbers": [...], "reasoning": "..."}
    """
    user_message = f"""
User question: {question}

Query plan:
{json.dumps(plan, indent=2)}

Which Census tables contain the data needed to answer this question?
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": TABLE_SELECTOR_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=500
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)

        if not result.get("physical_tables"):
            return {
                "physical_tables": [],
                "table_numbers": [],
                "reasoning": "no tables selected",
                "error": "table selector returned no tables"
            }
        return result

    except json.JSONDecodeError:
        return {
            "physical_tables": [],
            "table_numbers": [],
            "reasoning": "parse error",
            "error": "failed to parse table selector response"
        }
    except Exception as e:
        return {
            "physical_tables": [],
            "table_numbers": [],
            "reasoning": str(e),
            "error": str(e)
        }


def lookup_columns(table_numbers: list, year: str = "2019") -> dict:
    """
    Step 2: Query Snowflake metadata for exact column names.
    Returns all field levels for full structural context.
    Excludes margin of error columns and allocation tables.
    """
    if not table_numbers:
        return {"columns": None, "rows": [], "error": "no table numbers provided"}

    quoted = ", ".join(f"'{t}'" for t in table_numbers)

    sql = f"""
        SELECT 
            "TABLE_ID",
            "TABLE_NUMBER",
            "TABLE_TITLE",
            "FIELD_LEVEL_2",
            "FIELD_LEVEL_3",
            "FIELD_LEVEL_4",
            "FIELD_LEVEL_5",
            "FIELD_LEVEL_6"
        FROM "{year}_METADATA_CBG_FIELD_DESCRIPTIONS"
        WHERE "TABLE_NUMBER" IN ({quoted})
        AND "TABLE_ID" NOT LIKE '%m%'
        AND "TABLE_NUMBER" NOT LIKE 'B99%'
        ORDER BY "TABLE_NUMBER", "TABLE_ID"
        LIMIT 200
    """
    return execute_query(sql)


def format_columns_for_prompt(result: dict) -> str:
    """
    Format raw metadata rows into readable text for the column selector LLM.
    Includes all field levels for full structural context.
    """
    if result.get("error") or not result.get("rows"):
        return "No metadata found."

    lines = []
    for row in result["rows"]:
        table_id = row[0]
        table_number = row[1]
        levels = [row[i] for i in range(3, 8) if row[i]]
        description = " > ".join(levels)
        lines.append(f"{table_id} ({table_number}) | {description}")

    return "\n".join(lines)


def select_columns(question: str, plan: dict, metadata_text: str) -> dict:
    """
    Step 3: LLM picks exact columns from full metadata structure.
    Returns structured column selection with aggregation hints.
    """
    user_message = f"""
User question: {question}

Query plan:
{json.dumps(plan, indent=2)}

Available columns from selected tables:
{metadata_text}

Which specific columns are needed to answer this question?
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": COLUMN_SELECTOR_PROMPT},
                {"role": "user", "content": user_message}
            ],
            temperature=0,
            max_tokens=1200
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        return json.loads(raw)

    except json.JSONDecodeError:
        return {"columns": [], "reasoning": "parse error"}
    except Exception as e:
        return {"columns": [], "reasoning": str(e)}


def get_metadata_for_question(question: str, plan: dict) -> dict:
    """
    Main entry point. Full two-step metadata lookup.
    Handles year comparisons by using 2019 metadata (schemas are identical).
    For comparisons, returns both 2019 and 2020 physical tables.
    """
    year_raw = plan.get("year", "2019")
    is_comparison = plan.get("is_comparison", False)

    # Always use 2019 for metadata lookup — schemas are identical
    # We verified: 2019 has 8120 fields, 2020 has 8164 — same structure
    metadata_year = "2019"

    # Step 1: Select relevant tables
    table_selection = select_tables(question, plan)

    if table_selection.get("error") or not table_selection.get("table_numbers"):
        return {
            "error": table_selection.get("error", "no tables found"),
            "physical_tables": [],
            "columns": [],
            "metadata_text": "",
            "table_reasoning": table_selection.get("reasoning", "")
        }

    # Step 2: Look up columns using 2019 metadata always
    raw_metadata = lookup_columns(table_selection["table_numbers"], metadata_year)

    # Step 3: Format and select columns
    metadata_text = format_columns_for_prompt(raw_metadata)
    column_selection = select_columns(question, plan, metadata_text)

    # Step 4: Build physical tables list
    # For comparisons, include BOTH 2019 and 2020 versions
    physical_tables = table_selection["physical_tables"]
    if is_comparison:
        both_years = []
        for table in physical_tables:
            # Normalize to 2019 first
            t2019 = table.replace("2020_CBG", "2019_CBG")
            t2020 = t2019.replace("2019_CBG", "2020_CBG")
            if t2019 not in both_years:
                both_years.append(t2019)
            if t2020 not in both_years:
                both_years.append(t2020)
        physical_tables = both_years

    return {
        "error": None,
        "physical_tables": physical_tables,
        "table_numbers": table_selection["table_numbers"],
        "table_reasoning": table_selection["reasoning"],
        "columns": column_selection.get("columns", []),
        "column_reasoning": column_selection.get("reasoning", ""),
        "metadata_text": metadata_text,
        "is_comparison": is_comparison,
        "year": year_raw
    }