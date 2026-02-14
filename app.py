import streamlit as st
import tempfile
import os
import pandas as pd
from datetime import datetime

from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_full_interview
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech

from db import init_db, save_report, fetch_all_reports
from pdf_report import generate_pdf_report
from ui import load_css, header_ui, show_chat_bubbles, show_eval_table

# ---------------- INIT DB ----------------
init_db()

# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide", page_icon="🤖")

# ---------------- LOAD CSS ----------------
load_css("style.css")

# ---------------- HEADER ----------------
header_ui()

# ---------------- GROQ API CHECK ----------------
if not os.getenv("GROQ_API_KEY"):
    st.error("❌ GROQ_API_KEY missing! Add it in Streamlit secrets.")
    st.stop()

# ---------------- SIDEBAR ADMIN PANEL ----------------
st.sidebar.title("🛠️ HR Admin Panel")

role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])

TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 3, 20, 5)

mode = st.sidebar.radio("Candidate Mode", ["Text Mode", "Voice Mode"])

st.sidebar.divider()

st.sidebar.subheader("📊 HR Dashboard")
if st.sidebar.button("📂 View All Reports"):
    st.session_state.show_hr_dashboard = True

if "show_hr_dashboard" not in st.session_state:
    st.session_state.show_hr_dashboard = False


# ---------------- SESSION INIT ----------------
if "chat" not in st.session_state:
    st.session_state.chat = []

if "qa_list" not in st.session_state:
    st.session_state.qa_list = []

if "previous_answers" not in st.session_state:
    st.session_state.previous_answers = ""

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False

if "final_report" not in st.session_state:
    st.session_state.final_report = None

if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = ""

if "input_answer" not in st.session_state:
    st.session_state.input_answer = ""


# ---------------- RESET FUNCTION ----------------
def reset_interview():
    st.session_state.chat = []
    st.session_state.qa_list = []
    st.session_state.previous_answers = ""
    st.session_state.last_question = ""
    st.session_state.interview_started = False
    st.session_state.question_count = 0
    st.session_state.interview_ended = False
    st.session_state.final_report = None
    st.session_state.input_answer = ""


# ---------------- HR DASHBOARD PAGE ----------------
if st.session_state.show_hr_dashboard:
    st.markdown("<h2 class='section-title'>📊 HR Reports Dashboard</h2>", unsafe_allow_html=True)

    reports = fetch_all_reports()

    if len(reports) == 0:
        st.info("No reports saved yet.")
    else:
        df = pd.DataFrame(reports)
        st.dataframe(df, use_container_width=True)

    if st.button("⬅ Back to Interview App"):
        st.session_state.show_hr_dashboard = False
        st.rerun()

    st.stop()


# ---------------- MAIN APP ----------------
st.markdown("<h2 class='section-title'>🎯 Candidate Interview Portal</h2>", unsafe_allow_html=True)

candidate_name = st.text_input("👤 Candidate Name", value=st.session_state.candidate_name)
st.session_state.candidate_name = candidate_name

uploaded_file = st.file_uploader("📄 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])


if uploaded_file:
    resume_text = extract_text(uploaded_file)

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        if st.button("🚀 Start Interview", use_container_width=True):
            reset_interview()

            q = generate_question(resume_text, "", role, difficulty, interview_type)
            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            if mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

            st.rerun()

    with col2:
        if st.button("🛑 End Interview", use_container_width=True):
            st.session_state.interview_ended = True
            st.rerun()

    with col3:
        if st.button("🔁 Reset", use_container_width=True):
            reset_interview()
            st.rerun()

    st.divider()

    # ---------------- CHAT UI ----------------
    st.markdown("<h3 class='section-title'>💬 Interview Conversation</h3>", unsafe_allow_html=True)
    show_chat_bubbles(st.session_state.chat)

    # ---------------- INTERVIEW FLOW ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        st.markdown(
            f"<div class='progress-box'>📌 Question <b>{st.session_state.question_count}</b> / <b>{TOTAL_QUESTIONS}</b></div>",
            unsafe_allow_html=True
        )

        # Auto end after question limit
        if st.session_state.question_count > TOTAL_QUESTIONS:
            st.session_state.interview_ended = True
            st.rerun()

        st.divider()

        # ---------------- TEXT MODE ----------------
        if mode == "Text Mode":

            st.markdown("<h3 class='section-title'>⌨️ Text Answer Mode</h3>", unsafe_allow_html=True)

            user_answer = st.text_area(
                "Write your answer:",
                key="input_answer",
                height=150,
                placeholder="Type your answer here..."
            )

            if st.button("✅ Submit Answer", use_container_width=True):
                if user_answer.strip():

                    # Store Q&A
                    st.session_state.qa_list.append({
                        "question": st.session_state.last_question,
                        "answer": user_answer
                    })

                    st.session_state.chat.append(("You", user_answer))

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    # Next question
                    q = generate_question(resume_text, st.session_state.previous_answers, role, difficulty, interview_type)

                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))

                    st.session_state.question_count += 1

                    # CLEAR OLD ANSWER
                    st.session_state.input_answer = ""

                    st.rerun()

                else:
                    st.warning("⚠️ Please write an answer first.")

        # ---------------- VOICE MODE ----------------
        if mode == "Voice Mode":

            st.markdown("<h3 class='section-title'>🎤 Voice Answer Mode</h3>", unsafe_allow_html=True)

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

                from groq import Groq
                client = Groq(api_key=os.getenv("GROQ_API_KEY"))

                with open(audio_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=file,
                        model="whisper-large-v3"
                    )

                user_answer_voice = transcription.text

                st.success("✅ Transcribed Answer:")
                st.write(user_answer_voice)

                if st.button("🚀 Submit Voice Answer", use_container_width=True):
                    if user_answer_voice.strip():

                        st.session_state.qa_list.append({
                            "question": st.session_state.last_question,
                            "answer": user_answer_voice
                        })

                        st.session_state.chat.append(("You", user_answer_voice))

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        q = generate_question(resume_text, st.session_state.previous_answers, role, difficulty, interview_type)

                        st.session_state.last_question = q
                        st.session_state.chat.append(("AI", q))

                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()
                    else:
                        st.warning("⚠️ Voice answer is empty. Try again.")

    # ---------------- FINAL REPORT ----------------
    if st.session_state.interview_ended:

        st.divider()
        st.markdown("<h2 class='section-title'>📊 Final Interview Report</h2>", unsafe_allow_html=True)

        if st.session_state.final_report is None:

            report = evaluate_full_interview(
                st.session_state.qa_list,
                role=role,
                difficulty=difficulty,
                interview_type=interview_type
            )

            if not isinstance(report, dict):
                st.error("❌ Report format invalid.")
                st.write(report)
                st.stop()

            st.session_state.final_report = report

            # Save report in SQLite
            save_report(
                candidate_name=candidate_name if candidate_name.strip() else "Unknown",
                role=role,
                difficulty=difficulty,
                interview_type=interview_type,
                report_json=str(report)
            )

        report = st.session_state.final_report

        overall_score = report.get("overall_score", 0)
        verdict = report.get("verdict", "Unknown")
        summary_feedback = report.get("summary_feedback", "")
        improvement_plan = report.get("improvement_plan", "")

        st.markdown(
            f"""
            <div class='report-card'>
                <h3>🏆 Verdict: {verdict}</h3>
                <p><b>Overall Score:</b> {overall_score} / 10</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.subheader("📌 Summary Feedback")
        st.write(summary_feedback)

        st.subheader("🚀 Improvement Plan")
        st.write(improvement_plan)

        # Question-wise table
        st.subheader("📋 Question Wise Evaluation")
        show_eval_table(report)

        # Generate PDF
        st.divider()
        st.subheader("📄 Download Professional Report")

        pdf_file = generate_pdf_report(
            candidate_name=candidate_name if candidate_name.strip() else "Unknown",
            role=role,
            difficulty=difficulty,
            interview_type=interview_type,
            report=report
        )

        st.download_button(
            label="📥 Download PDF Report",
            data=pdf_file,
            file_name="AI_Interview_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

else:
    st.info("📌 Upload resume first to start interview.")
