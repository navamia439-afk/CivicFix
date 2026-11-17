"""
CivicFix Citizen & Complaint Test Suite
Tests unique CFX ID generation, complaint submission, validation checks,
citizen-scoped data access, emergency priority, duplicate support prevention,
reopening lifecycle, and star rating feedback.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, execute_update
from services.complaint_service import (
    create_complaint,
    get_citizen_complaints,
    get_complaint_details,
    get_complaint_timeline,
    support_complaint,
    has_supported_complaint,
    reopen_complaint,
    submit_feedback,
    get_citizen_stats,
    CATEGORIES
)
from utils.complaint_id import generate_complaint_id


class TestComplaintServiceAndCitizenModule(unittest.TestCase):
    def setUp(self):
        """Create an isolated test database with two citizens."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # Create Citizen 1
        self.c1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("cit1", "cit1@civicfix.org", "hash", "salt", "CITIZEN"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.c1_id, "Citizen One", "9876543210", "Indiranagar"),
            db_path=self.temp_db_path
        )

        # Create Citizen 2
        self.c2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, ?);",
            ("cit2", "cit2@civicfix.org", "hash", "salt", "CITIZEN"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality) VALUES (?, ?, ?, ?);",
            (self.c2_id, "Citizen Two", "9876543211", "Koramangala"),
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

    def test_complaint_id_formatting(self):
        """Verify complaint IDs follow CFX-YYYY-000001 sequential pattern."""
        id1 = generate_complaint_id(db_path=self.temp_db_path)
        self.assertTrue(id1.startswith("CFX-"))
        self.assertTrue(id1.endswith("-000001"))

        # Insert a complaint with id1
        execute_query(
            """INSERT INTO Complaints (complaint_id, citizen_id, title, description, category, location, locality)
               VALUES (?, ?, ?, ?, ?, ?, ?);""",
            (id1, self.c1_id, "Pothole", "A deep road hole", "Road damage / pothole", "Main St", "Indiranagar"),
            db_path=self.temp_db_path
        )

        # Next generated ID must be 000002
        id2 = generate_complaint_id(db_path=self.temp_db_path)
        self.assertTrue(id2.endswith("-000002"))

    def test_complaint_submission_success(self):
        """Verify successful complaint creation with status NEW and history log."""
        ok, code, db_id, msg = create_complaint(
            citizen_id=self.c1_id,
            title="Dangerous Open Manhole",
            description="Deep manhole cover is missing creating acute risk for pedestrians.",
            category="Drainage blockage",
            location="Near Metro Pillar 12",
            locality="Indiranagar",
            ward_number="Ward 74",
            is_emergency=True,
            is_anonymous=False,
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)
        self.assertIsNotNone(code)
        self.assertIsNotNone(db_id)

        # Verify Complaints table record
        comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (db_id,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "NEW")
        self.assertEqual(comp["priority"], "EMERGENCY")
        self.assertEqual(comp["is_emergency"], 1)

        # Verify Status History log
        history = get_complaint_timeline(db_id, db_path=self.temp_db_path)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["new_status"], "NEW")

    def test_validation_rejects_empty_fields(self):
        """Verify validation prevents short titles and descriptions."""
        # Short title (<5 chars)
        ok, code, _, msg = create_complaint(
            citizen_id=self.c1_id,
            title="Bad",
            description="Valid long description exceeding 10 characters.",
            category="Road damage / pothole",
            location="Loc",
            locality="Area",
            db_path=self.temp_db_path
        )
        self.assertFalse(ok)
        self.assertIn("at least 5 characters", msg)

        # Short description (<10 chars)
        ok, code, _, msg = create_complaint(
            citizen_id=self.c1_id,
            title="Valid Issue Title",
            description="Too short",
            category="Road damage / pothole",
            location="Loc",
            locality="Area",
            db_path=self.temp_db_path
        )
        self.assertFalse(ok)
        self.assertIn("at least 10 characters", msg)

    def test_citizen_privacy_and_scoped_listing(self):
        """Verify citizens can only see their own complaints in personal list."""
        create_complaint(self.c1_id, "Issue 1 by C1", "Description for issue 1", "Road damage / pothole", "St 1", "Indiranagar", db_path=self.temp_db_path)
        create_complaint(self.c2_id, "Issue 2 by C2", "Description for issue 2", "Broken streetlight", "St 2", "Koramangala", db_path=self.temp_db_path)

        c1_list = get_citizen_complaints(self.c1_id, db_path=self.temp_db_path)
        c2_list = get_citizen_complaints(self.c2_id, db_path=self.temp_db_path)

        self.assertEqual(len(c1_list), 1)
        self.assertEqual(c1_list[0]["title"], "Issue 1 by C1")

        self.assertEqual(len(c2_list), 1)
        self.assertEqual(c2_list[0]["title"], "Issue 2 by C2")

    def test_support_existing_issue_and_duplicate_prevention(self):
        """Test 'I Also Face This Issue' functionality and prevent multi-support."""
        ok, code, cid, _ = create_complaint(
            self.c1_id, "Broken Streetlight #4", "Flickering and sparking in rain.",
            "Broken streetlight", "Main Junction", "Koramangala", db_path=self.temp_db_path
        )

        # Citizen 2 supports the issue
        ok_sup, cnt, msg = support_complaint(cid, self.c2_id, db_path=self.temp_db_path)
        self.assertTrue(ok_sup)
        self.assertEqual(cnt, 1)

        # Citizen 2 attempts to support again
        ok_sup2, cnt2, msg2 = support_complaint(cid, self.c2_id, db_path=self.temp_db_path)
        self.assertFalse(ok_sup2)
        self.assertIn("already supported", msg2)

    def test_feedback_rating_lifecycle(self):
        """Test citizen rating is only allowed once complaint is resolved."""
        ok, code, cid, _ = create_complaint(
            self.c1_id, "Garbage Piles", "Garbage left uncollected for a week.",
            "Garbage / waste issue", "Park Gate", "Indiranagar", db_path=self.temp_db_path
        )

        # Attempt to rate while status is NEW (should fail)
        ok_fb, msg_fb = submit_feedback(cid, self.c1_id, rating=5, comments="Good", db_path=self.temp_db_path)
        self.assertFalse(ok_fb)
        self.assertIn("after the complaint is resolved", msg_fb)

        # Move status to RESOLVED
        execute_update("UPDATE Complaints SET status = 'RESOLVED' WHERE id = ?;", (cid,), db_path=self.temp_db_path)

        # Now rating should succeed
        ok_fb2, msg_fb2 = submit_feedback(cid, self.c1_id, rating=5, comments="Spotless clean!", db_path=self.temp_db_path)
        self.assertTrue(ok_fb2)

    def test_reopen_complaint_lifecycle(self):
        """Test reopening a resolved issue with reason recording."""
        ok, code, cid, _ = create_complaint(
            self.c1_id, "Water Pipe Leak", "Pavement water leak.",
            "Water leakage", "Corner Plot", "Indiranagar", db_path=self.temp_db_path
        )

        # Cannot reopen a NEW complaint
        ok_ro, msg_ro = reopen_complaint(cid, self.c1_id, "Still leaking", db_path=self.temp_db_path)
        self.assertFalse(ok_ro)

        # Resolve the complaint
        execute_update("UPDATE Complaints SET status = 'RESOLVED' WHERE id = ?;", (cid,), db_path=self.temp_db_path)

        # Reopen with valid explanation
        ok_ro2, msg_ro2 = reopen_complaint(
            cid, self.c1_id,
            "The pipe burst again under high pressure water supply.",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok_ro2)

        # Verify complaint status is now REOPENED
        comp = fetch_one("SELECT status, reopen_reason FROM Complaints WHERE id = ?;", (cid,), db_path=self.temp_db_path)
        self.assertEqual(comp["status"], "REOPENED")
        self.assertIn("pipe burst again", comp["reopen_reason"])


if __name__ == "__main__":
    unittest.main()
