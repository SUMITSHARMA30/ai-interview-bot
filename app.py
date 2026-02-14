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

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- CONFIG ----------------
TOTAL_QUESTIONS = 5   # change to 10 later


# ---------------- SPEECH TO TEXT ----------------
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

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "scores" not in st.session_state:
    st.session_state.scores = []

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False


# ---------------- RESET FUNCTION ----------------
def reset_interview():
    st.session_state.chat = []
    st.session_state.previous_answers = ""
    st.session_state.last_question = ""
    st.session_state.interview_started = False
    st.session_state.question_count = 0
    st.session_state.scores = []
    st.session_state.interview_ended = False


# ---------------- MAIN LOGIC ----------------
if uploaded_file:
    resume_text = extract_text(uploaded_file)

    # ---------------- BUTTONS TOP ----------------
    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "")
            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            voice_file = text_to_speech(q)
            st.audio(voice_file, format="audio/mp3")

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True

    # ---------------- CHAT DISPLAY ----------------
    st.subheader("💬 Interview Chat")
    for role, msg in st.session_state.chat:
        st.write(f"**{role}:** {msg}")

    # ---------------- INTERVIEW REPORT ----------------
    if st.session_state.interview_ended:

        st.divider()
        st.subheader("📊 Final Interview Report")

        if len(st.session_state.scores) > 0:
            avg_score = sum(st.session_state.scores) / len(st.session_state.scores)
        else:
            avg_score = 0

        st.write(f"✅ Questions Attempted: **{st.session_state.question_count - 1}** / {TOTAL_QUESTIONS}")
        st.write(f"⭐ Average Score: **{round(avg_score, 2)} / 10**")

        # Verdict system
        if avg_score >= 8:
            verdict = "🔥 Strong Hire"
        elif avg_score >= 6:
            verdict = "✅ Hire / Good Candidate"
        elif avg_score >= 4:
            verdict = "⚠️ Maybe (Needs Improvement)"
        else:
            verdict = "❌ Not Ready Yet"

        st.success(f"🏆 Final Verdict: **{verdict}**")

        st.divider()
        st.subheader("📌 Improvement Suggestions")

        if avg_score < 4:
            st.write("❌ You need to improve fundamentals, confidence, and communication.")
        elif avg_score < 6:
            st.write("⚠️ You are decent but need stronger explanations and better examples.")
        elif avg_score < 8:
            st.write("✅ You are good. Improve technical depth and answer structure.")
        else:
            st.write("🔥 You are interview-ready. Keep practicing system design + DSA.")

        st.divider()
        if st.button("🔁 Start New Interview"):
            reset_interview()
            st.rerun()

    # ---------------- INPUT MODE ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        # Auto stop after limit
        if st.session_state.question_count > TOTAL_QUESTIONS:
            st.session_state.interview_ended = True
            st.rerun()

        st.divider()
        st.write(f"📌 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")

        # ---------------- TEXT ANSWER MODE ----------------
        st.subheader("⌨️ Text Answer Mode")
        user_answer = st.text_input("Your Answer:")

        if st.button("✅ Submit Text Answer"):
            if user_answer.strip() != "":
                st.session_state.chat.append(("You", user_answer))

                evaluation = evaluate_answer(st.session_state.last_question, user_answer)
                st.session_state.chat.append(("Evaluation", str(evaluation)))

                # Store score if evaluator returns dict with score
                try:
                    st.session_state.scores.append(float(evaluation["final_score"]))
                except:
                    pass

                st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                q = generate_question(resume_text, st.session_state.previous_answers)
                st.session_state.last_question = q
                st.session_state.chat.append(("AI", q))

                st.session_state.question_count += 1

                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

                st.rerun()
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

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio["bytes"])
                audio_path = f.name

            user_answer_voice = transcribe_audio(audio_path)

            st.success("✅ Transcribed Answer:")
            st.write(user_answer_voice)

            if st.button("🚀 Submit Voice Answer"):
                if user_answer_voice.strip() != "":
                    st.session_state.chat.append(("You", user_answer_voice))

                    evaluation = evaluate_answer(st.session_state.last_question, user_answer_voice)
                    st.session_state.chat.append(("Evaluation", str(evaluation)))

                    try:
                        st.session_state.scores.append(float(evaluation["final_score"]))
                    except:
                        pass

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                    q = generate_question(resume_text, st.session_state.previous_answers)
                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))

                    st.session_state.question_count += 1

                    voice_file = text_to_speech(q)
                    st.audio(voice_file, format="audio/mp3")

                    st.rerun()
                else:
                    st.warning("Voice answer is empty. Try again.")

else:
    st.info("📌 Upload your resume first to start.")
