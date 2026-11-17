"""
CivicFix Authentication & Security Test Suite
Tests PBKDF2 password hashing, salt uniqueness, password strength validation,
citizen registration, duplicate detection, authentication via username/email,
role verification, and session state.
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import fetch_one, execute_update
from authentication.password_manager import (
    hash_password,
    verify_password,
    validate_password_strength
)
from authentication.auth import (
    register_citizen,
    create_worker_account,
    create_admin_account,
    authenticate,
    UserSession
)


class TestAuthenticationAndSecurity(unittest.TestCase):
    def setUp(self):
        """Create a fresh temporary database for each test run."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

    def tearDown(self):
        """Clean up the temporary database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_password_hashing_and_verification(self):
        """Verify PBKDF2 password hashing produces valid salts and verifies accurately."""
        password = "SecurePassword@123"
        pwd_hash, salt = hash_password(password)

        self.assertIsNotNone(pwd_hash)
        self.assertIsNotNone(salt)
        self.assertEqual(len(salt), 64)  # 32 bytes hex = 64 hex chars

        # Valid password verifies
        self.assertTrue(verify_password(password, pwd_hash, salt))

        # Wrong password fails
        self.assertFalse(verify_password("WrongPassword@123", pwd_hash, salt))
        self.assertFalse(verify_password("", pwd_hash, salt))

    def test_password_salt_uniqueness(self):
        """Verify that identical passwords produce distinct hashes due to random salting."""
        p = "CommonPassword1"
        hash1, salt1 = hash_password(p)
        hash2, salt2 = hash_password(p)

        self.assertNotEqual(salt1, salt2)
        self.assertNotEqual(hash1, hash2)

    def test_password_strength_validation(self):
        """Test password strength criteria: length >= 8, mixed letters and digits."""
        # Too short
        ok, msg = validate_password_strength("Short1")
        self.assertFalse(ok)

        # Only letters
        ok, msg = validate_password_strength("AllLettersOnly")
        self.assertFalse(ok)

        # Only digits
        ok, msg = validate_password_strength("1234567890")
        self.assertFalse(ok)

        # Valid
        ok, msg = validate_password_strength("ValidPass123")
        self.assertTrue(ok)

    def test_citizen_registration_success(self):
        """Test successful citizen registration creates both User and CitizenProfile."""
        ok, user_id, msg = register_citizen(
            full_name="John Doe",
            email="john.doe@example.com",
            phone="9876543210",
            username="johndoe",
            password="Password123",
            confirm_password="Password123",
            address="123 Oak St",
            locality="Central District",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)
        self.assertIsNotNone(user_id)

        # Check User record in database
        user = fetch_one("SELECT * FROM Users WHERE id = ?;", (user_id,), db_path=self.temp_db_path)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "johndoe")
        self.assertEqual(user["role"], "CITIZEN")

        # Check CitizenProfile record
        profile = fetch_one("SELECT * FROM CitizenProfiles WHERE user_id = ?;", (user_id,), db_path=self.temp_db_path)
        self.assertIsNotNone(profile)
        self.assertEqual(profile["full_name"], "John Doe")
        self.assertEqual(profile["locality"], "Central District")

    def test_duplicate_registration_rejected(self):
        """Ensure duplicate usernames and duplicate emails are blocked."""
        register_citizen(
            full_name="First User",
            email="unique@example.com",
            phone="9876543210",
            username="uniqueuser",
            password="Password123",
            confirm_password="Password123",
            address="Addr",
            locality="Loc",
            db_path=self.temp_db_path
        )

        # Attempt duplicate username
        ok, uid, msg = register_citizen(
            full_name="Second User",
            email="other@example.com",
            phone="9876543211",
            username="uniqueuser",
            password="Password123",
            confirm_password="Password123",
            address="Addr",
            locality="Loc",
            db_path=self.temp_db_path
        )
        self.assertFalse(ok)
        self.assertIn("already taken", msg)

        # Attempt duplicate email
        ok, uid, msg = register_citizen(
            full_name="Third User",
            email="unique@example.com",
            phone="9876543212",
            username="anotheruser",
            password="Password123",
            confirm_password="Password123",
            address="Addr",
            locality="Loc",
            db_path=self.temp_db_path
        )
        self.assertFalse(ok)
        self.assertIn("already registered", msg)

    def test_authentication_with_username_and_email(self):
        """Test authentication succeeds with both username and email, case-insensitively."""
        register_citizen(
            full_name="Alice Smith",
            email="alice@example.com",
            phone="9876543210",
            username="alicesmith",
            password="Password123",
            confirm_password="Password123",
            address="456 Elm St",
            locality="North Zone",
            db_path=self.temp_db_path
        )

        # Authenticate with username
        ok, user, profile, _ = authenticate("AliceSmith", "Password123", db_path=self.temp_db_path)
        self.assertTrue(ok)
        self.assertEqual(user["username"], "alicesmith")
        self.assertEqual(profile["full_name"], "Alice Smith")

        # Authenticate with email
        ok, user, profile, _ = authenticate("ALICE@EXAMPLE.COM", "Password123", db_path=self.temp_db_path)
        self.assertTrue(ok)
        self.assertEqual(user["email"], "alice@example.com")

        # Authenticate with wrong password
        ok, user, profile, msg = authenticate("alicesmith", "WrongPassword123", db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("Invalid", msg)

    def test_deactivated_account_cannot_login(self):
        """Test that deactivated accounts are prevented from logging in."""
        ok, uid, _ = register_citizen(
            full_name="Bob Brown",
            email="bob@example.com",
            phone="9876543210",
            username="bobbrown",
            password="Password123",
            confirm_password="Password123",
            address="789 Pine St",
            locality="South Zone",
            db_path=self.temp_db_path
        )

        # Deactivate user
        execute_update("UPDATE Users SET is_active = 0 WHERE id = ?;", (uid,), db_path=self.temp_db_path)

        ok, user, profile, msg = authenticate("bobbrown", "Password123", db_path=self.temp_db_path)
        self.assertFalse(ok)
        self.assertIn("deactivated", msg)

    def test_worker_account_creation_by_admin(self):
        """Test admin provisioning of field worker accounts with department and specialization."""
        # Create admin
        ok, admin_id, _ = create_admin_account(
            full_name="Admin Chief",
            email="admin@civicfix.org",
            username="sysadmin",
            password="AdminPassword123",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)

        # Admin creates field worker
        ok, worker_id, _ = create_worker_account(
            admin_id=admin_id,
            full_name="Worker Dave",
            email="dave@civicfix.org",
            phone="9876543299",
            username="workerdave",
            password="WorkerPassword123",
            department="Sanitation",
            specialization="Waste Collection & Logistics",
            db_path=self.temp_db_path
        )
        self.assertTrue(ok)

        # Verify WorkerProfile
        w_profile = fetch_one("SELECT * FROM WorkerProfiles WHERE user_id = ?;", (worker_id,), db_path=self.temp_db_path)
        self.assertIsNotNone(w_profile)
        self.assertEqual(w_profile["department"], "Sanitation")
        self.assertEqual(w_profile["specialization"], "Waste Collection & Logistics")

    def test_session_state_lifecycle(self):
        """Test UserSession object management."""
        session = UserSession()
        self.assertFalse(session.is_logged_in)

        user_data = {"id": 10, "username": "admin", "email": "admin@civicfix.org", "role": "ADMIN"}
        session.login(user_data, {"full_name": "Admin User"})

        self.assertTrue(session.is_logged_in)
        self.assertTrue(session.is_admin)
        self.assertFalse(session.is_citizen)
        self.assertFalse(session.is_worker)
        self.assertEqual(session.username, "admin")

        session.logout()
        self.assertFalse(session.is_logged_in)
        self.assertIsNone(session.username)


if __name__ == "__main__":
    unittest.main()
