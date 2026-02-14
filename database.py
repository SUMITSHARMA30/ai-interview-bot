import sqlite3
import json
from datetime import datetime

DB_NAME = "interview_reports.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        role TEXT,
        difficulty TEXT,
        interview_type TEXT,
        overall_score REAL,
        verdict TEXT,
        report_json TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_report(candidate_name, role, difficulty, interview_type, overall_score, verdict, report_json):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reports (
        candidate_name, role, difficulty, interview_type,
        overall_score, verdict, report_json, created_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_name,
        role,
        difficulty,
        interview_type,
        overall_score,
        verdict,
        json.dumps(report_json),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def fetch_all_reports():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, candidate_name, role, difficulty, interview_type,
           overall_score, verdict, created_at
    FROM reports
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()

    reports = []
    for row in rows:
        reports.append({
            "ID": row[0],
            "Candidate": row[1],
            "Role": row[2],
            "Difficulty": row[3],
            "Interview Type": row[4],
            "Score": row[5],
            "Verdict": row[6],
            "Created At": row[7]
        })

    return reports
