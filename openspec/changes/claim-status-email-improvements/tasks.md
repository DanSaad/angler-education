## 1. Database Schema Updates

- [ ] 1.1 Add `tracking_tokens` table to store token-to-claim mappings
- [ ] 1.2 Create unified `send_log` table with status column (sent, clicked, failed_to_send, invalid_recipient, no_click)
- [ ] 1.3 Update `init_db()` function to create new tables
- [ ] 1.4 Add migration logic for existing databases (if needed)

## 2. Token Generation & Tracking

- [ ] 2.1 Implement UUID token generation function
- [ ] 2.2 Add token persistence to database before sending email
- [ ] 2.3 Update `compose_email()` to use token-based tracking links
- [ ] 2.4 Add `TRACKING_BASE_URL` environment variable support

## 3. Email Body Updates

- [ ] 3.1 Modify plain text email body to include recipient's claim reference number
- [ ] 3.2 Modify HTML email body to include recipient's claim reference number

## 4. Database Logging Improvements

- [ ] 4.1 Replace `log_success()` file-based logging with database `send_log` entry
- [ ] 4.2 Update `log_failure()` to use unified `send_log` table with "failed_to_send" status
- [ ] 4.3 Add `log_invalid_recipient()` function for invalid email addresses
- [ ] 4.4 Add `log_no_click()` function for daily reconciliation

## 5. Web Tracker Updates

- [ ] 5.1 Update `/track` route to accept `token` query parameter only
- [ ] 5.2 Implement token lookup in database to resolve claim URL
- [ ] 5.3 Add status transition logic: update "no_click" to "clicked" on late clicks
- [ ] 5.4 Remove CSV-based claim URL loading at startup

## 6. Daily Reconciliation

- [ ] 6.1 Implement daily reconciliation function to mark non-responsive recipients
- [ ] 6.2 Integrate reconciliation with existing daily scheduler
- [ ] 6.3 Add logging for reconciliation activities

## 7. Testing & Validation

- [ ] 7.1 Test token generation and uniqueness
- [ ] 7.2 Test email sending with token-based links
- [ ] 7.3 Test click tracking with token resolution
- [ ] 7.4 Test status transitions (no_click → clicked)
- [ ] 7.5 Test daily reconciliation process
- [ ] 7.6 Validate all scenarios from delta spec