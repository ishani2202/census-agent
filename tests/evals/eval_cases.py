# tests/evals/eval_cases.py
EVAL_CASES = [
    {
        "id": "income_california",
        "question": "What is the median household income in California?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["california", "income"],
        "sql_should_contain": ["B19013", "06"],
        "answer_should_not_contain": ["trouble", "error", "cannot"]
    },
    {
        "id": "population_texas",
        "question": "What is the total population of Texas?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["texas"],
        "sql_should_contain": ["48"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "poverty_texas",
        "question": "What is the poverty rate in Texas?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["texas", "poverty"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "rent_new_york",
        "question": "What is the median rent in New York?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["new york", "rent"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "education_california",
        "question": "What percentage of people in California have a college degree?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["california"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "home_value_florida",
        "question": "What is the median home value in Florida?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["florida"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "state_normalization",
        "question": "What is the total population of California?",
        "should_be_blocked": False,
        "should_succeed": True,
        "sql_should_contain": ["06"],
        "sql_should_not_contain": ["California"]
    },
    {
        "id": "guardrail_recipe",
        "question": "What is the recipe for pasta?",
        "should_be_blocked": True,
        "should_succeed": False
    },
    {
        "id": "guardrail_individual",
        "question": "What is the net worth of Elon Musk?",
        "should_be_blocked": True,
        "should_succeed": False
    },
    {
        "id": "guardrail_foreign_country",
        "question": "What is the population of France?",
        "should_be_blocked": True,
        "should_succeed": False
    },
    {
        "id": "guardrail_financial_advice",
        "question": "Should I buy a house in California right now?",
        "should_be_blocked": True,
        "should_succeed": False
    },
    {
        "id": "city_level_graceful",
        "question": "What is the population of Austin city?",
        "should_be_blocked": False,
        "should_succeed": False,
        "answer_should_contain": ["city", "county"]
    },
    {
        "id": "wrong_year_defaults",
        "question": "What was the median income in California in 2015?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["california"]
    },
    {
        "id": "median_discloses_approximation",
        "question": "What is the median household income in Texas?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain_any": ["weighted", "approximation", "estimate"],
        "answer_should_not_contain": ["trouble", "error"]
    },
    {
        "id": "year_comparison",
        "question": "How did median income in California change between 2019 and 2020?",
        "should_be_blocked": False,
        "should_succeed": True,
        "answer_should_contain": ["2019", "2020"],
        "answer_should_not_contain": ["trouble", "error"]
    }
]