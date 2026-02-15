import os
from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_question(resume_text, previous_answers, role, difficulty, interview_type):
    prompt = f"""
You are a MAANG-level interviewer.

Generate ONE next interview question based on:
- Candidate resume
- Previous Q&A context
- Role, difficulty, interview type

Role: {role}
Difficulty: {difficulty}
Interview Type: {interview_type}

Resume:
{resume_text}

Previous Answers Context:
{previous_answers}

Rules:
- Ask only ONE question
- Keep it MAANG style
- Must be relevant to the resume + role
- Avoid repeating previous questions
- If difficulty is Hard, ask deep concepts / edge cases

Return only the question text. No extra formatting.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
