"""
CivicFix Administrator Module Business Controller
Orchestrates administrative operations: verification, rejection, priority adjustment,
worker dispatch, duplicate merges, worker account administration, and audits.
"""

from typing import List, Dict, Any, Optional, Tuple
from database.db_connection import get_db, DB_PATH
from database.database_operations import (
    fetch_one, fetch_all, execute_query, execute_update,
    record_status_change, record_admin_action, create_notification
)
from services.assignment_service import (
    assign_complaint_to_worker,
    get_available_workers,
    get_all_registered_workers,
    get_default_department_for_category,
    DEPARTMENTS
)
from services.priority_service import calculate_suggested_priority
from services.report_service import (
    get_admin_kpis,
    get_overdue_complaints,
    detect_potential_duplicates,
    export_complaints_to_csv,
    get_worker_performance_stats
)
from authentication.auth import create_worker_account
from utils.validators import validate_phone, validate_email
from services.state_machine import (
    transition_status,
    STATUS_VERIFIED,
    STATUS_REJECTED,
    STATUS_RESOLVED,
    STATUS_IN_PROGRESS,
    ROLE_ADMIN
)


class AdministratorController:
    """Controller exposing administrative actions and governance capabilities."""

    def __init__(self, admin_id: int, db_path: str = DB_PATH):
        self.admin_id = admin_id
        self.db_path = db_path

    def get_dashboard_kpis(self) -> Dict[str, int]:
        """Calculates live statistical KPI counts from database."""
        return get_admin_kpis()

    def fetch_all_complaints(
        self,
        search_query: Optional[str] = None,
        status_filter: Optional[str] = None,
        category_filter: Optional[str] = None,
        department_filter: Optional[str] = None,
        priority_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves system-wide complaints matching specified search criteria."""
        sql = """
            SELECT c.*, 
                   COALESCE(cp.full_name, u.username) as citizen_name,
                   cp.phone as citizen_phone,
                   COALESCE(wp.full_name, 'Unassigned') as assigned_worker_name,
                   wp.department as worker_department
            FROM Complaints c
            JOIN Users u ON c.citizen_id = u.id
            LEFT JOIN CitizenProfiles cp ON u.id = cp.user_id
            LEFT JOIN WorkerAssignments wa ON c.id = wa.complaint_id AND wa.is_current = 1
            LEFT JOIN WorkerProfiles wp ON wa.worker_id = wp.user_id
            WHERE 1=1
        """
        params = []

        if search_query:
            sq = f"%{search_query.strip()}%"
            sql += " AND (c.complaint_id LIKE ? OR c.title LIKE ? OR c.location LIKE ? OR c.locality LIKE ? OR citizen_name LIKE ?)"
            params.extend([sq, sq, sq, sq, sq])

        if status_filter and status_filter != "All Statuses":
            sql += " AND c.status = ?"
            params.append(status_filter)

        if category_filter and category_filter != "All Categories":
            sql += " AND c.category = ?"
            params.append(category_filter)

        if department_filter and department_filter != "All Departments":
            sql += " AND c.department = ?"
            params.append(department_filter)

        if priority_filter and priority_filter != "All Priorities":
            sql += " AND c.priority = ?"
            params.append(priority_filter)

        sql += " ORDER BY CASE WHEN c.priority = 'EMERGENCY' THEN 1 WHEN c.priority = 'HIGH' THEN 2 ELSE 3 END, c.submitted_at DESC;"
        return fetch_all(sql, tuple(params), db_path=self.db_path)

    def fetch_new_complaints_queue(self) -> List[Dict[str, Any]]:
        """Retrieves complaints requiring initial inspection and verification."""
        return self.fetch_all_complaints(status_filter="NEW")

    def verify_complaint(
        self,
        complaint_id: int,
        remarks: str,
        priority: str,
        department: str,
        due_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Verifies a reported complaint, approves priority, and assigns municipal department.
        """
        return transition_status(
            complaint_id=complaint_id,
            target_status=STATUS_VERIFIED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks=remarks,
            metadata={
                "priority": priority,
                "department": department,
                "due_date": due_date
            },
            db_path=self.db_path
        )

    def reject_complaint(self, complaint_id: int, rejection_reason: str) -> Tuple[bool, str]:
        """
        Rejects an invalid, duplicate, or out-of-scope civic complaint.
        """
        reason = (rejection_reason or "").strip()
        if not reason or len(reason) < 10:
            return False, "Rejection requires an explicit reason (minimum 10 characters)."

        return transition_status(
            complaint_id=complaint_id,
            target_status=STATUS_REJECTED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks=reason,
            db_path=self.db_path
        )

    def close_and_resolve_complaint(self, complaint_id: int, remarks: Optional[str] = None) -> Tuple[bool, str]:
        """
        Audits worker completion proof, verifies task resolution, and closes the complaint.
        """
        return transition_status(
            complaint_id=complaint_id,
            target_status=STATUS_RESOLVED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks=remarks or "Resolution approved and verified by administrator.",
            db_path=self.db_path
        )

    def request_rework(self, complaint_id: int, rework_instructions: str) -> Tuple[bool, str]:
        """
        Rejects worker completion proof and sends task back to IN_PROGRESS with corrective instructions.
        """
        reason = (rework_instructions or "").strip()
        if not reason or len(reason) < 10:
            return False, "Rework instructions require at least 10 characters."

        return transition_status(
            complaint_id=complaint_id,
            target_status=STATUS_IN_PROGRESS,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks=reason,
            db_path=self.db_path
        )

    def assign_worker(
        self,
        complaint_id: int,
        worker_id: int,
        due_date: Optional[str] = None,
        notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Dispatches verified issue to a field worker."""
        return assign_complaint_to_worker(
            complaint_id=complaint_id,
            worker_id=worker_id,
            admin_id=self.admin_id,
            due_date=due_date,
            admin_notes=notes
        )

    def fetch_all_workers(
        self,
        approval_status: Optional[str] = None,
        department: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Retrieves registered field workers with approval status and workload."""
        return get_all_registered_workers(
            approval_status=approval_status,
            department=department,
            search_query=search_query,
            db_path=self.db_path
        )

    def get_worker_approval_counts(self) -> Dict[str, int]:
        """Calculates worker registration counts by approval status."""
        workers = get_all_registered_workers(db_path=self.db_path)
        total = len(workers)
        pending = sum(1 for w in workers if w.get("approval_status") == "PENDING")
        approved = sum(1 for w in workers if w.get("approval_status") == "APPROVED")
        rejected = sum(1 for w in workers if w.get("approval_status") == "REJECTED")
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected
        }

    def approve_worker(self, worker_user_id: int) -> Tuple[bool, str]:
        """
        Approves a registered field worker's application.
        Sets approval_status to 'APPROVED' and activates account.
        """
        w = fetch_one(
            "SELECT u.username, wp.full_name, wp.department FROM Users u JOIN WorkerProfiles wp ON u.id = wp.user_id WHERE u.id = ?;",
            (worker_user_id,),
            db_path=self.db_path
        )
        if not w:
            return False, "Target field worker record not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE WorkerProfiles SET approval_status = 'APPROVED' WHERE user_id = ?;",
                    (worker_user_id,)
                )
                cursor.execute(
                    "UPDATE Users SET is_active = 1 WHERE id = ?;",
                    (worker_user_id,)
                )
                cursor.execute(
                    """
                    INSERT INTO AdminActionHistory (admin_id, action_type, details)
                    VALUES (?, 'APPROVE_WORKER', ?);
                    """,
                    (self.admin_id, f"Approved field worker application for '{w['full_name']}' ({w['username']}) - Department: {w['department']}.")
                )
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Account Approved!', 'Your field worker account application has been reviewed and approved by the administrator. You may now log in to the Field Worker Portal.', 'REGISTRATION_APPROVED');
                    """,
                    (worker_user_id,)
                )
            return True, f"Worker '{w['full_name']}' has been approved successfully."
        except Exception as exc:
            return False, f"Database error approving worker: {exc}"

    def reject_worker(self, worker_user_id: int, reason: Optional[str] = None) -> Tuple[bool, str]:
        """
        Rejects a registered field worker's application.
        Sets approval_status to 'REJECTED' and blocks portal access.
        """
        w = fetch_one(
            "SELECT u.username, wp.full_name, wp.department FROM Users u JOIN WorkerProfiles wp ON u.id = wp.user_id WHERE u.id = ?;",
            (worker_user_id,),
            db_path=self.db_path
        )
        if not w:
            return False, "Target field worker record not found."

        r_text = reason.strip() if reason else "Application criteria did not match municipal dispatch requirements."
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE WorkerProfiles SET approval_status = 'REJECTED' WHERE user_id = ?;",
                    (worker_user_id,)
                )
                cursor.execute(
                    """
                    INSERT INTO AdminActionHistory (admin_id, action_type, details)
                    VALUES (?, 'REJECT_WORKER', ?);
                    """,
                    (self.admin_id, f"Rejected field worker application for '{w['full_name']}' ({w['username']}). Reason: {r_text}")
                )
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, title, message, notification_type)
                    VALUES (?, 'Application Status', ?, 'REGISTRATION_REJECTED');
                    """,
                    (worker_user_id, f"Your field worker registration application was reviewed and rejected. Note: {r_text}")
                )
            return True, f"Worker application for '{w['full_name']}' has been rejected."
        except Exception as exc:
            return False, f"Database error rejecting worker: {exc}"

    def toggle_worker_status(self, worker_user_id: int, is_active: bool) -> Tuple[bool, str]:
        """Activates or deactivates a field worker account."""
        val = 1 if is_active else 0
        execute_update("UPDATE Users SET is_active = ? WHERE id = ? AND role = 'WORKER';", (val, worker_user_id))
        record_admin_action(
            admin_id=self.admin_id,
            complaint_id=None,
            action_type="WORKER_STATUS_CHANGE",
            details=f"Worker User ID {worker_user_id} active state set to {val}."
        )
        return True, "Worker account status updated."

    def merge_duplicates(self, primary_id: int, duplicate_id: int) -> Tuple[bool, str]:
        """
        Merges a duplicate complaint into a primary complaint:
        - Transfers duplicate's support count (+1) to primary
        - Sets duplicate status to CLOSED with merged remarks
        - Preserves original records in database
        """
        prim = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (primary_id,), db_path=self.db_path)
        dupe = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (duplicate_id,), db_path=self.db_path)

        if not prim or not dupe:
            return False, "Complaint record not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # Boost primary support count
                cursor.execute(
                    "UPDATE Complaints SET support_count = support_count + 1 WHERE id = ?;",
                    (primary_id,)
                )

                # Mark duplicate as CLOSED with reference
                cursor.execute(
                    """
                    UPDATE Complaints 
                    SET status = 'CLOSED', 
                        admin_remarks = ?
                    WHERE id = ?;
                    """,
                    (f"Merged duplicate: closed as duplicate of {prim['complaint_id']}.", duplicate_id)
                )

                # Status history log
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, ?, 'CLOSED', ?, ?);
                    """,
                    (duplicate_id, dupe["status"], self.admin_id, f"Merged as duplicate into {prim['complaint_id']}")
                )

                # Audit Log
                cursor.execute(
                    """
                    INSERT INTO AdminActionHistory (admin_id, complaint_id, action_type, details)
                    VALUES (?, ?, 'MERGE_DUPLICATE', ?);
                    """,
                    (self.admin_id, duplicate_id, f"Merged duplicate complaint {dupe['complaint_id']} into primary issue {prim['complaint_id']}.")
                )

                # Notify Citizen of Duplicate
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Complaint Merged', ?, 'STATUS_UPDATE');
                    """,
                    (
                        dupe["citizen_id"], duplicate_id,
                        f"Your issue {dupe['complaint_id']} was identified as duplicate of {prim['complaint_id']}. Your report has been merged to boost its priority."
                    )
                )

            return True, f"Successfully merged {dupe['complaint_id']} into {prim['complaint_id']}."
        except Exception as exc:
            return False, f"Database error merging complaints: {exc}"

    def merge_duplicate_complaint(self, primary_complaint_id: int, duplicate_complaint_id: int) -> Tuple[bool, str]:
        """Alias for merge_duplicates."""
        return self.merge_duplicates(primary_complaint_id, duplicate_complaint_id)

    def fetch_audit_history(self) -> List[Dict[str, Any]]:
        """Retrieves the administrative decision audit log."""
        sql = """
            SELECT ah.*, u.username as admin_username, c.complaint_id as complaint_code
            FROM AdminActionHistory ah
            JOIN Users u ON ah.admin_id = u.id
            LEFT JOIN Complaints c ON ah.complaint_id = c.id
            ORDER BY ah.performed_at DESC LIMIT 100;
        """
        return fetch_all(sql, db_path=self.db_path)

    def fetch_citizen_feedbacks(self) -> List[Dict[str, Any]]:
        """Retrieves citizen star ratings and reviews."""
        sql = """
            SELECT fb.*, c.complaint_id as complaint_code, c.title as complaint_title,
                   cp.full_name as citizen_name
            FROM Feedback fb
            JOIN Complaints c ON fb.complaint_id = c.id
            JOIN Users u ON fb.citizen_id = u.id
            JOIN CitizenProfiles cp ON u.id = cp.user_id
            ORDER BY fb.submitted_at DESC;
        """
        return fetch_all(sql, db_path=self.db_path)
