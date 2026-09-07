import csv

REQUIRED_COLUMNS = [
    'SenderEmail',
    'SubsidiaryName',
    'RecipientEmail',
    'ClaimReferenceNumber',
    'ClaimURL'
]

def read_csv(file_path):
    """
    Read CSV file and validate required columns.
    Returns a list of dictionaries, each representing a row.
    Raises ValueError if required columns are missing.
    """
    with open(file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        # Check if required columns are present
        missing = [col for col in REQUIRED_COLUMNS if col not in reader.fieldnames]
        if missing:
            raise ValueError(f"Missing required columns: {missing}")
        rows = list(reader)
    return rows