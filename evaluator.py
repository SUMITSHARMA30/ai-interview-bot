from groq import Groq
from dotenv import load_dotenv
import os
import json

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def evaluate_answer(question, answer):

    prompt = f"""
You are an expert interview evaluator like MAANG interviewers.

Question: {question}
Answer: {answer}

Return strictly JSON only in this format:

{{
  "technical_accuracy": 0-10,
  "clarity": 0-10,
  "confidence": 0-10,
  "depth": 0-10,
  "final_score": 0-10,
  "feedback": "...",
  "improvement": "...",
  "ideal_answer": "..."
}}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "Return JSON only. No explanation."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    text = response.choices[0].message.content.strip()

    try:
        return json.loads(text)
    except:
        return {"error": "Invalid JSON returned", "raw": text}
