import sqlite3
from datetime import datetime

SCHEMA = """
CREATE TABLE IF NOT EXISTS clicks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_email TEXT NOT NULL,
    claim_reference_number TEXT NOT NULL,
    claim_url TEXT NOT NULL,
    clicked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS send_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    row_data TEXT,
    error_msg TEXT,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db(db_path='claim_logs.db'):
    """Initialize the database with required tables."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()

def log_success(recipient_email, claim_reference_number, db_path='claim_logs.db'):
    """Log a successful email send to a file."""
    with open('send_successes.log', 'a') as f:
        f.write(f"{datetime.now()}: Sent to {recipient_email}, claim {claim_reference_number}\n")

def log_failure(row_data, error_msg, db_path='claim_logs.db'):
    """Log a failed email send."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO send_failures (row_data, error_msg, attempted_at) VALUES (?, ?, ?)",
        (row_data, error_msg, datetime.now())
    )
    conn.commit()
    conn.close()

def log_click(recipient_email, claim_reference_number, claim_url, db_path='claim_logs.db'):
    """Log a click on the tracking link."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO clicks (recipient_email, claim_reference_number, claim_url, clicked_at) VALUES (?, ?, ?, ?)",
        (recipient_email, claim_reference_number, claim_url, datetime.now())
    )
    conn.commit()
    conn.close()