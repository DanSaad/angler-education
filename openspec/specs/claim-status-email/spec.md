## ADDED Requirements

### Requirement: Send Claim Status Email
Feature: claim-status-email
Rule: email-claim-status

#### Scenario: Notify claim recipient via email
- **GIVEN** a CSV file containing `SenderEmail,SubsidiaryName,RecipientEmail,ClaimReferenceNumber,ClaimURL` and an SMTP server at `smtp://mysubsididary.mycompany.com:25`
- **WHEN** the utility processes a row
- **THEN** it sends an email with subject "Important Update on Your Claim Status" and body containing a link to `/track?recipient=<RecipientEmail>&claim=<ClaimReferenceNumber>` that redirects to `ClaimURL`

## MODIFIED Requirements

(no modifications)

## REMOVED Requirements