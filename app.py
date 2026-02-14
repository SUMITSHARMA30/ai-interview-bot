import streamlit as st
import tempfile
import os
from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_answer
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech
from groq import Groq

st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with evaluation.")

st.write("🔥 PHASE 2 DEPLOYED SUCCESSFULLY")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])


# ---------------- SESSION INIT ----------------
if "chat" not in st.session_state:
    st.session_state.chat = []

if "previous_answers" not in st.session_state:
    st.session_state.previous_answers = ""

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "interview_started" not in st.session_state:
    st.session_state.interview_started = False


# ---------------- MAIN LOGIC ----------------
if uploaded_file:
    resume_text = extract_text(uploaded_file)

    # START INTERVIEW BUTTON
    if st.button("🚀 Start Interview"):
        q = generate_question(resume_text, st.session_state.previous_answers)
        st.session_state.last_question = q
        st.session_state.chat.append(("AI", q))
        st.session_state.interview_started = True

        # AI speaks question
        voice_file = text_to_speech(q)
        st.audio(voice_file, format="audio/mp3")

    # CHAT DISPLAY
    st.subheader("💬 Interview Chat")
    for role, msg in st.session_state.chat:
        st.write(f"**{role}:** {msg}")

    # ONLY IF INTERVIEW STARTED
    if st.session_state.interview_started:

        st.divider()

        # ---------------- TEXT ANSWER MODE ----------------
        st.subheader("⌨️ Text Answer Mode")

        user_answer = st.text_input("Your Answer:")

        if st.button("✅ Submit Text Answer"):
            if user_answer.strip() != "":
                st.session_state.chat.append(("You", user_answer))

                evaluation = evaluate_answer(st.session_state.last_question, user_answer)
                st.session_state.chat.append(("Evaluation", str(evaluation)))

                st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                q = generate_question(resume_text, st.session_state.previous_answers)
                st.session_state.last_question = q
                st.session_state.chat.append(("AI", q))

                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

            else:
                st.warning("Please write an answer first.")

        st.divider()

        # ---------------- VOICE ANSWER MODE ----------------
        st.subheader("🎤 Voice Answer Mode")

        audio = mic_recorder(
            start_prompt="🎙️ Start Recording",
            stop_prompt="⏹️ Stop Recording",
            key="mic"
        )

        if audio:
            st.audio(audio["bytes"], format="audio/wav")

            # save audio
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio["bytes"])
                audio_path = f.name

            # transcribe
            user_answer_voice = transcribe_audio(audio_path)

            st.success("✅ Transcribed Answer:")
            st.write(user_answer_voice)

            if st.button("🚀 Submit Voice Answer"):
                if user_answer_voice.strip() != "":
                    st.session_state.chat.append(("You", user_answer_voice))

                    evaluation = evaluate_answer(st.session_state.last_question, user_answer_voice)
                    st.session_state.chat.append(("Evaluation", str(evaluation)))

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                    q = generate_question(resume_text, st.session_state.previous_answers)
                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))

                    voice_file = text_to_speech(q)
                    st.audio(voice_file, format="audio/mp3")

                else:
                    st.warning("Voice answer is empty. Try again.")

    else:
        st.info("Click 🚀 Start Interview to enable Voice Mode.")
else:
    st.info("📌 Upload your resume first to start.")
