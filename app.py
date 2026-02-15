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


# ---------------- FULLSCREEN PROMPT ----------------
def fullscreen_prompt():
    components.html("""
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
            margin-bottom:20px;
            text-align:center;
            font-family:Arial;
        ">
            <h2 style="margin:0; color:#0f172a;">🚀 Interview Fullscreen Mode</h2>
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


# ---------------- LANDING PAGE ----------------
if st.session_state.page == "Landing":

    st.markdown("<h1 class='main-title'>✨ AI Interview Platform</h1>", unsafe_allow_html=True)
    st.markdown("<div class='glow-line'></div>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>MAANG-style Interview • AI Reports • HR Dashboard</p>", unsafe_allow_html=True)

    st.markdown("<div class='card-container'>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div class="gemini-card">
            <h2>👨‍💼 Admin Login</h2>
            <p>Manage interview questions, view candidates, analytics and final reports.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Login as Admin", key="admin_btn"):
            st.session_state.page = "HR"
            st.rerun()

    with col2:
        st.markdown("""
        <div class="gemini-card">
            <h2>👨‍🎓 Candidate Login</h2>
            <p>Upload resume, attend MAANG-style interview, get AI evaluation report.</p>
        </div>
        """, unsafe_allow_html=True)

        if st.button("Login as Candidate", key="candidate_btn"):
            st.session_state.page = "Candidate"
            st.rerun()

    st.stop()
