"""
CivicFix Database Integrity, Cascades & Query Optimization Test Suite
Validates PRAGMA integrity, foreign key cascades, check constraints,
index usage via EXPLAIN QUERY PLAN, and cross-module referential integrity.
"""

import os
import sys
import tempfile
import sqlite3
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import get_connection, DB_PATH
from database.schema import init_db, get_table_names
from database.database_operations import execute_query, fetch_one, fetch_all
from scripts.verify_database import verify_database_health, EXPECTED_TABLES, EXPECTED_INDEXES


class TestDatabaseIntegrity(unittest.TestCase):
    def setUp(self):
        """Create an isolated test database with FKs enabled."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        """Clean up test database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_live_production_database_health(self):
        """Validates that civicfix.db passes PRAGMA checks and has zero FK violations."""
        if os.path.exists(DB_PATH):
            report = verify_database_health(DB_PATH)
            self.assertEqual(report["integrity_check"], "ok")
            self.assertEqual(len(report["foreign_key_violations"]), 0)
            self.assertEqual(len(report["missing_tables"]), 0)
            self.assertEqual(len(report["missing_indexes"]), 0)
            self.assertEqual(len(report["consistency_issues"]), 0)
            self.assertTrue(report["passed"])

    def test_schema_completeness(self):
        """All 14 tables and 17 performance indexes must exist."""
        existing_tables = set(get_table_names(self.temp_db_path))
        for t in EXPECTED_TABLES:
            self.assertIn(t, existing_tables, f"Missing table: {t}")

        conn = get_connection(self.temp_db_path)
        try:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
            existing_indexes = set(r[0] for r in cur.fetchall())
            for idx in EXPECTED_INDEXES:
                self.assertIn(idx, existing_indexes, f"Missing index: {idx}")
        finally:
            conn.close()

    def test_foreign_key_constraint_enforcement(self):
        """Inserting invalid foreign keys must raise sqlite3.IntegrityError."""
        conn = get_connection(self.temp_db_path)
        cur = conn.cursor()
        try:
            # Non-existent citizen_id (99999)
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute("""
                    INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality)
                    VALUES ('CFX-9999', 99999, 'Test Title', 'Test description min 10 chars', 'Road damage / pothole', 'Loc', 'Indiranagar');
                """)
        finally:
            conn.close()

    def test_check_constraints(self):
        """Database check constraints must reject invalid enum values."""
        conn = get_connection(self.temp_db_path)
        cur = conn.cursor()
        try:
            # 1. Invalid User Role
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('bad', 'bad@t.org', 'h', 's', 'SUPERUSER');")

            # Create valid user & citizen
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('cit_ok', 'cit@t.org', 'h', 's', 'CITIZEN');")
            uid = cur.lastrowid

            # 2. Invalid Priority
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute(f"INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality, priority) VALUES ('CFX-1', {uid}, 'Title', 'Description here', 'Road damage / pothole', 'L', 'Ind', 'SUPER_URGENT');")

            # 3. Invalid Status
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute(f"INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality, status) VALUES ('CFX-2', {uid}, 'Title', 'Description here', 'Road damage / pothole', 'L', 'Ind', 'DELETED');")

            # Create valid complaint
            cur.execute(f"INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality) VALUES ('CFX-3', {uid}, 'Title', 'Description here', 'Road damage / pothole', 'L', 'Ind');")
            cid = cur.lastrowid

            # 4. Invalid Rating (< 1 or > 5)
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute(f"INSERT INTO Feedback (complaint_id, citizen_id, rating) VALUES ({cid}, {uid}, 6);")
            with self.assertRaises(sqlite3.IntegrityError):
                cur.execute(f"INSERT INTO Feedback (complaint_id, citizen_id, rating) VALUES ({cid}, {uid}, 0);")
        finally:
            conn.close()

    def test_cascade_delete_complaint(self):
        """Deleting a complaint must automatically cascade and delete all associated records."""
        conn = get_connection(self.temp_db_path)
        cur = conn.cursor()
        try:
            # Setup Citizen & Worker
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('c1', 'c1@t.org', 'h', 's', 'CITIZEN');")
            cit_id = cur.lastrowid
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('w1', 'w1@t.org', 'h', 's', 'WORKER');")
            w_id = cur.lastrowid
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('a1', 'a1@t.org', 'h', 's', 'ADMIN');")
            adm_id = cur.lastrowid

            # Complaint
            cur.execute(f"INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality) VALUES ('CFX-DEL-1', {cit_id}, 'To Delete', 'Description min 10 chars', 'Road damage / pothole', 'L', 'Ind');")
            comp_id = cur.lastrowid

            # Associated items
            cur.execute(f"INSERT INTO ComplaintImages (complaint_id, image_path, image_type) VALUES ({comp_id}, 'uploads/t.jpg', 'EVIDENCE');")
            cur.execute(f"INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by) VALUES ({comp_id}, {w_id}, {adm_id});")
            asgn_id = cur.lastrowid
            cur.execute(f"INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by) VALUES ({comp_id}, 'NEW', 'ASSIGNED', {adm_id});")
            cur.execute(f"INSERT INTO WorkerProgressUpdates (assignment_id, complaint_id, worker_id, progress_notes, status_snapshot) VALUES ({asgn_id}, {comp_id}, {w_id}, 'Working', 'IN_PROGRESS');")
            cur.execute(f"INSERT INTO Feedback (complaint_id, citizen_id, rating) VALUES ({comp_id}, {cit_id}, 5);")
            cur.execute(f"INSERT INTO ComplaintSupports (complaint_id, citizen_id) VALUES ({comp_id}, {cit_id});")
            cur.execute(f"INSERT INTO WorkChecklistItems (assignment_id, complaint_id, item_text) VALUES ({asgn_id}, {comp_id}, 'Task 1');")
            cur.execute(f"INSERT INTO MaterialRequirements (assignment_id, complaint_id, item_name, quantity) VALUES ({asgn_id}, {comp_id}, 'Asphalt', '1 Bag');")
            cur.execute(f"INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type) VALUES ({cit_id}, {comp_id}, 'T', 'M', 'STATUS');")
            conn.commit()

            # Verify presence
            cur.execute("SELECT COUNT(*) FROM ComplaintImages WHERE complaint_id = ?;", (comp_id,))
            self.assertEqual(cur.fetchone()[0], 1)
            cur.execute("SELECT COUNT(*) FROM WorkerAssignments WHERE complaint_id = ?;", (comp_id,))
            self.assertEqual(cur.fetchone()[0], 1)

            # DELETE COMPLAINT
            cur.execute("DELETE FROM Complaints WHERE id = ?;", (comp_id,))
            conn.commit()

            # Verify complete cascading deletion across all dependent tables
            for tbl in ["ComplaintImages", "WorkerAssignments", "ComplaintStatusHistory",
                        "WorkerProgressUpdates", "Feedback", "ComplaintSupports",
                        "WorkChecklistItems", "MaterialRequirements", "Notifications"]:
                cur.execute(f"SELECT COUNT(*) FROM {tbl} WHERE complaint_id = ?;", (comp_id,))
                cnt = cur.fetchone()[0]
                self.assertEqual(cnt, 0, f"Cascade delete failed for table: {tbl}")

        finally:
            conn.close()

    def test_cascade_delete_user(self):
        """Deleting a user cascades and deletes their profile and citizen complaints."""
        conn = get_connection(self.temp_db_path)
        cur = conn.cursor()
        try:
            # 1. Citizen User
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('del_cit', 'del_cit@t.org', 'h', 's', 'CITIZEN');")
            cit_id = cur.lastrowid
            cur.execute(f"INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES ({cit_id}, 'Delete Me', '9999999999', 'Indiranagar');")
            cur.execute(f"INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality) VALUES ('CFX-CIT-DEL', {cit_id}, 'Pothole', 'Description min 10 chars', 'Road damage / pothole', 'L', 'Ind');")
            conn.commit()

            # Verify existence
            cur.execute("SELECT COUNT(*) FROM CitizenProfiles WHERE user_id = ?;", (cit_id,))
            self.assertEqual(cur.fetchone()[0], 1)
            cur.execute("SELECT COUNT(*) FROM Complaints WHERE citizen_id = ?;", (cit_id,))
            self.assertEqual(cur.fetchone()[0], 1)

            # Delete Citizen User
            cur.execute("DELETE FROM Users WHERE id = ?;", (cit_id,))
            conn.commit()

            # Profile and Complaints must be gone via ON DELETE CASCADE
            cur.execute("SELECT COUNT(*) FROM CitizenProfiles WHERE user_id = ?;", (cit_id,))
            self.assertEqual(cur.fetchone()[0], 0)
            cur.execute("SELECT COUNT(*) FROM Complaints WHERE citizen_id = ?;", (cit_id,))
            self.assertEqual(cur.fetchone()[0], 0)

            # 2. Worker User
            cur.execute("INSERT INTO Users (username, email, password_hash, salt, role) VALUES ('del_wrk', 'del_wrk@t.org', 'h', 's', 'WORKER');")
            w_id = cur.lastrowid
            cur.execute(f"INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES ({w_id}, 'Worker Del', '9999999998', 'Roads', 'General');")
            conn.commit()

            cur.execute("DELETE FROM Users WHERE id = ?;", (w_id,))
            conn.commit()
            cur.execute("SELECT COUNT(*) FROM WorkerProfiles WHERE user_id = ?;", (w_id,))
            self.assertEqual(cur.fetchone()[0], 0)
        finally:
            conn.close()

    def test_query_plan_uses_indexes(self):
        """Verifies that EXPLAIN QUERY PLAN uses indexes for critical performance queries."""
        conn = get_connection(self.temp_db_path)
        cur = conn.cursor()
        try:
            # Query 1: Filter complaints by status
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM Complaints WHERE status = 'ASSIGNED';")
            plan1 = " ".join(r[3] for r in cur.fetchall())
            self.assertIn("idx_complaints_status", plan1)

            # Query 2: Filter complaints by citizen_id
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM Complaints WHERE citizen_id = 1;")
            plan2 = " ".join(r[3] for r in cur.fetchall())
            self.assertIn("idx_complaints_citizen", plan2)

            # Query 3: Filter assignments by worker_id
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM WorkerAssignments WHERE worker_id = 1;")
            plan3 = " ".join(r[3] for r in cur.fetchall())
            self.assertIn("idx_assignments_worker", plan3)

            # Query 4: Status History by complaint_id
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM ComplaintStatusHistory WHERE complaint_id = 1;")
            plan4 = " ".join(r[3] for r in cur.fetchall())
            self.assertIn("idx_status_history_complaint", plan4)

            # Query 5: Unread notifications
            cur.execute("EXPLAIN QUERY PLAN SELECT * FROM Notifications WHERE user_id = 1 AND is_read = 0;")
            plan5 = " ".join(r[3] for r in cur.fetchall())
            self.assertIn("idx_notifications_user_unread", plan5)
        finally:
            conn.close()


if __name__ == "__main__":
    unittest.main()
