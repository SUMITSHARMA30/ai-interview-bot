import streamlit as st
import tempfile
import json

from streamlit_mic_recorder import mic_recorder
from groq import Groq

from utils.resume_parser import extract_text
from interviewer_engine import generate_next_question
from evaluator_v2 import evaluate_interview
from voice_engine import text_to_speech


# ---------------- CONFIG ----------------
st.set_page_config(page_title="Voice Interviewer V2", layout="wide")

client = Groq(api_key=st.secrets["GROQ_API_KEY"])


# ---------------- LOAD CSS ----------------
def load_css():
    try:
        with open("styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


load_css()


# ---------------- SPEECH TO TEXT ----------------
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


# ---------------- SESSION INIT ----------------
def init_session():
    defaults = {
        "resume_text": "",
        "candidate_name": "",
        "conversation": "",

        "current_question": "",
        "phase": "INTRO",

        "started": False,
        "ended": False,

        "phase_question_count": 0,
        "total_question_count": 0,

        "last_spoken_question": "",
        "question_audio": None
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ---------------- PHASE FLOW ----------------
PHASE_PLAN = {
    "INTRO": 1,
    "RESUME_DEEP_DIVE": 2,
    "STRENGTH_WEAKNESS": 2,
    "TECHNICAL": 3,
    "ANALYTICAL_PUZZLE": 1,
    "HR_BEHAVIORAL": 2,
    "CLOSING": 1
}

PHASE_ORDER = list(PHASE_PLAN.keys())


def move_to_next_phase():
    current = st.session_state.phase
    idx = PHASE_ORDER.index(current)

    if idx + 1 < len(PHASE_ORDER):
        st.session_state.phase = PHASE_ORDER[idx + 1]
        st.session_state.phase_question_count = 0
    else:
        st.session_state.ended = True


# ---------------- UI HEADER ----------------
st.markdown("<h1 class='main-title'>🎤 Voice Interviewer V2</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Gemini Style AI Voice Interview Experience</p>", unsafe_allow_html=True)
st.divider()


# ==========================================================
# START SCREEN
# ==========================================================
if not st.session_state.started and not st.session_state.ended:

    st.markdown("<h2 class='section-title'>👤 Candidate Setup</h2>", unsafe_allow_html=True)

    st.session_state.candidate_name = st.text_input("Candidate Name", value=st.session_state.candidate_name)

    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        st.session_state.resume_text = extract_text(uploaded_file)
        st.success("✅ Resume parsed successfully!")

    st.divider()

    if st.button("🚀 Start Voice Interview", use_container_width=True):

        if not st.session_state.candidate_name.strip():
            st.warning("⚠️ Please enter candidate name.")
            st.stop()

        if not st.session_state.resume_text.strip():
            st.warning("⚠️ Please upload resume first.")
            st.stop()

        st.session_state.started = True
        st.session_state.phase = "INTRO"
        st.session_state.phase_question_count = 0
        st.session_state.total_question_count = 0
        st.session_state.conversation = ""

        q = generate_next_question(
            st.session_state.resume_text,
            st.session_state.conversation,
            st.session_state.phase
        )

        st.session_state.current_question = q
        st.session_state.conversation += f"\nInterviewer: {q}\n"

        st.rerun()


# ==========================================================
# INTERVIEW LOOP
# ==========================================================
if st.session_state.started and not st.session_state.ended:

    st.markdown(f"<div class='phase-tag'>Phase: {st.session_state.phase}</div>", unsafe_allow_html=True)

    # ---------------- GEMINI ORB UI ----------------
    st.markdown("""
        <div class="orb-wrapper">
            <div class="orb"></div>
            <div class="orb-glow"></div>
            <p class="orb-text">AI Interviewer is speaking...</p>
        </div>
    """, unsafe_allow_html=True)

    # ---------------- AUTO SPEAK QUESTION ----------------
    if st.session_state.current_question != st.session_state.last_spoken_question:
        st.session_state.question_audio = text_to_speech(st.session_state.current_question)
        st.session_state.last_spoken_question = st.session_state.current_question

    if st.session_state.question_audio:
        st.audio(st.session_state.question_audio, format="audio/mp3")

    st.divider()

    # ---------------- RECORD ANSWER ----------------
    st.markdown("<h3 class='section-title'>🎤 Speak Your Answer</h3>", unsafe_allow_html=True)

    audio = mic_recorder(
        start_prompt="🎙️ Start Speaking",
        stop_prompt="⏹️ Stop",
        key=f"mic_{st.session_state.total_question_count}"
    )

    if audio:

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio["bytes"])
            audio_path = f.name

        user_answer = transcribe_audio(audio_path).strip()

        # ---------------- SILENCE / LOW RESPONSE DETECTION ----------------
        if len(user_answer.split()) < 3:
            st.warning("🤫 No clear response detected. Moving to next question...")

            st.session_state.conversation += "Candidate: (No response)\n"

            st.session_state.phase_question_count += 1
            st.session_state.total_question_count += 1

            if st.session_state.phase_question_count >= PHASE_PLAN[st.session_state.phase]:
                move_to_next_phase()

            if st.session_state.ended:
                st.rerun()

            q = generate_next_question(
                st.session_state.resume_text,
                st.session_state.conversation,
                st.session_state.phase
            )

            st.session_state.current_question = q
            st.session_state.conversation += f"\nInterviewer: {q}\n"
            st.rerun()

        # ---------------- VALID ANSWER ----------------
        st.success("✅ Answer Recorded")
        st.markdown(f"<div class='answer-box'>{user_answer}</div>", unsafe_allow_html=True)

        st.session_state.conversation += f"Candidate: {user_answer}\n"

        st.session_state.phase_question_count += 1
        st.session_state.total_question_count += 1

        if st.session_state.phase_question_count >= PHASE_PLAN[st.session_state.phase]:
            move_to_next_phase()

        if st.session_state.ended:
            st.rerun()

        q = generate_next_question(
            st.session_state.resume_text,
            st.session_state.conversation,
            st.session_state.phase
        )

        st.session_state.current_question = q
        st.session_state.conversation += f"\nInterviewer: {q}\n"
        st.rerun()

    # Emergency end
    if st.button("🛑 End Interview Now", use_container_width=True):
        st.session_state.ended = True
        st.rerun()


# ==========================================================
# FINAL REPORT
# ==========================================================
if st.session_state.ended:

    st.markdown("<h2 class='section-title'>📊 Final Interview Evaluation</h2>", unsafe_allow_html=True)

    report = evaluate_interview(st.session_state.conversation)

    if isinstance(report, str):
        try:
            report = json.loads(report)
        except:
            report = {}

    if not isinstance(report, dict):
        report = {}

    verdict = report.get("verdict", "NO_HIRE")
    score = report.get("overall_score", 0)

    st.success(f"🏆 Verdict: {verdict}")
    st.metric("Overall Score", f"{score}/10")

    st.divider()

    st.markdown("### 🧠 Summary Feedback")
    st.write(report.get("summary_feedback", "No feedback generated."))

    st.markdown("### ✅ Strengths")
    st.write(report.get("strengths", []))

    st.markdown("### ❌ Weaknesses")
    st.write(report.get("weaknesses", []))

    st.markdown("### 📌 Improvement Plan")
    st.write(report.get("improvement_plan", ""))

    st.divider()

    st.markdown("### 📝 Full Transcript")
    st.code(st.session_state.conversation)

    if st.button("🔁 Restart Interview", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
