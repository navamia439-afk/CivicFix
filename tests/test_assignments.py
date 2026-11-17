"""
CivicFix Administrator & Assignment Test Suite
Validates verification, rejection, automated priority suggestion,
worker assignment, duplicate detection, duplicate merging, and CSV report export.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, fetch_all
from services.priority_service import calculate_suggested_priority
from services.assignment_service import assign_complaint_to_worker
from services.report_service import (
    detect_potential_duplicates,
    export_complaints_to_csv,
    get_overdue_complaints
)
from modules.administrator import AdministratorController
from services.complaint_service import create_complaint


class TestAdministratorAndAssignments(unittest.TestCase):
    def setUp(self):
        """Create an isolated test database with Admin, Worker, and Citizen."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # Create Admin
        self.admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'ADMIN');",
            ("admin_test", "admin@test.org", "hash", "salt"),
            db_path=self.temp_db_path
        )
        self.controller = AdministratorController(admin_id=self.admin_id)

        # Create Field Worker
        self.worker_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_test", "worker@test.org", "hash", "salt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker_id, "Worker Test", "9876543200", "Roads", "Asphalt Patching"),
            db_path=self.temp_db_path
        )

        # Create Citizen
        self.citizen_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("cit_test", "cit@test.org", "hash", "salt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.citizen_id, "Citizen Test", "9876543201", "Indiranagar"),
            db_path=self.temp_db_path
        )

    def tearDown(self):
        """Clean up the test database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_priority_suggestion_engine(self):
        """Verify priority suggestion rules for emergency, support clusters, and categories."""
        # Emergency flag
        p_em, r_em = calculate_suggested_priority("Other civic issue", is_emergency=True)
        self.assertEqual(p_em, "EMERGENCY")

        # High support cluster (>= 5)
        p_sup, r_sup = calculate_suggested_priority("Broken streetlight", support_count=6)
        self.assertEqual(p_sup, "HIGH")

        # Road damage category with 2 supports
        p_road, r_road = calculate_suggested_priority("Road damage / pothole", support_count=2)
        self.assertEqual(p_road, "HIGH")

        # Standard low impact issue
        p_low, r_low = calculate_suggested_priority("Other civic issue", support_count=0)
        self.assertEqual(p_low, "LOW")

    def test_verification_workflow(self):
        """Test admin verifying complaint, setting priority, and assigning department."""
        ok, code, cid, _ = create_complaint(
            self.citizen_id, "Pothole on 5th Cross", "Deep asphalt depression.",
            "Road damage / pothole", "5th Cross Road", "Indiranagar", db_path=self.temp_db_path
        )

        # Admin verifies complaint
        # Need to patch controller to use test database
        from database.db_connection import get_db
        ok_v, msg_v = self.controller.verify_complaint(
            complaint_id=cid,
            remarks="Verified by engineer.",
            priority="HIGH",
            department="Roads",
            due_date="2026-11-20 18:00:00"
        )
        self.assertTrue(ok_v)

        # Check complaint in database
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "VERIFIED")
        self.assertEqual(comp["priority"], "HIGH")
        self.assertEqual(comp["department"], "Roads")

        # Check AdminActionHistory audit trail
        actions = fetch_all("SELECT * FROM AdminActionHistory WHERE complaint_id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["action_type"], "VERIFY")

    def test_rejection_workflow(self):
        """Test admin rejecting an invalid complaint with mandatory explanation."""
        ok, code, cid, _ = create_complaint(
            self.citizen_id, "Private property issue", "Cracked tile inside private kitchen.",
            "Other civic issue", "Flat 302", "Indiranagar", db_path=self.temp_db_path
        )

        ok_rej, msg_rej = self.controller.reject_complaint(
            complaint_id=cid,
            rejection_reason="Private domestic property, outside municipal jurisdiction."
        )
        self.assertTrue(ok_rej)

        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "REJECTED")
        self.assertIn("municipal jurisdiction", comp["rejection_reason"])

    def test_worker_assignment(self):
        """Test assigning verified complaint to a field worker."""
        ok, code, cid, _ = create_complaint(
            self.citizen_id, "Open drain risk", "Exposed storm drain.",
            "Drainage blockage", "1st Main", "Indiranagar", db_path=self.temp_db_path
        )
        self.controller.verify_complaint(cid, "Drainage verified", "HIGH", "Drainage")

        ok_asgn, msg_asgn = assign_complaint_to_worker(
            complaint_id=cid,
            worker_id=self.worker_id,
            admin_id=self.admin_id,
            due_date="2026-11-18 18:00:00",
            admin_notes="Clear blockage using vacuum suction.",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_asgn)

        # Verify assignment record created
        wa = fetch_one("SELECT * FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;", (cid,), db_path=self.temp_db_path)
        self.assertIsNotNone(wa)
        self.assertEqual(wa["worker_id"], self.worker_id)

        # Verify complaint updated to ASSIGNED
        comp = fetch_one("SELECT status FROM Complaints WHERE id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "ASSIGNED")

    def test_duplicate_detection_and_merge(self):
        """Test identifying and merging duplicate complaints in the same locality."""
        # Primary complaint
        ok1, code1, cid1, _ = create_complaint(
            self.citizen_id, "Dangerous pothole near metro pillar 10", "Deep road depression.",
            "Road damage / pothole", "100ft Road Metro Pillar 10", "Indiranagar", db_path=self.temp_db_path
        )

        # Duplicate complaint reported by another citizen
        c2 = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('c2', 'c2@t.org', 'h', 's', 'CITIZEN');",
            db_path=self.temp_db_path
        )
        execute_query("INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, 'C2', '123', 'Indiranagar');", (c2,), db_path=self.temp_db_path)

        ok2, code2, cid2, _ = create_complaint(
            c2, "Road pothole near metro pillar 10 hazardous", "Big pothole on road.",
            "Road damage / pothole", "100ft Road Metro Pillar 10", "Indiranagar", db_path=self.temp_db_path
        )

        # Detect duplicates
        dupes = detect_potential_duplicates(cid1, db_path=self.temp_db_path)
        self.assertGreater(len(dupes), 0)
        self.assertEqual(dupes[0]["id"], cid2)
        self.assertGreaterEqual(dupes[0]["similarity_score"], 60)

        # Merge duplicate into primary
        ok_m, msg_m = self.controller.merge_duplicates(cid1, cid2)
        self.assertTrue(ok_m)

        # Verify primary complaint received +1 support count
        prim = fetch_one("SELECT support_count FROM Complaints WHERE id = ?;", (cid1,), db_path=self.temp_db_path)
        self.assertEqual(prim["support_count"], 1)

        # Verify duplicate complaint is marked CLOSED
        dupe = fetch_one("SELECT status FROM Complaints WHERE id = ?;", (cid2,), db_path=self.temp_db_path)
        self.assertEqual(dupe["status"], "CLOSED")

    def test_csv_export(self):
        """Test CSV file generation with complaint rows."""
        create_complaint(self.citizen_id, "CSV Test Issue", "Desc for CSV testing.", "Water leakage", "Main Road", "Indiranagar", db_path=self.temp_db_path)

        csv_fd, csv_path = tempfile.mkstemp(suffix=".csv")
        try:
            os.close(csv_fd)
            ok, cnt, msg = export_complaints_to_csv(csv_path, db_path=self.temp_db_path)
            self.assertTrue(ok)
            self.assertGreater(cnt, 0)
            self.assertTrue(os.path.exists(csv_path))

            with open(csv_path, mode="r", encoding="utf-8") as f:
                content = f.read()
                self.assertIn("Complaint ID", content)
                self.assertIn("CSV Test Issue", content)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)


if __name__ == "__main__":
    unittest.main()
