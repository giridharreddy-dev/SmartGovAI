# database.py
import sqlite3
from datetime import datetime
import os

DB_PATH = 'feedback.db'

def init_db():
    """Create tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS requests
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         scheme_name TEXT,
                         source TEXT,
                         timestamp TEXT)''')
        conn.execute('''CREATE TABLE IF NOT EXISTS feedback
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         request_id INTEGER,
                         rating INTEGER,
                         comment TEXT,
                         timestamp TEXT,
                         FOREIGN KEY (request_id) REFERENCES requests(id))''')
    print("✅ Database initialized (feedback.db)")

def log_request(scheme_name, source):
    """Insert a new request and return its ID."""
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.cursor()
        cur.execute("INSERT INTO requests (scheme_name, source, timestamp) VALUES (?,?,?)",
                    (scheme_name, source, datetime.utcnow().isoformat()))
        return cur.lastrowid

def save_feedback(request_id, rating, comment):
    """Store user feedback."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO feedback (request_id, rating, comment, timestamp) VALUES (?,?,?,?)",
                     (request_id, rating, comment, datetime.utcnow().isoformat()))
