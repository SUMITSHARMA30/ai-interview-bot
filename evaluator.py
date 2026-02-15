import os
import json
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def evaluate_full_interview(qa_list, role, difficulty, interview_type):
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

Return STRICT JSON ONLY in this exact format:

{{
  "overall_score": 0,
  "verdict": "HIRE" or "NO_HIRE",
  "summary_feedback": "string",
  "improvement_plan": "string",
  "strengths": ["string", "string"],
  "weaknesses": ["string", "string"],
  "question_wise": [
    {{
      "question": "string",
      "candidate_answer": "string",
      "score": 0,
      "feedback": "string",
      "improvement": "string",
      "ideal_answer": "string"
    }}
  ]
}}
Rules:
- overall_score must be from 0 to 10
- Each question must have score 0-10
- verdict must be ONLY HIRE or NO_HIRE
- JSON must be valid and parsable
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    raw = response.choices[0].message.content.strip()

    try:
        return json.loads(raw)
    except Exception:
        raise ValueError(f"Groq returned invalid JSON:\n{raw}")
