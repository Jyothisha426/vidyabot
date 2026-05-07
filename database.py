import sqlite3
import os
from datetime import datetime

DB_PATH = "data/vidyabot.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            subject TEXT,
            class_level TEXT,
            language TEXT,
            created_at TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            role TEXT,
            content TEXT,
            timestamp TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT,
            subject TEXT,
            topic TEXT,
            attempts INTEGER DEFAULT 0,
            understood INTEGER DEFAULT 0,
            last_seen TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_session(student_name, subject, class_level, language):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO sessions (student_name, subject, class_level, language, created_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (student_name, subject, class_level, language, datetime.now().isoformat()))
    session_id = c.lastrowid
    conn.commit()
    conn.close()
    return session_id

def save_message(session_id, role, content):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO messages (session_id, role, content, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (session_id, role, content, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_session_messages(session_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT role, content FROM messages WHERE session_id = ? ORDER BY id', (session_id,))
    messages = [{"role": row[0], "content": row[1]} for row in c.fetchall()]
    conn.close()
    return messages

def update_progress(student_name, subject, topic, understood=False):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT id, attempts FROM progress WHERE student_name=? AND subject=? AND topic=?',
              (student_name, subject, topic))
    row = c.fetchone()
    if row:
        c.execute('''UPDATE progress SET attempts=?, understood=?, last_seen=?
                     WHERE id=?''',
                  (row[1]+1, 1 if understood else 0, datetime.now().isoformat(), row[0]))
    else:
        c.execute('''INSERT INTO progress (student_name, subject, topic, attempts, understood, last_seen)
                     VALUES (?, ?, ?, 1, ?, ?)''',
                  (student_name, subject, topic, 1 if understood else 0, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_student_progress(student_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT subject, topic, attempts, understood, last_seen FROM progress WHERE student_name=?',
              (student_name,))
    rows = c.fetchall()
    conn.close()
    return [{"subject": r[0], "topic": r[1], "attempts": r[2], "understood": r[3], "last_seen": r[4]} for r in rows]