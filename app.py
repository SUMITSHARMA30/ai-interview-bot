import streamlit as st
import tempfile
import os
import pandas as pd
from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_answer
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech
from groq import Groq

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from io import BytesIO
from datetime import datetime


# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with evaluation.")

# ---------------- GROQ CLIENT ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- CONFIG ----------------
TOTAL_QUESTIONS = 5


# ---------------- PDF REPORT FUNCTIONS ----------------
def wrap_text(text, max_chars=95):
    words = str(text).split()
    lines = []
    line = ""

    for word in words:
        if len(line + word) < max_chars:
            line += word + " "
        else:
            lines.append(line.strip())
            line = word + " "

    if line:
        lines.append(line.strip())

    return lines


def generate_pdf_report(chat, avg_score, verdict, scores):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    c.setFillColor(colors.darkblue)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, height - 50, "AI Interview Report (MAANG Style)")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 11)
    c.drawString(50, height - 75, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    c.line(50, height - 85, width - 50, height - 85)

    y = height - 120
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Summary")
    y -= 25

    c.setFont("Helvetica", 12)
    c.drawString(50, y, f"Final Score: {round(avg_score, 2)} / 10")
    y -= 20
    c.drawString(50, y, f"Verdict: {verdict}")
    y -= 30

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Score Breakdown (Per Question)")
    y -= 20

    c.setFont("Helvetica", 11)
    for i, score in enumerate(scores):
        c.drawString(60, y, f"Q{i+1}: {score} / 10")
        y -= 15
        if y < 100:
            c.showPage()
            y = height - 60

    y -= 20

    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, y, "Interview Transcript")
    y -= 25

    for role, msg in chat:
        if y < 120:
            c.showPage()
            y = height - 60

        if role == "AI":
            c.setFillColor(colors.darkblue)
            c.setFont("Helvetica-Bold", 11)
            prefix = "AI Question:"
        elif role == "You":
            c.setFillColor(colors.darkgreen)
            c.setFont("Helvetica-Bold", 11)
            prefix = "Candidate Answer:"
        else:
            c.setFillColor(colors.darkred)
            c.setFont("Helvetica-Bold", 11)
            prefix = "Evaluation:"

        c.drawString(50, y, prefix)
        y -= 15

        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)

        wrapped_lines = wrap_text(msg, 95)
        for line in wrapped_lines:
            if y < 80:
                c.showPage()
                y = height - 60
                c.setFont("Helvetica", 10)

            c.drawString(60, y, line)
            y -= 12

        y -= 15

    c.save()
    buffer.seek(0)
    return buffer


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

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False

if "mode" not in st.session_state:
    st.session_state.mode = None


def reset_interview():
    st.session_state.chat = []
    st.session_state.previous_answers = ""
    st.session_state.last_question = ""
    st.session_state.interview_started = False
    st.session_state.question_count = 0
    st.session_state.scores = []
    st.session_state.interview_ended = False


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])


# ---------------- MAIN APP ----------------
if uploaded_file:
    resume_text = extract_text(uploaded_file)

    st.divider()
    st.subheader("🎯 Choose Interview Mode")

    mode = st.radio(
        "Select Interview Mode",
        ["Text Mode", "Voice Mode"],
        index=0
    )

    st.session_state.mode = mode

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "")
            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            # Only Voice Mode should speak questions
            if st.session_state.mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True

    # ---------------- CHAT DISPLAY ----------------
    st.subheader("💬 Interview Chat")
    for role, msg in st.session_state.chat:
        st.write(f"**{role}:** {msg}")

    # ---------------- FINAL REPORT ----------------
    if st.session_state.interview_ended:
        st.divider()
        st.subheader("📊 Final Interview Report")

        if len(st.session_state.scores) > 0:
            avg_score = sum(st.session_state.scores) / len(st.session_state.scores)
        else:
            avg_score = 0

        st.write(f"✅ Questions Attempted: **{st.session_state.question_count - 1}** / {TOTAL_QUESTIONS}")
        st.write(f"⭐ Average Score: **{round(avg_score, 2)} / 10**")

        if avg_score >= 8:
            verdict = "🔥 Strong Hire"
        elif avg_score >= 6:
            verdict = "✅ Hire / Good Candidate"
        elif avg_score >= 4:
            verdict = "⚠️ Maybe (Needs Improvement)"
        else:
            verdict = "❌ Not Ready Yet"

        st.success(f"🏆 Final Verdict: **{verdict}**")

        st.divider()
        st.subheader("📈 Score Progress Chart")

        if len(st.session_state.scores) > 0:
            df = pd.DataFrame({
                "Question": list(range(1, len(st.session_state.scores) + 1)),
                "Score": st.session_state.scores
            })
            st.line_chart(df.set_index("Question"))

        st.divider()
        st.subheader("📄 Download Interview Report")

        pdf_file = generate_pdf_report(
            st.session_state.chat,
            avg_score,
            verdict,
            st.session_state.scores
        )

        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_file,
            file_name="AI_Interview_Report.pdf",
            mime="application/pdf"
        )

        st.divider()
        if st.button("🔁 Start New Interview"):
            reset_interview()
            st.rerun()

    # ---------------- INTERVIEW INPUT MODE ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        if st.session_state.question_count > TOTAL_QUESTIONS:
            st.session_state.interview_ended = True
            st.rerun()

        st.divider()
        st.write(f"📌 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")

        # ---------------- TEXT MODE ----------------
        if st.session_state.mode == "Text Mode":
            st.subheader("⌨️ Text Answer Mode")

            user_answer = st.text_input("Your Answer:")

            if st.button("✅ Submit Answer"):
                if user_answer.strip() != "":
                    st.session_state.chat.append(("You", user_answer))

                    evaluation = evaluate_answer(st.session_state.last_question, user_answer)
                    st.session_state.chat.append(("Evaluation", str(evaluation)))

                    try:
                        st.session_state.scores.append(float(evaluation["final_score"]))
                    except:
                        pass

                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    q = generate_question(resume_text, st.session_state.previous_answers)
                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))

                    st.session_state.question_count += 1
                    st.rerun()
                else:
                    st.warning("Please write an answer first.")

        # ---------------- VOICE MODE ----------------
        if st.session_state.mode == "Voice Mode":
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
                    if user_answer_voice.strip() != "":
                        st.session_state.chat.append(("You", user_answer_voice))

                        evaluation = evaluate_answer(st.session_state.last_question, user_answer_voice)
                        st.session_state.chat.append(("Evaluation", str(evaluation)))

                        try:
                            st.session_state.scores.append(float(evaluation["final_score"]))
                        except:
                            pass

                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        q = generate_question(resume_text, st.session_state.previous_answers)
                        st.session_state.last_question = q
                        st.session_state.chat.append(("AI", q))

                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()
                    else:
                        st.warning("Voice answer is empty. Try again.")

else:
    st.info("📌 Upload your resume first to start.")
