import streamlit as st
import streamlit.components.v1 as components
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


# ---------------- FULLSCREEN PROMPT ----------------
def fullscreen_prompt():
    components.html("""
        <script>
        function goFullscreen() {
            let elem = document.documentElement;
            if (elem.requestFullscreen) {
                elem.requestFullscreen();
            } else if (elem.webkitRequestFullscreen) {
                elem.webkitRequestFullscreen();
            } else if (elem.msRequestFullscreen) {
                elem.msRequestFullscreen();
            }
        }
        </script>

        <div style="
            background:white;
            padding:20px;
            border-radius:14px;
            box-shadow:0px 10px 25px rgba(0,0,0,0.12);
            margin-bottom:20px;
            text-align:center;
            font-family:Arial;
        ">
            <h2 style="margin:0; color:#0f172a;">🚀 Fullscreen Interview Mode</h2>
            <p style="color:gray; margin-top:5px;">
                Click below to enter fullscreen for MAANG-style interview experience.
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
                Enter Fullscreen 🚀
            </button>
        </div>
    """, height=220)


# ---------------- SESSION INIT ----------------
def init_session():
    defaults = {
        "page": "Landing",
        "hr_logged_in": False,

        "candidate_name": "",
        "candidate_email": "",
        "candidate_phone": "",
        "position_applied": "",

        "resume_text": "",

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


# ---------------- RESET ----------------
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


# ==========================================================
# 🌟 LANDING PAGE (Gemini Style)
# ==========================================================
if st.session_state.page == "Landing":

    hide_sidebar()

    st.markdown("<h1 class='main-title'>✨ AI Interview Platform</h1>", unsafe_allow_html=True)
    st.markdown("<div class='glow-line'></div>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>MAANG-style Interview • AI Reports • HR Dashboard</p>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="gemini-card">
            <h2>👨‍💼 Admin Login</h2>
            <p>Manage questions, view candidates, analytics, and download interview reports.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Login as Admin", use_container_width=True):
            st.session_state.page = "HR_LOGIN"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="gemini-card">
            <h2>👨‍🎓 Candidate Login</h2>
            <p>Upload resume, attend interview in fullscreen mode and get AI evaluation report.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Login as Candidate", use_container_width=True):
            st.session_state.page = "CANDIDATE_LOGIN"
            st.rerun()

    st.stop()


# ==========================================================
# 🔐 HR LOGIN PAGE
# ==========================================================
if st.session_state.page == "HR_LOGIN":

    hide_sidebar()

    st.markdown("<h1 class='main-title'>🔐 HR Login</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Only Admin/HR can access this portal.</p>", unsafe_allow_html=True)

    password = st.text_input("Enter Admin Password", type="password")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Login", use_container_width=True):
            if password == st.secrets["HR_PASSWORD"]:
                st.session_state.hr_logged_in = True
                st.session_state.page = "HR_DASHBOARD"
                st.success("✅ Login successful!")
                st.rerun()
            else:
                st.error("❌ Wrong password!")

    with col2:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.page = "Landing"
            st.rerun()

    st.stop()


# ==========================================================
# 📊 HR DASHBOARD PAGE
# ==========================================================
if st.session_state.page == "HR_DASHBOARD":

    if not st.session_state.hr_logged_in:
        st.session_state.page = "HR_LOGIN"
        st.rerun()

    hr_dashboard()

    if st.button("⬅️ Logout"):
        st.session_state.hr_logged_in = False
        st.session_state.page = "Landing"
        st.rerun()

    st.stop()


# ==========================================================
# 👨‍🎓 CANDIDATE LOGIN PAGE
# ==========================================================
if st.session_state.page == "CANDIDATE_LOGIN":

    hide_sidebar()

    st.markdown("<h1 class='main-title'>👨‍🎓 Candidate Login</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Enter your details to start the interview.</p>", unsafe_allow_html=True)

    st.session_state.candidate_name = st.text_input("Full Name", value=st.session_state.candidate_name)
    st.session_state.candidate_email = st.text_input("Email", value=st.session_state.candidate_email)
    st.session_state.candidate_phone = st.text_input("Phone", value=st.session_state.candidate_phone)
    st.session_state.position_applied = st.text_input("Position Applied For", value=st.session_state.position_applied)

    uploaded_file = st.file_uploader("📌 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        st.session_state.resume_text = extract_text(uploaded_file)
        st.success("✅ Resume uploaded & parsed successfully!")

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Proceed to Interview Setup", use_container_width=True):

            if not st.session_state.candidate_name.strip():
                st.warning("⚠️ Please enter your name.")
                st.stop()

            if not st.session_state.resume_text.strip():
                st.warning("⚠️ Please upload resume first.")
                st.stop()

            st.session_state.page = "CANDIDATE_SETUP"
            st.rerun()

    with col2:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.page = "Landing"
            st.rerun()

    st.stop()


# ==========================================================
# ⚙️ CANDIDATE INTERVIEW SETUP
# ==========================================================
if st.session_state.page == "CANDIDATE_SETUP":

    hide_sidebar()

    st.markdown("<h1 class='main-title'>⚙️ Interview Setup</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Select role, difficulty, interview type, and mode.</p>", unsafe_allow_html=True)

    st.session_state.role = st.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
    st.session_state.difficulty = st.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
    st.session_state.interview_type = st.selectbox("Interview Type", ["Technical", "HR", "Mixed"])
    st.session_state.total_questions = st.slider("Number of Questions", 5, 20, 5)
    st.session_state.mode = st.radio("Interview Mode", ["Text Mode", "Voice Mode"])

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview", use_container_width=True):

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
            st.session_state.page = "INTERVIEW"
            st.rerun()

    with col2:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.page = "CANDIDATE_LOGIN"
            st.rerun()

    st.stop()


# ==========================================================
# 🧠 INTERVIEW SCREEN
# ==========================================================
if st.session_state.page == "INTERVIEW":

    hide_sidebar()

    if st.session_state.interview_started and not st.session_state.interview_ended:
        fullscreen_prompt()

    TOTAL_QUESTIONS = st.session_state.total_questions
    mode = st.session_state.mode

    st.progress(st.session_state.question_count / TOTAL_QUESTIONS)

    st.markdown(f"### 🧠 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")
    st.markdown("---")

    st.markdown(f"""
    <div style="
        background:#ffffff;
        padding:22px;
        border-radius:18px;
        box-shadow:0px 10px 30px rgba(0,0,0,0.10);
        font-size:20px;
        font-weight:800;
        color:#0f172a;
    ">
        ❓ {st.session_state.last_question}
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")


    # ---------------- TEXT MODE ----------------
    if mode == "Text Mode":

        answer_key = f"text_answer_{st.session_state.question_count}"
        user_answer = st.text_area("✍️ Type your answer:", key=answer_key, height=200)

        colA, colB = st.columns(2)

        with colA:
            if st.button("✅ Submit Answer & Next", use_container_width=True):

                if user_answer.strip():

                    st.session_state.qa_list.append({
                        "question": st.session_state.last_question,
                        "answer": user_answer
                    })

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    if st.session_state.question_count >= TOTAL_QUESTIONS:
                        st.session_state.interview_ended = True
                        st.session_state.page = "FINAL_REPORT"
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
            if st.button("🛑 End Interview", use_container_width=True):
                st.session_state.interview_ended = True
                st.session_state.page = "FINAL_REPORT"
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
                if st.button("🚀 Submit Voice Answer", use_container_width=True):

                    if user_answer_voice.strip():

                        st.session_state.qa_list.append({
                            "question": st.session_state.last_question,
                            "answer": user_answer_voice
                        })

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        if st.session_state.question_count >= TOTAL_QUESTIONS:
                            st.session_state.interview_ended = True
                            st.session_state.page = "FINAL_REPORT"
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
                if st.button("🛑 End Interview", use_container_width=True):
                    st.session_state.interview_ended = True
                    st.session_state.page = "FINAL_REPORT"
                    st.rerun()

    st.stop()


# ==========================================================
# 📊 FINAL REPORT PAGE
# ==========================================================
if st.session_state.page == "FINAL_REPORT":

    hide_sidebar()

    if st.session_state.final_report is None:

        st.markdown("<h2 style='text-align:center;'>⏳ Generating Final Report...</h2>", unsafe_allow_html=True)
        st.info("Please wait... evaluating your full interview MAANG style 🔥")

        report = evaluate_full_interview(
            st.session_state.qa_list,
            role=st.session_state.role,
            difficulty=st.session_state.difficulty,
            interview_type=st.session_state.interview_type
        )

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

        st.rerun()

    report = st.session_state.final_report

    st.markdown("<h1 class='main-title'>📊 Final Interview Report</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>AI generated MAANG-style evaluation</p>", unsafe_allow_html=True)

    st.write(f"👤 Candidate: **{st.session_state.candidate_name}**")
    st.write(f"📧 Email: **{st.session_state.candidate_email}**")
    st.write(f"📱 Phone: **{st.session_state.candidate_phone}**")
    st.write(f"💼 Position: **{st.session_state.position_applied}**")

    st.divider()

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

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🔁 New Interview", use_container_width=True):
            reset_interview()
            st.session_state.page = "Landing"
            st.rerun()

    with col2:
        if st.button("🏠 Go to Home", use_container_width=True):
            st.session_state.page = "Landing"
            st.rerun()
