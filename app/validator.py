# app/validator.py
import sqlglot

# Tables that exist in our database
VALID_TABLES = {
    "2019_CBG_B01", "2019_CBG_B02", "2019_CBG_B03", "2019_CBG_B07",
    "2019_CBG_B08", "2019_CBG_B09", "2019_CBG_B11", "2019_CBG_B12",
    "2019_CBG_B14", "2019_CBG_B15", "2019_CBG_B16", "2019_CBG_B17",
    "2019_CBG_B19", "2019_CBG_B20", "2019_CBG_B21", "2019_CBG_B22",
    "2019_CBG_B23", "2019_CBG_B24", "2019_CBG_B25", "2019_CBG_B27",
    "2019_CBG_B28", "2019_CBG_B29", "2019_CBG_B99",
    "2020_CBG_B01", "2020_CBG_B02", "2020_CBG_B03", "2020_CBG_B07",
    "2020_CBG_B08", "2020_CBG_B09", "2020_CBG_B11", "2020_CBG_B12",
    "2020_CBG_B14", "2020_CBG_B15", "2020_CBG_B16", "2020_CBG_B17",
    "2020_CBG_B19", "2020_CBG_B20", "2020_CBG_B21", "2020_CBG_B22",
    "2020_CBG_B23", "2020_CBG_B24", "2020_CBG_B25", "2020_CBG_B27",
    "2020_CBG_B28", "2020_CBG_B29", "2020_CBG_B99",
    "2019_METADATA_CBG_FIELD_DESCRIPTIONS", "2019_METADATA_CBG_FIPS_CODES",
    "2019_METADATA_CBG_GEOGRAPHIC_DATA", "2020_METADATA_CBG_FIELD_DESCRIPTIONS",
    "2020_METADATA_CBG_FIPS_CODES", "2020_METADATA_CBG_GEOGRAPHIC_DATA",
    "2019_CBG_C02", "2019_CBG_C15", "2019_CBG_C16",
"2019_CBG_C17", "2019_CBG_C21", "2019_CBG_C24",
"2020_CBG_C02", "2020_CBG_C15", "2020_CBG_C16",
"2020_CBG_C17", "2020_CBG_C21", "2020_CBG_C24"

}

FORBIDDEN_KEYWORDS = [
    "DROP", "DELETE", "INSERT", "UPDATE", "CREATE",
    "ALTER", "TRUNCATE", "MERGE", "REPLACE"
]

def check_syntax(sql: str) -> dict:
    """
    Parse SQL using sqlglot to catch syntax errors before hitting Snowflake.
    Returns {"valid": bool, "error": str or None}
    """
    try:
        sqlglot.parse(sql, dialect="snowflake")
        return {"valid": True, "error": None}
    except sqlglot.errors.ParseError as e:
        return {"valid": False, "error": str(e)}

def check_safety(sql: str) -> dict:
    """
    Reject any SQL that contains write or destructive operations.
    Returns {"safe": bool, "error": str or None}
    """
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in sql_upper:
            return {
                "safe": False,
                "error": f"SQL contains forbidden keyword: {keyword}"
            }
    return {"safe": True, "error": None}

def ensure_limit(sql: str) -> str:
    """
    Inject LIMIT 1000 if no LIMIT clause exists.
    Protects against accidental full table scans.
    """
    if "LIMIT" not in sql.upper():
        sql = sql.rstrip(";") + "\nLIMIT 1000;"
    return sql

def validate_sql(sql: str) -> dict:
    """
    Main entry point. Runs all checks in order.
    Returns {"valid": bool, "sql": str, "error": str or None}
    """
    # Check 0: Reject empty SQL
    if not sql or not sql.strip():
        return {
            "valid": False,
            "sql": sql,
            "error": "empty SQL — generation failed"
        }
    # Check 1: Safety first
    safety = check_safety(sql)
    if not safety["safe"]:
        return {
            "valid": False,
            "sql": sql,
            "error": safety["error"]
        }

    # Check 2: Syntax check
    syntax = check_syntax(sql)
    if not syntax["valid"]:
        return {
            "valid": False,
            "sql": sql,
            "error": f"SQL syntax error: {syntax['error']}"
        }

    # Check 3: Ensure LIMIT exists
    sql = ensure_limit(sql)

    return {
        "valid": True,
        "sql": sql,
        "error": None
    }