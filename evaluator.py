from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def extract_json(text: str):
    if not text:
        return None

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        return None

    return text[start:end+1].strip()


def clamp_score(x):
    try:
        x = float(x)
        return max(0, min(10, round(x, 2)))
    except:
        return 0


def normalize_verdict(verdict: str):
    if not verdict:
        return "Maybe"

    verdict = verdict.strip().lower()

    if "strong" in verdict and "hire" in verdict:
        return "Strong Hire"
    if verdict == "hire" or "yes" in verdict:
        return "Hire"
    if "no" in verdict or "reject" in verdict:
        return "No Hire"
    if "maybe" in verdict:
        return "Maybe"

    return "Maybe"


def evaluate_full_interview(qa_list, role="SDE", difficulty="Medium", interview_type="Technical"):

    if not qa_list or len(qa_list) == 0:
        return {"error": "No interview data found. qa_list is empty."}

    transcript = ""
    for i, qa in enumerate(qa_list, start=1):
        transcript += f"\nQ{i}: {qa.get('question','')}\n"
        transcript += f"A{i}: {qa.get('answer','')}\n"

    prompt = f"""
You are a professional MAANG interview evaluator.

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

RULES:
- Output ONLY valid JSON (no markdown, no extra text).
- Verdict must be one of: Strong Hire, Hire, Maybe, No Hire.
- overall_score must be numeric (0-10).
- Each question must have score.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return only JSON. No markdown."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2
    )

    raw_text = response.choices[0].message.content.strip()
    json_text = extract_json(raw_text)

    if not json_text:
        return {"error": "Invalid JSON returned", "raw": raw_text}

    try:
        data = json.loads(json_text)

        data["overall_score"] = clamp_score(data.get("overall_score", 0))
        data["verdict"] = normalize_verdict(data.get("verdict", "Maybe"))

        data["summary_feedback"] = str(data.get("summary_feedback", "")).strip()
        data["improvement_plan"] = str(data.get("improvement_plan", "")).strip()

        if "question_wise" not in data or not isinstance(data["question_wise"], list):
            data["question_wise"] = []

        cleaned = []
        for item in data["question_wise"]:
            if not isinstance(item, dict):
                continue

            cleaned.append({
                "question": str(item.get("question", "")).strip(),
                "candidate_answer": str(item.get("candidate_answer", "")).strip(),
                "score": clamp_score(item.get("score", 0)),
                "feedback": str(item.get("feedback", "")).strip(),
                "improvement": str(item.get("improvement", "")).strip(),
                "ideal_answer": str(item.get("ideal_answer", "")).strip()
            })

        # Auto-fill missing evaluations if LLM returns less questions
        if len(cleaned) < len(qa_list):
            for i in range(len(cleaned), len(qa_list)):
                cleaned.append({
                    "question": qa_list[i].get("question", ""),
                    "candidate_answer": qa_list[i].get("answer", ""),
                    "score": 0,
                    "feedback": "Evaluation missing from model output.",
                    "improvement": "Try improving clarity and technical explanation.",
                    "ideal_answer": "Not generated."
                })

        data["question_wise"] = cleaned

        return data

    except Exception as e:
        return {"error": "JSON parse failed", "raw": raw_text, "exception": str(e)}
