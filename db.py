import sqlite3
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
            report_json TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def save_report(candidate_name, role, difficulty, interview_type, report_json):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reports (candidate_name, role, difficulty, interview_type, report_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (candidate_name, role, difficulty, interview_type, report_json, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()


def fetch_all_reports():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()

    reports = []
    for row in rows:
        reports.append({
            "id": row[0],
            "candidate_name": row[1],
            "role": row[2],
            "difficulty": row[3],
            "interview_type": row[4],
            "report_json": row[5],
            "created_at": row[6]
        })

    return reports
