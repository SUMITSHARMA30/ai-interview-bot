from groq import Groq
from dotenv import load_dotenv
import os
import json
import re

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- JSON CLEANER ----------------
def extract_json(text):
    """
    Extract JSON object from messy LLM output safely.
    """
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        return match.group()
    return None


def clamp_score(x):
    """
    Clamp score between 0 and 10
    """
    try:
        x = float(x)
        if x < 0:
            return 0
        if x > 10:
            return 10
        return round(x, 2)
    except:
        return 0


# ---------------- FULL INTERVIEW EVALUATOR ----------------
def evaluate_full_interview(qa_list, role="SDE", difficulty="Medium", interview_type="Technical"):
    """
    Evaluates the entire interview at the end.
    Returns a structured report JSON.
    """

    if not qa_list or len(qa_list) == 0:
        return {"error": "No interview data found. qa_list is empty."}

    # Convert Q&A list into readable transcript
    transcript = ""
    for i, qa in enumerate(qa_list, start=1):
        transcript += f"\nQ{i}: {qa.get('question','')}\n"
        transcript += f"A{i}: {qa.get('answer','')}\n"

    prompt = f"""
You are a professional MAANG interviewer evaluator.

Interview Settings:
Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Below is the complete interview transcript:

{transcript}

TASK:
Evaluate the candidate's performance question-by-question and also overall.

Return STRICT JSON ONLY in this format:

{{
  "overall_score": 0-10,
  "verdict": "Strong Hire/Hire/Maybe/No Hire",
  "summary_feedback": "...",
  "improvement_plan": "...",
  "question_wise": [
    {{
      "question": "...",
      "candidate_answer": "...",
      "score": 0-10,
      "feedback": "...",
      "improvement": "...",
      "ideal_answer": "..."
    }}
  ]
}}

IMPORTANT RULES:
- Output ONLY valid JSON (no markdown, no extra text).
- overall_score must be numeric (0-10).
- Each question must have its own score.
- Ideal answers must match role + difficulty.
- If answer is empty or wrong, score should be low.
- Verdict must be one of: Strong Hire, Hire, Maybe, No Hire.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return only valid JSON. No markdown. No explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    text = response.choices[0].message.content.strip()
    json_text = extract_json(text)

    if not json_text:
        return {"error": "Invalid JSON returned", "raw": text}

    try:
        data = json.loads(json_text)

        # Clamp overall score
        data["overall_score"] = clamp_score(data.get("overall_score", 0))

        # Ensure verdict exists
        if "verdict" not in data:
            data["verdict"] = "Unknown"

        # Ensure summary feedback exists
        if "summary_feedback" not in data:
            data["summary_feedback"] = ""

        # Ensure improvement plan exists
        if "improvement_plan" not in data:
            data["improvement_plan"] = ""

        # Ensure question_wise exists
        if "question_wise" not in data or not isinstance(data["question_wise"], list):
            data["question_wise"] = []

        # Fix each question wise block
        cleaned_qwise = []
        for item in data["question_wise"]:
            if not isinstance(item, dict):
                continue

            cleaned_qwise.append({
                "question": item.get("question", ""),
                "candidate_answer": item.get("candidate_answer", ""),
                "score": clamp_score(item.get("score", 0)),
                "feedback": item.get("feedback", ""),
                "improvement": item.get("improvement", ""),
                "ideal_answer": item.get("ideal_answer", "")
            })

        data["question_wise"] = cleaned_qwise

        return data

    except Exception as e:
        return {"error": "JSON parse failed", "raw": text, "exception": str(e)}
