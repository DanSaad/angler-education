## Context

The change introduces a small Python utility that reads a CSV containing claim information and sends an email to each recipient using the company SMTP server. A minimal Flask endpoint logs clicks when recipients follow the link in the email.

The project is low‑volume (50–100 emails per day) and requires no authentication on the SMTP server.

## Goals / Non-Goals

**Goals:**
- Provide a reliable, auditable way to notify claim recipients.
- Record click activity for audit purposes.
- Keep implementation simple: a single script and a tiny Flask app.

**Non‑Goals:**
- Full email queue or retry system.
- Authentication for SMTP.
- Distributed deployment – the utility will run locally on the same machine that owns the CSV.

## Decisions

1. **Programming language** – Python 3.x (widely supported, easy to ship). 
2. **CSV parsing** – Use `csv.DictReader` with explicit validation of required columns.
3. **Email format** – Plain‑text + HTML body; link redirects to `/track`. 
4. **SMTP transport** – `smtplib.SMTP(host='mysubsididary.mycompany.com', port=25)` without authentication.
5. **Retry logic** – Up to 3 attempts with exponential back‑off (1 s, 2 s, 4 s).
6. **Logging** – Successful sends are logged; failures go into `send_failures` table for later review.
7. **Click tracking endpoint** – Flask route `/track?recipient=&claim=` that records in a SQL table and redirects to the real claim URL.
8. **Database** – SQLite (file‑based) for simplicity; schema defined in design.
9. **Deployment** – Run `send_claims.py` via cron or Windows Task Scheduler once per day.

## Risks / Trade‑offs
- **SMTP limits**: The server may limit connections; low volume mitigates this risk.
- **No auth**: Exposes the SMTP endpoint; trust in internal network.
- **SQLite concurrency**: Not needed since single process.
- **Flask overhead**: Minimal for click logging.

## Migration Plan

The change is additive. No existing code is touched. Deployment steps:
1. Place `send_claims.py` and `web_tracker.py` in a directory.
2. Create SQLite file `claim_logs.db` (schema created by script on first run).
3. Schedule `send_claims.py --csv claims.csv` via cron/Task Scheduler.
4. Keep Flask app running during the day for click logging.

## Open Questions
- None identified; all decisions are supported by current constraints and low‑volume requirement.
