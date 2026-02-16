import streamlit as st
import pandas as pd
import plotly.express as px

from db import fetch_all_reports, fetch_report_by_id, delete_report
from pdf_report import generate_pdf_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Analytics + Candidate Reports</p>", unsafe_allow_html=True)
    st.divider()

    try:
        reports = fetch_all_reports()
    except Exception as e:
        st.error("❌ Database error while loading reports.")
        st.code(str(e))
        return

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

    # ---------------- VIEW REPORT ----------------
    st.subheader("📌 View Candidate Full Report")

    report_id = st.selectbox("Select Candidate Report ID", filtered_df["id"].tolist())

    if report_id:
        report_data = fetch_report_by_id(report_id)

        if report_data is None:
            st.error("❌ Report not found.")
            return

        st.markdown("### 👤 Candidate Details")
        st.write(f"**Name:** {report_data['candidate_name']}")
        st.write(f"**Role:** {report_data['role']}")
        st.write(f"**Difficulty:** {report_data['difficulty']}")
        st.write(f"**Interview Type:** {report_data['interview_type']}")
        st.write(f"**Mode:** {report_data['mode']}")
        st.write(f"**Timestamp:** {report_data['timestamp']}")

        st.divider()

        st.markdown("### 📊 Result")
        st.success(f"Verdict: **{report_data['verdict']}**")
        st.metric("Overall Score", f"{report_data['overall_score']}/10")
        st.metric("Plagiarism %", f"{report_data['plagiarism_percentage']}%")

        st.divider()

        st.markdown("### 🧾 Full JSON Report")
        import json
        st.code(json.dumps(report_data["report_json"], indent=4), language="json")


        st.divider()

        st.subheader("📄 Download PDF")

        pdf_bytes = generate_pdf_report(
            report_data["candidate_name"],
            report_data["role"],
            report_data["difficulty"],
            report_data["interview_type"],
            report_data["report_json"]
        )

        st.download_button(
            label="⬇️ Download PDF Report",
            data=pdf_bytes,
            file_name=f"{report_data['candidate_name']}_AI_Report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

        st.divider()

        st.subheader("🗑️ Delete Candidate Report")

        confirm = st.checkbox("I confirm delete permanently")

        if st.button("🗑️ Delete Report", use_container_width=True):
            if not confirm:
                st.error("❌ Please confirm deletion checkbox first.")
            else:
                delete_report(report_id)
                st.success("✅ Report deleted!")
                st.rerun()
