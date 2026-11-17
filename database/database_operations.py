"""
CivicFix Centralized Database Operations
Provides secure, parameterized query execution, transaction management,
and audit trail recording.
"""

from typing import Any, Dict, List, Optional, Tuple
from database.db_connection import get_connection, get_db_cursor, get_db, DB_PATH


def execute_query(sql: str, params: Tuple[Any, ...] = (), db_path: str = DB_PATH) -> int:
    """
    Executes an INSERT, UPDATE, or DELETE query with parameters.
    Returns the lastrowid of the inserted record or rows affected.
    """
    with get_db_cursor(db_path) as cursor:
        cursor.execute(sql, params)
        return cursor.lastrowid


def execute_update(sql: str, params: Tuple[Any, ...] = (), db_path: str = DB_PATH) -> int:
    """
    Executes an UPDATE or DELETE query with parameters.
    Returns the number of affected rows (rowcount).
    """
    with get_db_cursor(db_path) as cursor:
        cursor.execute(sql, params)
        return cursor.rowcount


def fetch_one(sql: str, params: Tuple[Any, ...] = (), db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """
    Executes a SELECT query and returns a single row as a dictionary,
    or None if no match is found.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        cursor.close()
        conn.close()


def fetch_all(sql: str, params: Tuple[Any, ...] = (), db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Executes a SELECT query and returns all matching rows as a list of dictionaries.
    """
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        cursor.close()
        conn.close()


def execute_transaction(operations: List[Tuple[str, Tuple[Any, ...]]], db_path: str = DB_PATH) -> bool:
    """
    Executes a sequence of (SQL, params) operations inside a single atomic transaction.
    If any operation fails, all previous changes are rolled back.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        for sql, params in operations:
            cursor.execute(sql, params)
        return True


def record_status_change(
    complaint_id: int,
    previous_status: Optional[str],
    new_status: str,
    changed_by_user_id: int,
    remarks: Optional[str] = None,
    db_path: str = DB_PATH
) -> bool:
    """
    Atomically updates the complaint status in the Complaints table
    and appends an immutable record into ComplaintStatusHistory.
    """
    with get_db(db_path) as conn:
        cursor = conn.cursor()
        
        # 1. Update the complaint's current status and relevant timestamp
        timestamp_col = ""
        if new_status == "VERIFIED":
            timestamp_col = ", verified_at = CURRENT_TIMESTAMP"
        elif new_status == "ASSIGNED":
            timestamp_col = ", assigned_at = CURRENT_TIMESTAMP"
        elif new_status == "COMPLETED_PENDING_VERIFICATION":
            timestamp_col = ", completed_at = CURRENT_TIMESTAMP"
        elif new_status == "RESOLVED":
            timestamp_col = ", resolved_at = CURRENT_TIMESTAMP"
        elif new_status == "CLOSED":
            timestamp_col = ", closed_at = CURRENT_TIMESTAMP"
        elif new_status == "REOPENED":
            timestamp_col = ", reopened_at = CURRENT_TIMESTAMP"

        cursor.execute(
            f"UPDATE Complaints SET status = ? {timestamp_col} WHERE id = ?;",
            (new_status, complaint_id)
        )

        # 2. Append history log
        cursor.execute(
            """
            INSERT INTO ComplaintStatusHistory 
                (complaint_id, previous_status, new_status, changed_by, remarks)
            VALUES (?, ?, ?, ?, ?);
            """,
            (complaint_id, previous_status, new_status, changed_by_user_id, remarks)
        )
        return True


def record_admin_action(
    admin_id: int,
    complaint_id: Optional[int],
    action_type: str,
    details: Optional[str] = None,
    db_path: str = DB_PATH
) -> int:
    """
    Records an administrative action in the audit trail.
    """
    return execute_query(
        """
        INSERT INTO AdminActionHistory (admin_id, complaint_id, action_type, details)
        VALUES (?, ?, ?, ?);
        """,
        (admin_id, complaint_id, action_type, details),
        db_path=db_path
    )


def create_notification(
    user_id: int,
    complaint_id: Optional[int],
    title: str,
    message: str,
    notification_type: str,
    db_path: str = DB_PATH
) -> int:
    """
    Inserts an in-app notification for a given user.
    """
    return execute_query(
        """
        INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
        VALUES (?, ?, ?, ?, ?);
        """,
        (user_id, complaint_id, title, message, notification_type),
        db_path=db_path
    )


def get_table_counts(db_path: str = DB_PATH) -> Dict[str, int]:
    """
    Returns a dictionary of all 14 tables with their current row counts.
    """
    tables = [
        "Users", "CitizenProfiles", "WorkerProfiles", "Complaints",
        "ComplaintImages", "WorkerAssignments", "ComplaintStatusHistory",
        "WorkerProgressUpdates", "Feedback", "ComplaintSupports",
        "AdminActionHistory", "WorkChecklistItems", "MaterialRequirements",
        "Notifications"
    ]
    counts = {}
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        for tbl in tables:
            try:
                cursor.execute(f"SELECT COUNT(*) FROM {tbl};")
                counts[tbl] = cursor.fetchone()[0]
            except Exception:
                counts[tbl] = -1
        return counts
    finally:
        conn.close()
