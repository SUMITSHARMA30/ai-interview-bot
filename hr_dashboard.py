import streamlit as st
import pandas as pd
import plotly.express as px
import json

from db import fetch_all_reports, fetch_report_by_id, delete_report
from pdf_report import generate_pdf_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Analytics + Candidate Reports (MAANG Style)</p>", unsafe_allow_html=True)
    st.divider()

    reports = fetch_all_reports()

    if not reports or len(reports) == 0:
        st.warning("⚠️ No interview reports found yet.")
        return

    df = pd.DataFrame(reports, columns=[
        "id", "candidate_name", "role", "difficulty", "interview_type",
        "mode", "verdict", "overall_score", "plagiarism_percentage", "timestamp"
    ])

    df["overall_score"] = pd.to_numeric(df["overall_score"], errors="coerce").fillna(0)
    df["plagiarism_percentage"] = pd.to_numeric(df["plagiarism_percentage"], errors="coerce").fillna(0)

    # ---------------- FILTERS ----------------
    st.subheader("🔍 Search & Filters")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        name_filter = st.text_input("Candidate Name")

    with col2:
        role_filter = st.selectbox("Role", ["All"] + sorted(df["role"].dropna().unique().tolist()))

    with col3:
        difficulty_filter = st.selectbox("Difficulty", ["All"] + sorted(df["difficulty"].dropna().unique().tolist()))

    with col4:
        verdict_filter = st.selectbox("Verdict", ["All"] + sorted(df["verdict"].dropna().unique().tolist()))

    filtered_df = df.copy()

    if name_filter.strip():
        filtered_df = filtered_df[filtered_df["candidate_name"].str.contains(name_filter, case=False, na=False)]

    if role_filter != "All":
        filtered_df = filtered_df[filtered_df["role"] == role_filter]

    if difficulty_filter != "All":
        filtered_df = filtered_df[filtered_df["difficulty"] == difficulty_filter]

    if verdict_filter != "All":
        filtered_df = filtered_df[filtered_df["verdict"] == verdict_filter]

    st.divider()

    # ---------------- TABLE ----------------
    st.subheader("📋 Candidate Reports Table")
    st.dataframe(filtered_df, use_container_width=True)

    st.divider()

    # ---------------- EXPORT CSV ----------------
    st.subheader("📤 Export Filtered Reports")

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name="filtered_interview_reports.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()

    # ---------------- ANALYTICS ----------------
    st.subheader("📊 Analytics")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### Verdict Distribution")
        verdict_counts = filtered_df["verdict"].value_counts().reset_index()
        verdict_counts.columns = ["verdict", "count"]
        fig = px.pie(verdict_counts, names="verdict", values="count", hole=0.4)
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        st.markdown("### Avg Score by Role")
        role_avg = filtered_df.groupby("role")["overall_score"].mean().reset_index()
        fig = px.bar(role_avg, x="role", y="overall_score")
        st.plotly_chart(fig, use_container_width=True)

    colC, colD = st.columns(2)

    with colC:
        st.markdown("### Avg Score by Difficulty")
        diff_avg = filtered_df.groupby("difficulty")["overall_score"].mean().reset_index()
        fig = px.bar(diff_avg, x="difficulty", y="overall_score")
        st.plotly_chart(fig, use_container_width=True)

    with colD:
        st.markdown("### Plagiarism Distribution")
        fig = px.histogram(filtered_df, x="plagiarism_percentage", nbins=10)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---------------- REPORT VIEWER ----------------
    st.subheader("📌 View Candidate Full Report")

    report_id = st.selectbox("Select Candidate Report ID", filtered_df["id"].tolist())

    if not report_id:
        return

    report_data = fetch_report_by_id(report_id)

    if report_data is None:
        st.error("❌ Report not found.")
        return

    report_json = report_data.get("report_json", {})
    if not isinstance(report_json, dict):
        report_json = {}

    verdict = report_json.get("verdict", "UNKNOWN")
    overall_score = report_json.get("overall_score", 0)
    plagiarism = report_json.get("plagiarism_percentage", 0)

    summary_feedback = report_json.get("summary_feedback", "No feedback available.")
    improvement_plan = report_json.get("improvement_plan", "No improvement plan available.")

    strengths = report_json.get("strengths", [])
    weaknesses = report_json.get("weaknesses", [])
    question_wise = report_json.get("question_wise", [])

    st.markdown("## 👤 Candidate Profile")
    col1, col2, col3 = st.columns(3)

    with col1:
        st.info(f"**Name:** {report_data['candidate_name']}")

    with col2:
        st.info(f"**Role:** {report_data['role']}")

    with col3:
        st.info(f"**Difficulty:** {report_data['difficulty']}")

    st.write(f"📌 **Interview Type:** {report_data['interview_type']}")
    st.write(f"🎤 **Mode:** {report_data['mode']}")
    st.write(f"🕒 **Timestamp:** {report_data['timestamp']}")

    st.divider()

    # ---------------- SCORE CARDS ----------------
    st.markdown("## 📊 Final Evaluation Summary")

    colA, colB, colC = st.columns(3)

    with colA:
        if "HIRE" in verdict:
            st.success(f"🏆 Verdict: {verdict}")
        elif "AI DETECTED" in verdict:
            st.error(f"🤖 Verdict: {verdict}")
        else:
            st.warning(f"❌ Verdict: {verdict}")

    with colB:
        st.metric("Overall Score", f"{overall_score}/10")

    with colC:
        st.metric("Plagiarism %", f"{plagiarism}%")

    st.divider()

    # ---------------- FEEDBACK CARDS ----------------
    st.markdown("## 🧠 Summary Feedback")
    st.success(summary_feedback)

    st.markdown("## 📌 Improvement Plan")
    st.info(improvement_plan)

    st.divider()

    # ---------------- STRENGTHS / WEAKNESSES ----------------
    colS, colW = st.columns(2)

    with colS:
        st.markdown("## ✅ Strengths")
        if strengths and isinstance(strengths, list):
            for s in strengths:
                st.markdown(f"🟢 **{s}**")
        else:
            st.write("No strengths detected.")

    with colW:
        st.markdown("## ❌ Weaknesses")
        if weaknesses and isinstance(weaknesses, list):
            for w in weaknesses:
                st.markdown(f"🔴 **{w}**")
        else:
            st.write("No weaknesses detected.")

    st.divider()

    # ---------------- QUESTION WISE TABLE ----------------
    st.markdown("## 📋 Question Wise Evaluation")

    if isinstance(question_wise, list) and len(question_wise) > 0:
        q_df = pd.DataFrame(question_wise)

        # Rename for cleaner UI
        q_df = q_df.rename(columns={
            "candidate_answer": "Candidate Answer",
            "ideal_answer": "Ideal Answer",
            "score": "Score",
            "feedback": "Feedback",
            "improvement": "Improvement",
            "question": "Question"
        })

        st.dataframe(q_df, use_container_width=True)
    else:
        st.warning("No question wise evaluation found.")

    st.divider()

    # ---------------- PDF DOWNLOAD ----------------
    st.subheader("📄 Download PDF Report")

    pdf_bytes = generate_pdf_report(
        report_data["candidate_name"],
        report_data["role"],
        report_data["difficulty"],
        report_data["interview_type"],
        report_json
    )

    st.download_button(
        label="⬇️ Download Candidate PDF Report",
        data=pdf_bytes,
        file_name=f"{report_data['candidate_name']}_AI_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.divider()

    # ---------------- DELETE ----------------
    st.subheader("🗑️ Delete Candidate Report")
    st.warning("⚠️ Deleting is permanent and cannot be undone.")

    confirm = st.checkbox("Yes I confirm delete")

    if st.button("🗑️ Delete This Report", use_container_width=True):
        if not confirm:
            st.error("❌ Please confirm deletion first.")
        else:
            delete_report(report_id)
            st.success("✅ Report deleted successfully!")
            st.rerun()
