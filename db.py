import sqlite3
import json
from datetime import datetime

DB_NAME = "interview_reports.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Reports table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT,
            role TEXT,
            difficulty TEXT,
            interview_type TEXT,
            mode TEXT,
            report_json TEXT,
            timestamp TEXT
        )
    """)

    # Admin Settings table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            role TEXT,
            difficulty TEXT,
            interview_type TEXT,
            total_questions INTEGER,
            mode TEXT,
            updated_at TEXT
        )
    """)

    conn.commit()
    conn.close()

    # Insert default settings if none exist
    if get_admin_settings() is None:
        save_admin_settings("SDE", "Easy", "Technical", 5, "Text Mode")


def save_report(candidate_name, role, difficulty, interview_type, mode, report_json):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO reports (candidate_name, role, difficulty, interview_type, mode, report_json, timestamp)
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


def fetch_reports():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows


# ---------------- ADMIN SETTINGS ----------------
def save_admin_settings(role, difficulty, interview_type, total_questions, mode):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO admin_settings (role, difficulty, interview_type, total_questions, mode, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        role,
        difficulty,
        interview_type,
        total_questions,
        mode,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


def get_admin_settings():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT role, difficulty, interview_type, total_questions, mode
        FROM admin_settings
        ORDER BY id DESC LIMIT 1
    """)

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "role": row[0],
        "difficulty": row[1],
        "interview_type": row[2],
        "total_questions": row[3],
        "mode": row[4]
    }
