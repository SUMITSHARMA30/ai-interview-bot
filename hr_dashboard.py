import streamlit as st
import pandas as pd
import json

from db import fetch_all_reports
from pdf_report import generate_pdf_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>View all candidate reports and download PDF.</p>", unsafe_allow_html=True)

    reports = fetch_all_reports()

    if not reports:
        st.warning("No reports found in database yet.")
        return

    df = pd.DataFrame(reports, columns=[
        "id", "candidate_name", "role", "difficulty",
        "interview_type", "mode", "report_json", "created_at"
    ])

    st.subheader("📌 All Reports")
    st.dataframe(df[["id", "candidate_name", "role", "difficulty", "interview_type", "mode", "created_at"]],
                 use_container_width=True)

    st.divider()
    st.subheader("🔍 View Report Details")

    report_id = st.number_input("Enter Report ID", min_value=1, step=1)

    selected = df[df["id"] == report_id]

    if selected.empty:
        st.info("Enter valid report ID to view.")
        return

    row = selected.iloc[0]
    report = json.loads(row["report_json"])

    st.success(f"Showing report for: {row['candidate_name']}")

    st.write("### 🏆 Verdict")
    st.write(report.get("verdict", "Unknown"))

    st.write("### ⭐ Overall Score")
    st.metric("Score", f"{report.get('overall_score', 0)}/10")

    st.write("### 🧠 Summary Feedback")
    st.write(report.get("summary_feedback", ""))

    st.write("### 📌 Improvement Plan")
    st.write(report.get("improvement_plan", ""))

    st.write("### 📋 Question Wise Evaluation")
    qwise = report.get("question_wise", [])

    if qwise:
        qdf = pd.DataFrame(qwise)
        st.dataframe(qdf, use_container_width=True)

    st.divider()
    st.subheader("📄 Download PDF Report")

    pdf_file = generate_pdf_report(
        candidate_name=row["candidate_name"],
        role=row["role"],
        difficulty=row["difficulty"],
        interview_type=row["interview_type"],
        report=report
    )

    st.download_button(
        label="📄 Download PDF",
        data=pdf_file,
        file_name=f"{row['candidate_name']}_Report.pdf",
        mime="application/pdf"
    )
