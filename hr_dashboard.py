import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from db import fetch_all_reports, fetch_report_by_id, delete_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Analytics + Candidate Reports</p>", unsafe_allow_html=True)

    reports = fetch_all_reports()

    if not reports:
        st.warning("No interview reports found yet.")
        return

    df = pd.DataFrame(reports, columns=[
        "id", "candidate_name", "role", "difficulty", "interview_type",
        "mode", "verdict", "overall_score", "plagiarism_percentage", "timestamp"
    ])
    df["overall_score"] = pd.to_numeric(df["overall_score"], errors="coerce").fillna(0)
    df["plagiarism_percentage"] = pd.to_numeric(df["plagiarism_percentage"], errors="coerce").fillna(0)


    # ---------------- FILTERS ----------------
    st.subheader("🔍 Search / Filter Reports")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        name_filter = st.text_input("Candidate Name")

    with col2:
        role_filter = st.selectbox("Role", ["All"] + sorted(df["role"].unique().tolist()))

    with col3:
        difficulty_filter = st.selectbox("Difficulty", ["All"] + sorted(df["difficulty"].unique().tolist()))

    with col4:
        verdict_filter = st.selectbox("Verdict", ["All"] + sorted(df["verdict"].unique().tolist()))

    if name_filter:
        df = df[df["candidate_name"].str.contains(name_filter, case=False)]

    if role_filter != "All":
        df = df[df["role"] == role_filter]

    if difficulty_filter != "All":
        df = df[df["difficulty"] == difficulty_filter]

    if verdict_filter != "All":
        df = df[df["verdict"] == verdict_filter]

    st.divider()

    # ---------------- REPORT TABLE ----------------
    st.subheader("📋 Candidate Reports Table")
    st.dataframe(df, use_container_width=True)

    # ---------------- EXPORT CSV ----------------
    st.subheader("📤 Export Reports")
    csv_data = df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="⬇️ Download CSV",
        data=csv_data,
        file_name="interview_reports.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()

    # ---------------- ANALYTICS ----------------
    st.subheader("📊 Analytics Charts")

    colA, colB = st.columns(2)

    with colA:
        st.markdown("### Verdict Distribution")
        verdict_counts = df["verdict"].value_counts()

        fig, ax = plt.subplots()
        ax.bar(verdict_counts.index, verdict_counts.values)
        ax.set_ylabel("Count")
        ax.set_xlabel("Verdict")
        st.pyplot(fig)

    with colB:
        st.markdown("### Avg Score by Role")
        role_avg = df.groupby("role")["overall_score"].mean()

        fig, ax = plt.subplots()
        ax.bar(role_avg.index, role_avg.values)
        ax.set_ylabel("Avg Score")
        ax.set_xlabel("Role")
        st.pyplot(fig)

    colC, colD = st.columns(2)

    with colC:
        st.markdown("### Avg Score by Difficulty")
        diff_avg = df.groupby("difficulty")["overall_score"].mean()

        fig, ax = plt.subplots()
        ax.bar(diff_avg.index, diff_avg.values)
        ax.set_ylabel("Avg Score")
        ax.set_xlabel("Difficulty")
        st.pyplot(fig)

    with colD:
        st.markdown("### Plagiarism Distribution")
        fig, ax = plt.subplots()
        ax.hist(df["plagiarism_percentage"], bins=10)
        ax.set_xlabel("Plagiarism %")
        ax.set_ylabel("Candidates")
        st.pyplot(fig)

    st.divider()

    # ---------------- REPORT VIEWER ----------------
    st.subheader("📌 View / Delete Report")

    report_id = st.selectbox("Select Report ID", df["id"].tolist())

    if report_id:
        report_data = fetch_report_by_id(report_id)

        if report_data:
            st.markdown("### 📝 Full Report JSON")
            st.json(report_data["report_json"])

            col1, col2 = st.columns(2)

            with col1:
                if st.button("🗑️ Delete Report", use_container_width=True):
                    delete_report(report_id)
                    st.success("Report deleted successfully!")
                    st.rerun()

            with col2:
                st.info("PDF download handled from saved report page.")
