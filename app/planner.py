# app/planner.py
import json
import os
from openai import OpenAI
from dotenv import load_dotenv
from app.prompts import PLANNER_PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# State name to abbreviation mapping
STATE_MAP = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC",
    "washington dc": "DC", "washington d.c.": "DC"
}

def normalize_state(location: str) -> str:
    """
    Convert full state name to abbreviation.
    Returns original string if already an abbreviation or not found.
    """
    if not location:
        return location
    
    # Already an abbreviation
    if len(location) == 2 and location.upper() in STATE_MAP.values():
        return location.upper()
    
    # Full name lookup
    normalized = STATE_MAP.get(location.lower().strip())
    return normalized if normalized else location

def make_plan(question: str, history: list = []) -> dict:
    """
    Convert a natural language question into a structured query plan.
    Returns a dict with topics, tables, geography, year, etc.
    """
    # Build conversation context
    messages = [{"role": "system", "content": PLANNER_PROMPT}]
    
    # Add recent history for context
    for turn in history[-5:]:
        messages.append({"role": "user", "content": turn["user"]})
        messages.append({"role": "assistant", "content": json.dumps(turn["plan"])})
    
    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0,
            max_tokens=500
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        plan = json.loads(raw)

        # Normalize state name regardless of what LLM returned
        if plan.get("location"):
            plan["location"] = normalize_state(plan["location"])

        return plan

    except json.JSONDecodeError:
        return {
            "is_answerable": False,
            "error": "Failed to parse query plan",
            "topics": [],
            "tables_needed": [],
            "geography_type": "unknown",
            "location": None,
            "year": "2019",
            "aggregation": None,
            "is_comparison": False,
            "ambiguities": []
        }
    except Exception as e:
        return {
            "is_answerable": False,
            "error": str(e),
            "topics": [],
            "tables_needed": [],
            "geography_type": "unknown",
            "location": None,
            "year": "2019",
            "aggregation": None,
            "is_comparison": False,
            "ambiguities": []
        }