import smtplib
import time
from email.message import EmailMessage
from .csv_processor import read_csv
from . import db

TRACKING_BASE_URL = "http://localhost:8000/track"
SMTP_HOST = 'mysubsididary.mycompany.com'
SMTP_PORT = 25
MAX_RETRIES = 3
RETRY_DELAY_BASE = 1  # seconds

def compose_email(row):
    """
    Compose an email message for a given claim row.
    Returns an EmailMessage object.
    """
    recipient_email = row['RecipientEmail']
    claim_ref = row['ClaimReferenceNumber']
    tracking_url = f"{TRACKING_BASE_URL}?recipient={recipient_email}&claim={claim_ref}"
    subject = "Important Update on Your Claim Status"
    plain_body = f"Dear {row['SubsidiaryName']} claimant,\n\nPlease check your claim status using the following link:\n{tracking_url}\n\nBest regards,\nClaims Team"
    html_body = f"""
    <html>
    <body>
    <p>Dear {row['SubsidiaryName']} claimant,</p>
    <p>Please check your claim status using the following link:</p>
    <p><a href="{tracking_url}">Check Claim Status</a></p>
    <p>Best regards,<br>Claims Team</p>
    </body>
    </html>
    """
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = row['SenderEmail']
    msg['To'] = recipient_email
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype='html')
    return msg

def send_email(msg, row):
    """
    Send an email message via SMTP with retry logic.
    Returns True on success, False on final failure.
    """
    row_str = str(row)  # for logging
    for attempt in range(MAX_RETRIES):
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.send_message(msg)
            # Log success
            db.log_success(row['RecipientEmail'], row['ClaimReferenceNumber'])
            print(f"Email sent to {msg['To']}")
            return True
        except Exception as e:
            delay = RETRY_DELAY_BASE * (2 ** attempt)
            print(f"Attempt {attempt+1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)
    # All retries failed
    db.log_failure(row_str, "All retries failed")
    print(f"Failed to send email to {msg['To']} after {MAX_RETRIES} attempts.")
    return False

def main(csv_path):
    # Initialize database
    db.init_db()
    # Read CSV
    rows = read_csv(csv_path)
    # Process each row
    for row in rows:
        msg = compose_email(row)
        send_email(msg, row)

if __name__ == '__main__':
    import sys
    if len(sys.argv) != 2:
        print("Usage: python -m src.send_claims <csv_path>")
        sys.exit(1)
    main(sys.argv[1])