import os
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

def get_connection():
    required = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing required environment variables: {missing}")
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        login_timeout=30
    )

def execute_query(sql: str, timeout: int = 45) -> dict:
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(f"ALTER SESSION SET STATEMENT_TIMEOUT_IN_SECONDS = {timeout}")
        cursor.execute(sql)
        rows = cursor.fetchmany(500)
        columns = [desc[0] for desc in cursor.description]
        return {
            "columns": columns,
            "rows": rows,
            "error": None,
            "row_count": len(rows)
        }
    except Exception as e:
        return {
            "columns": None,
            "rows": None,
            "error": str(e),
            "row_count": 0
        }
    finally:
        if conn:
            conn.close()

def test_connection() -> bool:
    result = execute_query("SELECT 1 AS test")
    return result["error"] is None