"""
CivicFix Database Test Suite
Validates schema creation, foreign key enforcement, check constraints,
indexes, transaction rollback, and atomic status recording.
"""

import os
import sys
import tempfile
import sqlite3
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import get_connection
from database.schema import init_db, get_table_names
from database.database_operations import (
    execute_query,
    fetch_one,
    fetch_all,
    execute_transaction,
    record_status_change,
    record_admin_action,
    get_table_counts
)


class TestDatabaseSchemaAndOperations(unittest.TestCase):
    def setUp(self):
        """Create a temporary SQLite database for isolated testing."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        """Close and remove the temporary test database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_all_14_tables_created(self):
        """Ensure all 14 core tables exist in the database."""
        expected_tables = {
            "Users", "CitizenProfiles", "WorkerProfiles", "Complaints",
            "ComplaintImages", "WorkerAssignments", "ComplaintStatusHistory",
            "WorkerProgressUpdates", "Feedback", "ComplaintSupports",
            "AdminActionHistory", "WorkChecklistItems", "MaterialRequirements",
            "Notifications"
        }
        existing_tables = set(get_table_names(self.temp_db_path))
        self.assertTrue(expected_tables.issubset(existing_tables), 
                        f"Missing tables: {expected_tables - existing_tables}")

    def test_idempotent_initialization(self):
        """Ensure init_db can be safely called multiple times without error."""
        # Insert a sample user
        user_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("testuser", "test@civicfix.org", "dummyhash", "dummysalt", "CITIZEN"),
            db_path=self.temp_db_path
        )
        self.assertGreater(user_id, 0)

        # Re-run init_db
        success = init_db(self.temp_db_path)
        self.assertTrue(success)

        # Verify the user still exists intact
        user = fetch_one("SELECT * FROM Users WHERE id = ?;", (user_id,), db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "testuser")

    def test_foreign_key_enforcement(self):
        """Verify that foreign key violations raise an IntegrityError."""
        # Trying to insert a citizen profile with non-existent user_id 9999
        with self.assertRaises(sqlite3.IntegrityError):
            execute_query(
                "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
                (9999, "Ghost User", "1234567890", "Downtown"),
                db_path=self.temp_db_path
            )

    def test_role_check_constraint(self):
        """Verify that invalid user roles are rejected."""
        with self.assertRaises(sqlite3.IntegrityError):
            execute_query(
                "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
                ("baduser", "bad@civicfix.org", "hash", "salt", "SUPERUSER"),
                db_path=self.temp_db_path
            )

    def test_rating_check_constraint(self):
        """Verify that feedback ratings must be between 1 and 5."""
        user_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("rater", "rater@civicfix.org", "hash", "salt", "CITIZEN"),
            db_path=self.temp_db_path
        )
        complaint_id = execute_query(
            """INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality)
               VALUES (?, ?, ?, ?, ?, ?, ?);""",
            ("CFX-2026-000001", user_id, "Pothole", "Big hole", "Road damage / pothole", "1st Main", "Central"),
            db_path=self.temp_db_path
        )

        # Rating 0 should fail
        with self.assertRaises(sqlite3.IntegrityError):
            execute_query(
                "INSERT INTO Feedback (complaint_id, citizen_id, rating) VALUES (?, ?, ?);",
                (complaint_id, user_id, 0),
                db_path=self.temp_db_path
            )

        # Rating 6 should fail
        with self.assertRaises(sqlite3.IntegrityError):
            execute_query(
                "INSERT INTO Feedback (complaint_id, citizen_id, rating) VALUES (?, ?, ?);",
                (complaint_id, user_id, 6),
                db_path=self.temp_db_path
            )

        # Rating 5 should succeed
        feedback_id = execute_query(
            "INSERT INTO Feedback (complaint_id, citizen_id, rating, comments) VALUES (?, ?, ?, ?);",
            (complaint_id, user_id, 5, "Great work!"),
            db_path=self.temp_db_path
        )
        self.assertGreater(feedback_id, 0)

    def test_status_history_atomic_recording(self):
        """Verify that status updates record history atomically."""
        admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("admin", "admin@civicfix.org", "hash", "salt", "ADMIN"),
            db_path=self.temp_db_path
        )
        citizen_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("cit", "cit@civicfix.org", "hash", "salt", "CITIZEN"),
            db_path=self.temp_db_path
        )
        cid = execute_query(
            """INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            ("CFX-2026-000002", citizen_id, "Light out", "Broken pole", "Broken streetlight", "2nd Cross", "West", "NEW"),
            db_path=self.temp_db_path
        )

        # Transition NEW -> VERIFIED
        success = record_status_change(
            complaint_id=cid,
            previous_status="NEW",
            new_status="VERIFIED",
            changed_by_user_id=admin_id,
            remarks="Verified by Admin",
            db_path=self.temp_db_path
        )
        self.assertTrue(success)

        # Check Complaint table updated
        comp = fetch_one("SELECT status, verified_at FROM Complaints WHERE id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "VERIFIED")
        self.assertIsNotNone(comp["verified_at"])

        # Check ComplaintStatusHistory has record
        history = fetch_all("SELECT * FROM ComplaintStatusHistory WHERE complaint_id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["previous_status"], "NEW")
        self.assertEqual(history[0]["new_status"], "VERIFIED")
        self.assertEqual(history[0]["changed_by"], admin_id)

    def test_transaction_rollback_on_failure(self):
        """Verify atomic rollback if any query in a batch fails."""
        user_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("txuser", "tx@civicfix.org", "hash", "salt", "CITIZEN"),
            db_path=self.temp_db_path
        )

        batch = [
            ("INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
             (user_id, "TX Valid Name", "9876543210", "North Zone")),
            # Deliberate failure: user_id 99999 does not exist (FK violation)
            ("INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
             (99999, "Invalid User", "0000000000", "Nowhere"))
        ]

        with self.assertRaises(sqlite3.IntegrityError):
            execute_transaction(batch, db_path=self.temp_db_path)

        # Verify that TX Valid Name was rolled back and never committed
        profile = fetch_one("SELECT * FROM CitizenProfiles WHERE user_id = ?;", (user_id,), db_path=self.temp_db_path)
        self.assertIsNone(profile)


if __name__ == "__main__":
    unittest.main()
