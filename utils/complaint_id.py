"""
CivicFix Unique Complaint ID Generator
Generates unique, sequentially incremented complaint identifiers in the format:
CFX-YYYY-000001
"""

import datetime
from database.db_connection import get_db, DB_PATH
from database.database_operations import fetch_one


def generate_complaint_id(db_path: str = DB_PATH) -> str:
    """
    Generates a unique complaint ID in the format CFX-<YEAR>-<6-DIGIT-SEQUENCE>.
    Example: CFX-2026-000001
    Queries the database to find the highest sequence for the current year.
    """
    current_year = datetime.datetime.now().year
    prefix = f"CFX-{current_year}-"

    # Query the highest complaint ID for the current year
    sql = """
        SELECT complaint_id FROM Complaints 
        WHERE complaint_id LIKE ? 
        ORDER BY id DESC LIMIT 1;
    """
    row = fetch_one(sql, (f"{prefix}%",), db_path=db_path)

    if not row or not row["complaint_id"]:
        next_seq = 1
    else:
        last_id = row["complaint_id"]
        try:
            # Extract sequence number after the second hyphen
            parts = last_id.split("-")
            last_seq = int(parts[2])
            next_seq = last_seq + 1
        except (IndexError, ValueError):
            next_seq = 1

    return f"{prefix}{next_seq:06d}"
