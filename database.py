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
        mode TEXT,
        total_questions INTEGER,
        avg_score REAL,
        verdict TEXT,
        chat TEXT,
        created_at TEXT,
        pdf BLOB
    )
    """)

    conn.commit()
    conn.close()


def save_report(candidate_name, role, difficulty, interview_type, mode, total_questions,
                avg_score, verdict, chat, pdf_bytes):

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO reports (
        candidate_name, role, difficulty, interview_type, mode,
        total_questions, avg_score, verdict, chat, created_at, pdf
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_name, role, difficulty, interview_type, mode,
        total_questions, avg_score, verdict, str(chat),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        pdf_bytes
    ))

    conn.commit()
    conn.close()


def fetch_reports():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT id, candidate_name, role, difficulty, interview_type, mode, total_questions, avg_score, verdict, created_at FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows


def fetch_pdf(report_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT pdf FROM reports WHERE id=?", (report_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        return row[0]
    return None
