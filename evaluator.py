import os
import json
import re
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- JSON EXTRACTOR ----------------
def extract_json(text):
    """
    Extract JSON safely even if model returns extra text.
    """
    if not text:
        return None

    text = text.strip()
    text = text.replace("```json", "").replace("```", "").strip()

    # Try direct parsing
    try:
        return json.loads(text)
    except:
        pass

    # Try regex extraction of JSON object
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except:
            return None

    return None


# ---------------- LOW EFFORT CHECK ----------------
def is_low_effort(answer: str):
    if not answer:
        return True

    answer = answer.strip()

    # Very short answer
    if len(answer) < 15:
        return True

    # Single word / random text
    if answer.lower() in ["a", "b", "c", "d", "yes", "no", "ok", "hmm", "kk", "ab"]:
        return True

    # Too few words
    if len(answer.split()) < 4:
        return True

    return False


# ---------------- RULE BASED PLAGIARISM ----------------
def calculate_plagiarism_percentage(qa_list):
    """
    Realistic heuristic plagiarism detection.

    - If answers are too short -> plagiarism = 0 (can't judge).
    - If answers are generic + long -> higher plagiarism.
    - If many low-effort answers -> plagiarism low (not plagiarism, just weak candidate).
    """

    if not qa_list:
        return 0

    total_words = 0
    short_answers = 0
    long_generic_answers = 0

    generic_phrases = [
        "as an ai",
        "in conclusion",
        "overall",
        "to summarize",
        "it is important to note",
        "in today's world",
        "there are many ways",
        "this can be done by",
        "the main objective",
        "firstly secondly",
        "in simple terms",
        "generally speaking"
    ]

    for qa in qa_list:
        ans = qa.get("answer", "").strip().lower()
        words = ans.split()
        total_words += len(words)

        # If answer too short, can't detect plagiarism
        if len(words) < 8:
            short_answers += 1

        # If long answer contains generic phrases, likely AI generated
        if len(words) > 60:
            for phrase in generic_phrases:
                if phrase in ans:
                    long_generic_answers += 1
                    break

    # If all answers too short -> plagiarism can't be judged
    if short_answers == len(qa_list):
        return 0

    # If many answers are short -> low plagiarism
    if short_answers >= (len(qa_list) * 0.6):
        return 5

    # If many long generic answers -> high plagiarism
    if long_generic_answers >= (len(qa_list) * 0.5):
        return 75

    if long_generic_answers >= 1:
        return 45

    # Default moderate plagiarism
    return 20


# ---------------- MAIN EVALUATOR ----------------
def evaluate_full_interview(qa_list, role, difficulty, interview_type):

    # Safety fallback
    if not qa_list:
        return {
            "overall_score": 0,
            "verdict": "NO_HIRE",
            "summary_feedback": "No answers were provided.",
            "improvement_plan": "Candidate did not attempt the interview.",
            "plagiarism_percentage": 0,
            "plagiarism_verdict": "Low",
            "strengths": [],
            "weaknesses": [],
            "question_wise": []
        }

    qa_text = ""
    for i, qa in enumerate(qa_list, start=1):
        qa_text += f"\nQ{i}: {qa.get('question','')}\nA{i}: {qa.get('answer','')}\n"

    prompt = f"""
You are a strict MAANG-level Interview Evaluator.

Evaluate the candidate based on the FULL interview.

Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Candidate Q&A:
{qa_text}

Return STRICT JSON ONLY in this exact format:

{{
  "overall_score": 0,
  "verdict": "HIRE" OR "NO_HIRE",
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

RULES:
- overall_score must be 0 to 10
- each question score must be 0 to 10
- output JSON ONLY (no markdown, no extra text)
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    raw = response.choices[0].message.content.strip()
    parsed = extract_json(raw)

    # If model fails
    if parsed is None:
        parsed = {
            "overall_score": 0,
            "verdict": "NO_HIRE",
            "summary_feedback": "Evaluation failed because AI returned invalid response.",
            "improvement_plan": "Please retry interview.",
            "strengths": [],
            "weaknesses": [],
            "question_wise": []
        }

    # Ensure structure
    if "question_wise" not in parsed or not isinstance(parsed["question_wise"], list):
        parsed["question_wise"] = []

    # ---------------- Force correct candidate answers in JSON ----------------
    # (Sometimes Groq messes candidate_answer field)
    for i, item in enumerate(parsed["question_wise"]):
        if i < len(qa_list):
            item["question"] = qa_list[i].get("question", "")
            item["candidate_answer"] = qa_list[i].get("answer", "")

    # ---------------- HARD LOW-EFFORT PENALTY ----------------
    qwise = parsed.get("question_wise", [])
    if isinstance(qwise, list):

        for item in qwise:
            ans = item.get("candidate_answer", "")

            if is_low_effort(ans):
                item["score"] = 0
                item["feedback"] = "Answer is too short / low-effort. No meaningful explanation provided."
                item["improvement"] = "Write a complete explanation with reasoning, steps, and examples."
                item["ideal_answer"] = item.get("ideal_answer", "A detailed correct explanation is required.")

    # ---------------- RECALCULATE OVERALL SCORE ----------------
    scores = []
    for item in qwise:
        try:
            scores.append(int(item.get("score", 0)))
        except:
            scores.append(0)

    if scores:
        parsed["overall_score"] = round(sum(scores) / len(scores), 1)
    else:
        parsed["overall_score"] = 0

    # ---------------- REAL PLAGIARISM LOGIC ----------------
    plagiarism = calculate_plagiarism_percentage(qa_list)
    parsed["plagiarism_percentage"] = plagiarism

    if plagiarism >= 70:
        parsed["plagiarism_verdict"] = "High"
    elif plagiarism >= 40:
        parsed["plagiarism_verdict"] = "Medium"
    else:
        parsed["plagiarism_verdict"] = "Low"

    # ---------------- FINAL VERDICT RULE ----------------
    if plagiarism > 50:
        parsed["verdict"] = "NOT_HIRE (AI DETECTED)"
        parsed["summary_feedback"] = parsed.get("summary_feedback", "") + " ⚠️ High plagiarism / AI-generated pattern detected."

    # ---------------- LOW SCORE RULE ----------------
    if parsed["overall_score"] <= 3 and plagiarism <= 50:
        parsed["verdict"] = "NO_HIRE"

    # ---------------- Ensure verdict is always present ----------------
    if "verdict" not in parsed:
        parsed["verdict"] = "NO_HIRE"

    return parsed
