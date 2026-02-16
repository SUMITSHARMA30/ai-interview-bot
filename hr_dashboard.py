import streamlit as st
import pandas as pd
import json

from db import fetch_reports, save_admin_settings, get_admin_settings
from pdf_report import generate_pdf_report


def hr_dashboard():
    st.markdown("<h1 class='main-title'>📊 HR Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>View reports, analytics & control interview settings</p>", unsafe_allow_html=True)
    st.divider()

    # ---------------- ADMIN SETTINGS PANEL ----------------
    st.subheader("⚙️ Admin Interview Settings")

    current = get_admin_settings()

    if current is None:
        current = {
            "role": "SDE",
            "difficulty": "Easy",
            "interview_type": "Technical",
            "total_questions": 5,
            "mode": "Text Mode"
        }

    with st.form("admin_settings_form"):

        role = st.selectbox("Role", ["SDE", "Data Scientist", "ML Engineer"], index=["SDE", "Data Scientist", "ML Engineer"].index(current["role"]))
        difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], index=["Easy", "Medium", "Hard"].index(current["difficulty"]))
        interview_type = st.selectbox("Interview Type", ["Technical", "HR", "Mixed"], index=["Technical", "HR", "Mixed"].index(current["interview_type"]))
        total_questions = st.slider("Total Questions", 5, 20, int(current["total_questions"]))
        mode = st.radio("Interview Mode", ["Text Mode", "Voice Mode"], index=0 if current["mode"] == "Text Mode" else 1)

        save_btn = st.form_submit_button("✅ Save Settings", use_container_width=True)

    if save_btn:
        save_admin_settings(role, difficulty, interview_type, total_questions, mode)
        st.success("🔥 Admin settings updated successfully!")
        st.rerun()

    st.divider()

    # ---------------- REPORTS TABLE ----------------
    st.subheader("📋 Candidate Interview Reports")

    reports = fetch_reports()

    if not reports:
        st.warning("No interview reports found yet.")
        return

    df = pd.DataFrame(reports, columns=[
        "ID", "Candidate Name", "Role", "Difficulty",
        "Interview Type", "Mode", "Report JSON", "Timestamp"
    ])

    # ---------------- FILTERS ----------------
    st.subheader("🔍 Search / Filters")

    col1, col2, col3 = st.columns(3)

    with col1:
        name_filter = st.text_input("Search Candidate Name")

    with col2:
        role_filter = st.selectbox("Filter Role", ["All", "SDE", "Data Scientist", "ML Engineer"])

    with col3:
        difficulty_filter = st.selectbox("Filter Difficulty", ["All", "Easy", "Medium", "Hard"])

    filtered_df = df.copy()

    if name_filter:
        filtered_df = filtered_df[filtered_df["Candidate Name"].str.contains(name_filter, case=False, na=False)]

    if role_filter != "All":
        filtered_df = filtered_df[filtered_df["Role"] == role_filter]

    if difficulty_filter != "All":
        filtered_df = filtered_df[filtered_df["Difficulty"] == difficulty_filter]

    st.dataframe(filtered_df[[
        "ID", "Candidate Name", "Role", "Difficulty", "Interview Type", "Mode", "Timestamp"
    ]], use_container_width=True)

    st.divider()

    # ---------------- DOWNLOAD PDF REPORT ----------------
    st.subheader("📄 Download Old Report PDF")

    selected_id = st.selectbox("Select Report ID", filtered_df["ID"].tolist())

    selected_row = df[df["ID"] == selected_id].iloc[0]

    try:
        report_json = json.loads(selected_row["Report JSON"])
    except:
        report_json = {}

    pdf_bytes = generate_pdf_report(
        selected_row["Candidate Name"],
        selected_row["Role"],
        selected_row["Difficulty"],
        selected_row["Interview Type"],
        report_json
    )

    st.download_button(
        label="📄 Download PDF",
        data=pdf_bytes,
        file_name=f"{selected_row['Candidate Name']}_Interview_Report.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    st.divider()

    # ---------------- ANALYTICS ----------------
    st.subheader("📈 HR Analytics")

    verdicts = []
    scores = []

    for item in df["Report JSON"]:
        try:
            r = json.loads(item)
            verdicts.append(r.get("verdict", "Unknown"))
            scores.append(r.get("overall_score", 0))
        except:
            verdicts.append("Unknown")
            scores.append(0)

    df["Verdict"] = verdicts
    df["Score"] = scores

    colA, colB, colC = st.columns(3)

    with colA:
        st.metric("Total Interviews", len(df))

    with colB:
        st.metric("Hire Count", verdicts.count("Hire"))

    with colC:
        avg_score = round(sum(scores) / len(scores), 2) if len(scores) > 0 else 0
        st.metric("Avg Score", avg_score)

    st.bar_chart(df["Verdict"].value_counts())
