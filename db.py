import sqlite3
import json
from datetime import datetime

DB_NAME = "interview_reports.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        candidate_name TEXT,
        role TEXT,
        difficulty TEXT,
        interview_type TEXT,
        mode TEXT,
        report_json TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def save_report(candidate_name, role, difficulty, interview_type, mode, report_json):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
    INSERT INTO reports (candidate_name, role, difficulty, interview_type, mode, report_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_name,
        role,
        difficulty,
        interview_type,
        mode,
        json.dumps(report_json),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def fetch_all_reports():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cur.fetchall()

    conn.close()
    return rows


def fetch_report_by_id(report_id):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
    row = cur.fetchone()

    conn.close()
    return row
