import sqlite3
import json
from datetime import datetime

DB_NAME = "interview_reports.db"


def get_connection():
    return sqlite3.connect(DB_NAME, check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # ---------------- REPORTS TABLE ----------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_name TEXT,
            role TEXT,
            difficulty TEXT,
            interview_type TEXT,
            mode TEXT,

            verdict TEXT,
            overall_score REAL,
            plagiarism_percentage INTEGER,

            report_json TEXT,
            timestamp TEXT
        )
    """)

    # ---------------- ADMIN SETTINGS TABLE ----------------
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


# ---------------- SAVE REPORT ----------------
def save_report(candidate_name, role, difficulty, interview_type, mode, report_json):
    conn = get_connection()
    cursor = conn.cursor()

    verdict = report_json.get("verdict", "Unknown")
    overall_score = report_json.get("overall_score", 0)
    plagiarism_percentage = report_json.get("plagiarism_percentage", 0)

    try:
        overall_score = float(overall_score)
    except:
        overall_score = 0

    try:
        plagiarism_percentage = int(plagiarism_percentage)
    except:
        plagiarism_percentage = 0

    cursor.execute("""
        INSERT INTO reports (
            candidate_name, role, difficulty, interview_type, mode,
            verdict, overall_score, plagiarism_percentage,
            report_json, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        candidate_name,
        role,
        difficulty,
        interview_type,
        mode,
        verdict,
        overall_score,
        plagiarism_percentage,
        json.dumps(report_json),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))

    conn.commit()
    conn.close()


# ---------------- FETCH REPORTS ----------------
def fetch_reports():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM reports ORDER BY id DESC")
    rows = cursor.fetchall()

    conn.close()
    return rows


def fetch_all_reports():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, candidate_name, role, difficulty, interview_type, mode,
               verdict, overall_score, plagiarism_percentage, timestamp
        FROM reports
        ORDER BY id DESC
    """)

    rows = cursor.fetchall()
    conn.close()
    return rows


def fetch_report_by_id(report_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, candidate_name, role, difficulty, interview_type, mode,
               verdict, overall_score, plagiarism_percentage, report_json, timestamp
        FROM reports
        WHERE id = ?
    """, (report_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    try:
        report_json = json.loads(row[9])
    except:
        report_json = {}

    return {
        "id": row[0],
        "candidate_name": row[1],
        "role": row[2],
        "difficulty": row[3],
        "interview_type": row[4],
        "mode": row[5],
        "verdict": row[6],
        "overall_score": row[7],
        "plagiarism_percentage": row[8],
        "report_json": report_json,
        "timestamp": row[10]
    }


def delete_report(report_id):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    conn.commit()
    conn.close()


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
