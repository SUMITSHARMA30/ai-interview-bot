import streamlit as st
import os
import tempfile
import pandas as pd

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
        st.warning("⚠️ styles.css file missing!")

load_css()


# ---------------- FULLSCREEN BUTTON ----------------
st.markdown("""
<script>
function openFullscreen() {
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

<button onclick="openFullscreen()" style="
    background: #2563eb;
    color: white;
    padding: 12px 20px;
    border-radius: 12px;
    border: none;
    font-weight: 700;
    cursor: pointer;
    width: 100%;
    margin-bottom: 15px;
">
🚀 Enter Full Screen Interview Mode
</button>
""", unsafe_allow_html=True)


# ---------------- SESSION INIT ----------------
def init_session():
    defaults = {
        "page": "Candidate",
        "hr_logged_in": False,
        "qa_list": [],
        "previous_answers": "",
        "last_question": "",
        "interview_started": False,
        "question_count": 0,
        "interview_ended": False,
        "final_report": None,
        "resume_text": "",
        "candidate_name": "Unknown"
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


# ---------------- HR DASHBOARD LOGIN ----------------
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
st.markdown("<h1 class='main-title'>🤖 AI Powered Interview Bot</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>MAANG Style Mock Interview • Groq Powered • PDF Report + HR Dashboard</p>", unsafe_allow_html=True)

st.divider()


# ---------------- SETTINGS ----------------
st.sidebar.title("🛠️ Interview Settings")

role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])

TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 5, 20, 5)

mode = st.sidebar.radio("Interview Mode", ["Text Mode", "Voice Mode"])

st.sidebar.divider()
candidate_name = st.sidebar.text_input("Candidate Name", value=st.session_state.candidate_name)
st.session_state.candidate_name = candidate_name


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("📌 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

if uploaded_file:
    resume_text = extract_text(uploaded_file)
    st.session_state.resume_text = resume_text

    st.success("✅ Resume parsed successfully!")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "", role, difficulty, interview_type)

            st.session_state.last_question = q
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            if mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

            st.rerun()

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True
            st.rerun()


    # ---------------- INTERVIEW FLOW ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        if st.session_state.question_count > TOTAL_QUESTIONS:
            st.session_state.interview_ended = True
            st.rerun()

        # Progress bar
        st.progress(st.session_state.question_count / TOTAL_QUESTIONS)

        st.markdown(f"### 🧠 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")
        st.markdown("---")

        # Show ONLY current question
        st.markdown(f"## ❓ {st.session_state.last_question}")
        st.markdown("---")

        # ---------------- TEXT MODE ----------------
        if mode == "Text Mode":
            st.subheader("⌨️ Type Your Answer")

            answer_key = f"text_answer_{st.session_state.question_count}"
            user_answer = st.text_area("Answer:", key=answer_key, height=180)

            if st.button("✅ Submit Answer & Continue"):
                if user_answer.strip():

                    st.session_state.qa_list.append({
                        "question": st.session_state.last_question,
                        "answer": user_answer
                    })

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    # If last question done
                    if st.session_state.question_count >= TOTAL_QUESTIONS:
                        st.session_state.interview_ended = True
                        st.rerun()

                    # Generate next question
                    q = generate_question(
                        st.session_state.resume_text,
                        st.session_state.previous_answers,
                        role,
                        difficulty,
                        interview_type
                    )

                    st.session_state.last_question = q
                    st.session_state.question_count += 1
                    st.rerun()

                else:
                    st.warning("⚠️ Please type an answer first!")


        # ---------------- VOICE MODE ----------------
        if mode == "Voice Mode":
            st.subheader("🎤 Voice Mode Answer")

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

                if st.button("🚀 Submit Voice Answer & Continue"):
                    if user_answer_voice.strip():

                        st.session_state.qa_list.append({
                            "question": st.session_state.last_question,
                            "answer": user_answer_voice
                        })

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        # If last question done
                        if st.session_state.question_count >= TOTAL_QUESTIONS:
                            st.session_state.interview_ended = True
                            st.rerun()

                        # Generate next question
                        q = generate_question(
                            st.session_state.resume_text,
                            st.session_state.previous_answers,
                            role,
                            difficulty,
                            interview_type
                        )

                        st.session_state.last_question = q
                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()

                    else:
                        st.warning("⚠️ Voice answer empty, try again!")


    # ---------------- FINAL REPORT GENERATION ----------------
    if st.session_state.interview_ended and st.session_state.final_report is None:

        st.info("⏳ Generating final report... Please wait...")

        report = evaluate_full_interview(
            st.session_state.qa_list,
            role=role,
            difficulty=difficulty,
            interview_type=interview_type
        )

        st.session_state.final_report = report

        save_report(
            candidate_name=candidate_name,
            role=role,
            difficulty=difficulty,
            interview_type=interview_type,
            mode=mode,
            report_json=report
        )

        st.success("✅ Report saved to SQLite Database!")
        st.rerun()


    # ---------------- FINAL REPORT DISPLAY ----------------
    if st.session_state.final_report:

        report = st.session_state.final_report

        st.divider()
        st.subheader("📊 Final Interview Report")

        st.write(f"👤 Candidate: **{candidate_name}**")
        st.write(f"🎯 Role: **{role}**")
        st.write(f"⚡ Difficulty: **{difficulty}**")
        st.write(f"📌 Type: **{interview_type}**")
        st.write(f"🎤 Mode: **{mode}**")

        overall_score = report.get("overall_score", 0)
        verdict = report.get("verdict", "Unknown")

        st.success(f"🏆 Verdict: **{verdict}**")
        st.metric("Overall Score", f"{overall_score}/10")

        st.divider()
        st.subheader("🧠 Summary Feedback")
        st.write(report.get("summary_feedback", ""))

        st.subheader("📌 Improvement Plan")
        st.write(report.get("improvement_plan", ""))

        st.divider()
        st.subheader("📋 Question Wise Evaluation Table")

        qwise = report.get("question_wise", [])

        if qwise:
            df = pd.DataFrame(qwise)
            st.dataframe(df, use_container_width=True)

        # ---------------- PDF DOWNLOAD ----------------
        st.divider()
        st.subheader("📄 Download PDF Report")

        # ✅ FIXED: positional args (no keyword TypeError)
        pdf_file = generate_pdf_report(
            candidate_name,
            role,
            difficulty,
            interview_type,
            report
        )

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_file,
            file_name=f"{candidate_name}_AI_Interview_Report.pdf",
            mime="application/pdf"
        )

        st.divider()
        if st.button("🔁 Start New Interview"):
            reset_interview()
            st.rerun()

else:
    st.info("📌 Upload your resume to start the interview.")
