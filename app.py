import streamlit as st
import os
import tempfile
import pandas as pd
import json

from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_full_interview
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech
from groq import Groq

from pdf_report import generate_pdf_report
from db import init_db, save_report
from hr_dashboard import hr_dashboard


# ---------------- CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))
init_db()


# ---------------- LOAD CSS ----------------
def load_css():
    try:
        with open("styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


load_css()


# ---------------- HIDE SIDEBAR ----------------
def hide_sidebar():
    st.markdown("""
        <style>
        section[data-testid="stSidebar"] {display: none !important;}
        div[data-testid="stSidebarNav"] {display: none !important;}
        </style>
    """, unsafe_allow_html=True)


# ---------------- FULLSCREEN REQUEST ----------------
def request_fullscreen():
    st.markdown("""
    <script>
    function goFullscreen() {
        let elem = document.documentElement;
        if (elem.requestFullscreen) {
            elem.requestFullscreen();
        }
    }
    </script>

    <div style="
        background:white;
        padding:20px;
        border-radius:14px;
        box-shadow:0px 10px 25px rgba(0,0,0,0.12);
        margin-bottom:15px;
        text-align:center;
        font-family:Arial;
    ">
        <h2 style="margin:0; color:#0f172a;">🎯 Interview Fullscreen Mode</h2>
        <p style="color:gray; margin-top:5px;">
            Please enable fullscreen for the best MAANG-style interview experience.
        </p>

        <button onclick="goFullscreen()" style="
            background:#2563eb;
            color:white;
            padding:12px 20px;
            border:none;
            border-radius:12px;
            font-size:16px;
            font-weight:700;
            cursor:pointer;
            width:100%;
        ">
            Enter Fullscreen
        </button>
    </div>
    """, unsafe_allow_html=True)


# ---------------- SESSION INIT ----------------
def init_session():
    defaults = {
        "page": "Candidate",
        "hr_logged_in": False,

        "resume_text": "",
        "candidate_name": "Unknown",

        "role": "SDE",
        "difficulty": "Easy",
        "interview_type": "Technical",
        "mode": "Text Mode",
        "total_questions": 5,

        "qa_list": [],
        "previous_answers": "",
        "last_question": "",

        "interview_started": False,
        "question_count": 0,
        "interview_ended": False,
        "final_report": None
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ---------------- RESET INTERVIEW ----------------
def reset_interview():
    st.session_state.qa_list = []
    st.session_state.previous_answers = ""
    st.session_state.last_question = ""
    st.session_state.interview_started = False
    st.session_state.question_count = 0
    st.session_state.interview_ended = False
    st.session_state.final_report = None


# ---------------- SPEECH TO TEXT ----------------
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


# ---------------- NAVIGATION ----------------
st.sidebar.title("🌍 Navigation")

page = st.sidebar.radio(
    "Choose Portal",
    ["Candidate Portal", "HR Dashboard"],
    index=0
)

if page == "Candidate Portal":
    st.session_state.page = "Candidate"
else:
    st.session_state.page = "HR"


# ---------------- HR DASHBOARD ----------------
if st.session_state.page == "HR":

    if not st.session_state.hr_logged_in:

        st.markdown("<h1 class='main-title'>🔐 HR Login</h1>", unsafe_allow_html=True)
        st.markdown("<p class='subtitle'>Only HR/Admin can access interview reports.</p>", unsafe_allow_html=True)

        password = st.text_input("Enter HR Password", type="password")

        if st.button("Login"):
            if password == st.secrets["HR_PASSWORD"]:
                st.session_state.hr_logged_in = True
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Wrong Password!")

        st.stop()

    else:
        hr_dashboard()
        st.stop()


# ---------------- CANDIDATE PORTAL ----------------
if st.session_state.interview_started and st.session_state.final_report is None:
    hide_sidebar()

st.markdown("<h1 class='main-title'>🤖 AI Powered Interview Bot</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>MAANG Style Interview • Groq Powered • PDF Report + HR Dashboard</p>", unsafe_allow_html=True)

st.divider()


# ---------------- SETTINGS BEFORE START ----------------
if not st.session_state.interview_started and st.session_state.final_report is None:

    st.sidebar.title("🛠️ Interview Settings")

    st.session_state.role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
    st.session_state.difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
    st.session_state.interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])
    st.session_state.total_questions = st.sidebar.slider("Number of Questions", 5, 20, 5)
    st.session_state.mode = st.sidebar.radio("Interview Mode", ["Text Mode", "Voice Mode"])

    st.sidebar.divider()
    st.session_state.candidate_name = st.sidebar.text_input("Candidate Name", value=st.session_state.candidate_name)


# ---------------- UPLOAD BEFORE START ----------------
if not st.session_state.interview_started and st.session_state.final_report is None:

    uploaded_file = st.file_uploader("📌 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        resume_text = extract_text(uploaded_file)
        st.session_state.resume_text = resume_text

        st.success("✅ Resume parsed successfully!")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("🚀 Start Interview"):
                reset_interview()

                q = generate_question(
                    st.session_state.resume_text,
                    "",
                    st.session_state.role,
                    st.session_state.difficulty,
                    st.session_state.interview_type
                )

                st.session_state.last_question = q
                st.session_state.interview_started = True
                st.session_state.question_count = 1

                st.rerun()

        with col2:
            if st.button("🧹 Reset"):
                reset_interview()
                st.rerun()

    else:
        st.info("📌 Upload your resume to start the interview.")
        st.stop()


# ---------------- INTERVIEW SCREEN ----------------
if st.session_state.interview_started and not st.session_state.interview_ended:

    hide_sidebar()
    request_fullscreen()

    TOTAL_QUESTIONS = st.session_state.total_questions
    mode = st.session_state.mode

    st.progress(st.session_state.question_count / TOTAL_QUESTIONS)

    st.markdown(f"### 🧠 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")
    st.markdown("---")

    st.markdown(f"""
    <div style="
        background:#ffffff;
        padding:20px;
        border-radius:16px;
        box-shadow:0px 10px 30px rgba(0,0,0,0.08);
        font-size:20px;
        font-weight:700;
        color:#0f172a;
    ">
        ❓ {st.session_state.last_question}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # ---------------- TEXT MODE ----------------
    if mode == "Text Mode":

        answer_key = f"text_answer_{st.session_state.question_count}"
        user_answer = st.text_area("✍️ Type your answer:", key=answer_key, height=220)

        colA, colB = st.columns(2)

        with colA:
            if st.button("✅ Submit Answer"):
                if user_answer.strip():

                    st.session_state.qa_list.append({
                        "question": st.session_state.last_question,
                        "answer": user_answer
                    })

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    if st.session_state.question_count >= TOTAL_QUESTIONS:
                        st.session_state.interview_ended = True
                        st.rerun()

                    q = generate_question(
                        st.session_state.resume_text,
                        st.session_state.previous_answers,
                        st.session_state.role,
                        st.session_state.difficulty,
                        st.session_state.interview_type
                    )

                    st.session_state.last_question = q
                    st.session_state.question_count += 1
                    st.rerun()

                else:
                    st.warning("⚠️ Please type an answer first!")

        with colB:
            if st.button("🛑 End Interview Now"):
                st.session_state.interview_ended = True
                st.rerun()


    # ---------------- VOICE MODE ----------------
    if mode == "Voice Mode":

        st.subheader("🎤 Record Your Answer")

        audio = mic_recorder(
            start_prompt="🎙️ Start Recording",
            stop_prompt="⏹️ Stop Recording",
            key=f"mic_{st.session_state.question_count}"
        )

        if audio:
            st.audio(audio["bytes"], format="audio/wav")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio["bytes"])
                audio_path = f.name

            user_answer_voice = transcribe_audio(audio_path)

            st.success("✅ Transcribed Answer:")
            st.write(user_answer_voice)

            colA, colB = st.columns(2)

            with colA:
                if st.button("🚀 Submit Voice Answer"):
                    if user_answer_voice.strip():

                        st.session_state.qa_list.append({
                            "question": st.session_state.last_question,
                            "answer": user_answer_voice
                        })

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        if st.session_state.question_count >= TOTAL_QUESTIONS:
                            st.session_state.interview_ended = True
                            st.rerun()

                        q = generate_question(
                            st.session_state.resume_text,
                            st.session_state.previous_answers,
                            st.session_state.role,
                            st.session_state.difficulty,
                            st.session_state.interview_type
                        )

                        st.session_state.last_question = q
                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()

                    else:
                        st.warning("⚠️ Voice answer empty. Try again!")

            with colB:
                if st.button("🛑 End Interview"):
                    st.session_state.interview_ended = True
                    st.rerun()


# ---------------- FINAL REPORT GENERATION ----------------
if st.session_state.interview_ended and st.session_state.final_report is None:

    hide_sidebar()

    st.markdown("<h2 style='text-align:center;'>⏳ Generating Final Report...</h2>", unsafe_allow_html=True)
    st.info("Please wait... evaluating your full interview MAANG style 🔥")

    report = evaluate_full_interview(
        st.session_state.qa_list,
        role=st.session_state.role,
        difficulty=st.session_state.difficulty,
        interview_type=st.session_state.interview_type
    )

    # ✅ force report to dict
    if report is None:
        report = {}

    if isinstance(report, str):
        try:
            report = json.loads(report)
        except:
            report = {}

    if not isinstance(report, dict):
        report = {}

    st.session_state.final_report = report

    save_report(
        candidate_name=st.session_state.candidate_name,
        role=st.session_state.role,
        difficulty=st.session_state.difficulty,
        interview_type=st.session_state.interview_type,
        mode=st.session_state.mode,
        report_json=report
    )

    st.success("✅ Report saved to database!")
    st.rerun()


# ---------------- FINAL REPORT DISPLAY ----------------
if st.session_state.final_report:

    hide_sidebar()

    report = st.session_state.final_report

    # ✅ force report to dict
    if report is None:
        report = {}

    if isinstance(report, str):
        try:
            report = json.loads(report)
        except:
            report = {}

    if not isinstance(report, dict):
        report = {}

    st.divider()
    st.subheader("📊 Final Interview Report")

    st.write(f"👤 Candidate: **{st.session_state.candidate_name}**")
    st.write(f"🎯 Role: **{st.session_state.role}**")
    st.write(f"⚡ Difficulty: **{st.session_state.difficulty}**")
    st.write(f"📌 Type: **{st.session_state.interview_type}**")
    st.write(f"🎤 Mode: **{st.session_state.mode}**")

    overall_score = report.get("overall_score", 0)
    verdict = report.get("verdict", "Unknown")

    st.success(f"🏆 Verdict: **{verdict}**")
    st.metric("Overall Score", f"{overall_score}/10")

    st.divider()
    st.subheader("🧠 Summary Feedback")
    st.write(report.get("summary_feedback", "No feedback generated."))

    st.subheader("📌 Improvement Plan")
    st.write(report.get("improvement_plan", "No improvement plan generated."))

    st.divider()
    st.subheader("📋 Question Wise Evaluation")

    qwise = report.get("question_wise", [])
    if isinstance(qwise, list) and len(qwise) > 0:
        df = pd.DataFrame(qwise)
        st.dataframe(df, use_container_width=True)

    st.divider()
    st.subheader("📄 Download PDF Report")

    pdf_file = generate_pdf_report(
        st.session_state.candidate_name,
        st.session_state.role,
        st.session_state.difficulty,
        st.session_state.interview_type,
        report
    )

    st.download_button(
        label="📄 Download PDF Report",
        data=pdf_file,
        file_name=f"{st.session_state.candidate_name}_AI_Interview_Report.pdf",
        mime="application/pdf"
    )

    st.divider()
    if st.button("🔁 Start New Interview"):
        reset_interview()
        st.rerun()
