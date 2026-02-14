import streamlit as st
import tempfile
import os
import pandas as pd
from resume_parser import extract_text
from ai_engine import generate_question
from evaluator import evaluate_full_interview
from streamlit_mic_recorder import mic_recorder
from tts_engine import text_to_speech
from groq import Groq
from pdf_report import generate_pdf_report
from db import init_db, save_report, fetch_all_reports


# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with final evaluation report.")


# ---------------- INIT DATABASE ----------------
init_db()


# ---------------- GROQ CLIENT ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- ADMIN PANEL ----------------
st.sidebar.title("🛠️ Admin Panel (HR Settings)")

role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])
TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 3, 20, 5)

mode = st.sidebar.radio("Candidate Mode", ["Text Mode", "Voice Mode"])

st.sidebar.divider()
st.sidebar.subheader("📊 HR Dashboard")
show_dashboard = st.sidebar.checkbox("Show Saved Reports")


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

if "qa_list" not in st.session_state:
    st.session_state.qa_list = []

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False

if "final_report" not in st.session_state:
    st.session_state.final_report = None


# ---------------- RESET FUNCTION ----------------
def reset_interview():
    st.session_state.chat = []
    st.session_state.qa_list = []
    st.session_state.last_question = ""
    st.session_state.question_count = 0
    st.session_state.interview_started = False
    st.session_state.interview_ended = False
    st.session_state.final_report = None


# ---------------- HR DASHBOARD ----------------
if show_dashboard:
    st.subheader("📊 HR Dashboard - Saved Reports")

    reports = fetch_all_reports()

    if reports:
        df = pd.DataFrame(reports)
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No reports saved yet.")

    st.divider()


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("📄 Upload Resume (PDF/DOCX)", type=["pdf", "docx"])

candidate_name = st.text_input("Candidate Name (Optional)", "")


# ---------------- MAIN APP ----------------
if uploaded_file:

    resume_text = extract_text(uploaded_file)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "", role, difficulty, interview_type)

            st.session_state.last_question = q
            st.session_state.chat.append(("AI", q))
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            if mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True


    # ---------------- CHAT DISPLAY ----------------
    st.subheader("💬 Interview Chat")
    for role_msg, msg in st.session_state.chat:
        st.write(f"**{role_msg}:** {msg}")


    # ---------------- INTERVIEW FLOW ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        st.divider()
        st.write(f"📌 Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")

        # ---------------- TEXT MODE ----------------
        if mode == "Text Mode":
            st.subheader("⌨️ Text Answer Mode")

            user_answer = st.text_area("Type Your Answer Here:")

            if st.button("✅ Submit Answer"):
                if user_answer.strip():

                    st.session_state.chat.append(("You", user_answer))

                    st.session_state.qa_list.append({
                        "question": st.session_state.last_question,
                        "answer": user_answer
                    })

                    if st.session_state.question_count >= TOTAL_QUESTIONS:
                        st.session_state.interview_ended = True
                        st.rerun()

                    q = generate_question(
                        resume_text,
                        st.session_state.qa_list,
                        role,
                        difficulty,
                        interview_type
                    )

                    st.session_state.last_question = q
                    st.session_state.chat.append(("AI", q))
                    st.session_state.question_count += 1

                    st.rerun()

                else:
                    st.warning("⚠️ Answer cannot be empty.")


        # ---------------- VOICE MODE ----------------
        if mode == "Voice Mode":
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
                    if user_answer_voice.strip():

                        st.session_state.chat.append(("You", user_answer_voice))

                        st.session_state.qa_list.append({
                            "question": st.session_state.last_question,
                            "answer": user_answer_voice
                        })

                        if st.session_state.question_count >= TOTAL_QUESTIONS:
                            st.session_state.interview_ended = True
                            st.rerun()

                        q = generate_question(
                            resume_text,
                            st.session_state.qa_list,
                            role,
                            difficulty,
                            interview_type
                        )

                        st.session_state.last_question = q
                        st.session_state.chat.append(("AI", q))
                        st.session_state.question_count += 1

                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()

                    else:
                        st.warning("⚠️ Voice answer is empty. Try again.")



    # ---------------- FINAL REPORT ----------------
    if st.session_state.interview_ended and st.session_state.final_report is None:

        st.divider()
        st.subheader("📊 Generating Final Report...")

        final_report = evaluate_full_interview(
            st.session_state.qa_list,
            role,
            difficulty,
            interview_type
        )

        st.session_state.final_report = final_report
        st.rerun()


    # ---------------- SHOW FINAL REPORT ----------------
    if st.session_state.final_report is not None:

        report = st.session_state.final_report

        if "error" in report:
            st.error("❌ Report generation failed.")
            st.write(report)
        else:
            st.divider()
            st.subheader("🏆 Final Interview Report")

            st.write(f"🎯 Role: **{role}**")
            st.write(f"⚡ Difficulty: **{difficulty}**")
            st.write(f"📌 Interview Type: **{interview_type}**")

            st.success(f"⭐ Overall Score: **{report['overall_score']} / 10**")
            st.info(f"📌 Verdict: **{report['verdict']}**")

            st.subheader("📝 Summary Feedback")
            st.write(report["summary_feedback"])

            st.subheader("📌 Improvement Plan")
            st.write(report["improvement_plan"])


            # ---------------- QUESTION WISE TABLE ----------------
            st.subheader("📋 Question-Wise Evaluation")

            qwise_df = pd.DataFrame(report["question_wise"])
            st.dataframe(qwise_df, use_container_width=True)


            # ---------------- SAVE REPORT TO SQLITE ----------------
            if st.button("💾 Save Report to Database"):
                save_report(
                    candidate_name=candidate_name if candidate_name.strip() else "Unknown",
                    role=role,
                    difficulty=difficulty,
                    interview_type=interview_type,
                    overall_score=report["overall_score"],
                    verdict=report["verdict"],
                    report_json=report
                )
                st.success("✅ Report Saved Successfully!")


            # ---------------- PDF DOWNLOAD ----------------
            st.subheader("📄 Download PDF Report")

            pdf_file = generate_pdf_report(
                candidate_name if candidate_name.strip() else "Unknown",
                role,
                difficulty,
                interview_type,
                report
            )

            st.download_button(
                label="📄 Download Interview PDF",
                data=pdf_file,
                file_name="AI_Interview_Report.pdf",
                mime="application/pdf"
            )


            st.divider()
            if st.button("🔁 Start New Interview"):
                reset_interview()
                st.rerun()


else:
    st.info("📌 Upload your resume first to start.")
