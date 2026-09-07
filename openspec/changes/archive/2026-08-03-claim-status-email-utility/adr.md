## Title
Claim‑Status Email Utility – Design Decisions

## Context
The project introduces a small utility to read CSV claim records and send templated status‑update emails, while logging click activity through a lightweight Flask endpoint.

## Decision
1. **Programming language**: Python 3.x – chosen for its rich standard library (csv, smtplib) and easy packaging.
2. **CSV parsing**: `csv.DictReader` with explicit column validation; ensures required columns (`SenderEmail,SubsidiaryName,RecipientEmail,ClaimReferenceNumber,ClaimURL`).
3. **Email format**: Plain‑text + HTML body containing a link to `/track?recipient=&claim=` that redirects to the claim URL.
4. **SMTP transport**: `smtplib.SMTP(host='mysubsididary.mycompany.com', port=25)` – no authentication, matching current infrastructure.
5. **Retry logic**: Up to 3 attempts with exponential back‑off (1 s, 2 s, 4 s) for transient failures.
6. **Logging**: Successful sends are recorded; failures inserted into `send_failures` table for later review.
7. **Click tracking endpoint**: Flask route `/track?recipient=&claim=` that records the hit in a SQLite table and redirects to the real claim URL.
8. **Database choice**: SQLite file‑based DB (`claim_logs.db`) – sufficient for low‑volume, single‑process usage.
9. **Deployment model**: Run `send_claims.py` via cron/Windows Task Scheduler once per day; keep Flask app running during the day for logging.

## Rationale
- Python is already available and well‑supported in the environment.
- `csv.DictReader` provides a simple, robust way to validate CSV rows.
- Using smtplib without authentication matches the company SMTP setup and keeps the utility lightweight.
- Retry logic protects against transient network hiccups while remaining low‑cost.
- SQLite offers persistence without the overhead of a server; adequate for 50–100 emails per day.
- Flask provides an immediate, minimal HTTP endpoint to capture clicks.

## Consequences
- No authentication required: trust the internal network.
- The utility is additive; no changes to existing production code.
- Click data is stored in SQLite – suitable for audit but not meant for high concurrency.
- Deployment relies on local scheduling; if the environment changes, the scheduler command may need adjustment.

## Supersedes
N/A