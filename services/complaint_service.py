"""
CivicFix Complaint Service Layer
Encapsulates all business logic for complaint submissions, citizen scoped queries,
timeline tracking, duplicate issue supporting, reopening, and feedback submission.
"""

from typing import List, Dict, Any, Optional, Tuple
from database.db_connection import get_db, DB_PATH
from database.database_operations import (
    fetch_one, fetch_all, execute_query, execute_update,
    record_status_change, create_notification
)
from utils.complaint_id import generate_complaint_id

# Standard Civic Issue Categories (as specified in requirements)
CATEGORIES = [
    "Road damage / pothole",
    "Broken streetlight",
    "Garbage / waste issue",
    "Drainage blockage",
    "Water leakage",
    "Damaged public property",
    "Illegal dumping",
    "Other civic issue",
]


def create_complaint(
    citizen_id: int,
    title: str,
    description: str,
    category: str,
    location: str,
    locality: str,
    ward_number: Optional[str] = None,
    image_rel_path: Optional[str] = None,
    is_emergency: bool = False,
    is_anonymous: bool = False,
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[str], Optional[int], str]:
    """
    Submits a new citizen complaint.
    - Generates unique ID (e.g. CFX-2026-000001)
    - Records initial status as 'NEW'
    - Saves evidence image reference
    - Creates status history and welcome notification
    """
    # Validation
    title = (title or "").strip()
    description = (description or "").strip()
    location = (location or "").strip()
    locality = (locality or "").strip()
    ward_number = (ward_number or "").strip() or None

    if not title or len(title) < 5:
        return False, None, None, "Complaint title must be at least 5 characters."
    if not description or len(description) < 10:
        return False, None, None, "Detailed description must be at least 10 characters."
    if category not in CATEGORIES:
        return False, None, None, "Please select a valid issue category."
    if not location:
        return False, None, None, "Specific issue location is required."
    if not locality:
        return False, None, None, "Locality / Area is required."

    complaint_code = generate_complaint_id(db_path=db_path)
    priority = "EMERGENCY" if is_emergency else "MEDIUM"
    suggested = "EMERGENCY" if is_emergency else "MEDIUM"
    reason = "Citizen marked this issue as an emergency." if is_emergency else "Default standard submission."

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            # 1. Insert Complaint Record
            cursor.execute(
                """
                INSERT INTO Complaints (
                    complaint_id, citizen_id, title, description, category,
                    location, locality, ward_number, is_emergency, is_anonymous,
                    priority, suggested_priority, priority_reason, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'NEW');
                """,
                (
                    complaint_code, citizen_id, title, description, category,
                    location, locality, ward_number, 1 if is_emergency else 0,
                    1 if is_anonymous else 0, priority, suggested, reason
                )
            )
            complaint_db_id = cursor.lastrowid

            # 2. Insert Evidence Image if provided
            if image_rel_path:
                cursor.execute(
                    """
                    INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption)
                    VALUES (?, ?, 'EVIDENCE', ?, 'Initial evidence photo uploaded by citizen.');
                    """,
                    (complaint_db_id, image_rel_path, citizen_id)
                )

            # 3. Insert Initial Lifecycle Status History
            cursor.execute(
                """
                INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                VALUES (?, NULL, 'NEW', ?, 'Complaint submitted by citizen.');
                """,
                (complaint_db_id, citizen_id)
            )

            # 4. Create Notification for the Citizen
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                VALUES (?, ?, ?, ?, 'STATUS_UPDATE');
                """,
                (
                    citizen_id, complaint_db_id, "Complaint Submitted Successfully",
                    f"Your complaint '{title}' has been registered with ID {complaint_code}. Status: NEW."
                )
            )

        return True, complaint_code, complaint_db_id, f"Complaint submitted successfully! ID: {complaint_code}"
    except Exception as exc:
        return False, None, None, f"Database error creating complaint: {exc}"


def get_citizen_complaints(
    citizen_id: int,
    search_query: Optional[str] = None,
    category_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Returns complaints filed by a specific citizen with optional search and filters.
    Enforces privacy by restricting results exclusively to citizen_id.
    """
    sql = """
        SELECT c.*, 
               (SELECT image_path FROM ComplaintImages WHERE complaint_id = c.id AND image_type = 'EVIDENCE' LIMIT 1) as evidence_image,
               (SELECT image_path FROM ComplaintImages WHERE complaint_id = c.id AND image_type = 'COMPLETION' LIMIT 1) as completion_image,
               (SELECT full_name FROM WorkerProfiles WHERE user_id = (SELECT worker_id FROM WorkerAssignments WHERE complaint_id = c.id AND is_current = 1 LIMIT 1)) as assigned_worker_name
        FROM Complaints c
        WHERE c.citizen_id = ?
    """
    params: List[Any] = [citizen_id]

    if search_query:
        sq = f"%{search_query.strip()}%"
        sql += " AND (c.complaint_id LIKE ? OR c.title LIKE ? OR c.location LIKE ? OR c.locality LIKE ?)"
        params.extend([sq, sq, sq, sq])

    if category_filter and category_filter != "All Categories":
        sql += " AND c.category = ?"
        params.append(category_filter)

    if status_filter and status_filter != "All Statuses":
        sql += " AND c.status = ?"
        params.append(status_filter)

    sql += " ORDER BY c.submitted_at DESC;"
    return fetch_all(sql, tuple(params), db_path=db_path)


def get_complaint_details(complaint_id_or_code: Any, db_path: str = DB_PATH) -> Optional[Dict[str, Any]]:
    """
    Fetches full metadata for a complaint by integer ID or 'CFX-...' string code.
    """
    if isinstance(complaint_id_or_code, int) or str(complaint_id_or_code).isdigit():
        sql = "SELECT * FROM Complaints WHERE id = ?;"
        param = int(complaint_id_or_code)
    else:
        sql = "SELECT * FROM Complaints WHERE complaint_id = ?;"
        param = str(complaint_id_or_code)

    complaint = fetch_one(sql, (param,), db_path=db_path)
    if not complaint:
        return None

    cid = complaint["id"]

    # Fetch Evidence and Completion Images
    images = fetch_all("SELECT * FROM ComplaintImages WHERE complaint_id = ? ORDER BY uploaded_at ASC;", (cid,), db_path=db_path)
    complaint["images"] = images

    # Fetch Worker Assignment if assigned
    assignment = fetch_one(
        """
        SELECT wa.*, wp.full_name as worker_name, wp.phone as worker_phone, wp.department as worker_dept
        FROM WorkerAssignments wa
        JOIN WorkerProfiles wp ON wa.worker_id = wp.user_id
        WHERE wa.complaint_id = ? AND wa.is_current = 1;
        """,
        (cid,),
        db_path=db_path
    )
    complaint["assignment"] = assignment

    # Fetch Progress Updates
    updates = fetch_all(
        "SELECT * FROM WorkerProgressUpdates WHERE complaint_id = ? ORDER BY created_at DESC;",
        (cid,),
        db_path=db_path
    )
    complaint["progress_updates"] = updates

    # Fetch Feedback if exists
    feedback = fetch_one("SELECT * FROM Feedback WHERE complaint_id = ?;", (cid,), db_path=db_path)
    complaint["feedback"] = feedback

    # Fetch Citizen Details
    citizen = fetch_one(
        "SELECT cp.full_name, cp.phone, cp.locality, u.username, u.email FROM Users u JOIN CitizenProfiles cp ON u.id = cp.user_id WHERE u.id = ?;",
        (complaint["citizen_id"],),
        db_path=db_path
    )
    complaint["citizen"] = citizen

    return complaint


def get_complaint_timeline(complaint_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieves the chronological audit trail of all status transitions for a complaint.
    """
    sql = """
        SELECT sh.*, u.username as changer_username, u.role as changer_role
        FROM ComplaintStatusHistory sh
        JOIN Users u ON sh.changed_by = u.id
        WHERE sh.complaint_id = ?
        ORDER BY sh.changed_at ASC, sh.id ASC;
    """
    return fetch_all(sql, (complaint_id,), db_path=db_path)


def support_complaint(complaint_id: int, citizen_id: int, db_path: str = DB_PATH) -> Tuple[bool, int, str]:
    """
    Adds citizen support to an existing issue ('I ALSO FACE THIS ISSUE').
    Enforces unique constraints so each citizen can only support a complaint once.
    """
    existing = fetch_one(
        "SELECT id FROM ComplaintSupports WHERE complaint_id = ? AND citizen_id = ?;",
        (complaint_id, citizen_id),
        db_path=db_path
    )
    if existing:
        return False, 0, "You have already supported this complaint."

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ComplaintSupports (complaint_id, citizen_id) VALUES (?, ?);",
                (complaint_id, citizen_id)
            )
            cursor.execute(
                "UPDATE Complaints SET support_count = support_count + 1 WHERE id = ?;",
                (complaint_id,)
            )

        updated = fetch_one("SELECT support_count FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
        new_cnt = updated["support_count"] if updated else 1
        return True, new_cnt, f"Support recorded! Total citizens affected: {new_cnt}."
    except Exception as exc:
        return False, 0, f"Database error: {exc}"


def has_supported_complaint(complaint_id: int, citizen_id: int, db_path: str = DB_PATH) -> bool:
    """Checks whether the citizen has already supported this issue."""
    row = fetch_one(
        "SELECT id FROM ComplaintSupports WHERE complaint_id = ? AND citizen_id = ?;",
        (complaint_id, citizen_id),
        db_path=db_path
    )
    return row is not None


def reopen_complaint(
    complaint_id: int,
    citizen_id: int,
    reopen_reason: str,
    db_path: str = DB_PATH
) -> Tuple[bool, str]:
    """
    Requests reopening of a previously RESOLVED or CLOSED complaint.
    Preserves all historical records while advancing the lifecycle to 'REOPENED'.
    """
    reason = (reopen_reason or "").strip()
    if not reason or len(reason) < 10:
        return False, "Please provide a detailed explanation of why the issue needs to be reopened (min 10 characters)."

    comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
    if not comp:
        return False, "Complaint not found."

    if comp["citizen_id"] != citizen_id:
        return False, "You are not authorized to reopen a complaint submitted by another citizen."

    if comp["status"] not in ("RESOLVED", "CLOSED", "REJECTED"):
        return False, f"Only resolved, closed, or rejected complaints can be reopened. Current status: {comp['status']}."

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE Complaints 
                SET status = 'REOPENED', reopen_reason = ?, reopened_at = CURRENT_TIMESTAMP 
                WHERE id = ?;
                """,
                (reason, complaint_id)
            )

            # Record in status history
            cursor.execute(
                """
                INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                VALUES (?, ?, 'REOPENED', ?, ?);
                """,
                (complaint_id, comp["status"], citizen_id, f"Reopened by citizen: {reason}")
            )

            # Notify Citizen
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                VALUES (?, ?, 'Complaint Reopened', ?, 'STATUS_UPDATE');
                """,
                (citizen_id, complaint_id, f"Complaint {comp['complaint_id']} has been reopened for administrative review.")
            )

            # Alert Admins
            cursor.execute("SELECT id FROM Users WHERE role = 'ADMIN' AND is_active = 1;")
            admin_rows = cursor.fetchall()
            for a_row in admin_rows:
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Complaint Reopened by Citizen', ?, 'ADMIN_ALERT');
                    """,
                    (a_row[0], complaint_id, f"Citizen reopened {comp['complaint_id']}: {reason}")
                )

        return True, "Complaint has been successfully reopened for administrative review."
    except Exception as exc:
        return False, f"Database error reopening complaint: {exc}"


def submit_feedback(
    complaint_id: int,
    citizen_id: int,
    rating: int,
    comments: Optional[str] = None,
    suggestions: Optional[str] = None,
    db_path: str = DB_PATH
) -> Tuple[bool, str]:
    """
    Submits citizen rating (1-5 stars) and feedback for a resolved complaint.
    """
    if rating not in (1, 2, 3, 4, 5):
        return False, "Rating must be an integer between 1 and 5 stars."

    comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
    if not comp:
        return False, "Complaint not found."

    if comp["citizen_id"] != citizen_id:
        return False, "You can only rate complaints submitted under your account."

    if comp["status"] not in ("RESOLVED", "CLOSED"):
        return False, "Feedback can only be submitted after the complaint is resolved."

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Feedback (complaint_id, citizen_id, rating, comments, suggestions)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(complaint_id) DO UPDATE SET
                    rating = excluded.rating,
                    comments = excluded.comments,
                    suggestions = excluded.suggestions,
                    submitted_at = CURRENT_TIMESTAMP;
                """,
                (complaint_id, citizen_id, rating, (comments or "").strip(), (suggestions or "").strip())
            )

            # If resolved, automatically finalize to CLOSED
            if comp["status"] == "RESOLVED":
                cursor.execute(
                    "UPDATE Complaints SET status = 'CLOSED', closed_at = CURRENT_TIMESTAMP WHERE id = ?;",
                    (complaint_id,)
                )
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, 'RESOLVED', 'CLOSED', ?, ?);
                    """,
                    (complaint_id, citizen_id, f"Closed with citizen feedback ({rating}/5 stars).")
                )
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Complaint Finalized and Closed', ?, 'STATUS_UPDATE');
                    """,
                    (citizen_id, complaint_id, f"Complaint {comp['complaint_id']} has been officially closed. Thank you for your review!")
                )

        return True, "Thank you! Your feedback has been recorded and the complaint has been finalized."
    except Exception as exc:
        return False, f"Database error submitting feedback: {exc}"


def get_citizen_stats(citizen_id: int, db_path: str = DB_PATH) -> Dict[str, int]:
    """
    Computes summary KPI metrics for a citizen's dashboard.
    """
    all_rows = fetch_all("SELECT status FROM Complaints WHERE citizen_id = ?;", (citizen_id,), db_path=db_path)

    stats = {
        "total": len(all_rows),
        "pending": 0,
        "in_progress": 0,
        "resolved": 0,
        "reopened": 0
    }

    for r in all_rows:
        st = r["status"]
        if st in ("NEW", "UNDER_REVIEW", "VERIFIED"):
            stats["pending"] += 1
        elif st in ("ASSIGNED", "ACKNOWLEDGED", "IN_PROGRESS", "DELAYED", "COMPLETED_PENDING_VERIFICATION"):
            stats["in_progress"] += 1
        elif st in ("RESOLVED", "CLOSED"):
            stats["resolved"] += 1
        elif st == "REOPENED":
            stats["reopened"] += 1

    return stats


def get_browseable_complaints(
    citizen_id: int,
    locality: Optional[str] = None,
    category: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Returns public complaints in the neighborhood so citizens can support existing issues
    instead of filing duplicates.
    """
    sql = """
        SELECT c.id, c.complaint_id, c.title, c.description, c.category,
               c.location, c.locality, c.status, c.priority, c.support_count, c.submitted_at,
               (SELECT image_path FROM ComplaintImages WHERE complaint_id = c.id AND image_type = 'EVIDENCE' LIMIT 1) as evidence_image,
               (SELECT COUNT(*) FROM ComplaintSupports WHERE complaint_id = c.id AND citizen_id = ?) as user_has_supported
        FROM Complaints c
        WHERE c.status NOT IN ('CLOSED', 'REJECTED')
    """
    params: List[Any] = [citizen_id]

    if locality and locality != "All Localities":
        sql += " AND c.locality = ?"
        params.append(locality)

    if category and category != "All Categories":
        sql += " AND c.category = ?"
        params.append(category)

    if search_query:
        sq = f"%{search_query.strip()}%"
        sql += " AND (c.title LIKE ? OR c.description LIKE ? OR c.location LIKE ?)"
        params.extend([sq, sq, sq])

    sql += " ORDER BY c.support_count DESC, c.submitted_at DESC LIMIT 50;"
    return fetch_all(sql, tuple(params), db_path=db_path)
