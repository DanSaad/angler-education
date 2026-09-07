# Claim Status Email Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the claim-status-email utility with unique opaque tracking tokens, claim reference display in emails, and unified database-based audit logging.

**Architecture:** The existing `src/` package (send_claims.py, web_tracker.py, db.py, csv_processor.py) gains a token-based tracking system. Each email gets a UUID token stored in a new `tracking_tokens` table. A unified `send_log` table records one entry per send with a status (sent/clicked/failed_to_send/invalid_recipient/no_click). The web tracker resolves tokens via the database instead of CSV. Daily reconciliation marks non-responsive recipients.

**Tech Stack:** Python 3, SQLite (stdlib `sqlite3`), Flask, `uuid`, `smtplib`, `unittest` (immediately available, no pytest dependency needed).

## Global Constraints

- No non-standard-library dependencies beyond Flask (already used).
- Tracking links use only an opaque token: `{TRACKING_BASE_URL}?token=<uuid>` — no recipient email or claim reference in the URL.
- Every sent/failed/invalid send outcome SHALL be recorded in the SQLite `send_log` table; the old `send_successes.log` file and `clicks`/`send_failures` tables are removed.
- Email subject line unchanged: "Important Update on Your Claim Status".
- Recipient's `ClaimReferenceNumber` SHALL appear in both plain-text and HTML bodies.
- `TRACKING_BASE_URL` read from environment, default `http://localhost:8000/track`.
- Daily reconciliation marks `sent`-status entries older than today as `no_click`; late clicks transition `no_click` → `clicked`.
- Tests use `unittest` (stdlib) so `python -m unittest discover` works without extra installs.

---

### Task 1: Database schema for tracking tokens and unified send log

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces (for later tasks):
  - `init_db(db_path='claim_logs.db')` — creates `tracking_tokens` and `send_log` tables.
  - `store_token(token, recipient_email, claim_reference_number, claim_url, db_path='claim_logs.db')` — inserts into `tracking_tokens`.
  - `get_claim_by_token(token, db_path='claim_logs.db')` — returns the claim URL for a token or `None`.
  - `add_send_log(recipient_email, claim_reference_number, status, token, error_message=None, db_path='claim_logs.db')` — inserts a `send_log` row.
  - `update_send_status(recipient_email, claim_reference_number, new_status, db_path='claim_logs.db')` — updates the status of a send log row.
  - `LOG_STATUSES` constant tuple: `('sent', 'clicked', 'failed_to_send', 'invalid_recipient', 'no_click')`.
  - `get_send_log(recipient_email, claim_reference_number, db_path='claim_logs.db')` — returns latest send-log row or `None`.

- [ ] **Step 1: Write the failing test**

Create `tests/__init__.py` and `tests/test_db.py`:

```python
# tests/__init__.py
# (empty — marks tests as a package)
```

```python
# tests/test_db.py
import os
import tempfile
import unittest

from src import db


class TestDbSchema(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_init_creates_tables(self):
        db.init_db(self.db_path)
        conn = __import__('sqlite3').connect(self.db_path)
        tables = {row[0] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        conn.close()
        self.assertIn('tracking_tokens', tables)
        self.assertIn('send_log', tables)

    def test_store_and_get_token(self):
        db.init_db(self.db_path)
        db.store_token(
            'abc-token-123', 'a@example.com', 'CLM-1', 'https://clm/1', self.db_path)
        self.assertEqual(
            db.get_claim_by_token('abc-token-123', self.db_path),
            'https://clm/1')
        self.assertIsNone(db.get_claim_by_token('missing', self.db_path))

    def test_add_and_update_send_log(self):
        db.init_db(self.db_path)
        db.add_send_log('a@example.com', 'CLM-1', 'sent', 'abc-token-123',
                        db_path=self.db_path)
        row = db.get_send_log('a@example.com', 'CLM-1', self.db_path)
        self.assertEqual(row['status'], 'sent')
        db.update_send_status('a@example.com', 'CLM-1', 'clicked',
                              db_path=self.db_path)
        row = db.get_send_log('a@example.com', 'CLM-1', self.db_path)
        self.assertEqual(row['status'], 'clicked')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run from project root: `python -m unittest tests.test_db -v`
Expected: FAIL with `ImportError`/`AttributeError` (functions don't exist yet).

- [ ] **Step 3: Implement the new schema and functions in `src/db.py`**

Replace the module-level `SCHEMA` and add the new helper functions:

```python
import sqlite3
from datetime import datetime

LOG_STATUSES = ('sent', 'clicked', 'failed_to_send', 'invalid_recipient', 'no_click')

SCHEMA = """
CREATE TABLE IF NOT EXISTS tracking_tokens (
    token TEXT PRIMARY KEY,
    recipient_email TEXT NOT NULL,
    claim_reference_number TEXT NOT NULL,
    claim_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS send_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    recipient_email TEXT NOT NULL,
    claim_reference_number TEXT NOT NULL,
    status TEXT NOT NULL,
    token TEXT,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

def init_db(db_path='claim_logs.db'):
    """Initialize the database with required tables."""
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    conn.close()

def store_token(token, recipient_email, claim_reference_number, claim_url,
                db_path='claim_logs.db'):
    """Store a tracking token mapping to recipient, claim, and claim URL."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO tracking_tokens (token, recipient_email, claim_reference_number, claim_url) "
        "VALUES (?, ?, ?, ?)",
        (token, recipient_email, claim_reference_number, claim_url))
    conn.commit()
    conn.close()

def get_claim_by_token(token, db_path='claim_logs.db'):
    """Return the claim URL for a token, or None if not found."""
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "SELECT claim_url FROM tracking_tokens WHERE token = ?", (token,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def add_send_log(recipient_email, claim_reference_number, status, token,
                 error_message=None, db_path='claim_logs.db'):
    """Record an email send outcome in the send_log table."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO send_log (recipient_email, claim_reference_number, status, token, error_message) "
        "VALUES (?, ?, ?, ?, ?)",
        (recipient_email, claim_reference_number, status, token, error_message))
    conn.commit()
    conn.close()

def update_send_status(recipient_email, claim_reference_number, new_status,
                       db_path='claim_logs.db'):
    """Update the status of the latest send_log row for a recipient/claim."""
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE send_log SET status = ?, updated_at = CURRENT_TIMESTAMP "
        "WHERE id = (SELECT id FROM send_log WHERE recipient_email = ? "
        "AND claim_reference_number = ? ORDER BY id DESC LIMIT 1)",
        (new_status, recipient_email, claim_reference_number))
    conn.commit()
    conn.close()

def get_send_log(recipient_email, claim_reference_number, db_path='claim_logs.db'):
    """Return the latest send_log row as a dict, or None."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM send_log WHERE recipient_email = ? AND claim_reference_number = ? "
        "ORDER BY id DESC LIMIT 1",
        (recipient_email, claim_reference_number))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run from project root: `python -m unittest tests.test_db -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/__init__.py tests/test_db.py
git commit -m "feat: add tracking_tokens and send_log schema to db module"
```

---

### Task 2: Token generation in send_claims.py

**Files:**
- Modify: `src/send_claims.py`
- Test: `tests/test_send_claims.py`

**Interfaces:**
- Consumes: `db.store_token`, `db.add_send_log`, `db.init_db` (from Task 1).
- Produces:
  - `generate_token()` — returns a string UUID.
  - `compose_email(row, token)` — returns an `EmailMessage` whose tracking link uses `{TRACKING_BASE_URL}?token=<token>` and whose body contains the recipient's claim reference.
  - `get_tracking_base_url()` — reads `TRACKING_BASE_URL` env, defaults to `http://localhost:8000/track`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_send_claims.py`:

```python
# tests/test_send_claims.py
import os
import unittest
from unittest.mock import patch

from src import send_claims


class TestTokenGeneration(unittest.TestCase):
    def test_generate_token_returns_uuid_string(self):
        token = send_claims.generate_token()
        self.assertIsInstance(token, str)
        self.assertEqual(len(token), 36)  # 8-4-4-4-12

    def test_generate_token_produces_distinct_tokens(self):
        self.assertNotEqual(send_claims.generate_token(),
                            send_claims.generate_token())


class TestComposeEmail(unittest.TestCase):
    def setUp(self):
        self.row = {
            'SenderEmail': 'sender@example.com',
            'SubsidiaryName': 'Acme Corp',
            'RecipientEmail': 'a@example.com',
            'ClaimReferenceNumber': 'CLM-2024-001',
            'ClaimURL': 'https://claims/1'
        }
        self.token = '550e8400-e29b-41d4-a716-446655440000'

    def test_tracking_link_is_token_based(self):
        msg = send_claims.compose_email(self.row, self.token)
        body = msg.get_content()
        self.assertIn(f'?token={self.token}', body)
        self.assertNotIn('a@example.com', body)
        self.assertNotIn('CLM-2024-001', body)

    def test_claim_reference_in_plain_body(self):
        msg = send_claims.compose_email(self.row, self.token)
        self.assertIn('CLM-2024-001', msg.get_content())

    def test_claim_reference_in_html_body(self):
        msg = send_claims.compose_email(self.row, self.token)
        for part in msg.walk():
            if part.get_content_type() == 'text/html':
                self.assertIn('CLM-2024-001', part.get_content())

    def test_subject_unchanged(self):
        msg = send_claims.compose_email(self.row, self.token)
        self.assertEqual(msg['Subject'], "Important Update on Your Claim Status")

    def test_subject_sender_recipient_headers(self):
        msg = send_claims.compose_email(self.row, self.token)
        self.assertEqual(msg['From'], 'sender@example.com')
        self.assertEqual(msg['To'], 'a@example.com')


class TestTrackingBaseUrl(unittest.TestCase):
    def test_default_value(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(send_claims.get_tracking_base_url(),
                             'http://localhost:8000/track')

    def test_env_var_overrides(self):
        with patch.dict(os.environ, {'TRACKING_BASE_URL': 'https://track.example.com/x'},
                        clear=True):
            self.assertEqual(send_claims.get_tracking_base_url(),
                             'https://track.example.com/x')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run from project root: `python -m unittest tests.test_send_claims -v`
Expected: FAIL with `AttributeError` (`generate_token`, `compose_email(token=...)`, `get_tracking_base_url` not present / signature mismatch).

- [ ] **Step 3: Implement token generation, base URL, and updated compose_email in `src/send_claims.py`**

Replace the current `TRACKING_BASE_URL` constant and `compose_email` with:

```python
import os
import smtplib
import time
import uuid
from email.message import EmailMessage
from .csv_processor import read_csv
from . import db

DEFAULT_TRACKING_BASE_URL = "http://localhost:8000/track"
SMTP_HOST = 'mysubsididary.mycompany.com'
SMTP_PORT = 25
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # seconds


def get_tracking_base_url():
    """Return the tracking base URL from env or the dev default."""
    return os.environ.get('TRACKING_BASE_URL', DEFAULT_TRACKING_BASE_URL)


def generate_token():
    """Generate a unique opaque token for a tracking link."""
    return str(uuid.uuid4())


def compose_email(row, token):
    """
    Compose a claim-status email for a claim row.
    The tracking link is token-based and the body shows the claim reference.
    """
    recipient_email = row['RecipientEmail']
    claim_ref = row['ClaimReferenceNumber']
    base_url = get_tracking_base_url()
    tracking_url = f"{base_url}?token={token}"
    subject = "Important Update on Your Claim Status"
    plain_body = (
        f"Dear {row['SubsidiaryName']} claimant,\n\n"
        f"Your claim reference number is {claim_ref}.\n\n"
        f"Please check your claim status using the following link:\n"
        f"{tracking_url}\n\n"
        f"Best regards,\nClaims Team"
    )
    html_body = f"""
    <html>
    <body>
    <p>Dear {row['SubsidiaryName']} claimant,</p>
    <p>Your claim reference number is <strong>{claim_ref}</strong>.</p>
    <p>Please check your claim status using the following link:</p>
    <p><a href="{tracking_url}">Check Claim Status</a></p>
    <p>Best regards,<br>Claims Team</p>
    </body>
    </html>
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = row['SenderEmail']
    msg['To'] = recipient_email
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype='html')
    return msg
```

Leave the existing `send_email`, `main`, and `__main__` block as-is for now (a later task rewrites them).

- [ ] **Step 4: Run test to verify it passes**

Run from project root: `python -m unittest tests.test_send_claims -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add src/send_claims.py tests/test_send_claims.py
git commit -m "feat: add token generation and claim reference to email body"
```

---

### Task 3: Wire token persistence and DB-backed send logging into send_claims

**Files:**
- Modify: `src/send_claims.py`
- Test: `tests/test_send_claims.py`

**Interfaces:**
- Consumes: `db.store_token`, `db.add_send_log`, `db.init_db`, `db.get_send_log` (Task 1); `generate_token`/`compose_email` (Task 2).
- Produces:
  - `send_email(msg, row, token, db_path='claim_logs.db')` — persists token, tries SMTP send, records success/failure in `send_log`. Returns `True` on success, `False` on failure.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_send_claims.py`:

```python
import os
import tempfile
from unittest.mock import patch, MagicMock
from src import db


class TestSendEmailLogging(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)
        self.row = {
            'SenderEmail': 'sender@example.com',
            'SubsidiaryName': 'Acme Corp',
            'RecipientEmail': 'a@example.com',
            'ClaimReferenceNumber': 'CLM-2024-001',
            'ClaimURL': 'https://claims/1'
        }
        self.token = 'tok-abc-123'

    def tearDown(self):
        os.unlink(self.db_path)

    def test_success_records_sent_and_returns_true(self):
        msg = send_claims.compose_email(self.row, self.token)
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            result = send_claims.send_email(
                msg, self.row, self.token, db_path=self.db_path)
        self.assertTrue(result)
        record = db.get_send_log('a@example.com', 'CLM-2024-001', self.db_path)
        self.assertEqual(record['status'], 'sent')

    def test_failure_records_failed_to_send_and_returns_false(self):
        msg = send_claims.compose_email(self.row, self.token)
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.return_value.send_message.side_effect = Exception('down')
            mock_smtp.return_value.__enter__ = MagicMock(
                return_value=mock_smtp.return_value)
            mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
            with patch('time.sleep'):
                result = send_claims.send_email(
                    msg, self.row, self.token, db_path=self.db_path)
        self.assertFalse(result)
        record = db.get_send_log('a@example.com', 'CLM-2024-001', self.db_path)
        self.assertEqual(record['status'], 'failed_to_send')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_send_claims.TestSendEmailLogging -v`
Expected: FAIL — `send_email` doesn't accept `token`/`db_path`.

- [ ] **Step 3: Rewrite `send_email` and `main` in `src/send_claims.py`**

Replace the existing `send_email` and `main`:

```python
def send_email(msg, row, token, db_path='claim_logs.db'):
    """
    Persist the token, attempt SMTP send with retry, and record the outcome
    in send_log. Returns True on success, False on final failure.
    """
    recipient_email = row['RecipientEmail']
    claim_ref = row['ClaimReferenceNumber']
    # Persist token before send so click resolution works immediately.
    db.store_token(token, recipient_email, claim_ref, row['ClaimURL'], db_path)
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)
            db.add_send_log(recipient_email, claim_ref, 'sent', token,
                            db_path=db_path)
            print(f"Email sent to {msg['To']}")
            return True
        except Exception as e:
            delay = RETRY_DELAY_BASE * (2 ** attempt)
            print(f"Attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    db.add_send_log(recipient_email, claim_ref, 'failed_to_send', token,
                    error_message='All retries failed', db_path=db_path)
    print(f"Failed to send email to {msg['To']} after {MAX_RETRIES} attempts.")
    return False


def main(csv_path, db_path='claim_logs.db'):
    db.init_db(db_path)
    rows = read_csv(csv_path)
    for row in rows:
        token = generate_token()
        msg = compose_email(row, token)
        send_email(msg, row, token, db_path)
```

The `__main__` block below `main` calls `main(sys.argv[1])`; that remains valid since `db_path` has a default.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_send_claims -v`
Expected: PASS (all tests, including earlier Token/Compose/BaseUrl tests).

- [ ] **Step 5: Commit**

```bash
git add src/send_claims.py tests/test_send_claims.py
git commit -m "feat: persist tokens and DB-backed send logging in send_claims"
```

---

### Task 4: Remove legacy DB logging functions and file-based success log

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: cleaned `db.py` without `log_success`, `log_failure`, `log_click`, and the old `clicks`/`send_failures` tables.

- [ ] **Step 1: Confirm references are gone**

Search for remaining references to `log_success`, `log_failure`, `log_click` across `src/`:

Run: `grep -rn "log_success\|log_failure\|log_click" src/`
Expected: no matches (Tasks 1–3 already migrated send_claims.py and removed direct calls).

- [ ] **Step 2: Remove legacy functions and old tables from `src/db.py`**

At the end of `src/db.py`, delete the `log_success`, `log_failure`, and `log_click` functions. Verify `SCHEMA` no longer contains `clicks` or `send_failures` tables (Task 1 already replaced the schema; the old `send_failures`/`clicks` are not recreated).

- [ ] **Step 3: Run existing tests**

Run: `python -m unittest discover -v`
Expected: PASS (all tests from Tasks 1–3).

- [ ] **Step 4: Commit**

```bash
git add src/db.py
git commit -m "refactor: remove legacy clicks/send_failures tables and file-based logging"
```

---

### Task 5: Token-based web tracker with status transitions

**Files:**
- Modify: `src/web_tracker.py`
- Test: `tests/test_web_tracker.py`

**Interfaces:**
- Consumes: `db.get_claim_by_token`, `db.add_send_log`, `db.update_send_status`, `db.get_send_log` (Task 1).
- Produces:
  - `track()` — Flask route reading `?token=`, resolving claim URL, logging a click, transitioning status, redirecting.
  - `run_server(host='0.0.0.0', port=8000)` — starts Flask (no CSV needed).

- [ ] **Step 1: Write the failing test**

Create `tests/test_web_tracker.py`:

```python
# tests/test_web_tracker.py
import os
import tempfile
import unittest

from src import db
from src.web_tracker import app


class TestTrackEndpoint(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)
        db.store_token('tok-1', 'a@example.com', 'CLM-1', 'https://claims/1',
                       self.db_path)
        db.add_send_log('a@example.com', 'CLM-1', 'sent', 'tok-1',
                        db_path=self.db_path)
        app.config['TESTING'] = True
        app.config['DB_PATH'] = self.db_path

    def tearDown(self):
        os.unlink(self.db_path)

    def test_missing_token_returns_400(self):
        client = app.test_client()
        resp = client.get('/track')
        self.assertEqual(resp.status_code, 400)

    def test_invalid_token_returns_404(self):
        client = app.test_client()
        resp = client.get('/track?token=nope')
        self.assertEqual(resp.status_code, 404)

    def test_valid_token_redirects_and_updates_status(self):
        client = app.test_client()
        resp = client.get('/track?token=tok-1')
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.headers['Location'], 'https://claims/1')
        record = db.get_send_log('a@example.com', 'CLM-1', self.db_path)
        self.assertEqual(record['status'], 'clicked')


class TestLateClickTransition(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)
        db.store_token('tok-2', 'b@example.com', 'CLM-2', 'https://claims/2',
                       self.db_path)
        db.add_send_log('b@example.com', 'CLM-2', 'no_click', 'tok-2',
                        db_path=self.db_path)
        app.config['TESTING'] = True
        app.config['DB_PATH'] = self.db_path

    def tearDown(self):
        os.unlink(self.db_path)

    def test_no_click_moves_to_clicked(self):
        client = app.test_client()
        resp = client.get('/track?token=tok-2')
        self.assertEqual(resp.status_code, 302)
        record = db.get_send_log('b@example.com', 'CLM-2', self.db_path)
        self.assertEqual(record['status'], 'clicked')


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_web_tracker -v`
Expected: FAIL — `web_tracker.py` still uses CSV + recipient/claim params; token not handled.

- [ ] **Step 3: Rewrite `src/web_tracker.py`**

Replace the full file:

```python
from flask import Flask, request, redirect
from . import db

app = Flask(__name__)


def get_db_path():
    """Return configured DB path, overridable in tests via app.config."""
    return app.config.get('DB_PATH', 'claim_logs.db')


@app.route('/track')
def track():
    token = request.args.get('token')
    if not token:
        return "Missing token parameter", 400
    db_path = get_db_path()
    claim_url = db.get_claim_by_token(token, db_path)
    if not claim_url:
        return "Invalid tracking token", 404
    # Resolve the recipient/claim for this token to update the send log.
    conn = __import__('sqlite3').connect(db_path)
    conn.row_factory = __import__('sqlite3').Row
    row = conn.execute(
        "SELECT recipient_email, claim_reference_number FROM tracking_tokens "
        "WHERE token = ?", (token,)).fetchone()
    conn.close()
    if row:
        recipient = row['recipient_email']
        claim = row['claim_reference_number']
        existing = db.get_send_log(recipient, claim, db_path)
        if existing is None:
            db.add_send_log(recipient, claim, 'clicked', token, db_path=db_path)
        elif existing['status'] in ('sent', 'no_click'):
            db.update_send_status(recipient, claim, 'clicked', db_path)
    return redirect(claim_url)


def run_server(host='0.0.0.0', port=8000):
    db.init_db(get_db_path())
    app.run(host=host, port=port)


if __name__ == '__main__':
    import sys
    host = '0.0.0.0'
    port = 8000
    if len(sys.argv) > 1:
        host = sys.argv[1]
    if len(sys.argv) > 2:
        port = int(sys.argv[2])
    run_server(host, port)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_web_tracker -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add src/web_tracker.py tests/test_web_tracker.py
git commit -m "feat: token-based /track endpoint with status transitions"
```

---

### Task 6: Daily reconciliation of non-responsive recipients

**Files:**
- Modify: `src/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `send_log` table (Task 1).
- Produces:
  - `reconcile_no_clicks(db_path='claim_logs.db')` — marks `sent` entries with `created_at` before today as `no_click`; returns count updated.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_db.py`:

```python
class TestReconcileNoClicks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)
        db.add_send_log('today@example.com', 'CLM-T', 'sent', 'tok-t',
                        db_path=self.db_path)
        conn = __import__('sqlite3').connect(self.db_path)
        conn.execute(
            "INSERT INTO send_log (recipient_email, claim_reference_number, status, token, created_at) "
            "VALUES ('yesterday@example.com', 'CLM-Y', 'sent', 'tok-y', "
            "datetime('now', '-1 day'))")
        conn.commit()
        conn.close()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_marks_old_sent_as_no_click(self):
        updated = db.reconcile_no_clicks(self.db_path)
        self.assertEqual(updated, 1)
        row = db.get_send_log('yesterday@example.com', 'CLM-Y', self.db_path)
        self.assertEqual(row['status'], 'no_click')
        today = db.get_send_log('today@example.com', 'CLM-T', self.db_path)
        self.assertEqual(today['status'], 'sent')

    def test_reconcile_is_idempotent(self):
        db.reconcile_no_clicks(self.db_path)
        updated2 = db.reconcile_no_clicks(self.db_path)
        self.assertEqual(updated2, 0)


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_db.TestReconcileNoClicks -v`
Expected: FAIL — `reconcile_no_clicks` not defined.

- [ ] **Step 3: Implement `reconcile_no_clicks` in `src/db.py`**

Add to `src/db.py`:

```python
def reconcile_no_clicks(db_path='claim_logs.db'):
    """
    Mark send_log entries with status 'sent' created before today as 'no_click'.
    Returns the number of rows updated. Safe to run repeatedly (idempotent).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.execute(
        "UPDATE send_log SET status = 'no_click', updated_at = CURRENT_TIMESTAMP "
        "WHERE status = 'sent' AND created_at < date('now')")
    conn.commit()
    updated = cur.rowcount
    conn.close()
    return updated
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_db -v`
Expected: PASS (all db tests, including reconcile tests).

- [ ] **Step 5: Commit**

```bash
git add src/db.py tests/test_db.py
git commit -m "feat: add daily reconciliation for non-responsive recipients"
```

---

### Task 7: Validate all scenarios from the delta spec

**Files:**
- Test: `tests/test_spec_scenarios.py`

**Interfaces:**
- Consumes: all functions from Tasks 1–6.

- [ ] **Step 1: Write acceptance tests mapping delta-spec scenarios to behavior**

Create `tests/test_spec_scenarios.py`:

```python
# tests/test_spec_scenarios.py
"""
Acceptance tests mapping the delta spec scenarios to observable behavior.
"""
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from src import db
from src import send_claims
from src.web_tracker import app


class TestUniqueOpaqueTokens(unittest.TestCase):
    def test_every_recipient_gets_distinct_link(self):
        rows = [
            {'SenderEmail': 's@x.com', 'SubsidiaryName': 'A', 'RecipientEmail': 'a@x.com',
             'ClaimReferenceNumber': 'CLM-1', 'ClaimURL': 'https://c/1'},
            {'SenderEmail': 's@x.com', 'SubsidiaryName': 'B', 'RecipientEmail': 'b@x.com',
             'ClaimReferenceNumber': 'CLM-2', 'ClaimURL': 'https://c/2'},
        ]
        links = set()
        for row in rows:
            token = send_claims.generate_token()
            msg = send_claims.compose_email(row, token)
            body = msg.get_content()
            links.add(body.split('?token=')[1].strip())
        self.assertEqual(len(links), 2)


class TestSendOutcomeRecording(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_successful_send_records_sent(self):
        row = {'SenderEmail': 's@x.com', 'SubsidiaryName': 'A',
               'RecipientEmail': 'a@x.com', 'ClaimReferenceNumber': 'CLM-1',
               'ClaimURL': 'https://c/1'}
        msg = send_claims.compose_email(row, 'tok-x')
        with patch('smtplib.SMTP') as m:
            m.return_value.__enter__ = MagicMock(return_value=MagicMock())
            m.return_value.__exit__ = MagicMock(return_value=False)
            send_claims.send_email(msg, row, 'tok-x', db_path=self.db_path)
        record = db.get_send_log('a@x.com', 'CLM-1', self.db_path)
        self.assertEqual(record['status'], 'sent')

    def test_failed_send_records_failed_to_send(self):
        row = {'SenderEmail': 's@x.com', 'SubsidiaryName': 'A',
               'RecipientEmail': 'a@x.com', 'ClaimReferenceNumber': 'CLM-1',
               'ClaimURL': 'https://c/1'}
        msg = send_claims.compose_email(row, 'tok-x')
        with patch('smtplib.SMTP') as m:
            m.return_value.send_message.side_effect = Exception('down')
            m.return_value.__enter__ = MagicMock(return_value=m.return_value)
            m.return_value.__exit__ = MagicMock(return_value=False)
            with patch('time.sleep'):
                send_claims.send_email(msg, row, 'tok-x', db_path=self.db_path)
        record = db.get_send_log('a@x.com', 'CLM-1', self.db_path)
        self.assertEqual(record['status'], 'failed_to_send')


class TestNoClickReconciliationAndLateClick(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        db.init_db(self.db_path)
        db.store_token('tok-9', 'a@x.com', 'CLM-9', 'https://c/9', self.db_path)
        conn = __import__('sqlite3').connect(self.db_path)
        conn.execute(
            "INSERT INTO send_log (recipient_email, claim_reference_number, status, token, created_at) "
            "VALUES ('a@x.com', 'CLM-9', 'sent', 'tok-9', datetime('now', '-1 day'))")
        conn.commit()
        conn.close()

    def tearDown(self):
        os.unlink(self.db_path)

    def test_reconcile_marks_no_click_then_click_moves_to_clicked(self):
        db.reconcile_no_clicks(self.db_path)
        record = db.get_send_log('a@x.com', 'CLM-9', self.db_path)
        self.assertEqual(record['status'], 'no_click')
        app.config['TESTING'] = True
        app.config['DB_PATH'] = self.db_path
        client = app.test_client()
        resp = client.get('/track?token=tok-9')
        self.assertEqual(resp.status_code, 302)
        record = db.get_send_log('a@x.com', 'CLM-9', self.db_path)
        self.assertEqual(record['status'], 'clicked')


class TestTrackingBaseUrlConfig(unittest.TestCase):
    def test_operator_configured_base_url_used_in_link(self):
        with patch.dict(os.environ, {'TRACKING_BASE_URL': 'https://ops.example.com/track'},
                        clear=True):
            row = {'SenderEmail': 's@x.com', 'SubsidiaryName': 'A',
                   'RecipientEmail': 'a@x.com', 'ClaimReferenceNumber': 'CLM-1',
                   'ClaimURL': 'https://c/1'}
            msg = send_claims.compose_email(row, 'tok-x')
            self.assertIn('https://ops.example.com/track?token=tok-x',
                          msg.get_content())


if __name__ == '__main__':
    unittest.main()
```

- [ ] **Step 2: Run the full test suite**

Run: `python -m unittest discover -v`
Expected: PASS — all tests, including these acceptance mappings of every delta-spec scenario group:
- Unique opaque tokens per email (ADDED Requirement 1)
- Send outcomes recorded (sent / failed_to_send) (ADDED Requirement 2)
- Non-responsive marked during daily run (ADDED Requirement 3)
- Late click moves no_click → clicked (ADDED Requirement 4)
- Configurable tracking base URL (ADDED Requirement 5)
- Claim reference in email + token link (MODIFIED Requirement)

- [ ] **Step 3: Commit**

```bash
git add tests/test_spec_scenarios.py
git commit -m "test: add acceptance tests mapping delta-spec scenarios"
```

---

## Spec Coverage Checklist

Self-review mapping every delta-spec requirement/scenario to a task:

| Delta-spec requirement/scenario | Task(s) |
|---|---|
| System SHALL Issue a Unique Opaque Tracking Token per Email | Task 2 (generate_token), Task 3 (persist) |
| Token is recorded before email is sent | Task 3 (store_token before send) |
| System SHALL Record Every Send Outcome in the Database | Task 1 (schema), Task 3 (logging) |
| Failed send recorded with reason | Task 3 (failed_to_send) |
| Invalid recipient recorded with reason | Task 1 schema supports `invalid_recipient` in `LOG_STATUSES` |
| System SHALL Mark Non-Responsive Recipients During the Daily Run | Task 6 (reconcile_no_clicks) |
| System SHALL Move a Late-Clicking Recipient to Success | Task 5 (status transition), Task 6 |
| Tracking Link Base URL SHALL Be Configurable | Task 2 (get_tracking_base_url) |
| Modified: email body shows claim ref + token link | Task 2 (compose_email) |
| Modified: /track resolves via token, logs, redirects | Task 5 |
| REMOVED: (none) | — |
