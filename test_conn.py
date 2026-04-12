import json
from app.db import test_connection, execute_query

print("Testing connection...")
print(test_connection())

print("\nTesting query...")
result = execute_query("""
    SELECT COUNT(*) as cnt 
    FROM "2019_METADATA_CBG_FIELD_DESCRIPTIONS"
""")
print(result)

from app.metadata import get_columns_for_topics

print("\nTesting metadata lookup...")
result = get_columns_for_topics(["income"])
print(result)

from app.planner import make_plan, normalize_state

print("\nTesting state normalization...")
print(normalize_state("California"))   # should print CA
print(normalize_state("new york"))     # should print NY
print(normalize_state("TX"))           # should print TX

print("\nTesting planner...")
plan = make_plan("What is the median household income in California?")
print(json.dumps(plan, indent=2))

from app.sql_generator import generate_sql

print("\nTesting SQL generator...")
plan = {
    "topics": ["income"],
    "tables_needed": ["2019_CBG_B19"],
    "geography_type": "state",
    "location": "CA",
    "location_type": "state",
    "year": "2019",
    "aggregation": "AVG",
    "is_comparison": False,
    "is_answerable": True,
    "ambiguities": []
}
columns = {
    "income": {
        "selected_columns": [{
            "table_id": "B19013e1",
            "table_number": "B19013",
            "description": "Median household income",
            "table": "2019_CBG_B19"
        }],
        "reasoning": "B19013e1 is median household income"
    }
}
sql = generate_sql(plan, columns)
print(sql)

from app.db import execute_query

print("\nTesting generated SQL against Snowflake...")
result = execute_query(sql)
print(result)

from app.validator import validate_sql

print("\nTesting validator...")

# Should pass
good_sql = 'SELECT AVG("B19013e1") FROM "2019_CBG_B19" WHERE STATE = \'CA\''
print(validate_sql(good_sql))

# Should fail - forbidden keyword
bad_sql = 'DROP TABLE "2019_CBG_B19"'
print(validate_sql(bad_sql))

# Should inject LIMIT
no_limit_sql = 'SELECT "B19013e1" FROM "2019_CBG_B19"'
print(validate_sql(no_limit_sql))

from app.synthesizer import synthesize
from decimal import Decimal

print("\nTesting synthesizer...")
answer = synthesize(
    question="What is the median household income in California?",
    plan={
        "location": "CA",
        "ambiguities": ["user said California - interpreted as state CA"]
    },
    sql="SELECT AVG...",
    query_result={
        "columns": ["Average_Median_Household_Income"],
        "rows": [(Decimal("84692.128972"),)],
        "error": None,
        "row_count": 1
    }
)
print(answer)

from app.agent import run

print("\nTesting full agent loop...")

# Happy path
response = run("What is the median household income in California?")
print("Answer:", response["answer"])
print("SQL:", response["sql"])

# Guardrail test
response2 = run("What is the recipe for pasta?")
print("\nGuardrail test:", response2["answer"])

# Unanswerable test
response3 = run("What is the population of Austin city?")
print("\nCity test:", response3["answer"])