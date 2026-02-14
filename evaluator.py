from groq import Groq
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json(text):
    """
    Extract JSON object from messy LLM output safely.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    return None


def clamp_score(x):
    try:
        x = float(x)
        if x < 0:
            return 0
        if x > 10:
            return 10
        return round(x, 2)
    except:
        return 0


def evaluate_answer(question, answer):
    prompt = f"""
You are an expert interview evaluator like MAANG interviewers.

Evaluate this candidate answer properly.

Question: {question}
Answer: {answer}

Return strictly JSON ONLY in this format:

{{
  "technical_accuracy": 0-10,
  "clarity": 0-10,
  "confidence": 0-10,
  "depth": 0-10,
  "final_score": 0-10,
  "strengths": ["...","..."],
  "weaknesses": ["...","..."],
  "feedback": "...",
  "improvement": "...",
  "ideal_answer": "..."
}}

Important rules:
- Return ONLY JSON.
- Scores must be numbers between 0 and 10.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a strict JSON generator. Return JSON only."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    text = response.choices[0].message.content.strip()

    json_text = extract_json(text)

    if not json_text:
        return {"error": "Invalid JSON returned", "raw": text}

    try:
        data = json.loads(json_text)

        # Clamp scores
        data["technical_accuracy"] = clamp_score(data.get("technical_accuracy", 0))
        data["clarity"] = clamp_score(data.get("clarity", 0))
        data["confidence"] = clamp_score(data.get("confidence", 0))
        data["depth"] = clamp_score(data.get("depth", 0))
        data["final_score"] = clamp_score(data.get("final_score", 0))

        # Ensure strengths/weaknesses exist
        if "strengths" not in data or not isinstance(data["strengths"], list):
            data["strengths"] = []

        if "weaknesses" not in data or not isinstance(data["weaknesses"], list):
            data["weaknesses"] = []

        return data

    except Exception as e:
        return {"error": "JSON parse failed", "raw": text, "exception": str(e)}
