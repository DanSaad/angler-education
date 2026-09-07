# Claim Status Email Utility

A Python utility that automates sending claim status update emails to recipients and tracks click activity.

## Overview

This utility reads a CSV file containing claim information and sends personalized emails to each recipient using the company's SMTP server. When recipients click the tracking link in the email, their activity is logged in a SQL database for audit purposes.

## Features

- **CSV Processing**: Reads claim data from CSV files with columns: `SenderEmail`, `SubsidiaryName`, `RecipientEmail`, `ClaimReferenceNumber`, `ClaimURL`
- **Email Sending**: Sends emails via SMTP (port 25, no authentication) with retry logic (up to 3 attempts with exponential backoff)
- **Click Tracking**: Logs recipient clicks in a SQLite database with timestamps
- **Error Handling**: Records failed sends for later review

## Project Structure

```
src/
├── __init__.py          # Package initialization
├── send_claims.py       # Main email sender script
├── web_tracker.py       # Flask endpoint for click tracking
├── csv_processor.py     # CSV reading and validation
└── db.py                # SQLite database operations
```

## Usage

### Sending Emails

```bash
python -m src.send_claims claims.csv
```

### Running the Tracking Server

```bash
python -m src.web_tracker claims.csv
```

The tracking server runs on `http://localhost:8000` and provides a `/track` endpoint that logs clicks and redirects to the claim URL.

## Database Schema

The utility creates a SQLite database `claim_logs.db` with two tables:

- **clicks**: Stores recipient click activity (recipient email, claim reference, claim URL, timestamp)
- **send_failures**: Stores failed email attempts (row data, error message, timestamp)

## Configuration

- **SMTP Server**: `mysubsididary.mycompany.com:25` (no authentication)
- **Tracking Server**: `http://localhost:8000`
- **Database**: SQLite file `claim_logs.db` (created automatically)

## Dependencies

- Python 3.x
- Flask (for the tracking server)
- Standard library modules: `smtplib`, `csv`, `sqlite3`, `email`

## Development

This project was developed using the OpenSpec intent-driven workflow with the following artifacts:

- **Proposal**: Defines the problem and solution
- **Design**: Technical architecture and decisions
- **Specs**: Gherkin-style requirements
- **ADR**: Architectural decisions
- **Tasks**: Implementation checklist

All artifacts are stored in the `openspec/changes/claim-status-email-utility/` directory.