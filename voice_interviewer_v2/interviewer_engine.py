import os
from groq import Groq
from utils.prompts import INTERVIEW_SYSTEM_PROMPT

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def generate_next_question(resume_text, conversation_history, phase):
    prompt = f"""
Resume:
{resume_text}

Conversation History:
{conversation_history}

Current Interview Phase: {phase}

Now ask the next BEST question as a MAANG interviewer.
Return only the question text.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": INTERVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ],
        temperature=0.4
    )

    return response.choices[0].message.content.strip()
