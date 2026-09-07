from flask import Flask, request, redirect
import csv
import os
from . import db

app = Flask(__name__)

# Load claim URLs from CSV at startup
CLAIM_URLS = {}

def load_claim_urls(csv_path='claims.csv'):
    """Load mapping of claim_reference_number to claim_url from CSV."""
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            CLAIM_URLS[row['ClaimReferenceNumber']] = row['ClaimURL']

@app.route('/track')
def track():
    recipient = request.args.get('recipient')
    claim = request.args.get('claim')
    if not recipient or not claim:
        return "Missing recipient or claim parameter", 400
    # Look up claim URL
    claim_url = CLAIM_URLS.get(claim)
    if not claim_url:
        return "Claim not found", 404
    # Log click
    db.log_click(recipient, claim, claim_url)
    # Redirect to claim URL
    return redirect(claim_url)

def run_server(csv_path='claims.csv', host='0.0.0.0', port=8000):
    load_claim_urls(csv_path)
    db.init_db()
    app.run(host=host, port=port)

if __name__ == '__main__':
    import sys
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'claims.csv'
    run_server(csv_path)