import streamlit as st
import tempfile
import os
import pandas as pd
import ast

from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_answer
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech
from groq import Groq

from pdf_report import generate_pdf_report
from database import init_db, save_report, fetch_reports, fetch_pdf


# ---------------- INIT DATABASE ----------------
init_db()


# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with evaluation.")


# ---------------- GROQ CLIENT ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- HR / CANDIDATE SWITCH ----------------
st.sidebar.title("🔐 Panel Switch")

panel = st.sidebar.radio("Choose Panel", ["Candidate Panel", "HR Dashboard"])


# ==========================================================
#                     HR DASHBOARD
# ==========================================================
if panel == "HR Dashboard":
    st.subheader("📊 HR Dashboard (Saved Interview Reports)")

    reports = fetch_reports()

    if not reports:
        st.warning("No interview reports found yet.")
    else:
        df = pd.DataFrame(reports, columns=[
            "Report ID", "Candidate Name", "Role", "Difficulty",
            "Interview Type", "Mode", "Total Questions",
            "Avg Score", "Verdict", "Created At"
        ])

        st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("📥 Download Candidate PDF Report")

        report_id = st.number_input("Enter Report ID", min_value=1, step=1)

        if st.button("Download PDF"):
            pdf_bytes = fetch_pdf(report_id)

            if pdf_bytes:
                st.download_button(
                    label="📄 Download Report PDF",
                    data=pdf_bytes,
                    file_name=f"Interview_Report_{report_id}.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Invalid Report ID or PDF not found.")

    st.stop()


# ==========================================================
#                    CANDIDATE PANEL
# ==========================================================

# ---------------- ADMIN PANEL ----------------
st.sidebar.title("🛠️ Admin Panel (HR Settings)")

candidate_name = st.sidebar.text_input("Candidate Name", value="Candidate")

role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])

TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 5, 20, 5)

mode = st.sidebar.radio("Candidate Interview Mode", ["Text Mode", "Voice Mode"])


# ---------------- SPEECH TO TEXT ----------------
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


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

if "evaluations" not in st.session_state:
    st.session_state.evaluations = []

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False


def reset_interview():
    st.session_state.chat = []
    st.session_state.previous_answers = ""
    st.session_state.last_question = ""
    st.session_state.interview_started = False
    st.session_state.question_count = 0
    st.session_state.scores = []
    st.session_state.evaluations = []
    st.session_state.interview_ended = False


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])


# ---------------- MAIN APP ----------------
if uploaded_file:
    resume_text = extract_text(uploaded_file)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "", role, difficulty, interview_type)
            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            if mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True

    # ---------------- CHAT DISPLAY ----------------
    st.subheader("💬 Interview Chat")
    for role_msg, msg in st.session_state.chat:
        st.write(f"**{role_msg}:** {msg}")

    # ---------------- INTERVIEW FLOW ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        if st.session_state.question_count > TOTAL_QUESTIONS:
            st.session_state.interview_ended = True
            st.rerun()

        st.divider()
        st.write(f"📌 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")

        # ---------------- TEXT MODE ----------------
        if mode == "Text Mode":
            st.subheader("⌨️ Text Answer Mode")

            user_answer = st.text_input("Your Answer:")

            if st.button("✅ Submit Answer"):
                if user_answer.strip():
                    st.session_state.chat.append(("You", user_answer))

                    evaluation = evaluate_answer(st.session_state.last_question, user_answer, role, difficulty)
                    st.session_state.evaluations.append(evaluation)

                    st.session_state.chat.append(("Evaluation", str(evaluation)))

                    try:
                        st.session_state.scores.append(float(evaluation["final_score"]))
                    except:
                        st.session_state.scores.append(0)

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    q = generate_question(resume_text, st.session_state.previous_answers, role, difficulty, interview_type)
                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))

                    st.session_state.question_count += 1
                    st.rerun()

                else:
                    st.warning("Please write an answer first.")

        # ---------------- VOICE MODE ----------------
        if mode == "Voice Mode":
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
                    if user_answer_voice.strip():
                        st.session_state.chat.append(("You", user_answer_voice))

                        evaluation = evaluate_answer(st.session_state.last_question, user_answer_voice, role, difficulty)
                        st.session_state.evaluations.append(evaluation)

                        st.session_state.chat.append(("Evaluation", str(evaluation)))

                        try:
                            st.session_state.scores.append(float(evaluation["final_score"]))
                        except:
                            st.session_state.scores.append(0)

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        q = generate_question(resume_text, st.session_state.previous_answers, role, difficulty, interview_type)
                        st.session_state.last_question = q
                        st.session_state.chat.append(("AI", q))

                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()

                    else:
                        st.warning("Voice answer is empty. Try again.")

    # ---------------- FINAL REPORT ----------------
    if st.session_state.interview_ended:
        st.divider()
        st.subheader("📊 Final Interview Report")

        avg_score = sum(st.session_state.scores) / len(st.session_state.scores) if st.session_state.scores else 0

        if avg_score >= 8:
            verdict = "🔥 Strong Hire"
        elif avg_score >= 6:
            verdict = "✅ Hire / Good Candidate"
        elif avg_score >= 4:
            verdict = "⚠️ Maybe (Needs Improvement)"
        else:
            verdict = "❌ Not Ready Yet"

        st.success(f"🏆 Final Verdict: **{verdict}**")
        st.write(f"⭐ Average Score: **{round(avg_score, 2)} / 10**")

        st.divider()
        st.subheader("📈 Score Progress Chart")

        if st.session_state.scores:
            df = pd.DataFrame({
                "Question": list(range(1, len(st.session_state.scores) + 1)),
                "Score": st.session_state.scores
            })
            st.line_chart(df.set_index("Question"))

        st.divider()
        st.subheader("📄 Generate & Save Interview Report")

        pdf_bytes = generate_pdf_report(
            candidate_name=candidate_name,
            chat=st.session_state.chat,
            avg_score=avg_score,
            verdict=verdict,
            scores=st.session_state.scores,
            role=role,
            difficulty=difficulty,
            interview_type=interview_type,
            mode=mode
        )

        # Save to DB
        save_report(
            candidate_name=candidate_name,
            role=role,
            difficulty=difficulty,
            interview_type=interview_type,
            mode=mode,
            total_questions=TOTAL_QUESTIONS,
            avg_score=avg_score,
            verdict=verdict,
            chat=st.session_state.chat,
            pdf_bytes=pdf_bytes
        )

        st.success("✅ Report saved successfully in SQLite Database!")

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_bytes,
            file_name=f"{candidate_name}_Interview_Report.pdf",
            mime="application/pdf"
        )

        st.divider()
        if st.button("🔁 Start New Interview"):
            reset_interview()
            st.rerun()

else:
    st.info("📌 Upload your resume first to start.")
