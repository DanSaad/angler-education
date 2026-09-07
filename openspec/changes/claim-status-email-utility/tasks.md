## 1. Setup

- [ ] 1.1 Create project folder `src` and add `__init__.py`
- [ ] 1.2 Add placeholder scripts: `send_claims.py` and `web_tracker.py`

## 2. Database

- [ ] 2.1 Define SQLite schema for `claim_logs.db`: tables `clicks` and `send_failures`
- [ ] 2.2 Implement helper functions to init DB on first run

## 3. CSV Processing

- [ ] 3.1 Write function to read CSV rows, validate required columns
- [ ] 3.2 For each row, compose email subject/body with link to `/track`

## 4. Email Sending

- [ ] 4.1 Configure `smtplib.SMTP` to host `mysubsididary.mycompany.com`, port 25
- [ ] 4.2 Implement retry logic: up to 3 attempts, exponential back‑off
- [ ] 4.3 Log successes and failures; write failures to `send_failures`

## 5. Tracking Endpoint

- [ ] 5.1 Create Flask route `/track` that records recipient & claim into DB then redirects to ClaimURL
- [ ] 5.2 Ensure database connection is thread‑safe for Flask

## 6. Deployment

- [ ] 6.1 Schedule `send_claims.py` via cron/Task Scheduler once per day
- [ ] 6.2 Keep Flask app running during the day for click logging

