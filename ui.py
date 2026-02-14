import streamlit as st
import pandas as pd


def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def header_ui():
    st.markdown(
        """
        <div class="header-box">
            <h1>🤖 AI Interview Bot</h1>
            <p>MAANG-style Resume-based Mock Interview with Evaluation + HR Dashboard</p>
        </div>
        """,
        unsafe_allow_html=True
    )


def show_chat_bubbles(chat):
    for role, msg in chat:
        if role == "AI":
            st.markdown(f"<div class='chat-ai'><b>AI:</b> {msg}</div>", unsafe_allow_html=True)
        elif role == "You":
            st.markdown(f"<div class='chat-user'><b>You:</b> {msg}</div>", unsafe_allow_html=True)
        else:
            st.markdown(f"<div class='chat-eval'><b>Evaluation:</b> {msg}</div>", unsafe_allow_html=True)


def show_eval_table(report):
    qwise = report.get("question_wise", [])

    if not qwise:
        st.warning("No question-wise evaluation found.")
        return

    df = pd.DataFrame(qwise)

    df = df.rename(columns={
        "candidate_answer": "Candidate Answer",
        "ideal_answer": "Ideal Answer",
        "feedback": "Feedback",
        "improvement": "Improvement",
        "score": "Score",
        "question": "Question"
    })

    st.dataframe(df, use_container_width=True)
