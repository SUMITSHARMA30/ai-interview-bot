from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_question(resume_text, previous_answers, role="SDE", difficulty="Medium", interview_type="Technical"):

    prompt = f"""
You are a professional MAANG interviewer.

Interview Settings:
Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Candidate Resume:
{resume_text}

Previous Q&A:
{previous_answers}

TASK:
Generate the next best interview question.

RULES:
- Output ONLY ONE QUESTION.
- Output only question text (no numbering, no explanation).
- Question must match the role selected.
- Difficulty must match the difficulty selected.
- If interview_type = HR → ask behavioral HR question.
- If interview_type = Technical → ask technical/coding/system/ML question.
- If interview_type = Mixed → alternate HR and technical.

Return only the question text.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return only the question text. No explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response.choices[0].message.content.strip()
