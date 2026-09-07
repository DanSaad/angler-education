# Proposal

## Why

The claim-status email utility sends per-recipient status emails and logs click activity, but three gaps remain: (1) recipients never see their own claim reference in the email body, (2) tracking links expose recipient email addresses and claim references as plaintext query parameters and are only *incidentally* unique per row, and (3) database behavior is informally defined — successful sends go to a plain file while failures go to a table, and click-redirect resolution relies on a CSV map loaded at startup. This change makes links opaque and guaranteed unique, surfaces the recipient's claim number in the email body, and makes the SQLite database the single audit source for all send and click outcomes.

## What Changes

- **Email body shows the claim number**: each email body (plain text and HTML) displays the recipient's own `ClaimReferenceNumber`. Subject line unchanged.
- **Opaque, unique tracking links**: each sent email is assigned a unique UUID token before sending; the token (recipient → claim → claim URL) is persisted to the database. Email links become `/track?token=<uuid>` — no recipient email or claim reference in the URL. The old `/track?recipient=…&claim=…` format is removed.
- **Configurable tracking base URL**: the base URL used to build tracking links is read from a `TRACKING_BASE_URL` environment variable (default: `http://localhost:8000/track` for development).
- **Database as single audit source**:
  - New `tracking_tokens` table stores the token-to-claim mapping.
  - A single send-log table holds one entry per recipient with a status column: `sent`, `clicked`, `failed_to_send`, `invalid_recipient`, or `no_click` (replacing the `send_successes.log` file and the separate failure table).
  - A daily reconciliation step (same scheduler as the daily send) writes `no_click` entries for previously sent recipients with no recorded click.
  - `/track` resolves the claim URL from the database via the token, logs every click, and updates the send-log entry: a recipient previously marked `no_click` is moved to `clicked` (success) when they click their link. Tokens remain valid indefinitely.

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `claim-status-email`: email body includes the recipient's claim reference; tracking links are opaque, unique, and token-based; send outcomes (success, failure with reason, no-click) are persisted in the database; `/track` resolves and logs via token lookup and moves a previously `no_click` recipient to `clicked` when they click.

## Impact

- **Code**:
  - `src/send_claims.py` — token generation and persistence before send, claim number in body, `TRACKING_BASE_URL` env var, DB-backed success/failure logging.
  - `src/web_tracker.py` — token-only `/track` route, DB lookup for redirect, status transition (`no_click` → `clicked`) on late clicks, removal of the startup CSV claim-URL map.
  - `src/db.py` — schema additions (`tracking_tokens`, single send-log table with status column), success/failure logging, token/click helpers.
  - `src/csv_processor.py` — unchanged (claim reference column already required).
- **Database**: `claim_logs.db` schema changes; existing databases (if any) require re-initialization or migration. Utility is low-volume and not yet in production, so data loss risk is minimal.
- **Configuration/deployment**: `TRACKING_BASE_URL` must be set to a tracker URL reachable by recipients; the daily scheduler additionally performs no-click reconciliation.
- **Dependencies**: none added (`uuid4` and `sqlite3` are standard library).
