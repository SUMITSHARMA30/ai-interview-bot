import streamlit as st
import os
import tempfile

from streamlit_mic_recorder import mic_recorder
from groq import Groq

from utils.resume_parser import extract_text
from interviewer_engine import generate_next_question
from evaluator_v2 import evaluate_interview
from voice_engine import text_to_speech
from audio_utils import silence_detected


st.set_page_config(page_title="Voice Interviewer V2", layout="wide")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def load_css():
    try:
        with open("styles.css") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except:
        pass


load_css()


def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


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
        "last_audio_played_for": "",
        "orb_state": "idle",
        "silence_count": 0
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


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


def next_question():
    q = generate_next_question(
        st.session_state.resume_text,
        st.session_state.conversation,
        st.session_state.phase
    )

    st.session_state.current_question = q
    st.session_state.conversation += f"\nInterviewer: {q}\n"
    st.session_state.phase_question_count += 1
    st.session_state.total_question_count += 1

    # Phase complete?
    if st.session_state.phase_question_count >= PHASE_PLAN[st.session_state.phase]:
        move_to_next_phase()


# ---------------- UI ----------------
st.markdown("<h1 class='main-title'>🎤 Voice Interviewer V2</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Real MAANG Style AI Voice Interview Experience</p>", unsafe_allow_html=True)
st.divider()


# ---------------- START SCREEN ----------------
if not st.session_state.started:

    st.session_state.candidate_name = st.text_input("Candidate Name")

    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        st.session_state.resume_text = extract_text(uploaded_file)
        st.success("✅ Resume parsed successfully!")

    if st.button("🚀 Start Interview", use_container_width=True):

        if not st.session_state.candidate_name.strip():
            st.warning("Enter candidate name.")
            st.stop()

        if not st.session_state.resume_text.strip():
            st.warning("Upload resume first.")
            st.stop()

        st.session_state.started = True
        st.session_state.phase = "INTRO"
        st.session_state.phase_question_count = 0
        st.session_state.total_question_count = 0

        next_question()
        st.rerun()


# ---------------- INTERVIEW LOOP ----------------
if st.session_state.started and not st.session_state.ended:

    # Orb UI
    orb_class = "orb"
    if st.session_state.orb_state == "speaking":
        orb_class += " speaking"
    elif st.session_state.orb_state == "listening":
        orb_class += " listening"

    st.markdown(f"""
        <div class="orb-container">
            <div class="{orb_class}"></div>
        </div>
        <div class="status-text">
            Phase: {st.session_state.phase}
        </div>
    """, unsafe_allow_html=True)

    # Auto speak question once
    if st.session_state.last_audio_played_for != st.session_state.current_question:
        st.session_state.orb_state = "speaking"

        audio_file = text_to_speech(st.session_state.current_question)
        st.audio(audio_file, format="audio/mp3", autoplay=True)

        st.session_state.last_audio_played_for = st.session_state.current_question
        st.session_state.orb_state = "listening"

    st.divider()

    # Candidate recording (only 1 mic component)
    audio = mic_recorder(
        start_prompt="🎙️ Speak Now",
        stop_prompt="⏹️ Stop",
        key=f"mic_{st.session_state.total_question_count}"
    )

    if audio:
        st.session_state.orb_state = "listening"

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio["bytes"])
            audio_path = f.name

        # Silence detection
        silent, rms = silence_detected(audio["bytes"], silence_seconds=4, threshold=500)

        user_answer = transcribe_audio(audio_path)

        # Add candidate answer
        st.session_state.conversation += f"Candidate: {user_answer}\n"

        # Auto-next logic
        if silent:
            st.session_state.silence_count += 1
        else:
            st.session_state.silence_count = 0

        # If silence detected -> move next question
        if st.session_state.silence_count >= 1:
            st.session_state.silence_count = 0
            next_question()
            st.rerun()


# ---------------- FINAL REPORT ----------------
if st.session_state.ended:

    st.markdown("<h2 class='main-title'>📊 Final Interview Report</h2>", unsafe_allow_html=True)
    st.divider()

    report = evaluate_interview(st.session_state.conversation)

    st.success(f"🏆 Verdict: {report.get('verdict', 'NO_HIRE')}")
    st.metric("Overall Score", f"{report.get('overall_score', 0)}/10")

    st.markdown("<div class='report-card'>", unsafe_allow_html=True)

    st.subheader("🧠 Summary Feedback")
    st.write(report.get("summary_feedback", ""))

    st.subheader("✅ Strengths")
    st.write(report.get("strengths", []))

    st.subheader("❌ Weaknesses")
    st.write(report.get("weaknesses", []))

    st.subheader("📌 Improvement Plan")
    st.write(report.get("improvement_plan", ""))

    st.markdown("</div>", unsafe_allow_html=True)

    st.divider()
    st.subheader("📝 Full Transcript")
    st.code(st.session_state.conversation)

    if st.button("🔁 Restart Interview", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()
