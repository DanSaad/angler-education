# Claim Status Email Improvements Design

## Overview

This design document outlines improvements to the claim-status-email utility to address three key gaps: recipients not seeing their claim reference in emails, tracking links exposing sensitive information, and informal database behavior. The changes make links opaque and unique, surface the recipient's claim number in the email body, and establish the SQLite database as the single audit source for all send and click outcomes.

## Architecture

### Current Architecture
- `send_claims.py` → Sends emails with tracking links containing recipient email and claim reference
- `web_tracker.py` → Flask app that logs clicks and redirects using CSV-loaded claim URLs
- `db.py` → SQLite database with separate tables for clicks and send failures

### Proposed Architecture
- `send_claims.py` → Generates unique tokens, stores them in DB, sends emails with token-based links
- `web_tracker.py` → Flask app that resolves tokens via DB lookup, logs clicks, updates status
- `db.py` → Unified database with token mapping, send log with status tracking, and reconciliation functions

### Key Changes
1. **Token System**: Each email gets a unique UUID token stored in `tracking_tokens` table
2. **Unified Logging**: Single `send_log` table tracks all outcomes (sent, clicked, failed, invalid, no_click)
3. **Status Transitions**: Recipients can move from "no_click" to "clicked" when they finally click
4. **Daily Reconciliation**: Automated marking of non-responsive recipients

## Database Design

### New Tables

#### `tracking_tokens`
Maps tokens to claim details:
- `token` (TEXT, PRIMARY KEY) - UUID token
- `recipient_email` (TEXT) - Recipient's email address
- `claim_reference_number` (TEXT) - Claim reference number
- `claim_url` (TEXT) - URL to redirect to
- `created_at` (TIMESTAMP) - When token was created

#### `send_log`
Unified tracking of all email outcomes:
- `id` (INTEGER, PRIMARY KEY) - Auto-increment ID
- `recipient_email` (TEXT) - Recipient's email address
- `claim_reference_number` (TEXT) - Claim reference number
- `status` (TEXT) - One of: 'sent', 'clicked', 'failed_to_send', 'invalid_recipient', 'no_click'
- `token` (TEXT) - Reference to tracking_tokens table
- `error_message` (TEXT) - Error details for failed sends
- `created_at` (TIMESTAMP) - When record was created
- `updated_at` (TIMESTAMP) - When record was last updated

### Removed Tables
- `clicks` - Replaced by status updates in `send_log`
- `send_failures` - Replaced by 'failed_to_send' status in `send_log`

### Key Relationships
- `send_log.token` references `tracking_tokens.token`
- Status transitions: 'sent' → 'clicked' (on click), 'sent' → 'no_click' (daily reconciliation), 'no_click' → 'clicked' (late click)

## Token System Design

### Token Generation
- Use Python's `uuid.uuid4()` to generate unique tokens
- Tokens are 36-character strings (e.g., `550e8400-e29b-41d4-a716-446655440000`)
- Generated before email composition to ensure persistence

### Token Lifecycle
1. **Generation**: Token created when processing each CSV row
2. **Persistence**: Token stored in `tracking_tokens` table with recipient/claim details
3. **Email Composition**: Tracking link uses token: `{TRACKING_BASE_URL}?token={token}`
4. **Click Resolution**: `/track` endpoint looks up token in database
5. **Status Update**: Click event updates `send_log` status from 'sent' to 'clicked'

### Token Uniqueness
- UUID4 provides cryptographically random tokens
- Probability of collision is negligible for this use case
- No need for additional uniqueness checks

### Token Storage
- Token stored before email send to ensure it exists if click occurs
- Token remains valid indefinitely (no expiration)
- Token maps to recipient email, claim reference, and claim URL

### Configuration
- `TRACKING_BASE_URL` environment variable (default: `http://localhost:8000/track`)
- Base URL used to construct full tracking link

## Email Body Design

### Current Email Body
- Plain text: "Dear {SubsidiaryName} claimant, Please check your claim status using the following link: {tracking_url}"
- HTML: Similar content with clickable link

### Proposed Email Body
- Plain text: "Dear {SubsidiaryName} claimant, Your claim reference number is {ClaimReferenceNumber}. Please check your claim status using the following link: {tracking_url}"
- HTML: Similar content with claim reference number displayed prominently

### Key Changes
1. **Claim Reference Display**: Recipient's own claim reference number added to body
2. **Tracking Link**: Now uses token-based URL: `{TRACKING_BASE_URL}?token={token}`
3. **Subject Line**: Unchanged ("Important Update on Your Claim Status")

### Example Updated Email (Plain Text)
```
Dear Acme Corp claimant,

Your claim reference number is CLM-2024-001.

Please check your claim status using the following link:
http://localhost:8000/track?token=550e8400-e29b-41d4-a716-446655440000

Best regards,
Claims Team
```

### Example Updated Email (HTML)
```html
<html>
<body>
<p>Dear Acme Corp claimant,</p>
<p>Your claim reference number is <strong>CLM-2024-001</strong>.</p>
<p>Please check your claim status using the following link:</p>
<p><a href="http://localhost:8000/track?token=550e8400-e29b-41d4-a716-446655440000">Check Claim Status</a></p>
<p>Best regards,<br>Claims Team</p>
</body>
</html>
```

## Web Tracker Design

### Current Implementation
- Loads claim URLs from CSV at startup
- `/track` endpoint expects `recipient` and `claim` query parameters
- Logs click to `clicks` table

### Proposed Implementation
- No CSV loading at startup
- `/track` endpoint expects only `token` query parameter
- Looks up token in `tracking_tokens` table to get claim URL
- Updates `send_log` status from 'sent' to 'clicked'
- Handles late clicks (status transitions from 'no_click' to 'clicked')

### Updated `/track` Endpoint
1. **Token Validation**: Check if token exists in `tracking_tokens` table
2. **Claim Resolution**: Get claim URL from token mapping
3. **Status Update**: Update `send_log` status to 'clicked' (handle both 'sent' and 'no_click' statuses)
4. **Click Logging**: Log click details (optional, could be derived from status update)
5. **Redirect**: Redirect user to claim URL

### Error Handling
- Invalid token: Return 404 "Invalid tracking token"
- Missing token: Return 400 "Missing token parameter"
- Database error: Return 500 "Internal server error"

### Status Transition Logic
- If current status is 'sent' → update to 'clicked'
- If current status is 'no_click' → update to 'clicked' (late click)
- If current status is already 'clicked' → no change (idempotent)

## Daily Reconciliation Design

### Current Implementation
- No reconciliation process exists
- Recipients who don't click are not tracked

### Proposed Implementation
- Daily process runs after email sending
- Identifies recipients with status 'sent' who haven't clicked
- Updates their status to 'no_click'
- Logs reconciliation activities

### Reconciliation Logic
1. **Query**: Find all `send_log` entries with status 'sent' where `created_at` < today
2. **Update**: Change status from 'sent' to 'no_click' for these entries
3. **Logging**: Record how many recipients were marked as non-responsive
4. **Idempotency**: Running multiple times per day should not cause issues

### Integration with Daily Scheduler
- Reconciliation runs as part of the daily email sending process
- Could run before or after sending new emails
- Recommended: Run after sending to avoid marking new emails as non-responsive

### Example Reconciliation Output
```
Daily reconciliation completed:
- Marked 15 recipients as non-responsive
- Total recipients tracked: 150
- Recipients who clicked: 120
- Recipients who haven't clicked: 30
```

### Edge Cases
- Recipient clicks after being marked 'no_click' → Status updates to 'clicked' (handled by web tracker)
- Recipient never receives email (failed send) → Status remains 'failed_to_send'
- Invalid recipient → Status remains 'invalid_recipient'

## Implementation Tasks

See `openspec/changes/claim-status-email-improvements/tasks.md` for detailed implementation tasks organized into 7 groups:

1. Database Schema Updates
2. Token Generation & Tracking
3. Email Body Updates
4. Database Logging Improvements
5. Web Tracker Updates
6. Daily Reconciliation
7. Testing & Validation

## Testing Strategy

### Unit Tests
- Token generation and uniqueness
- Database operations (token storage, status updates)
- Email composition with claim reference
- Web tracker token resolution

### Integration Tests
- End-to-end email sending with token-based links
- Click tracking and status transitions
- Daily reconciliation process

### Validation
- Verify all scenarios from delta spec are implemented
- Test error handling for invalid tokens, missing parameters
- Test idempotency of status updates

## Deployment Considerations

### Configuration
- Set `TRACKING_BASE_URL` environment variable to tracker URL reachable by recipients
- Ensure SQLite database file is writable by both email sender and web tracker

### Migration
- Existing databases require re-initialization or migration
- Low-volume utility not yet in production, so data loss risk is minimal

### Monitoring
- Log all token generation, email sends, clicks, and reconciliation activities
- Monitor database size and performance