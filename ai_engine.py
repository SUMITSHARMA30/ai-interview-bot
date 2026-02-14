from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_question(resume_text, qa_list, role, difficulty, interview_type):

    # Convert QA list to string transcript
    transcript = ""
    if isinstance(qa_list, list):
        for i, qa in enumerate(qa_list, start=1):
            transcript += f"\nQ{i}: {qa.get('question','')}\nA{i}: {qa.get('answer','')}\n"
    else:
        transcript = str(qa_list)

    prompt = f"""
You are a professional MAANG interviewer.

Interview Settings:
Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Candidate Resume:
{resume_text}

Previous Q&A Transcript:
{transcript}

TASK:
Generate the next best interview question.

RULES:
- Output ONLY ONE QUESTION.
- Output only question text (no numbering, no explanation).
- Question must match role selected.
- Difficulty must match difficulty selected.
- If interview_type = HR → ask behavioral HR question.
- If interview_type = Technical → ask technical/coding/system/ML question.
- If interview_type = Mixed → alternate HR and technical.

Make it realistic like MAANG interviewers.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a strict MAANG interviewer. Return only question text."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.6
    )

    return response.choices[0].message.content.strip()
