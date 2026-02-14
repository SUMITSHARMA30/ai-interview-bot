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


# ---------------- PAGE CONFIG ----------------
st.set_page_config(page_title="AI Interview Bot", layout="wide")

st.title("🤖 AI Powered Interview Bot (MAANG Style)")
st.write("Upload your Resume and start a mock interview with full evaluation report at the end.")


# ---------------- GROQ CLIENT ----------------
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------------- ADMIN PANEL ----------------
st.sidebar.title("🛠️ Admin Panel (HR Settings)")

role = st.sidebar.selectbox("Select Role", ["SDE", "Data Scientist", "ML Engineer"])
difficulty = st.sidebar.selectbox("Select Difficulty", ["Easy", "Medium", "Hard"])
interview_type = st.sidebar.selectbox("Interview Type", ["Technical", "HR", "Mixed"])

TOTAL_QUESTIONS = st.sidebar.slider("Number of Questions", 3, 20, 5)

mode = st.sidebar.radio("Candidate Interview Mode", ["Text Mode", "Voice Mode"])
st.sidebar.divider()
st.sidebar.write("📌 These settings control question generation + evaluation.")


# ---------------- SPEECH TO TEXT ----------------
def transcribe_audio(audio_path):
    with open(audio_path, "rb") as f:
        transcription = client.audio.transcriptions.create(
            file=f,
            model="whisper-large-v3"
        )
    return transcription.text


# ---------------- SESSION INIT ----------------
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False

if "interview_ended" not in st.session_state:
    st.session_state.interview_ended = False

if "question_count" not in st.session_state:
    st.session_state.question_count = 0

if "last_question" not in st.session_state:
    st.session_state.last_question = ""

if "previous_answers" not in st.session_state:
    st.session_state.previous_answers = ""

if "qa_list" not in st.session_state:
    st.session_state.qa_list = []   # stores {"question": "...", "answer": "..."}

if "final_report" not in st.session_state:
    st.session_state.final_report = None


# ---------------- RESET FUNCTION ----------------
def reset_interview():
    st.session_state.interview_started = False
    st.session_state.interview_ended = False
    st.session_state.question_count = 0
    st.session_state.last_question = ""
    st.session_state.previous_answers = ""
    st.session_state.qa_list = []
    st.session_state.final_report = None


# ---------------- FILE UPLOAD ----------------
uploaded_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=["pdf", "docx"])


# ---------------- MAIN APP ----------------
if uploaded_file:
    resume_text = extract_text(uploaded_file)

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("🚀 Start Interview"):
            reset_interview()

            q = generate_question(resume_text, "", role, difficulty, interview_type)

            st.session_state.last_question = q
            st.session_state.interview_started = True
            st.session_state.question_count = 1

            # Store AI question in qa_list
            st.session_state.qa_list.append({"question": q, "answer": ""})

            # Speak only in Voice Mode
            if mode == "Voice Mode":
                voice_file = text_to_speech(q)
                st.audio(voice_file, format="audio/mp3")

            st.rerun()

    with col2:
        if st.button("🛑 End Interview"):
            st.session_state.interview_ended = True
            st.rerun()

    with col3:
        if st.button("🔁 Reset Interview"):
            reset_interview()
            st.rerun()

    st.divider()

    # ---------------- INTERVIEW CHAT UI ----------------
    st.subheader("💬 Interview Transcript")

    if st.session_state.qa_list:
        for i, qa in enumerate(st.session_state.qa_list, start=1):
            st.markdown(f"### Q{i}: {qa['question']}")
            if qa["answer"].strip():
                st.markdown(f"**Candidate Answer:** {qa['answer']}")
            else:
                st.info("⏳ Awaiting answer...")
            st.divider()

    # ---------------- INTERVIEW RUNNING ----------------
    if st.session_state.interview_started and not st.session_state.interview_ended:

        st.subheader(f"📌 Current Question {st.session_state.question_count} / {TOTAL_QUESTIONS}")

        # ---------------- TEXT MODE ----------------
        if mode == "Text Mode":
            st.subheader("⌨️ Text Answer Mode")

            user_answer = st.text_area("Write your answer here:", height=150)

            if st.button("✅ Submit Answer"):
                if user_answer.strip():

                    # Save answer to latest question
                    st.session_state.qa_list[-1]["answer"] = user_answer

                    # Update previous_answers memory
                    st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer}\n"

                    # If last question reached
                    if st.session_state.question_count >= TOTAL_QUESTIONS:
                        st.session_state.interview_ended = True
                        st.rerun()

                    # Generate next question
                    q = generate_question(
                        resume_text,
                        st.session_state.previous_answers,
                        role,
                        difficulty,
                        interview_type
                    )

                    st.session_state.last_question = q
                    st.session_state.question_count += 1

                    st.session_state.qa_list.append({"question": q, "answer": ""})
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

                        # Save answer to latest question
                        st.session_state.qa_list[-1]["answer"] = user_answer_voice

                        # Update memory
                        st.session_state.previous_answers += f"\nQ: {st.session_state.last_question}\nA: {user_answer_voice}\n"

                        # If last question reached
                        if st.session_state.question_count >= TOTAL_QUESTIONS:
                            st.session_state.interview_ended = True
                            st.rerun()

                        # Generate next question
                        q = generate_question(
                            resume_text,
                            st.session_state.previous_answers,
                            role,
                            difficulty,
                            interview_type
                        )

                        st.session_state.last_question = q
                        st.session_state.question_count += 1

                        st.session_state.qa_list.append({"question": q, "answer": ""})

                        # AI voice output
                        voice_file = text_to_speech(q)
                        st.audio(voice_file, format="audio/mp3")

                        st.rerun()

                    else:
                        st.warning("⚠️ Voice answer is empty. Try again.")

    # ---------------- INTERVIEW ENDED ----------------
    if st.session_state.interview_ended:

        st.subheader("📊 Final Interview Report")

        # Generate evaluation once
        if st.session_state.final_report is None:
            with st.spinner("⏳ Generating Final MAANG Report..."):
                report = evaluate_full_interview(
                    st.session_state.qa_list,
                    role,
                    difficulty,
                    interview_type
                )
                st.session_state.final_report = report

        report = st.session_state.final_report

        if "error" in report:
            st.error("❌ Report generation failed.")
            st.write(report)
        else:
            overall_score = report.get("overall_score", 0)
            verdict = report.get("verdict", "Unknown")
            summary_feedback = report.get("summary_feedback", "")
            improvement_plan = report.get("improvement_plan", "")

            st.success(f"🏆 Verdict: **{verdict}**")
            st.write(f"⭐ Overall Score: **{overall_score} / 10**")

            st.divider()
            st.subheader("📝 Summary Feedback")
            st.write(summary_feedback)

            st.subheader("🚀 Improvement Plan")
            st.write(improvement_plan)

            st.divider()
            st.subheader("📌 Question Wise Evaluation")

            qwise = report.get("question_wise", [])

            if qwise:
                table_data = []
                scores = []

                for i, item in enumerate(qwise, start=1):
                    table_data.append({
                        "Q No": i,
                        "Score": item.get("score", 0),
                        "Feedback": item.get("feedback", ""),
                        "Improvement": item.get("improvement", "")
                    })
                    scores.append(item.get("score", 0))

                df = pd.DataFrame(table_data)
                st.dataframe(df, use_container_width=True)

                st.divider()
                st.subheader("📈 Score Progress Chart")
                chart_df = pd.DataFrame({"Question": range(1, len(scores) + 1), "Score": scores})
                st.line_chart(chart_df.set_index("Question"))

                st.divider()
                st.subheader("📄 Download Full PDF Report")

                pdf_file = generate_pdf_report(
                    report=report,
                    role=role,
                    difficulty=difficulty,
                    interview_type=interview_type,
                    total_questions=TOTAL_QUESTIONS
                )

                st.download_button(
                    label="📥 Download Interview PDF Report",
                    data=pdf_file,
                    file_name="AI_Interview_Report.pdf",
                    mime="application/pdf"
                )

                st.divider()

                st.subheader("📌 Detailed Question Review")

                for i, item in enumerate(qwise, start=1):
                    st.markdown(f"## Q{i}: {item.get('question','')}")
                    st.markdown(f"### 🧑 Candidate Answer")
                    st.write(item.get("candidate_answer", ""))

                    st.markdown(f"### ⭐ Score: {item.get('score', 0)} / 10")
                    st.markdown("### ✅ Feedback")
                    st.write(item.get("feedback", ""))

                    st.markdown("### 🔥 Improvement")
                    st.write(item.get("improvement", ""))

                    st.markdown("### 🟢 Ideal Answer (MAANG Standard)")
                    st.write(item.get("ideal_answer", ""))

                    st.divider()

            else:
                st.warning("No question-wise evaluation found.")

else:
    st.info("📌 Upload your resume first to start.")
