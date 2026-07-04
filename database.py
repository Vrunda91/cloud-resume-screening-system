"""
database.py
-------------------------------------------------------
Data layer for the Cloud-Based AI Resume Screening System.

For this demo build we use SQLite so the project runs anywhere
with zero setup. In a real cloud deployment, this module is the
ONLY file that would change -- swap the connection logic below
for AWS RDS (MySQL/PostgreSQL) or Azure SQL Database, and the
rest of the application (app.py, matcher.py, resume_parser.py)
does not need to change at all. This is intentional: it keeps
the persistence layer decoupled from business logic.
"""

import sqlite3
import os
import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "resume_screening.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            required_skills TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS candidates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            candidate_name TEXT NOT NULL,
            filename TEXT NOT NULL,
            storage_path TEXT NOT NULL,
            extracted_text TEXT,
            matched_skills TEXT,
            missing_skills TEXT,
            match_score REAL,
            uploaded_at TEXT NOT NULL,
            FOREIGN KEY (job_id) REFERENCES jobs (id)
        )
    """)

    conn.commit()
    conn.close()


def add_job(title, description, required_skills):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jobs (title, description, required_skills, created_at) VALUES (?, ?, ?, ?)",
        (title, description, ",".join(required_skills), datetime.datetime.now().isoformat())
    )
    conn.commit()
    job_id = cur.lastrowid
    conn.close()
    return job_id


def get_job(job_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs WHERE id = ?", (job_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_jobs():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM jobs ORDER BY created_at DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_candidate(job_id, candidate_name, filename, storage_path, extracted_text,
                   matched_skills, missing_skills, match_score):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO candidates
        (job_id, candidate_name, filename, storage_path, extracted_text,
         matched_skills, missing_skills, match_score, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (job_id, candidate_name, filename, storage_path, extracted_text,
          ",".join(matched_skills), ",".join(missing_skills), match_score,
          datetime.datetime.now().isoformat()))
    conn.commit()
    candidate_id = cur.lastrowid
    conn.close()
    return candidate_id


def get_ranked_candidates(job_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM candidates
        WHERE job_id = ?
        ORDER BY match_score DESC
    """, (job_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]
