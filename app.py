import streamlit as st
from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_answer
from streamlit_mic_recorder import mic_recorder
import tempfile
from tts_engine import text_to_speech

from groq import Groq
import os

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with evaluation.")

uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

if uploaded_file:
    resume_text = extract_text(uploaded_file)

    if "chat" not in st.session_state:
        st.session_state.chat = []
        st.session_state.previous_answers = ""
        st.session_state.last_question = ""

    if st.button("🚀 Start Interview"):
        q = generate_question(resume_text, st.session_state.previous_answers)
        st.session_state.last_question = q
        st.session_state.chat.append(("AI", q))

    st.subheader("💬 Interview Chat")

    for role, msg in st.session_state.chat:
        st.write(f"**{role}:** {msg}")

    user_answer = st.text_input("Your Answer:")

    if st.button("✅ Submit Answer"):
        if user_answer.strip() != "":
            st.session_state.chat.append(("You", user_answer))

            # Evaluate answer
            evaluation = evaluate_answer(st.session_state.last_question, user_answer)

            st.session_state.chat.append(("Evaluation", str(evaluation)))

            st.session_state.previous_answers += f"\nQuestion: {st.session_state.last_question}\nAnswer: {user_answer}\n"

            # Generate next question
            q = generate_question(resume_text, st.session_state.previous_answers)
            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
        else:
            st.warning("Please write an answer first.")
