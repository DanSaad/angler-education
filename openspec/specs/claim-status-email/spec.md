## Requirements

### Requirement: System SHALL Send Claim Status Email via SMTP

The system SHALL send a claim status email to each recipient listed in the CSV file using the company SMTP server.

#### Scenario: Notify claim recipient via email
- **GIVEN** a CSV file containing `SenderEmail`, `SubsidiaryName`, `RecipientEmail`, `ClaimReferenceNumber`, and `ClaimURL` and an SMTP server at `smtp://mysubsididary.mycompany.com:25`
- **WHEN** the utility processes a row from the CSV
- **THEN** the system SHALL send an email with subject "Important Update on Your Claim Status" and body containing a link to `/track?recipient=<RecipientEmail>&claim=<ClaimReferenceNumber>` that redirects to `ClaimURL`

#### Scenario: Track recipient clicks
- **GIVEN** a recipient clicks the tracking link in the email
- **WHEN** the request reaches `/track` with `recipient` and `claim` query parameters
- **THEN** the system MUST log the recipient email, claim reference, and claim URL to a SQL database and redirect the recipient to the claim URL
