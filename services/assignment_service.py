"""
CivicFix Worker Assignment & Field Dispatch Service Layer
Handles assigning verified complaints to departmental field workers,
workload tracking, deadline management, and assignment history.
"""

from typing import List, Dict, Any, Optional, Tuple
import datetime
from database.db_connection import get_db, DB_PATH
from database.database_operations import (
    fetch_one, fetch_all, execute_query, execute_update,
    record_status_change, record_admin_action, create_notification
)

DEPARTMENTS = [
    "Roads",
    "Sanitation",
    "Water Supply",
    "Drainage",
    "Electrical Maintenance",
    "Other",
]

CATEGORY_DEPARTMENT_MAP = {
    "Road damage / pothole": "Roads",
    "Broken streetlight": "Electrical Maintenance",
    "Garbage / waste issue": "Sanitation",
    "Drainage blockage": "Drainage",
    "Water leakage": "Water Supply",
    "Damaged public property": "Other",
    "Illegal dumping": "Sanitation",
    "Other civic issue": "Other",
}


def get_default_department_for_category(category: str) -> str:
    """Returns the recommended municipal department for an issue category."""
    return CATEGORY_DEPARTMENT_MAP.get(category, "Other")


def get_available_workers(department: Optional[str] = None, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns active, approved field workers with their current pending task workload.
    Can be filtered by department. Only APPROVED workers are returned.
    """
    sql = """
        SELECT u.id as user_id, u.username, u.email, u.is_active,
               wp.full_name, wp.phone, wp.department, wp.specialization, wp.is_available,
               wp.approval_status,
               (SELECT COUNT(*) FROM WorkerAssignments wa 
                JOIN Complaints c ON wa.complaint_id = c.id
                WHERE wa.worker_id = u.id AND wa.is_current = 1 AND c.status IN ('ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'DELAYED')) as active_tasks,
               (SELECT COUNT(*) FROM WorkerAssignments wa 
                JOIN Complaints c ON wa.complaint_id = c.id
                WHERE wa.worker_id = u.id AND c.status IN ('RESOLVED', 'CLOSED')) as completed_tasks
        FROM Users u
        JOIN WorkerProfiles wp ON u.id = wp.user_id
        WHERE u.role = 'WORKER' AND u.is_active = 1 AND (wp.approval_status = 'APPROVED' OR wp.approval_status IS NULL)
    """
    params = []
    if department and department != "All Departments":
        sql += " AND wp.department = ?"
        params.append(department)

    sql += " ORDER BY active_tasks ASC, wp.full_name ASC;"
    return fetch_all(sql, tuple(params), db_path=db_path)


def get_all_registered_workers(
    approval_status: Optional[str] = None,
    department: Optional[str] = None,
    search_query: Optional[str] = None,
    db_path: str = DB_PATH
) -> List[Dict[str, Any]]:
    """
    Returns all registered field workers with their approval status,
    contact info, department, and assigned workload metrics.
    Supports filtering by approval status, department, and keyword search.
    """
    sql = """
        SELECT u.id as user_id, u.username, u.email, u.is_active, u.created_at as account_created,
               wp.id as profile_id, wp.full_name, wp.phone, wp.department, wp.specialization,
               wp.is_available, COALESCE(wp.approval_status, 'APPROVED') as approval_status,
               wp.created_at as registered_at,
               (SELECT COUNT(*) FROM WorkerAssignments wa 
                JOIN Complaints c ON wa.complaint_id = c.id
                WHERE wa.worker_id = u.id AND wa.is_current = 1 AND c.status IN ('ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'DELAYED')) as active_tasks,
               (SELECT COUNT(*) FROM WorkerAssignments wa 
                JOIN Complaints c ON wa.complaint_id = c.id
                WHERE wa.worker_id = u.id AND c.status IN ('RESOLVED', 'CLOSED')) as completed_tasks
        FROM Users u
        JOIN WorkerProfiles wp ON u.id = wp.user_id
        WHERE u.role = 'WORKER'
    """
    params = []

    if approval_status and approval_status != "All Statuses":
        sql += " AND COALESCE(wp.approval_status, 'APPROVED') = ?"
        params.append(approval_status)

    if department and department != "All Departments":
        sql += " AND wp.department = ?"
        params.append(department)

    if search_query:
        sq = f"%{search_query.strip()}%"
        sql += " AND (wp.full_name LIKE ? OR u.username LIKE ? OR u.email LIKE ? OR wp.phone LIKE ? OR wp.specialization LIKE ?)"
        params.extend([sq, sq, sq, sq, sq])

    sql += " ORDER BY CASE WHEN wp.approval_status = 'PENDING' THEN 1 WHEN wp.approval_status = 'APPROVED' THEN 2 ELSE 3 END, wp.created_at DESC;"
    return fetch_all(sql, tuple(params), db_path=db_path)


def assign_complaint_to_worker(
    complaint_id: int,
    worker_id: int,
    admin_id: int,
    due_date: Optional[str] = None,
    admin_notes: Optional[str] = None,
    db_path: str = DB_PATH
) -> Tuple[bool, str]:
    """
    Assigns a verified complaint to a designated field worker.
    Updates complaint status to 'ASSIGNED', tracks workload,
    records administrative action audit, and dispatches in-app notifications.
    """
    comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
    if not comp:
        return False, "Complaint record not found."

    if comp["status"] not in ("VERIFIED", "REOPENED", "DELAYED", "ASSIGNED"):
        return False, f"Cannot assign worker: complaint must be VERIFIED or REOPENED. Current status: {comp['status']}."

    worker = fetch_one(
        "SELECT u.id, u.username, wp.full_name, wp.department FROM Users u JOIN WorkerProfiles wp ON u.id = wp.user_id WHERE u.id = ? AND u.role = 'WORKER';",
        (worker_id,),
        db_path=db_path
    )
    if not worker:
        return False, "Target field worker does not exist or is inactive."

    # Default deadline: 3 days from now if not specified
    if not due_date:
        due_date = (datetime.datetime.now() + datetime.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            # 1. Archive any previous active assignments for this complaint
            cursor.execute(
                "UPDATE WorkerAssignments SET is_current = 0 WHERE complaint_id = ?;",
                (complaint_id,)
            )

            # 2. Insert New Worker Assignment
            cursor.execute(
                """
                INSERT INTO WorkerAssignments (
                    complaint_id, worker_id, assigned_by, assigned_at, due_date, is_current
                ) VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, 1);
                """,
                (complaint_id, worker_id, admin_id, due_date)
            )

            # 3. Update Complaint Status & Department
            cursor.execute(
                """
                UPDATE Complaints 
                SET status = 'ASSIGNED', department = ?, due_date = ?, assigned_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (worker["department"], due_date, complaint_id)
            )

            # 4. Status History Log
            cursor.execute(
                """
                INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                VALUES (?, ?, 'ASSIGNED', ?, ?);
                """,
                (
                    complaint_id, comp["status"], admin_id,
                    f"Assigned to {worker['full_name']} ({worker['department']}). Due: {due_date}. Notes: {admin_notes or 'None'}"
                )
            )

            # 5. Admin Action Audit Trail
            cursor.execute(
                """
                INSERT INTO AdminActionHistory (admin_id, complaint_id, action_type, details)
                VALUES (?, ?, 'ASSIGN_WORKER', ?);
                """,
                (
                    admin_id, complaint_id,
                    f"Dispatched {comp['complaint_id']} to field worker '{worker['username']}' with deadline {due_date}."
                )
            )

            # 6. Notify Field Worker
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                VALUES (?, ?, 'New Task Assigned', ?, 'ASSIGNMENT');
                """,
                (
                    worker_id, complaint_id,
                    f"New assignment for {comp['complaint_id']}: '{comp['title']}' at {comp['location']}. Due: {due_date}."
                )
            )

            # 7. Notify Citizen
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                VALUES (?, ?, 'Field Worker Assigned', ?, 'STATUS_UPDATE');
                """,
                (
                    comp["citizen_id"], complaint_id,
                    f"Your complaint {comp['complaint_id']} has been assigned to field worker {worker['full_name']} ({worker['department']})."
                )
            )

        return True, f"Successfully assigned {comp['complaint_id']} to {worker['full_name']}."
    except Exception as exc:
        return False, f"Database error during worker assignment: {exc}"
