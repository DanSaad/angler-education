# Proposal
## Why

The current claim‑status workflow relies on manual or ad‑hoc email notifications, making it error‑prone and lacking auditability.  This change introduces an automated, low‑volume utility that sends a single “Important Update on Your Claim Status” email to each recipient and records click activity for transparency.

## What Changes
- Add `send_claims.py` – CLI script that reads CSV rows, formats the message, and sends via SMTP.
- Add `web_tracker.py` – minimal Flask app that serves `/track?recipient=…&claim=` and logs clicks in a SQL table.
- Create accompanying documentation (specs, design, ADR, tasks).

## Capabilities
### New Capabilities
- `claim-status-email`: Send templated status‑update emails for claim references.
  - Sends via company SMTP server (`smtp://mysubsididary.mycompany.com:25`).
  - Tracks clicks through `/track` endpoint and logs to a SQL table.

### Modified Capabilities
(none)

## Impact
- Adds two small scripts; no changes to existing production code.
- Requires the ability to run a Flask app locally for tracking, which is already available in the environment.
