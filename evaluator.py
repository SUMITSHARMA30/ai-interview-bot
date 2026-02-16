import os
import json
import re
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------- JSON EXTRACTOR (ROBUST) ----------
def extract_json(text):
    """
    Extract valid JSON even if Groq adds extra text or markdown.
    """
    if not text:
        return None

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    # Try direct parse
    try:
        return json.loads(text)
    except:
        pass

    # Try regex extraction
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            return None

    return None


# ---------- MAIN EVALUATOR ----------
def evaluate_full_interview(qa_list, role, difficulty, interview_type):

    if not qa_list:
        return {
            "overall_score": 0,
            "verdict": "NOT_HIRE",
            "summary_feedback": "No answers provided.",
            "improvement_plan": "Candidate did not attempt the interview.",
            "plagiarism_percentage": 0,
            "plagiarism_verdict": "Low",
            "strengths": [],
            "weaknesses": [],
            "question_wise": []
        }

    qa_text = ""
    for i, qa in enumerate(qa_list, start=1):
        qa_text += f"\nQ{i}: {qa['question']}\nA{i}: {qa['answer']}\n"

    prompt = f"""
You are a MAANG-level Interview Evaluator.

Evaluate the candidate based on the FULL interview.

Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Candidate Q&A:
{qa_text}

In addition to evaluation, DETECT PLAGIARISM / AI-GENERATED ANSWERS.

Plagiarism indicators:
- Generic textbook answers
- Copy-paste style responses
- AI-generated tone
- Repetitive patterns
- Lack of personal reasoning

Return STRICT JSON ONLY in this exact format:

{{
  "overall_score": 0-10,
  "verdict": "HIRE" OR "NO_HIRE" OR "NOT_HIRE (AI DETECTED)",
  "summary_feedback": "string",
  "improvement_plan": "string",

  "plagiarism_percentage": 0-100,
  "plagiarism_verdict": "Low" OR "Medium" OR "High",

  "strengths": ["string", "string"],
  "weaknesses": ["string", "string"],

  "question_wise": [
    {{
      "question": "string",
      "candidate_answer": "string",
      "score": 0-10,
      "feedback": "string",
      "improvement": "string",
      "ideal_answer": "string"
    }}
  ]
}}

STRICT RULES:
- If plagiarism_percentage > 50 → verdict MUST be "NOT_HIRE (AI DETECTED)"
- Output JSON ONLY
- No markdown
- No explanation text
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    raw = response.choices[0].message.content
    parsed = extract_json(raw)

    # ---------- FALLBACK ----------
    if parsed is None:
        return {
            "overall_score": 0,
            "verdict": "NOT_HIRE",
            "summary_feedback": "Evaluation failed due to invalid AI response.",
            "improvement_plan": "Retry interview.",
            "plagiarism_percentage": 0,
            "plagiarism_verdict": "Low",
            "strengths": [],
            "weaknesses": [],
            "question_wise": []
        }

    # ---------- HARD ENFORCEMENT ----------
    plagiarism = parsed.get("plagiarism_percentage", 0)

    try:
        plagiarism = int(plagiarism)
    except:
        plagiarism = 0

    parsed["plagiarism_percentage"] = plagiarism

    if plagiarism > 50:
        parsed["verdict"] = "NOT_HIRE (AI DETECTED)"
        parsed["plagiarism_verdict"] = "High"
        parsed["summary_feedback"] = (
            parsed.get("summary_feedback", "")
            + " ⚠️ High plagiarism detected. Answers appear AI-generated or copied."
        )

    return parsed
