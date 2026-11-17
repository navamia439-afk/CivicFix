"""
CivicFix Field Worker Operations & End-to-End Workflow Test Suite
Validates worker task scoping, acknowledgment, progress tracking, category checklists,
material requisition, delay justification, completion proof submission, and the complete
end-to-end lifecycle from citizen reporting to administrative resolution.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, fetch_all
from services.complaint_service import create_complaint
from services.assignment_service import assign_complaint_to_worker
from modules.administrator import AdministratorController
from modules.field_worker import WorkerController


class TestWorkerAndWorkflow(unittest.TestCase):
    def setUp(self):
        """Create an isolated test database with Admin, 2 Workers, and Citizen."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # 1. Create Admin
        self.admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'ADMIN');",
            ("admin_test", "admin@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        self.admin_controller = AdministratorController(admin_id=self.admin_id, db_path=self.temp_db_path)

        # 2. Create Field Worker 1 (Raj)
        self.worker1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_raj", "raj@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker1_id, "Raj Kumar", "9876543210", "Roads & Infrastructure", "Asphalt & Potholes"),
            db_path=self.temp_db_path
        )
        self.worker1_ctrl = WorkerController(worker_user_id=self.worker1_id, db_path=self.temp_db_path)

        # 3. Create Field Worker 2 (Anita)
        self.worker2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_anita", "anita@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker2_id, "Anita Sharma", "9876543220", "Electrical & Lighting", "Streetlight Wiring"),
            db_path=self.temp_db_path
        )
        self.worker2_ctrl = WorkerController(worker_user_id=self.worker2_id, db_path=self.temp_db_path)

        # 4. Create Citizen
        self.citizen_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_rahul", "rahul@test.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.citizen_id, "Rahul Varma", "9876543230", "Indiranagar"),
            db_path=self.temp_db_path
        )

    def tearDown(self):
        """Clean up the isolated database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def _create_and_assign_task(self, title="Pothole on 100ft Rd", category="Road damage / pothole", worker_id=None):
        """Helper to create a complaint and assign it to worker 1 by default."""
        target_worker = worker_id or self.worker1_id
        res, code, comp_id, err = create_complaint(
            citizen_id=self.citizen_id,
            title=title,
            description="Deep pothole causing vehicular damage.",
            category=category,
            location="100ft Road, near junction",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(res, f"Complaint creation failed: {err}")

        # Mark complaint as VERIFIED before assignment
        execute_query("UPDATE Complaints SET status = 'VERIFIED' WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)

        # Admin assigns complaint to target worker
        assign_res, asgn_msg = assign_complaint_to_worker(
            complaint_id=comp_id,
            worker_id=target_worker,
            admin_id=self.admin_id,
            due_date="2026-11-20 18:00:00",
            admin_notes="Please expedite repair.",
            db_path=self.temp_db_path
        )
        self.assertTrue(assign_res, f"Assignment failed: {asgn_msg}")

        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        asgn = fetch_one("SELECT * FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;", (comp_id,), db_path=self.temp_db_path)
        return comp_id, comp["complaint_id"], asgn["id"]

    def test_worker_task_scoping(self):
        """Field worker must only see tasks assigned to them, never other workers' tasks."""
        comp1_id, code1, asgn1_id = self._create_and_assign_task(title="Road Task for Raj", worker_id=self.worker1_id)
        comp2_id, code2, asgn2_id = self._create_and_assign_task(title="Lighting Task for Anita", category="Broken streetlight", worker_id=self.worker2_id)

        # Worker 1 (Raj) tasks
        tasks_raj = self.worker1_ctrl.get_assigned_tasks()
        raj_codes = [t["complaint_id"] for t in tasks_raj]
        self.assertIn(code1, raj_codes)
        self.assertNotIn(code2, raj_codes)

        # Worker 2 (Anita) tasks
        tasks_anita = self.worker2_ctrl.get_assigned_tasks()
        anita_codes = [t["complaint_id"] for t in tasks_anita]
        self.assertIn(code2, anita_codes)
        self.assertNotIn(code1, anita_codes)

        # Task Details Scoping
        self.assertIsNotNone(self.worker1_ctrl.get_task_details(code1))
        self.assertIsNone(self.worker1_ctrl.get_task_details(code2))

    def test_worker_kpi_summary(self):
        """Worker KPI counts reflect actual assignment statuses."""
        comp_id, code, asgn_id = self._create_and_assign_task()

        kpi = self.worker1_ctrl.get_worker_kpi_summary()
        self.assertEqual(kpi["total_assigned"], 1)
        self.assertEqual(kpi["new_assigned"], 1)
        self.assertEqual(kpi["acknowledged"], 0)
        self.assertEqual(kpi["in_progress"], 0)

    def test_task_acknowledgment(self):
        """Worker acknowledges task, updating timestamp, status, history, and notifying citizen."""
        comp_id, code, asgn_id = self._create_and_assign_task()

        ok, msg = self.worker1_ctrl.acknowledge_task(asgn_id, comp_id)
        self.assertTrue(ok, msg)

        # Verify complaint status
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "ACKNOWLEDGED")

        # Verify assignment acknowledged_at
        asgn = fetch_one("SELECT * FROM WorkerAssignments WHERE id = ?;", (asgn_id,), db_path=self.temp_db_path)
        self.assertIsNotNone(asgn["acknowledged_at"])

        # Verify status history
        history = fetch_all("SELECT * FROM ComplaintStatusHistory WHERE complaint_id = ?;", (comp_id,), db_path=self.temp_db_path)
        new_statuses = [h["new_status"] for h in history]
        self.assertIn("ACKNOWLEDGED", new_statuses)

        # Verify citizen notification
        notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.citizen_id,), db_path=self.temp_db_path)
        self.assertTrue(any("acknowledged" in n["title"].lower() or "acknowledged" in n["message"].lower() for n in notifs))

    def test_update_task_progress(self):
        """Worker logs progress update, advancing status to IN_PROGRESS."""
        comp_id, code, asgn_id = self._create_and_assign_task()
        self.worker1_ctrl.acknowledge_task(asgn_id, comp_id)

        # Validation: notes too short
        ok_fail, msg_fail = self.worker1_ctrl.update_task_progress(asgn_id, comp_id, "ok")
        self.assertFalse(ok_fail)

        # Valid progress update
        ok, msg = self.worker1_ctrl.update_task_progress(
            asgn_id,
            comp_id,
            progress_notes="Excavated pothole boundaries and applied bitumen prime coat.",
            estimated_completion_date="2026-11-15 17:00:00"
        )
        self.assertTrue(ok, msg)

        # Verify complaint status
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "IN_PROGRESS")

        # Verify WorkerProgressUpdates entry
        progress_entries = fetch_all("SELECT * FROM WorkerProgressUpdates WHERE assignment_id = ?;", (asgn_id,), db_path=self.temp_db_path)
        self.assertEqual(len(progress_entries), 1)
        self.assertIn("bitumen prime coat", progress_entries[0]["progress_notes"])

    def test_report_delay_reason(self):
        """Worker flags task as DELAYED with required justification."""
        comp_id, code, asgn_id = self._create_and_assign_task()

        # Validation: reason too short (< 10 chars)
        ok_fail, msg_fail = self.worker1_ctrl.report_delay_reason(asgn_id, comp_id, "rain")
        self.assertFalse(ok_fail)

        # Valid delay report
        ok, msg = self.worker1_ctrl.report_delay_reason(
            asgn_id,
            comp_id,
            delay_reason="Continuous torrential rainfall prevents asphalt laying on road surface."
        )
        self.assertTrue(ok, msg)

        # Verify complaint status
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "DELAYED")

        # Verify delay_reason on assignment
        asgn = fetch_one("SELECT * FROM WorkerAssignments WHERE id = ?;", (asgn_id,), db_path=self.temp_db_path)
        self.assertIn("torrential rainfall", asgn["delay_reason"])

    def test_checklist_and_material_requirements(self):
        """Category checklist initializes template items and allows toggling; materials can be added."""
        comp_id, code, asgn_id = self._create_and_assign_task(category="Road damage / pothole")

        # Checklist initialization
        checklist = self.worker1_ctrl.get_or_create_checklist(asgn_id, comp_id, "Road damage / pothole")
        self.assertGreaterEqual(len(checklist), 5)
        first_item = checklist[0]
        self.assertEqual(first_item["is_completed"], 0)

        # Toggle checklist item
        self.worker1_ctrl.toggle_checklist_item(first_item["id"], is_completed=True)
        updated_item = fetch_one("SELECT * FROM WorkChecklistItems WHERE id = ?;", (first_item["id"],), db_path=self.temp_db_path)
        self.assertEqual(updated_item["is_completed"], 1)
        self.assertIsNotNone(updated_item["completed_at"])

        # Material Requisition
        mat_ok, mat_msg = self.worker1_ctrl.add_material_requirement(
            asgn_id,
            comp_id,
            item_name="Cold Mix Bitumen",
            quantity="4 Bags (200kg)",
            notes="Need by tomorrow morning"
        )
        self.assertTrue(mat_ok, mat_msg)

        materials = fetch_all("SELECT * FROM MaterialRequirements WHERE assignment_id = ?;", (asgn_id,), db_path=self.temp_db_path)
        self.assertEqual(len(materials), 1)
        self.assertEqual(materials[0]["item_name"], "Cold Mix Bitumen")

    def test_submit_task_completion_sets_pending_verification(self):
        """
        Worker cannot directly resolve or close complaints.
        Completion submission must require photo and remarks, setting status to COMPLETED_PENDING_VERIFICATION.
        """
        comp_id, code, asgn_id = self._create_and_assign_task()

        # Validation: missing image
        ok_fail, msg_fail = self.worker1_ctrl.submit_task_completion(
            asgn_id, comp_id, completion_image_rel_path="", final_remarks="Finished work."
        )
        self.assertFalse(ok_fail)

        # Valid completion submission
        fake_photo_path = "uploads/completion_images/test_resolution_proof.jpg"
        ok, msg = self.worker1_ctrl.submit_task_completion(
            asgn_id,
            comp_id,
            completion_image_rel_path=fake_photo_path,
            final_remarks="Pothole completely leveled, asphalt compacted, and traffic flow safely restored."
        )
        self.assertTrue(ok, msg)

        # Verify complaint status is strictly COMPLETED_PENDING_VERIFICATION, not RESOLVED or CLOSED
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "COMPLETED_PENDING_VERIFICATION")
        self.assertIsNotNone(comp["completed_at"])

        # Verify completion image saved in ComplaintImages
        img = fetch_one(
            "SELECT * FROM ComplaintImages WHERE complaint_id = ? AND image_type = 'COMPLETION';",
            (comp_id,),
            db_path=self.temp_db_path
        )
        self.assertIsNotNone(img)
        self.assertEqual(img["image_path"], fake_photo_path)

    def test_end_to_end_complaint_lifecycle(self):
        """
        Comprehensive test of the full civic issue resolution lifecycle:
        1. Citizen Reports (NEW)
        2. Admin Verifies and Assigns to Worker (ASSIGNED)
        3. Worker Acknowledges (ACKNOWLEDGED)
        4. Worker Begins Work (IN_PROGRESS)
        5. Worker Submits Completion Proof (COMPLETED_PENDING_VERIFICATION)
        6. Admin Audits and Resolves (RESOLVED)
        7. Citizen Submits 5-star Feedback
        """
        # 1. Citizen creates issue
        ok_c, code, comp_id, err_c = create_complaint(
            citizen_id=self.citizen_id,
            title="Dangerous pothole outside metro station",
            description="Causing two-wheelers to skid during rush hour.",
            category="Road damage / pothole",
            location="MG Road Metro Pillar 140",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_c, f"Create complaint failed: {err_c}")
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "NEW")

        # 2. Admin verifies and assigns to Worker 1
        execute_query("UPDATE Complaints SET status = 'VERIFIED' WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        ok_a, _ = assign_complaint_to_worker(
            complaint_id=comp_id,
            worker_id=self.worker1_id,
            admin_id=self.admin_id,
            due_date="2026-11-25 18:00:00",
            admin_notes="High traffic zone.",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_a)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "ASSIGNED")
        asgn = fetch_one("SELECT * FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;", (comp_id,), db_path=self.temp_db_path)
        asgn_id = asgn["id"]

        # 3. Worker Acknowledges
        ok_ack, _ = self.worker1_ctrl.acknowledge_task(asgn_id, comp_id)
        self.assertTrue(ok_ack)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "ACKNOWLEDGED")

        # 4. Worker Starts Work
        ok_prog, _ = self.worker1_ctrl.update_task_progress(
            asgn_id, comp_id, progress_notes="Site barricaded and base course laid."
        )
        self.assertTrue(ok_prog)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "IN_PROGRESS")

        # 5. Worker Submits Completion
        ok_comp, _ = self.worker1_ctrl.submit_task_completion(
            asgn_id,
            comp_id,
            completion_image_rel_path="uploads/completion_images/resolved_pothole_mg_road.jpg",
            final_remarks="Road resurfaced smoothly and barricades removed."
        )
        self.assertTrue(ok_comp)
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "COMPLETED_PENDING_VERIFICATION")

        # 6. Admin Audits and Resolves
        # Record admin resolution
        execute_query(
            "UPDATE Complaints SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP WHERE id = ?;",
            (comp_id,),
            db_path=self.temp_db_path
        )
        execute_query(
            """
            INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
            VALUES (?, 'COMPLETED_PENDING_VERIFICATION', 'RESOLVED', ?, 'Admin verified completion photo and closed ticket.');
            """,
            (comp_id, self.admin_id),
            db_path=self.temp_db_path
        )
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "RESOLVED")

        # 7. Citizen Feedback
        from services.complaint_service import submit_feedback
        fb_ok, fb_msg = submit_feedback(
            complaint_id=comp_id,
            citizen_id=self.citizen_id,
            rating=5,
            comments="Outstanding prompt repair! Commute is safe again.",
            db_path=self.temp_db_path
        )
        self.assertTrue(fb_ok, fb_msg)

        feedback = fetch_one("SELECT * FROM Feedback WHERE complaint_id = ?;", (comp_id,), db_path=self.temp_db_path)
        self.assertEqual(feedback["rating"], 5)
        self.assertEqual(feedback["comments"], "Outstanding prompt repair! Commute is safe again.")

        # Verify complete status history timeline
        timeline = fetch_all("SELECT * FROM ComplaintStatusHistory WHERE complaint_id = ? ORDER BY id ASC;", (comp_id,), db_path=self.temp_db_path)
        statuses_journey = [t["new_status"] for t in timeline]
        self.assertIn("NEW", statuses_journey)
        self.assertIn("ASSIGNED", statuses_journey)
        self.assertIn("ACKNOWLEDGED", statuses_journey)
        self.assertIn("IN_PROGRESS", statuses_journey)
        self.assertIn("COMPLETED_PENDING_VERIFICATION", statuses_journey)
        self.assertIn("RESOLVED", statuses_journey)


if __name__ == "__main__":
    unittest.main()
