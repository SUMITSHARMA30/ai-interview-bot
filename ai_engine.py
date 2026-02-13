from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_question(resume_text, previous_answers):

    prompt = f"""
You are a professional interviewer.

Resume:
{resume_text}

Previous Answers:
{previous_answers}

Ask the next best interview question based on the resume.
Only output the question only.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": "You are a strict professional interviewer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    return response.choices[0].message.content.strip()
