import streamlit as st
import os
import tempfile
from streamlit_mic_recorder import mic_recorder
from groq import Groq

from utils.resume_parser import extract_text
from interviewer_engine import generate_next_question
from evaluator_v2 import evaluate_interview
from voice_engine import text_to_speech


# ---------------- CONFIG ----------------
st.set_page_config(page_title="Voice Interviewer V2", layout="wide")

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- CSS LOADER ----------------
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


# ---------------- PHASE PLAN ----------------
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
        "last_audio_played_for": "",
        "mic_key": 0
    }

    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_session()


# ---------------- RESET ----------------
def reset_all():
    for k in list(st.session_state.keys()):
        del st.session_state[k]
    st.rerun()


# ---------------- PHASE SWITCH ----------------
def move_to_next_phase():
    current = st.session_state.phase
    idx = PHASE_ORDER.index(current)

    if idx + 1 < len(PHASE_ORDER):
        st.session_state.phase = PHASE_ORDER[idx + 1]
        st.session_state.phase_question_count = 0
    else:
        st.session_state.ended = True


# ---------------- SILENCE CHECK ----------------
def is_silence(text: str):
    if text is None:
        return True
    cleaned = text.strip()
    if len(cleaned) < 3:
        return True
    if len(cleaned.split()) < 2:
        return True
    return False


# ---------------- UI HEADER ----------------
st.markdown("<h1 class='main-title'>🎤 Voice Interviewer V2</h1>", unsafe_allow_html=True)
st.markdown("<p class='subtitle'>Gemini Style AI Interview (Real MAANG Flow)</p>", unsafe_allow_html=True)
st.divider()


# ==========================================================
# START PAGE
# ==========================================================
if not st.session_state.started:

    st.subheader("👤 Candidate Details")

    st.session_state.candidate_name = st.text_input("Candidate Name", value=st.session_state.candidate_name)

    uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        st.session_state.resume_text = extract_text(uploaded_file)
        st.success("✅ Resume parsed successfully!")

    st.divider()

    st.markdown("""
        <div class="neon-card">
            ⚡ Interview will feel like a real MAANG interviewer <br>
            🎤 Speak naturally after the AI question is spoken <br>
            🧠 Silence / weak answers will trigger follow-up or next question
        </div>
    """, unsafe_allow_html=True)

    st.divider()

    if st.button("🚀 Start Interview", use_container_width=True):

        if not st.session_state.candidate_name.strip():
            st.warning("⚠️ Enter candidate name.")
            st.stop()

        if not st.session_state.resume_text.strip():
            st.warning("⚠️ Upload resume first.")
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
# INTERVIEW LOOP (GEMINI STYLE UI)
# ==========================================================
if st.session_state.started and not st.session_state.ended:

    st.markdown(f"### 🧠 Phase: `{st.session_state.phase}`")
    st.markdown(f"### 🔥 Question {st.session_state.total_question_count + 1}")

    st.markdown("""
        <div class="orb-container">
            <div class="orb"></div>
        </div>
        <div class="ai-speaking">AI Interviewer is speaking...</div>
        <div class="ai-subtext">Listen carefully, then answer naturally 🎧</div>
    """, unsafe_allow_html=True)

    # AUTO SPEAK QUESTION
    if st.session_state.last_audio_played_for != st.session_state.current_question:
        audio_file = text_to_speech(st.session_state.current_question)
        st.audio(audio_file, format="audio/mp3", autoplay=True)
        st.session_state.last_audio_played_for = st.session_state.current_question

    st.divider()

    st.subheader("🎤 Speak Your Answer (Recording)")

    # Only mic recorder (no extra button)
    audio = mic_recorder(
        start_prompt="🎙️ Start Speaking",
        stop_prompt="⏹️ Stop",
        key=f"mic_{st.session_state.mic_key}"
    )

    st.divider()

    if st.button("🛑 End Interview Now", use_container_width=True):
        st.session_state.ended = True
        st.rerun()

    # AUTO NEXT AFTER AUDIO
    if audio:

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio["bytes"])
            audio_path = f.name

        user_answer = transcribe_audio(audio_path)

        # SILENCE HANDLING
        if is_silence(user_answer):
            st.warning("⚠️ No response detected. Moving to next question...")

            silence_msg = "No response (silence / unclear answer)."
            st.session_state.conversation += f"Candidate: {silence_msg}\n"

        else:
            st.success("✅ Answer Captured")
            st.write(user_answer)
            st.session_state.conversation += f"Candidate: {user_answer}\n"

        # Update counts
        st.session_state.phase_question_count += 1
        st.session_state.total_question_count += 1

        # Phase complete?
        if st.session_state.phase_question_count >= PHASE_PLAN[st.session_state.phase]:
            move_to_next_phase()

        # Ended?
        if st.session_state.ended:
            st.rerun()

        # Generate next question
        q = generate_next_question(
            st.session_state.resume_text,
            st.session_state.conversation,
            st.session_state.phase
        )

        st.session_state.current_question = q
        st.session_state.conversation += f"\nInterviewer: {q}\n"

        # refresh mic component
        st.session_state.mic_key += 1

        st.rerun()


# ==========================================================
# FINAL REPORT
# ==========================================================
if st.session_state.ended:

    st.subheader("📊 Final Evaluation Report")

    report = evaluate_interview(st.session_state.conversation)

    verdict = report.get("verdict", "NO_HIRE")
    score = report.get("overall_score", 0)

    st.success(f"🏆 Verdict: {verdict}")
    st.metric("Overall Score", f"{score}/10")

    st.divider()

    st.markdown("### 🧠 Summary Feedback")
    st.write(report.get("summary_feedback", ""))

    st.markdown("### ✅ Strengths")
    strengths = report.get("strengths", [])
    if strengths:
        for s in strengths:
            st.markdown(f"- ✅ {s}")
    else:
        st.write("No strengths detected.")

    st.markdown("### ❌ Weaknesses")
    weaknesses = report.get("weaknesses", [])
    if weaknesses:
        for w in weaknesses:
            st.markdown(f"- ❌ {w}")
    else:
        st.write("No weaknesses detected.")

    st.markdown("### 📌 Improvement Plan")
    st.write(report.get("improvement_plan", ""))

    st.divider()

    st.markdown("### 📝 Full Interview Transcript")
    st.code(st.session_state.conversation)

    if st.button("🔁 Restart Interview", use_container_width=True):
        reset_all()
