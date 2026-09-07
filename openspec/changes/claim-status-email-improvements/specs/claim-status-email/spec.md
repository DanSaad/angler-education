## ADDED Requirements

### Requirement: System SHALL Issue a Unique Opaque Tracking Token per Email
Feature: Tracking link privacy

The system SHALL assign every sent email a distinct opaque tracking token so that no tracking link reveals the recipient's identity or claim reference.

#### Scenario: Every recipient receives a distinct link
- **GIVEN** the utility processes a CSV with multiple recipients
- **WHEN** each email is composed
- **THEN** every email's tracking link contains a distinct token
- **AND** no tracking link reveals the recipient's email address or claim reference

#### Scenario: Token is recorded before the email is sent
- **GIVEN** the utility has composed an email for a recipient
- **WHEN** the email is about to be sent
- **THEN** the token is stored in the database together with the recipient's details and claim URL

### Requirement: System SHALL Record Every Send Outcome in the Database
Feature: Claim status email audit trail

The system SHALL persist the outcome of every email send in the database, including successful sends and failures with their reason.

#### Scenario: Successful send is recorded
- **GIVEN** the utility sends an email to a recipient
- **WHEN** the SMTP server accepts the message
- **THEN** the database records the send with status "sent"

#### Scenario: Failed send is recorded with a reason
- **GIVEN** the utility attempts to send an email to a recipient
- **WHEN** the send fails
- **THEN** the database records the send with status "failed to send"

#### Scenario: Invalid recipient is recorded with a reason
- **GIVEN** the utility attempts to send an email to a recipient
- **WHEN** the recipient's email address is rejected as invalid
- **THEN** the database records the send with status "invalid recipient"

### Requirement: System SHALL Mark Non-Responsive Recipients During the Daily Run

The system SHALL identify recipients who were sent an email but never clicked their tracking link, during the daily run.

#### Scenario: Recipient with no recorded click is marked non-responsive
- **GIVEN** a recipient was sent a claim status email on a previous day
- **AND** the recipient has not clicked their tracking link
- **WHEN** the daily reconciliation runs
- **THEN** the database records the recipient's send with status "did not click"

### Requirement: System SHALL Move a Late-Clicking Recipient to Success

When a recipient marked as non-responsive later clicks their tracking link, the system SHALL update their record from "did not click" to "clicked".

#### Scenario: Non-responsive recipient clicks after being marked
- **GIVEN** a recipient's send is recorded as "did not click"
- **WHEN** the recipient clicks their tracking link
- **THEN** the system logs the click
- **AND** updates the recipient's record from "did not click" to "clicked"

### Requirement: Tracking Link Base URL SHALL Be Configurable

The base URL used to build tracking links SHALL be configurable by the operator, defaulting to a development value.

#### Scenario: Operator configures the tracking base URL
- **GIVEN** an operator has configured the tracker's base URL
- **WHEN** the utility composes an email
- **THEN** the email's tracking link uses the configured base URL

## MODIFIED Requirements

### Requirement: System SHALL Send Claim Status Email via SMTP

The system SHALL send a claim status email to each recipient listed in the CSV file using the company SMTP server.

#### Scenario: Notify claim recipient via email
- **GIVEN** a CSV file containing `SenderEmail`, `SubsidiaryName`, `RecipientEmail`, `ClaimReferenceNumber`, and `ClaimURL` and an SMTP server at `smtp://mysubsididary.mycompany.com:25`
- **WHEN** the utility processes a row from the CSV
- **THEN** the system SHALL send an email with subject "Important Update on Your Claim Status"
- **AND** the email body SHALL display the recipient's own claim reference number
- **AND** the email body SHALL contain a link to `/track?token=<tracking token>` that redirects to the recipient's `ClaimURL`

#### Scenario: Track recipient clicks
- **GIVEN** a recipient clicks the tracking link in the email
- **WHEN** the request reaches `/track` with a `token` query parameter
- **THEN** the system MUST log the click and redirect the recipient to the claim URL associated with the token

## REMOVED Requirements

(none)
