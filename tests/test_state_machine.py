"""
CivicFix State Machine & Lifecycle Transition Test Suite
Validates the complete 12-state transition matrix, role permissions,
automated multi-party notifications, and audit logging.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, fetch_all
from services.state_machine import (
    STATUS_NEW,
    STATUS_UNDER_REVIEW,
    STATUS_VERIFIED,
    STATUS_REJECTED,
    STATUS_ASSIGNED,
    STATUS_ACKNOWLEDGED,
    STATUS_IN_PROGRESS,
    STATUS_DELAYED,
    STATUS_COMPLETED_PENDING_VERIFICATION,
    STATUS_RESOLVED,
    STATUS_CLOSED,
    STATUS_REOPENED,
    ALL_STATUSES,
    ROLE_CITIZEN,
    ROLE_WORKER,
    ROLE_ADMIN,
    can_transition,
    get_allowed_transitions,
    transition_status,
    get_status_metadata,
)


class TestStateMachine(unittest.TestCase):
    def setUp(self):
        """Create an isolated test database with Admin, Worker, and 2 Citizens."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # 1. Admin User
        self.admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'ADMIN');",
            ("admin_test", "admin@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )

        # 2. Field Worker 1
        self.worker1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_vikram", "vikram@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker1_id, "Vikram Patil", "9876543210", "Roads", "Pothole Patching"),
            db_path=self.temp_db_path
        )

        # 3. Field Worker 2 (Unassigned)
        self.worker2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_meena", "meena@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker2_id, "Meena Rao", "9876543220", "Sanitation", "Waste Clearance"),
            db_path=self.temp_db_path
        )

        # 4. Citizen 1 (Owner)
        self.citizen1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_priya", "priya@gmail.com", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.citizen1_id, "Priya Nair", "9876543230", "Indiranagar"),
            db_path=self.temp_db_path
        )

        # 5. Citizen 2 (Other Citizen)
        self.citizen2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_arun", "arun@gmail.com", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.citizen2_id, "Arun Kumar", "9876543240", "Koramangala"),
            db_path=self.temp_db_path
        )

        # Helper method to create a complaint
        self.complaint_id = execute_query(
            """
            INSERT INTO Complaints (
                complaint_id, citizen_id, title, description, category, location, locality, priority, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "CFX-2026-000099",
                self.citizen1_id,
                "Deep pothole on 100ft road",
                "Severe pothole causing traffic hazards near signal.",
                "Road damage / pothole",
                "Near BDA Complex",
                "Indiranagar",
                "MEDIUM",
                STATUS_NEW
            ),
            db_path=self.temp_db_path
        )

    def tearDown(self):
        """Clean up temporary test database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_01_status_metadata_coverage(self):
        """Verify all 12 system statuses have comprehensive styling and metadata."""
        self.assertEqual(len(ALL_STATUSES), 12)
        for st in ALL_STATUSES:
            meta = get_status_metadata(st)
            self.assertIn("label", meta)
            self.assertIn("bg", meta)
            self.assertIn("fg", meta)
            self.assertIn("icon", meta)
            self.assertIn("stage", meta)
            self.assertTrue(meta["bg"].startswith("#"))
            self.assertTrue(meta["fg"].startswith("#"))

    def test_02_illegal_transitions_prevented(self):
        """Verify state machine strictly rejects illegal, backward, or skipped transitions."""
        # 1. Cannot transition to identical status
        ok, msg, _ = can_transition(self.complaint_id, STATUS_NEW, self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("already in", msg)

        # 2. Cannot jump from NEW directly to RESOLVED
        ok, msg, _ = can_transition(self.complaint_id, STATUS_RESOLVED, self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("Invalid transition", msg)

        # 3. Cannot jump from NEW directly to IN_PROGRESS
        ok, msg, _ = can_transition(self.complaint_id, STATUS_IN_PROGRESS, self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("Invalid transition", msg)

        # 4. Unknown status rejection
        ok, msg, _ = can_transition(self.complaint_id, "NON_EXISTENT_STATUS", self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("Invalid target status", msg)

    def test_03_role_authorization_guards(self):
        """Verify strict role-based execution boundaries."""
        # Citizen cannot verify their own complaint
        ok, msg, _ = can_transition(self.complaint_id, STATUS_VERIFIED, self.citizen1_id, ROLE_CITIZEN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("not authorized", msg)

        # Field worker cannot verify complaints
        ok, msg, _ = can_transition(self.complaint_id, STATUS_VERIFIED, self.worker1_id, ROLE_WORKER, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("not authorized", msg)

        # Admin CAN verify complaint
        ok, msg, _ = can_transition(self.complaint_id, STATUS_VERIFIED, self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertTrue(ok)

    def test_04_ownership_and_assignment_guards(self):
        """Verify actor identity checks: citizen ownership and worker active assignment."""
        # Mark complaint as RESOLVED
        execute_query("UPDATE Complaints SET status = 'RESOLVED' WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)

        # Citizen 2 (not author) attempts to reopen Citizen 1's complaint
        ok, msg, _ = can_transition(self.complaint_id, STATUS_REOPENED, self.citizen2_id, ROLE_CITIZEN, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("only transition their own", msg)

        # Citizen 1 (author) attempts to reopen Citizen 1's complaint
        ok, msg, _ = can_transition(self.complaint_id, STATUS_REOPENED, self.citizen1_id, ROLE_CITIZEN, db_path=self.temp_db_path)
        self.assertTrue(ok)

        # Set complaint to ASSIGNED
        execute_query("UPDATE Complaints SET status = 'ASSIGNED' WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        # Assign to Worker 1
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # Worker 2 (unassigned) attempts to acknowledge task
        ok, msg, _ = can_transition(self.complaint_id, STATUS_ACKNOWLEDGED, self.worker2_id, ROLE_WORKER, db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("not currently assigned", msg)

        # Worker 1 (assigned) acknowledges task
        ok, msg, _ = can_transition(self.complaint_id, STATUS_ACKNOWLEDGED, self.worker1_id, ROLE_WORKER, db_path=self.temp_db_path)
        self.assertTrue(ok)

    def test_05_complete_end_to_end_happy_path_with_notifications(self):
        """
        Tests the complete 9-stage lifecycle from NEW to CLOSED:
        NEW -> VERIFIED -> ASSIGNED -> ACKNOWLEDGED -> IN_PROGRESS ->
        DELAYED -> IN_PROGRESS -> COMPLETED_PENDING_VERIFICATION -> RESOLVED -> CLOSED
        """
        # 1. NEW -> VERIFIED (Admin)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_VERIFIED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Verified site hazard. Assigned to Roads.",
            metadata={"priority": "HIGH", "department": "Roads"},
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_VERIFIED)
        self.assertEqual(comp["priority"], "HIGH")
        self.assertEqual(comp["department"], "Roads")
        self.assertIsNotNone(comp["verified_at"])

        # Check Citizen notification for VERIFIED
        notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.citizen1_id,), db_path=self.temp_db_path)
        self.assertEqual(len(notifs), 1)
        self.assertIn("Verified", notifs[0]["title"])

        # 2. VERIFIED -> ASSIGNED (Admin)
        # Create assignment record
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )
        success, msg = transition_status(
            self.complaint_id,
            STATUS_ASSIGNED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Dispatched to Vikram Patil.",
            metadata={"worker_id": self.worker1_id},
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status, assigned_at FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_ASSIGNED)
        self.assertIsNotNone(comp["assigned_at"])

        # Worker should have received assignment notification
        worker_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.worker1_id,), db_path=self.temp_db_path)
        self.assertEqual(len(worker_notifs), 1)
        self.assertIn("New Field Assignment", worker_notifs[0]["title"])

        # 3. ASSIGNED -> ACKNOWLEDGED (Worker 1)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_ACKNOWLEDGED,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Task acknowledged, arriving at site by 2 PM.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        # 4. ACKNOWLEDGED -> IN_PROGRESS (Worker 1)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_IN_PROGRESS,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Pothole excavation and cleaning started.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        # 5. IN_PROGRESS -> DELAYED (Worker 1)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_DELAYED,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Heavy rainfall delayed asphalt roller.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        # Admin should receive alert regarding delay
        admin_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ? AND notification_type = 'ADMIN_ALERT';", (self.admin_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Task Delayed Notice" in n["title"] for n in admin_notifs))

        # 6. DELAYED -> IN_PROGRESS (Worker 1 resumes)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_IN_PROGRESS,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Rain cleared, asphalt laying resumed.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        # 7. IN_PROGRESS -> COMPLETED_PENDING_VERIFICATION (Worker 1)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_COMPLETED_PENDING_VERIFICATION,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Asphalt laid, leveled, compacted. Proof photo uploaded.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status, completed_at FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_COMPLETED_PENDING_VERIFICATION)
        self.assertIsNotNone(comp["completed_at"])

        # Admin must have received inspection audit notification
        admin_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ? AND notification_type = 'ADMIN_ALERT';", (self.admin_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Audit Required" in n["title"] for n in admin_notifs))

        # 8. COMPLETED_PENDING_VERIFICATION -> RESOLVED (Admin audit approval)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_RESOLVED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Visual inspection passed. Road surface restored.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status, resolved_at FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_RESOLVED)
        self.assertIsNotNone(comp["resolved_at"])

        # Worker should receive congratulatory resolution notification
        worker_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.worker1_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Work Approved" in n["title"] for n in worker_notifs))

        # 9. RESOLVED -> CLOSED (Citizen satisfaction feedback)
        success, msg = transition_status(
            self.complaint_id,
            STATUS_CLOSED,
            actor_id=self.citizen1_id,
            actor_role=ROLE_CITIZEN,
            remarks="Rated 5 stars. Pothole completely repaired.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status, closed_at FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_CLOSED)
        self.assertIsNotNone(comp["closed_at"])

    def test_06_immutable_audit_trails_recorded(self):
        """Verify ComplaintStatusHistory and AdminActionHistory log all transitions accurately."""
        # 1. Admin verifies
        transition_status(
            self.complaint_id,
            STATUS_VERIFIED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Inspected by junior engineer.",
            db_path=self.temp_db_path
        )

        # 2. Assign Worker
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )
        transition_status(
            self.complaint_id,
            STATUS_ASSIGNED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Assigned to Vikram.",
            db_path=self.temp_db_path
        )

        # 3. Worker acknowledges
        transition_status(
            self.complaint_id,
            STATUS_ACKNOWLEDGED,
            actor_id=self.worker1_id,
            actor_role=ROLE_WORKER,
            remarks="Received.",
            db_path=self.temp_db_path
        )

        # Check ComplaintStatusHistory
        history = fetch_all(
            "SELECT * FROM ComplaintStatusHistory WHERE complaint_id = ? ORDER BY id ASC;",
            (self.complaint_id,),
            db_path=self.temp_db_path
        )
        self.assertEqual(len(history), 3)

        self.assertEqual(history[0]["previous_status"], STATUS_NEW)
        self.assertEqual(history[0]["new_status"], STATUS_VERIFIED)
        self.assertEqual(history[0]["changed_by"], self.admin_id)

        self.assertEqual(history[1]["previous_status"], STATUS_VERIFIED)
        self.assertEqual(history[1]["new_status"], STATUS_ASSIGNED)
        self.assertEqual(history[1]["changed_by"], self.admin_id)

        self.assertEqual(history[2]["previous_status"], STATUS_ASSIGNED)
        self.assertEqual(history[2]["new_status"], STATUS_ACKNOWLEDGED)
        self.assertEqual(history[2]["changed_by"], self.worker1_id)

        # Check AdminActionHistory (only the 2 admin actions should be logged here)
        admin_actions = fetch_all(
            "SELECT * FROM AdminActionHistory WHERE complaint_id = ? ORDER BY id ASC;",
            (self.complaint_id,),
            db_path=self.temp_db_path
        )
        self.assertEqual(len(admin_actions), 2)
        self.assertEqual(admin_actions[0]["action_type"], "VERIFY")
        self.assertEqual(admin_actions[1]["action_type"], "TRANSITION_ASSIGNED")

    def test_07_reopen_lifecycle(self):
        """Verify reopening of resolved issues by citizen and admin re-triage."""
        # Setup as RESOLVED
        execute_query("UPDATE Complaints SET status = 'RESOLVED' WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # Citizen reopens
        success, msg = transition_status(
            self.complaint_id,
            STATUS_REOPENED,
            actor_id=self.citizen1_id,
            actor_role=ROLE_CITIZEN,
            remarks="Pothole was only partially filled; loose gravel is still dangerous.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        comp = fetch_one("SELECT status, reopen_reason, reopened_at FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_REOPENED)
        self.assertIn("partially filled", comp["reopen_reason"])
        self.assertIsNotNone(comp["reopened_at"])

        # Admin alert triggered
        admin_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ? AND notification_type = 'ADMIN_ALERT';", (self.admin_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Reopened by Citizen" in n["title"] for n in admin_notifs))

        # Admin moves back to VERIFIED
        success, msg = transition_status(
            self.complaint_id,
            STATUS_VERIFIED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Re-evaluated site; rework required.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

    def test_08_rejection_and_reopen_appeal(self):
        """Verify complaint rejection by admin and citizen appeal."""
        success, msg = transition_status(
            self.complaint_id,
            STATUS_REJECTED,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Issue falls under private residential society boundary.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status, rejection_reason FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_REJECTED)
        self.assertIn("private residential society", comp["rejection_reason"])

        # Citizen appeals rejection
        success, msg = transition_status(
            self.complaint_id,
            STATUS_REOPENED,
            actor_id=self.citizen1_id,
            actor_role=ROLE_CITIZEN,
            remarks="This is on the public main road right in front of the gate, not inside private property.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)
        comp = fetch_one("SELECT status FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_REOPENED)

    def test_09_admin_rework_request_from_inspection(self):
        """Verify admin can send completed task back to IN_PROGRESS for rework."""
        # Setup as COMPLETED_PENDING_VERIFICATION
        execute_query(
            "UPDATE Complaints SET status = 'COMPLETED_PENDING_VERIFICATION' WHERE id = ?;",
            (self.complaint_id,),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # Admin requests rework
        success, msg = transition_status(
            self.complaint_id,
            STATUS_IN_PROGRESS,
            actor_id=self.admin_id,
            actor_role=ROLE_ADMIN,
            remarks="Proof photo shows uneven surface; please re-level and compact properly.",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        comp = fetch_one("SELECT status FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_IN_PROGRESS)

        # Worker must receive "Rework Requested" notification
        worker_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.worker1_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Rework Requested" in n["title"] for n in worker_notifs))

    def test_10_allowed_transitions_query(self):
        """Verify get_allowed_transitions dynamically returns only permitted target states."""
        # When status is NEW
        admin_targets = get_allowed_transitions(self.complaint_id, self.admin_id, ROLE_ADMIN, db_path=self.temp_db_path)
        self.assertEqual(admin_targets, [STATUS_REJECTED, STATUS_UNDER_REVIEW, STATUS_VERIFIED])

        citizen_targets = get_allowed_transitions(self.complaint_id, self.citizen1_id, ROLE_CITIZEN, db_path=self.temp_db_path)
        self.assertEqual(citizen_targets, [])

        worker_targets = get_allowed_transitions(self.complaint_id, self.worker1_id, ROLE_WORKER, db_path=self.temp_db_path)
        self.assertEqual(worker_targets, [])

    def test_11_administrator_controller_integration(self):
        """Verify AdministratorController methods leverage state machine transition rules."""
        from modules.administrator import AdministratorController
        admin_ctrl = AdministratorController(admin_id=self.admin_id, db_path=self.temp_db_path)

        # 1. Verify complaint via AdministratorController
        ok_v, msg_v = admin_ctrl.verify_complaint(
            complaint_id=self.complaint_id,
            remarks="Verified site hazard by junior engineer.",
            priority="HIGH",
            department="Roads",
            due_date="2026-11-25 18:00:00"
        )
        self.assertTrue(ok_v, msg_v)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], STATUS_VERIFIED)
        self.assertEqual(comp["priority"], "HIGH")
        self.assertEqual(comp["department"], "Roads")

        # 2. Cannot close directly from VERIFIED
        ok_bad, msg_bad = admin_ctrl.close_and_resolve_complaint(self.complaint_id, remarks="Premature close")
        self.assertFalse(ok_bad)
        self.assertIn("Invalid transition", msg_bad)

    def test_12_worker_notifications_and_admin_alerts(self):
        """Verify WorkerController operations send alerts to active administrators and citizen."""
        from modules.field_worker import WorkerController
        worker_ctrl = WorkerController(worker_user_id=self.worker1_id, db_path=self.temp_db_path)

        # Move to ASSIGNED and create assignment record
        execute_query("UPDATE Complaints SET status = 'ASSIGNED' WHERE id = ?;", (self.complaint_id,), db_path=self.temp_db_path)
        asgn_id = execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current) VALUES (?, ?, ?, 1);",
            (self.complaint_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # 1. Worker reports delay
        ok_d, msg_d = worker_ctrl.report_delay_reason(
            assignment_id=asgn_id,
            complaint_id=self.complaint_id,
            delay_reason="Heavy rain caused delay in procuring asphalt."
        )
        self.assertTrue(ok_d, msg_d)

        # Admin alert check
        admin_notifs = fetch_all(
            "SELECT * FROM Notifications WHERE user_id = ? AND notification_type = 'ADMIN_ALERT';",
            (self.admin_id,),
            db_path=self.temp_db_path
        )
        self.assertTrue(any("Task Delayed Notice" in n["title"] for n in admin_notifs))

        # Citizen update check
        citizen_notifs = fetch_all(
            "SELECT * FROM Notifications WHERE user_id = ?;",
            (self.citizen1_id,),
            db_path=self.temp_db_path
        )
        self.assertTrue(any("Delayed" in n["title"] for n in citizen_notifs))

        # 2. Worker submits completion
        ok_c, msg_c = worker_ctrl.submit_task_completion(
            assignment_id=asgn_id,
            complaint_id=self.complaint_id,
            completion_image_rel_path="uploads/proof.jpg",
            final_remarks="Road completely patched and smoothed."
        )
        self.assertTrue(ok_c, msg_c)

        # Admin must receive "Audit Required: Work Completed"
        admin_notifs_after = fetch_all(
            "SELECT * FROM Notifications WHERE user_id = ? AND notification_type = 'ADMIN_ALERT';",
            (self.admin_id,),
            db_path=self.temp_db_path
        )
        self.assertTrue(any("Audit Required" in n["title"] for n in admin_notifs_after))


if __name__ == "__main__":
    unittest.main()
