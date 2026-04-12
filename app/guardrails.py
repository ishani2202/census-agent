# app/guardrails.py
import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from app.prompts import GUARDRAIL_PROMPT

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def check_guardrail(question: str, history: list = []) -> dict:
    """
    Check if a question is appropriate for the census agent.
    Includes recent history so follow-up questions get context.
    Returns {"allowed": bool, "reason": str}
    Fails open on error — never blocks legitimate questions.
    """
    # Build context from recent history
    context = ""
    if history:
        last = history[-1]
        context = f"\nPrevious question: {last.get('user', '')}"

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": GUARDRAIL_PROMPT},
                {"role": "user", "content": f"{question}{context}"}
            ],
            temperature=0,
            max_tokens=100
        )
        raw = response.choices[0].message.content.strip()
        result = json.loads(raw)
        return result

    except json.JSONDecodeError:
        return {"allowed": True, "reason": "classifier parse error — defaulting to allowed"}
    except Exception as e:
        print(f"Guardrail error: {e}")
        return {"allowed": True, "reason": f"classifier error — defaulting to allowed"}