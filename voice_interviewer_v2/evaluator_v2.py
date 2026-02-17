import os
import json
import re
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json(text):
    if not text:
        return None

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    try:
        return json.loads(text)
    except:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            return None

    return None


def evaluate_interview(conversation_history):
    prompt = f"""
You are a strict MAANG interview evaluator.

Conversation transcript:
{conversation_history}

Return STRICT JSON ONLY:

{{
  "overall_score": 0,
  "verdict": "HIRE" OR "NO_HIRE",
  "summary_feedback": "string",
  "strengths": ["string"],
  "weaknesses": ["string"],
  "improvement_plan": "string"
}}
Rules:
- overall_score must be 0 to 10
- JSON must be valid
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    raw = response.choices[0].message.content.strip()
    parsed = extract_json(raw)

    if parsed is None:
        parsed = {
            "overall_score": 0,
            "verdict": "NO_HIRE",
            "summary_feedback": "Evaluation failed.",
            "strengths": [],
            "weaknesses": [],
            "improvement_plan": "Retry interview."
        }

    return parsed
