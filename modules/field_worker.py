"""
CivicFix Field Worker Module Business Controller
Orchestrates worker operations: task acknowledgment, category-specific checklists,
progress updates, material requisitions, delay justifications, and completion proof uploads.
"""

from typing import List, Dict, Any, Optional, Tuple
import datetime
from database.db_connection import get_db, DB_PATH
from database.database_operations import (
    fetch_one, fetch_all, execute_query, execute_update,
    record_status_change, create_notification
)
from utils.image_handler import save_image_to_uploads

# Standard category-specific operational checklists
DEFAULT_CHECKLISTS = {
    "Road damage / pothole": [
        "Inspect road surface and measure pothole dimensions",
        "Erect safety barricades and warning cones",
        "Arrange asphalt mix, bitumen, and compaction equipment",
        "Perform asphalt laying and roller compaction repair",
        "Clean surrounding debris and clear traffic pathway",
        "Capture resolution proof photo"
    ],
    "Broken streetlight": [
        "Inspect streetlight pole, bulb, and wiring junction",
        "Diagnose electrical issue (fuse, bulb, or cable break)",
        "Repair or replace damaged LED/fixture component",
        "Conduct live illumination testing at night",
        "Capture resolution proof photo"
    ],
    "Garbage / waste issue": [
        "Inspect site and assess waste volume",
        "Deploy collection truck and sanitation crew",
        "Clear accumulated garbage and sweep vicinity",
        "Disinfect and sanitize waste disposal point",
        "Capture resolution proof photo"
    ],
    "Illegal dumping": [
        "Inspect dumped materials and document violations",
        "Deploy heavy loader vehicle for debris removal",
        "Clear illegal waste from public footpath/road",
        "Install warning signboard against illegal dumping",
        "Capture resolution proof photo"
    ],
    "Water leakage": [
        "Locate underground or surface pipe burst point",
        "Shut off local valve to halt potable water loss",
        "Excavate and replace burst pipe section",
        "Pressure test water flow and backfill pavement",
        "Capture resolution proof photo"
    ],
    "Drainage blockage": [
        "Inspect clogged storm drain or manhole",
        "Deploy vacuum de-silting suction machine",
        "Clear silt, solid waste, and restore gravity flow",
        "Fasten secure drain grating cover",
        "Capture resolution proof photo"
    ],
    "Other": [
        "Inspect site and evaluate reported civic issue",
        "Arrange required municipal tools and materials",
        "Execute civic repair or remedial action",
        "Inspect work quality and clean area",
        "Capture resolution proof photo"
    ]
}


class WorkerController:
    """Business controller for the Field Worker portal."""

    def __init__(self, worker_user_id: int, db_path: str = DB_PATH):
        self.worker_id = worker_user_id
        self.db_path = db_path

    def get_worker_kpi_summary(self) -> Dict[str, int]:
        """Calculates workload metrics for this specific field worker."""
        sql = """
            SELECT c.status, wa.due_date
            FROM WorkerAssignments wa
            JOIN Complaints c ON wa.complaint_id = c.id
            WHERE wa.worker_id = ? AND wa.is_current = 1;
        """
        rows = fetch_all(sql, (self.worker_id,), db_path=self.db_path)

        kpis = {
            "total_assigned": len(rows),
            "new_assigned": 0,
            "acknowledged": 0,
            "in_progress": 0,
            "delayed": 0,
            "completed": 0,
            "overdue": 0
        }

        now = datetime.datetime.now()

        for r in rows:
            st = r["status"]
            if st == "ASSIGNED":
                kpis["new_assigned"] += 1
            elif st == "ACKNOWLEDGED":
                kpis["acknowledged"] += 1
            elif st == "IN_PROGRESS":
                kpis["in_progress"] += 1
            elif st == "DELAYED":
                kpis["delayed"] += 1
            elif st in ("COMPLETED_PENDING_VERIFICATION", "RESOLVED", "CLOSED"):
                kpis["completed"] += 1

            # Check if overdue
            if r["due_date"] and st not in ("RESOLVED", "CLOSED", "REJECTED"):
                try:
                    due_dt = datetime.datetime.fromisoformat(r["due_date"].replace(" ", "T"))
                    if due_dt < now:
                        kpis["overdue"] += 1
                except Exception:
                    pass

        return kpis

    def get_assigned_tasks(
        self,
        status_filter: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieves all tasks assigned to the logged-in field worker.
        Enforces strict worker scoping.
        """
        sql = """
            SELECT c.*, 
                   wa.id as assignment_id, wa.assigned_at, wa.due_date,
                   wa.acknowledged_at, wa.delay_reason, wa.estimated_completion_date,
                   (SELECT image_path FROM ComplaintImages WHERE complaint_id = c.id AND image_type = 'EVIDENCE' LIMIT 1) as evidence_image,
                   (SELECT image_path FROM ComplaintImages WHERE complaint_id = c.id AND image_type = 'COMPLETION' LIMIT 1) as completion_image,
                   COALESCE(cp.full_name, u.username) as citizen_name,
                   cp.phone as citizen_phone
            FROM WorkerAssignments wa
            JOIN Complaints c ON wa.complaint_id = c.id
            JOIN Users u ON c.citizen_id = u.id
            LEFT JOIN CitizenProfiles cp ON u.id = cp.user_id
            WHERE wa.worker_id = ? AND wa.is_current = 1
        """
        params: List[Any] = [self.worker_id]

        if status_filter:
            if status_filter == "PENDING":
                sql += " AND c.status IN ('ASSIGNED', 'ACKNOWLEDGED')"
            elif status_filter == "IN_PROGRESS":
                sql += " AND c.status = 'IN_PROGRESS'"
            elif status_filter == "DELAYED":
                sql += " AND c.status = 'DELAYED'"
            elif status_filter == "COMPLETED":
                sql += " AND c.status IN ('COMPLETED_PENDING_VERIFICATION', 'RESOLVED', 'CLOSED')"
            elif status_filter != "ALL":
                sql += " AND c.status = ?"
                params.append(status_filter)

        if search_query:
            sq = f"%{search_query.strip()}%"
            sql += " AND (c.complaint_id LIKE ? OR c.title LIKE ? OR c.location LIKE ? OR c.locality LIKE ?)"
            params.extend([sq, sq, sq, sq])

        sql += " ORDER BY CASE WHEN c.priority = 'EMERGENCY' THEN 1 WHEN c.priority = 'HIGH' THEN 2 ELSE 3 END, wa.assigned_at DESC;"
        return fetch_all(sql, tuple(params), db_path=self.db_path)

    def get_task_details(self, complaint_id_or_code: Any) -> Optional[Dict[str, Any]]:
        """Retrieves complete task metadata, checklists, materials, and progress notes."""
        if isinstance(complaint_id_or_code, int) or str(complaint_id_or_code).isdigit():
            sql = "SELECT c.*, wa.id as assignment_id, wa.due_date, wa.acknowledged_at, wa.delay_reason, wa.estimated_completion_date FROM Complaints c JOIN WorkerAssignments wa ON c.id = wa.complaint_id AND wa.is_current = 1 WHERE c.id = ? AND wa.worker_id = ?;"
            param = int(complaint_id_or_code)
        else:
            sql = "SELECT c.*, wa.id as assignment_id, wa.due_date, wa.acknowledged_at, wa.delay_reason, wa.estimated_completion_date FROM Complaints c JOIN WorkerAssignments wa ON c.id = wa.complaint_id AND wa.is_current = 1 WHERE c.complaint_id = ? AND wa.worker_id = ?;"
            param = str(complaint_id_or_code)

        task = fetch_one(sql, (param, self.worker_id), db_path=self.db_path)
        if not task:
            return None

        cid = task["id"]
        asgn_id = task["assignment_id"]

        # Images
        task["images"] = fetch_all("SELECT * FROM ComplaintImages WHERE complaint_id = ? ORDER BY uploaded_at ASC;", (cid,), db_path=self.db_path)

        # Progress updates
        task["progress_notes"] = fetch_all("SELECT * FROM WorkerProgressUpdates WHERE assignment_id = ? ORDER BY created_at DESC;", (asgn_id,), db_path=self.db_path)

        # Checklist Items
        task["checklist"] = self.get_or_create_checklist(asgn_id, cid, task["category"])

        # Material Requisitions
        task["materials"] = fetch_all("SELECT * FROM MaterialRequirements WHERE assignment_id = ? ORDER BY created_at ASC;", (asgn_id,), db_path=self.db_path)

        # Citizen Contact
        task["citizen"] = fetch_one("SELECT cp.full_name, cp.phone, cp.locality FROM Users u JOIN CitizenProfiles cp ON u.id = cp.user_id WHERE u.id = ?;", (task["citizen_id"],), db_path=self.db_path)

        return task

    def acknowledge_task(self, assignment_id: int, complaint_id: int) -> Tuple[bool, str]:
        """
        Acknowledges receipt of task assignment.
        Records timestamp and advances status to 'ACKNOWLEDGED'.
        """
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=self.db_path)
        if not comp:
            return False, "Complaint record not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Update WorkerAssignments timestamp
                cursor.execute(
                    "UPDATE WorkerAssignments SET acknowledged_at = CURRENT_TIMESTAMP WHERE id = ? AND worker_id = ?;",
                    (assignment_id, self.worker_id)
                )

                # 2. Update Complaint Status
                cursor.execute(
                    "UPDATE Complaints SET status = 'ACKNOWLEDGED' WHERE id = ?;",
                    (complaint_id,)
                )

                # 3. Status History
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, ?, 'ACKNOWLEDGED', ?, 'Task acknowledged by assigned field worker.');
                    """,
                    (complaint_id, comp["status"], self.worker_id)
                )

                # 4. Notify Citizen
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Worker Acknowledged Task', ?, 'STATUS_UPDATE');
                    """,
                    (comp["citizen_id"], complaint_id, f"Field worker has acknowledged your complaint {comp['complaint_id']} and scheduled site inspection.")
                )

            return True, f"Task {comp['complaint_id']} successfully acknowledged."
        except Exception as exc:
            return False, f"Database error: {exc}"

    def update_task_progress(
        self,
        assignment_id: int,
        complaint_id: int,
        progress_notes: str,
        estimated_completion_date: Optional[str] = None,
        progress_image_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Advances task status to 'IN_PROGRESS' and logs detailed operational progress notes.
        """
        notes = (progress_notes or "").strip()
        if not notes or len(notes) < 5:
            return False, "Progress notes must be at least 5 characters."

        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=self.db_path)
        if not comp:
            return False, "Complaint not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Update Complaint Status to IN_PROGRESS
                cursor.execute(
                    "UPDATE Complaints SET status = 'IN_PROGRESS' WHERE id = ?;",
                    (complaint_id,)
                )

                # 2. Update Assignment estimated completion if given
                if estimated_completion_date:
                    cursor.execute(
                        "UPDATE WorkerAssignments SET estimated_completion_date = ? WHERE id = ?;",
                        (estimated_completion_date, assignment_id)
                    )

                # 3. Insert WorkerProgressUpdates log
                cursor.execute(
                    """
                    INSERT INTO WorkerProgressUpdates (
                        assignment_id, complaint_id, worker_id, progress_notes, status_snapshot, progress_image_path
                    ) VALUES (?, ?, ?, ?, 'IN_PROGRESS', ?);
                    """,
                    (assignment_id, complaint_id, self.worker_id, notes, progress_image_path)
                )

                # 4. Status History
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, ?, 'IN_PROGRESS', ?, ?);
                    """,
                    (complaint_id, comp["status"], self.worker_id, f"Progress update: {notes}")
                )

                # 5. Notify Citizen
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Work In Progress', ?, 'STATUS_UPDATE');
                    """,
                    (comp["citizen_id"], complaint_id, f"Work has started on {comp['complaint_id']}: {notes}")
                )

            return True, "Progress updated successfully! Status set to IN_PROGRESS."
        except Exception as exc:
            return False, f"Database error: {exc}"

    def report_delay_reason(
        self,
        assignment_id: int,
        complaint_id: int,
        delay_reason: str
    ) -> Tuple[bool, str]:
        """
        Flags task as 'DELAYED' and records mandatory operational explanation.
        """
        reason = (delay_reason or "").strip()
        if not reason or len(reason) < 10:
            return False, "Delay explanation requires at least 10 characters (e.g. material unavailable, weather conditions)."

        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=self.db_path)
        if not comp:
            return False, "Complaint not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Update WorkerAssignments delay reason
                cursor.execute(
                    "UPDATE WorkerAssignments SET delay_reason = ? WHERE id = ?;",
                    (reason, assignment_id)
                )

                # 2. Update Complaint Status to DELAYED
                cursor.execute(
                    "UPDATE Complaints SET status = 'DELAYED' WHERE id = ?;",
                    (complaint_id,)
                )

                # 3. Status History
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, ?, 'DELAYED', ?, ?);
                    """,
                    (complaint_id, comp["status"], self.worker_id, f"Delay reported: {reason}")
                )

                # 4. Notify Citizen
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Resolution Delayed', ?, 'STATUS_UPDATE');
                    """,
                    (comp["citizen_id"], complaint_id, f"Notice: Work on {comp['complaint_id']} has been delayed: {reason}")
                )

                # 5. Alert Admins
                cursor.execute("SELECT id FROM Users WHERE role = 'ADMIN' AND is_active = 1;")
                admin_rows = cursor.fetchall()
                for a_row in admin_rows:
                    cursor.execute(
                        """
                        INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                        VALUES (?, ?, 'Task Delayed Notice', ?, 'ADMIN_ALERT');
                        """,
                        (a_row[0], complaint_id, f"Worker reported delay on {comp['complaint_id']}: {reason}")
                    )

            return True, f"Delay explanation recorded for {comp['complaint_id']}."
        except Exception as exc:
            return False, f"Database error: {exc}"

    def get_or_create_checklist(
        self,
        assignment_id: int,
        complaint_id: int,
        category: str
    ) -> List[Dict[str, Any]]:
        """
        Retrieves checklist items for this assignment, initializing the default
        category-specific template if not yet created.
        """
        existing = fetch_all(
            "SELECT * FROM WorkChecklistItems WHERE assignment_id = ? ORDER BY id ASC;",
            (assignment_id,),
            db_path=self.db_path
        )
        if existing:
            return existing

        # Initialize defaults
        template = DEFAULT_CHECKLISTS.get(category, DEFAULT_CHECKLISTS["Other"])
        with get_db(self.db_path) as conn:
            cur = conn.cursor()
            for item in template:
                cur.execute(
                    """
                    INSERT INTO WorkChecklistItems (assignment_id, complaint_id, item_text, is_completed)
                    VALUES (?, ?, ?, 0);
                    """,
                    (assignment_id, complaint_id, item)
                )

        return fetch_all(
            "SELECT * FROM WorkChecklistItems WHERE assignment_id = ? ORDER BY id ASC;",
            (assignment_id,),
            db_path=self.db_path
        )

    def toggle_checklist_item(self, item_id: int, is_completed: bool) -> bool:
        """Updates checklist item completion state."""
        val = 1 if is_completed else 0
        comp_time = "CURRENT_TIMESTAMP" if is_completed else "NULL"
        execute_update(
            f"UPDATE WorkChecklistItems SET is_completed = ?, completed_at = {comp_time} WHERE id = ?;",
            (val, item_id),
            db_path=self.db_path
        )
        return True

    def add_material_requirement(
        self,
        assignment_id: int,
        complaint_id: int,
        item_name: str,
        quantity: str,
        notes: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Records required materials or equipment requisition."""
        item = (item_name or "").strip()
        qty = (quantity or "").strip()
        if not item or not qty:
            return False, "Item name and quantity are required."

        try:
            execute_query(
                """
                INSERT INTO MaterialRequirements (assignment_id, complaint_id, item_name, quantity, notes)
                VALUES (?, ?, ?, ?, ?);
                """,
                (assignment_id, complaint_id, item, qty, (notes or "").strip()),
                db_path=self.db_path
            )
            return True, f"Material requirement '{item}' added."
        except Exception as exc:
            return False, f"Database error: {exc}"

    def submit_task_completion(
        self,
        assignment_id: int,
        complaint_id: int,
        completion_image_rel_path: str,
        final_remarks: str
    ) -> Tuple[bool, str]:
        """
        Submits resolution proof photo and final remarks.
        Sets status to 'COMPLETED_PENDING_VERIFICATION'.
        Workers do NOT close complaints directly; administrator audits and closes.
        """
        remarks = (final_remarks or "").strip()
        if not completion_image_rel_path:
            return False, "Completion proof photo is mandatory before submitting task resolution."
        if not remarks or len(remarks) < 5:
            return False, "Final completion remarks are required (min 5 characters)."

        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=self.db_path)
        if not comp:
            return False, "Complaint not found."

        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # 1. Save Completion Photo to ComplaintImages
                cursor.execute(
                    """
                    INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption)
                    VALUES (?, ?, 'COMPLETION', ?, 'Field worker resolution proof photo.');
                    """,
                    (complaint_id, completion_image_rel_path, self.worker_id)
                )

                # 2. Update WorkerAssignments completion record
                cursor.execute(
                    """
                    UPDATE WorkerAssignments 
                    SET completed_at = CURRENT_TIMESTAMP, completion_remarks = ?
                    WHERE id = ? AND worker_id = ?;
                    """,
                    (remarks, assignment_id, self.worker_id)
                )

                # 3. Update Complaint Status to COMPLETED_PENDING_VERIFICATION
                cursor.execute(
                    """
                    UPDATE Complaints 
                    SET status = 'COMPLETED_PENDING_VERIFICATION', completed_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (complaint_id,)
                )

                # 4. Status History
                cursor.execute(
                    """
                    INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                    VALUES (?, ?, 'COMPLETED_PENDING_VERIFICATION', ?, ?);
                    """,
                    (complaint_id, comp["status"], self.worker_id, f"Work completed by field worker: {remarks}")
                )

                # 5. Notify Citizen
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, 'Resolution Proof Uploaded', ?, 'STATUS_UPDATE');
                    """,
                    (
                        comp["citizen_id"], complaint_id,
                        f"Field worker has completed physical repair for {comp['complaint_id']} with proof photo. Awaiting municipal admin sign-off."
                    )
                )

                # 6. Alert Admins for Audit Sign-off
                cursor.execute("SELECT id FROM Users WHERE role = 'ADMIN' AND is_active = 1;")
                admin_rows = cursor.fetchall()
                for a_row in admin_rows:
                    cursor.execute(
                        """
                        INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                        VALUES (?, ?, 'Audit Required: Work Completed', ?, 'ADMIN_ALERT');
                        """,
                        (a_row[0], complaint_id, f"Field worker submitted completion proof for {comp['complaint_id']}. Verification audit required.")
                    )

            return True, f"Task {comp['complaint_id']} marked as COMPLETED_PENDING_VERIFICATION! Admin has been notified for final audit."
        except Exception as exc:
            return False, f"Database error submitting completion: {exc}"

    def get_notifications(self) -> List[Dict[str, Any]]:
        """Retrieves in-app alerts and assignment notices for the worker."""
        return fetch_all(
            "SELECT * FROM Notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 25;",
            (self.worker_id,),
            db_path=self.db_path
        )

    def get_profile(self) -> Optional[Dict[str, Any]]:
        """Retrieves field worker profile details and specialization."""
        return fetch_one(
            "SELECT u.username, u.email, wp.* FROM Users u JOIN WorkerProfiles wp ON u.id = wp.user_id WHERE u.id = ?;",
            (self.worker_id,),
            db_path=self.db_path
        )
