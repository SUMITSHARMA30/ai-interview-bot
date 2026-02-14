import streamlit as st
import tempfile
import os
import pandas as pd

from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_full_interview
from tts_engine import text_to_speech
from streamlit_mic_recorder import mic_recorder
from groq import Groq

from pdf_report import generate_pdf_report
from db import init_db, save_report, fetch_all_reports

# -----------------------------------
# INITIAL SETUP
# -----------------------------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

init_db()

# -----------------------------------
# LOAD CSS
# -----------------------------------
def load_css():
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()

# -----------------------------------
# HEADER
# -----------------------------------
st.markdown("""
<div style="
    background: linear-gradient(90deg, #2563eb, #7c3aed);
    padding: 30px;
    border-radius: 22px;
    margin-bottom: 25px;
    box-shadow: 0px 15px 40px rgba(0,0,0,0.45);
">
    <h1 style="margin:0; font-size:42px;">🤖 AI Interview Bot</h1>
    <p style="margin-top:8px; color:#e0e7ff;">
        MAANG-style Resume-based Mock Interview with HR Dashboard
    </p>
</div>
""", unsafe_allow_html=True)

# -----------------------------------
# SIDEBAR – ADMIN / HR PANEL
# -----------------------------------
st.sidebar.title("🛠️ HR Control Panel")

role = st.sidebar.selectbox("Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])
TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 3, 15, 5)

mode = st.sidebar.radio("Interview Mode", ["Text Mode", "Voice Mode"])

st.sidebar.divider()
if st.sidebar.button("📊 View HR Dashboard"):
    st.session_state.view_dashboard = True

# -----------------------------------
# SESSION STATE
# -----------------------------------
defaults = {
    "started": False,
    "ended": False,
    "q_index": 0,
    "qa_list": [],
    "current_question": "",
    "candidate_name": "",
    "resume_text": "",
    "final_report": None,
    "view_dashboard": False
}

for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# -----------------------------------
# HR DASHBOARD
# -----------------------------------
if st.session_state.view_dashboard:
    st.subheader("📊 HR Dashboard")
    reports = fetch_all_reports()

    if reports:
        df = pd.DataFrame(reports)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No reports found.")

    if st.button("⬅ Back"):
        st.session_state.view_dashboard = False

    st.stop()

# -----------------------------------
# CANDIDATE INPUT
# -----------------------------------
st.subheader("🎯 Candidate Interview Portal")

st.session_state.candidate_name = st.text_input("Candidate Name")

uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

if uploaded_file:
    st.session_state.resume_text = extract_text(uploaded_file)

# -----------------------------------
# START INTERVIEW
# -----------------------------------
if st.button("🚀 Start Interview", disabled=not uploaded_file):
    st.session_state.started = True
    st.session_state.ended = False
    st.session_state.q_index = 1
    st.session_state.qa_list = []

    q = generate_question(
        st.session_state.resume_text,
        "",
        role,
        difficulty,
        interview_type
    )

    st.session_state.current_question = q

    if mode == "Voice Mode":
        audio = text_to_speech(q)
        st.audio(audio, format="audio/mp3")

# -----------------------------------
# INTERVIEW FLOW
# -----------------------------------
if st.session_state.started and not st.session_state.ended:

    st.markdown(f"### 📌 Question {st.session_state.q_index} / {TOTAL_QUESTIONS}")
    st.markdown(f"""
    <div class="chat-box ai-msg">
        <b>🤖 AI Question</b><br>
        {st.session_state.current_question}
    </div>
    """, unsafe_allow_html=True)

    user_answer = ""

    # ---------- TEXT MODE ----------
    if mode == "Text Mode":
        user_answer = st.text_area(
            "Your Answer",
            key=f"answer_{st.session_state.q_index}"
        )

        submitted = st.button("✅ Submit Answer")

    # ---------- VOICE MODE ----------
    else:
        audio = mic_recorder(
            start_prompt="🎙️ Start Recording",
            stop_prompt="⏹️ Stop Recording",
            key=f"mic_{st.session_state.q_index}"
        )

        submitted = False

        if audio:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio["bytes"])
                path = f.name

            user_answer = client.audio.transcriptions.create(
                file=open(path, "rb"),
                model="whisper-large-v3"
            ).text

            st.markdown(f"""
            <div class="chat-box user-msg">
                <b>🧑 Your Answer</b><br>
                {user_answer}
            </div>
            """, unsafe_allow_html=True)

            submitted = st.button("🚀 Submit Voice Answer")

    # ---------- HANDLE SUBMIT ----------
    if submitted and user_answer.strip():

        st.session_state.qa_list.append({
            "question": st.session_state.current_question,
            "answer": user_answer
        })

        if st.session_state.q_index >= TOTAL_QUESTIONS:
            st.session_state.ended = True
        else:
            st.session_state.q_index += 1
            next_q = generate_question(
                st.session_state.resume_text,
                str(st.session_state.qa_list),
                role,
                difficulty,
                interview_type
            )
            st.session_state.current_question = next_q

        st.rerun()

# -----------------------------------
# FINAL EVALUATION
# -----------------------------------
if st.session_state.ended and not st.session_state.final_report:

    report = evaluate_full_interview(
        st.session_state.qa_list,
        role,
        difficulty,
        interview_type
    )

    st.session_state.final_report = report

    save_report(
        st.session_state.candidate_name,
        role,
        difficulty,
        interview_type,
        report
    )

# -----------------------------------
# FINAL REPORT UI
# -----------------------------------
if st.session_state.final_report:

    r = st.session_state.final_report

    st.subheader("🏁 Final Interview Result")

    st.metric("Overall Score", f"{r['overall_score']} / 10")
    st.success(f"Verdict: **{r['verdict']}**")

    st.markdown("### 🧠 Summary Feedback")
    st.write(r["summary_feedback"])

    st.markdown("### 📌 Improvement Plan")
    st.write(r["improvement_plan"])

    st.markdown("### 📄 Download Report")

    pdf = generate_pdf_report(
        st.session_state.candidate_name,
        role,
        difficulty,
        interview_type,
        r
    )

    st.download_button(
        "⬇ Download PDF Report",
        pdf,
        file_name="AI_Interview_Report.pdf",
        mime="application/pdf"
    )

    if st.button("🔁 Start New Interview"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()
