import streamlit as st
import pandas as pd
import plotly.express as px

from db import fetch_all_reports, fetch_report_by_id, delete_report
from pdf_report import generate_pdf_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Analytics + Candidate Reports (MAANG Style)</p>", unsafe_allow_html=True)
    st.divider()

    reports = fetch_all_reports()

    if not reports:
        st.warning("⚠️ No interview reports found yet.")
        return

    df = pd.DataFrame(reports, columns=[
        "id", "candidate_name", "role", "difficulty", "interview_type",
        "mode", "verdict", "overall_score", "plagiarism_percentage", "timestamp"
    ])

    # Convert numeric safely
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

    if name_filter.strip():
        df = df[df["candidate_name"].str.contains(name_filter, case=False, na=False)]

    if role_filter != "All":
        df = df[df["role"] == role_filter]

    if difficulty_filter != "All":
        df = df[df["difficulty"] == difficulty_filter]

    if verdict_filter != "All":
        df = df[df["verdict"] == verdict_filter]

    st.divider()

    # ---------------- TOP CANDIDATES ----------------
    st.subheader("🏆 Top Candidates")

    top_df = df.sort_values(by="overall_score", ascending=False).head(5)

    if len(top_df) > 0:
        st.dataframe(
            top_df[["candidate_name", "role", "overall_score", "plagiarism_percentage", "verdict", "timestamp"]],
            use_container_width=True
        )
    else:
        st.info("No candidates available for ranking.")

    st.divider()

    # ---------------- REPORTS TABLE ----------------
    st.subheader("📋 Candidate Reports Table")
    st.dataframe(df, use_container_width=True)

    st.divider()

    # ---------------- EXPORT CSV ----------------
    st.subheader("📤 Export Reports")

    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download Filtered CSV",
        data=csv_data,
        file_name="filtered_interview_reports.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()

    # ---------------- ANALYTICS ----------------
    st.subheader("📊 Analytics Dashboard")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### ✅ Verdict Distribution")
        verdict_counts = df["verdict"].value_counts().reset_index()
        verdict_counts.columns = ["verdict", "count"]

        fig = px.pie(
            verdict_counts,
            names="verdict",
            values="count",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)

    with colB:
        st.markdown("### ⭐ Avg Score by Role")
        role_avg = df.groupby("role")["overall_score"].mean().reset_index()

        fig = px.bar(role_avg, x="role", y="overall_score")
        st.plotly_chart(fig, use_container_width=True)

    colC, colD = st.columns(2)

    with colC:
        st.markdown("### ⚡ Avg Score by Difficulty")
        diff_avg = df.groupby("difficulty")["overall_score"].mean().reset_index()

        fig = px.bar(diff_avg, x="difficulty", y="overall_score")
        st.plotly_chart(fig, use_container_width=True)

    with colD:
        st.markdown("### 🤖 Plagiarism Distribution")
        fig = px.histogram(df, x="plagiarism_percentage", nbins=10)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ---------------- REPORT VIEWER ----------------
    st.subheader("📌 View / Download / Delete Report")

    report_id = st.selectbox("Select Report ID", df["id"].tolist())

    if report_id:
        report_data = fetch_report_by_id(report_id)

        if not report_data:
            st.error("❌ Report not found.")
            return

        st.markdown("### 👤 Candidate Details")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.info(f"**Name:** {report_data['candidate_name']}")

        with col2:
            st.info(f"**Role:** {report_data['role']}")

        with col3:
            st.info(f"**Difficulty:** {report_data['difficulty']}")

        st.markdown("### 📌 Verdict & Scores")
        colA, colB, colC = st.columns(3)

        with colA:
            st.success(f"Verdict: **{report_data['verdict']}**")

        with colB:
            st.metric("Overall Score", f"{report_data['overall_score']}/10")

        with colC:
            st.metric("Plagiarism %", f"{report_data['plagiarism_percentage']}%")

        st.divider()

        st.markdown("### 📋 Full Report JSON")
        st.json(report_data["report_json"])

        st.divider()

        # ---------------- DOWNLOAD PDF ----------------
        st.subheader("📄 Download PDF Report")

        pdf_bytes = generate_pdf_report(
            report_data["candidate_name"],
            report_data["role"],
            report_data["difficulty"],
            report_data["interview_type"],
            report_data["report_json"]
        )

        st.download_button(
            label="⬇️ Download Candidate PDF Report",
            data=pdf_bytes,
            file_name=f"{report_data['candidate_name']}_AI_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.divider()

        # ---------------- DELETE REPORT ----------------
        st.subheader("🗑️ Delete Report")

        st.warning("⚠️ Deleting is permanent. This cannot be undone.")

        confirm = st.checkbox("Yes, I confirm deletion")

        if st.button("🗑️ Delete This Report", use_container_width=True):
            if not confirm:
                st.error("❌ Please confirm deletion checkbox first.")
            else:
                delete_report(report_id)
                st.success("✅ Report deleted successfully!")
                st.rerun()
