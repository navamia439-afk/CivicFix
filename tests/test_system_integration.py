"""
CivicFix End-to-End System Integration & Invariant Validation Test Suite
Tests multi-role concurrent workflows, duplicate detection and merging,
notification lifecycle scoping, SQL injection resilience, and PBKDF2 security.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, fetch_all
from authentication.password_manager import hash_password, verify_password, validate_password_strength
from authentication.auth import authenticate_user, register_citizen
from utils.validators import validate_email, validate_phone
from services.complaint_service import create_complaint, submit_feedback, reopen_complaint
from services.assignment_service import assign_complaint_to_worker
from services.report_service import detect_potential_duplicates, get_admin_kpis
from modules.administrator import AdministratorController
from modules.field_worker import WorkerController
from modules.citizen import CitizenController
from scripts.verify_database import verify_database_health


class TestSystemIntegration(unittest.TestCase):
    def setUp(self):
        """Creates an isolated test environment with complete municipal staffing."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # 1. Admin
        admin_hash, admin_salt = hash_password("AdminSecure2026!")
        self.admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'ADMIN');",
            ("chief_commissioner", "commissioner@civicfix.org", admin_hash, admin_salt),
            db_path=self.temp_db_path
        )
        self.admin_ctrl = AdministratorController(admin_id=self.admin_id, db_path=self.temp_db_path)

        # 2. Field Workers (Roads, Sanitation, Electrical)
        w1_hash, w1_salt = hash_password("WorkerSecure2026!")
        self.worker_roads_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_ramesh", "ramesh@civicfix.org", w1_hash, w1_salt),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker_roads_id, "Ramesh Gowda", "9876543211", "Roads", "Asphalt Laying & Paving"),
            db_path=self.temp_db_path
        )
        self.worker_roads_ctrl = WorkerController(worker_user_id=self.worker_roads_id, db_path=self.temp_db_path)

        self.worker_san_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_suresh", "suresh@civicfix.org", w1_hash, w1_salt),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker_san_id, "Suresh Kumar", "9876543212", "Sanitation", "Solid Waste Management"),
            db_path=self.temp_db_path
        )
        self.worker_san_ctrl = WorkerController(worker_user_id=self.worker_san_id, db_path=self.temp_db_path)

        # 3. Citizens
        c1_hash, c1_salt = hash_password("CitizenPass2026!")
        self.citizen1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_priya", "priya@gmail.com", c1_hash, c1_salt),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality, address) VALUES (?, ?, ?, ?, ?);",
            (self.citizen1_id, "Priya Nair", "9876543231", "Indiranagar", "100ft Road"),
            db_path=self.temp_db_path
        )
        self.citizen1_ctrl = CitizenController(citizen_id=self.citizen1_id)

        self.citizen2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_kavita", "kavita@gmail.com", c1_hash, c1_salt),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality, address) VALUES (?, ?, ?, ?, ?);",
            (self.citizen2_id, "Kavita Rao", "9876543232", "Indiranagar", "12th Main"),
            db_path=self.temp_db_path
        )

    def tearDown(self):
        """Removes the isolated test database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_01_multi_role_concurrent_lifecycle(self):
        """
        Tests multiple complaints progressing concurrently through reporting,
        triage, worker assignment, physical repair, and rating finalization.
        """
        # Citizen 1 reports Pothole
        ok1, code1, id1, _ = create_complaint(
            citizen_id=self.citizen1_id,
            title="Dangerous pothole outside metro",
            description="Deep crater causing vehicles to swerve abruptly.",
            category="Road damage / pothole",
            location="Near Indiranagar Metro Station",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok1)

        # Citizen 2 reports Garbage issue
        ok2, code2, id2, _ = create_complaint(
            citizen_id=self.citizen2_id,
            title="Garbage bin overflowing near school",
            description="Severe odor and health hazard for children.",
            category="Garbage / waste issue",
            location="5th Cross Indiranagar",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok2)

        # Admin verifies both issues
        self.admin_ctrl.verify_complaint(id1, remarks="High traffic zone.", priority="HIGH", department="Roads")
        self.admin_ctrl.verify_complaint(id2, remarks="Near school premises.", priority="HIGH", department="Sanitation")

        # Admin dispatches to respective workers
        ok_a1, _ = assign_complaint_to_worker(id1, self.worker_roads_id, self.admin_id, db_path=self.temp_db_path)
        ok_a2, _ = assign_complaint_to_worker(id2, self.worker_san_id, self.admin_id, db_path=self.temp_db_path)
        self.assertTrue(ok_a1)
        self.assertTrue(ok_a2)

        # Workers acknowledge their respective tasks
        asgn1 = fetch_one("SELECT id FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;", (id1,), db_path=self.temp_db_path)
        asgn2 = fetch_one("SELECT id FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;", (id2,), db_path=self.temp_db_path)

        self.worker_roads_ctrl.acknowledge_task(asgn1["id"], id1)
        self.worker_san_ctrl.acknowledge_task(asgn2["id"], id2)

        # Worker 1 logs progress
        self.worker_roads_ctrl.update_task_progress(asgn1["id"], id1, "Bitumen mix prepared and surface leveled.")
        
        # Worker 1 completes task
        self.worker_roads_ctrl.submit_task_completion(
            asgn1["id"], id1,
            completion_image_rel_path="uploads/completion_images/pothole_fixed.jpg",
            final_remarks="Road surface rolled, compacted, and traffic reopened."
        )

        # Admin inspects and resolves Task 1
        ok_res, _ = self.admin_ctrl.close_and_resolve_complaint(id1, remarks="Inspection passed.")
        self.assertTrue(ok_res)

        # Citizen 1 rates Task 1 with 5 stars (automatically advances to CLOSED)
        fb_ok, _ = submit_feedback(id1, self.citizen1_id, rating=5, comments="Excellent swift work!", db_path=self.temp_db_path)
        self.assertTrue(fb_ok)

        comp1_final = fetch_one("SELECT status, closed_at FROM Complaints WHERE id = ?;", (id1,), db_path=self.temp_db_path)
        self.assertEqual(comp1_final["status"], "CLOSED")
        self.assertIsNotNone(comp1_final["closed_at"])

        # Task 2 remains active in Sanitation
        comp2_active = fetch_one("SELECT status FROM Complaints WHERE id = ?;", (id2,), db_path=self.temp_db_path)
        self.assertEqual(comp2_active["status"], "ACKNOWLEDGED")

    def test_02_duplicate_detection_and_merging_lifecycle(self):
        """
        Tests automated text similarity duplicate detection and administrative ticket merging.
        """
        # Primary complaint
        ok1, code1, id1, _ = create_complaint(
            citizen_id=self.citizen1_id,
            title="Large water pipe burst near Sony signal",
            description="Massive clean water loss on main road.",
            category="Water leakage",
            location="Sony World Signal, 100ft Rd",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok1)

        # Candidate duplicate complaint from another citizen
        ok2, code2, id2, _ = create_complaint(
            citizen_id=self.citizen2_id,
            title="Water pipe burst near Sony signal junction",
            description="Drinking water pipe leakage flooding road.",
            category="Water leakage",
            location="Sony World Signal junction",
            locality="Indiranagar",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok2)

        # Run duplicate detection for id2 against id1
        duplicates = detect_potential_duplicates(id2, db_path=self.temp_db_path)
        self.assertGreaterEqual(len(duplicates), 1)
        matched = duplicates[0]
        self.assertEqual(matched["id"], id1)
        self.assertGreaterEqual(matched["similarity_score"], 60)

        # Admin merges id2 into id1
        merge_ok, merge_msg = self.admin_ctrl.merge_duplicate_complaint(
            primary_complaint_id=id1,
            duplicate_complaint_id=id2
        )
        self.assertTrue(merge_ok, merge_msg)

        # Primary complaint should have support count incremented to 1
        prim = fetch_one("SELECT support_count FROM Complaints WHERE id = ?;", (id1,), db_path=self.temp_db_path)
        self.assertEqual(prim["support_count"], 1)

        # Duplicate complaint should be marked CLOSED with admin remarks
        dupe = fetch_one("SELECT status, admin_remarks FROM Complaints WHERE id = ?;", (id2,), db_path=self.temp_db_path)
        self.assertEqual(dupe["status"], "CLOSED")
        self.assertIn("Merged duplicate", dupe["admin_remarks"])

        # Citizen 2 should receive a notification explaining the merge
        notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.citizen2_id,), db_path=self.temp_db_path)
        self.assertTrue(any("Merged" in n["title"] for n in notifs))

    def test_03_notification_queue_unreads_and_scoping(self):
        """
        Validates in-app notification creation, unread count tracking,
        marking as read, and user isolation.
        """
        # Create a notification for citizen 1
        execute_query(
            """
            INSERT INTO Notifications (user_id, title, message, notification_type, is_read)
            VALUES (?, 'Update on your issue', 'Worker arrived at site.', 'STATUS_UPDATE', 0);
            """,
            (self.citizen1_id,),
            db_path=self.temp_db_path
        )

        # Check unread count
        unreads = fetch_one("SELECT COUNT(*) as cnt FROM Notifications WHERE user_id = ? AND is_read = 0;", (self.citizen1_id,), db_path=self.temp_db_path)
        self.assertEqual(unreads["cnt"], 1)

        # Mark notification as read
        execute_query("UPDATE Notifications SET is_read = 1 WHERE user_id = ?;", (self.citizen1_id,), db_path=self.temp_db_path)
        unreads_after = fetch_one("SELECT COUNT(*) as cnt FROM Notifications WHERE user_id = ? AND is_read = 0;", (self.citizen1_id,), db_path=self.temp_db_path)
        self.assertEqual(unreads_after["cnt"], 0)

        # User scoping: Citizen 2 must not see Citizen 1's notifications
        cit2_notifs = fetch_all("SELECT * FROM Notifications WHERE user_id = ?;", (self.citizen2_id,), db_path=self.temp_db_path)
        self.assertEqual(len(cit2_notifs), 0)

    def test_04_sql_injection_resilience(self):
        """
        Validates that SQL injection attempts in titles, searches, and filters
        are neutralized by parameterized queries and treated strictly as strings.
        """
        malicious_inputs = [
            "' OR '1'='1",
            "'; DROP TABLE Users; --",
            "admin'--",
            "1 UNION SELECT username, password_hash, salt, role FROM Users --"
        ]

        for payload in malicious_inputs:
            # 1. Search Query Test
            results = self.admin_ctrl.fetch_all_complaints(search_query=payload)
            self.assertIsInstance(results, list)

            # 2. Complaint Submission with SQL injection title & description
            ok, code, comp_id, _ = create_complaint(
                citizen_id=self.citizen1_id,
                title=f"Road issue {payload}",
                description=f"Hazard description containing SQL payload: {payload}",
                category="Road damage / pothole",
                location="Main Road",
                locality="Indiranagar",
                db_path=self.temp_db_path
            )
            self.assertTrue(ok)

            # Verify database table is completely intact
            users = fetch_all("SELECT id FROM Users;", db_path=self.temp_db_path)
            self.assertGreaterEqual(len(users), 4)

    def test_05_password_security_and_pbkdf2_invariants(self):
        """
        Validates PBKDF2-HMAC-SHA256 salted password generation,
        unique salt per hashing, and verification.
        """
        pwd = "TestUserPassword99!"
        h1, s1 = hash_password(pwd)
        h2, s2 = hash_password(pwd)

        # Distinct salts generated every time
        self.assertNotEqual(s1, s2)
        self.assertNotEqual(h1, h2)

        # Correct password verifies
        self.assertTrue(verify_password(pwd, h1, s1))
        self.assertTrue(verify_password(pwd, h2, s2))

        # Incorrect password fails
        self.assertFalse(verify_password("WrongPassword!", h1, s1))

    def test_06_input_validation_rules(self):
        """Validates phone number, email, and password format rules."""
        # Valid Phone
        self.assertTrue(validate_phone("9876543210")[0])
        # Invalid Phone (< 10 digits or alphabets)
        self.assertFalse(validate_phone("12345")[0])
        self.assertFalse(validate_phone("98765abcde")[0])

        # Valid Email
        self.assertTrue(validate_email("citizen@example.com")[0])
        # Invalid Email
        self.assertFalse(validate_email("notanemail")[0])
        self.assertFalse(validate_email("missing@domain")[0])

        # Valid Password (>= 8 chars with letter and number)
        self.assertTrue(validate_password_strength("PassWord123")[0])
        # Invalid Password (< 8 chars)
        self.assertFalse(validate_password_strength("123")[0])
        # Invalid Password (no digits)
        self.assertFalse(validate_password_strength("onlyletters")[0])

    def test_07_full_database_health_and_foreign_keys(self):
        """Runs the PRAGMA database health inspection on the test database."""
        report = verify_database_health(self.temp_db_path)
        self.assertEqual(report["integrity_check"], "ok")
        self.assertEqual(len(report["foreign_key_violations"]), 0)
        self.assertEqual(len(report["missing_tables"]), 0)
        self.assertEqual(len(report["missing_indexes"]), 0)
        self.assertEqual(len(report["consistency_issues"]), 0)
        self.assertTrue(report["passed"])


if __name__ == "__main__":
    unittest.main()
