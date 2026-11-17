"""
CivicFix Authentication and Session Management Service
Handles citizen registration, administrative worker account provisioning,
credential verification, and role-based session state.
"""

from typing import Tuple, Optional, Dict, Any
from database.db_connection import get_db, DB_PATH
from database.database_operations import fetch_one, execute_query, record_admin_action, create_notification
from authentication.password_manager import hash_password, verify_password, validate_password_strength
from utils.validators import (
    sanitize_text,
    validate_username,
    validate_email,
    validate_phone,
    validate_citizen_registration
)


class UserSession:
    """Represents the active user session in the application."""

    def __init__(self):
        self._user_id: Optional[int] = None
        self._username: Optional[str] = None
        self._email: Optional[str] = None
        self._role: Optional[str] = None
        self._profile: Dict[str, Any] = {}

    def login(self, user_data: Dict[str, Any], profile_data: Optional[Dict[str, Any]] = None):
        """Sets the active user session upon successful authentication."""
        self._user_id = user_data["id"]
        self._username = user_data["username"]
        self._email = user_data["email"]
        self._role = user_data["role"]
        self._profile = profile_data or {}

    def logout(self):
        """Clears the active session securely."""
        self._user_id = None
        self._username = None
        self._email = None
        self._role = None
        self._profile = {}

    @property
    def is_logged_in(self) -> bool:
        return self._user_id is not None

    @property
    def user_id(self) -> Optional[int]:
        return self._user_id

    @property
    def username(self) -> Optional[str]:
        return self._username

    @property
    def email(self) -> Optional[str]:
        return self._email

    @property
    def role(self) -> Optional[str]:
        return self._role

    @property
    def profile(self) -> Dict[str, Any]:
        return self._profile

    @property
    def is_admin(self) -> bool:
        return self._role == "ADMIN"

    @property
    def is_worker(self) -> bool:
        return self._role == "WORKER"

    @property
    def is_citizen(self) -> bool:
        return self._role == "CITIZEN"


# Global session singleton
current_session = UserSession()


def authenticate(
    identifier: str,
    password: str,
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[Dict[str, Any]], str]:
    """
    Authenticates a user via either their username or email address.
    
    Returns:
        (success, user_dict, profile_dict, message)
    """
    ident = sanitize_text(identifier)
    if not ident or not password:
        return False, None, None, "Please enter both your username/email and password."

    # Look up user by username OR email (case-insensitive)
    sql = "SELECT * FROM Users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;"
    user = fetch_one(sql, (ident, ident), db_path=db_path)

    if not user:
        return False, None, None, "Invalid username/email or password."

    if not user["is_active"]:
        return False, None, None, "This account has been deactivated. Please contact an administrator."

    # Verify PBKDF2 password hash
    is_valid = verify_password(password, user["password_hash"], user["salt"])
    if not is_valid:
        return False, None, None, "Invalid username/email or password."

    # Fetch corresponding role profile
    profile = None
    role = user["role"]
    if role == "CITIZEN":
        profile = fetch_one("SELECT * FROM CitizenProfiles WHERE user_id = ?;", (user["id"],), db_path=db_path)
    elif role == "WORKER":
        profile = fetch_one("SELECT * FROM WorkerProfiles WHERE user_id = ?;", (user["id"],), db_path=db_path)
        if profile:
            st = profile.get("approval_status", "APPROVED")
            if st == "PENDING":
                return False, None, None, "Your registration is currently waiting for administrator approval. Please check back later."
            elif st == "REJECTED":
                return False, None, None, "Your worker registration application has been rejected by the administrator. Access denied."
    elif role == "ADMIN":
        profile = {"full_name": "System Administrator", "department": "Administration"}

    return True, dict(user), profile, "Authentication successful."


def register_citizen(
    full_name: str,
    email: str,
    phone: str,
    username: str,
    password: str,
    confirm_password: str,
    address: str,
    locality: str,
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[int], str]:
    """
    Registers a new Citizen with complete validation and PBKDF2 password hashing.
    Ensures unique usernames and email addresses.
    
    Returns:
        (success, new_user_id, message)
    """
    # 1. Input Validation
    valid, err_msg = validate_citizen_registration(
        full_name, email, phone, username, password, confirm_password, locality
    )
    if not valid:
        return False, None, err_msg

    fn = sanitize_text(full_name)
    em = sanitize_text(email).lower()
    ph = sanitize_text(phone)
    un = sanitize_text(username).lower()
    addr = sanitize_text(address)
    loc = sanitize_text(locality)

    # 2. Check for duplicate username or email
    existing_user = fetch_one(
        "SELECT id, username, email FROM Users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;",
        (un, em),
        db_path=db_path
    )
    if existing_user:
        if existing_user["username"].lower() == un:
            return False, None, f"Username '{un}' is already taken. Please choose another."
        if existing_user["email"].lower() == em:
            return False, None, f"An account with email '{em}' is already registered."

    # 3. Hash Password using PBKDF2
    pwd_hash, salt = hash_password(password)

    # 4. Atomic Transaction: Insert User + Insert CitizenProfile + Welcome Notification
    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO Users (username, email, password_hash, salt, role, is_active)
                VALUES (?, ?, ?, ?, 'CITIZEN', 1);
                """,
                (un, em, pwd_hash, salt)
            )
            user_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO CitizenProfiles (user_id, full_name, phone, address, locality)
                VALUES (?, ?, ?, ?, ?);
                """,
                (user_id, fn, ph, addr, loc)
            )

            # Send welcome notification to the citizen
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, title, message, notification_type)
                VALUES (?, ?, ?, 'WELCOME');
                """,
                (user_id, "Welcome to CivicFix!",
                 f"Hello {fn}, your account has been successfully created. You can now report and track civic issues.",)
            )

        return True, user_id, "Registration successful! You may now log in."
    except Exception as exc:
        return False, None, f"Database error during registration: {exc}"


def create_worker_account(
    admin_id: int,
    full_name: str,
    email: str,
    phone: str,
    username: str,
    password: str,
    department: str,
    specialization: Optional[str] = None,
    approval_status: str = "APPROVED",
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[int], str]:
    """
    Creates a new Field Worker account. Used for demo seeding and administrative provisioning.
    """
    fn = sanitize_text(full_name)
    em = sanitize_text(email).lower()
    ph = sanitize_text(phone)
    un = sanitize_text(username).lower()
    dept = sanitize_text(department)
    spec = sanitize_text(specialization)

    if not fn or len(fn) < 2:
        return False, None, "Worker full name is required."

    ok_u, msg_u = validate_username(un)
    if not ok_u:
        return False, None, msg_u

    ok_e, msg_e = validate_email(em)
    if not ok_e:
        return False, None, msg_e

    ok_p, msg_p = validate_phone(ph)
    if not ok_p:
        return False, None, msg_p

    if not dept:
        return False, None, "Department is required."

    ok_pwd, msg_pwd = validate_password_strength(password)
    if not ok_pwd:
        return False, None, msg_pwd

    # Check for duplicates
    existing = fetch_one(
        "SELECT id, username, email FROM Users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;",
        (un, em),
        db_path=db_path
    )
    if existing:
        if existing["username"].lower() == un:
            return False, None, f"Username '{un}' is already taken."
        if existing["email"].lower() == em:
            return False, None, f"Email '{em}' is already in use."

    pwd_hash, salt = hash_password(password)

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Users (username, email, password_hash, salt, role, is_active)
                VALUES (?, ?, ?, ?, 'WORKER', 1);
                """,
                (un, em, pwd_hash, salt)
            )
            worker_user_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization, is_available, approval_status)
                VALUES (?, ?, ?, ?, ?, 1, ?);
                """,
                (worker_user_id, fn, ph, dept, spec, approval_status)
            )

            # Record in admin audit history
            cursor.execute(
                """
                INSERT INTO AdminActionHistory (admin_id, action_type, details)
                VALUES (?, 'CREATE_WORKER', ?);
                """,
                (admin_id, f"Created field worker account '{un}' ({fn}) for department '{dept}'.")
            )

        return True, worker_user_id, f"Field worker '{fn}' created successfully."
    except Exception as exc:
        return False, None, f"Database error creating worker: {exc}"


def register_field_worker(
    full_name: str,
    email: str,
    phone: str,
    username: str,
    password: str,
    confirm_password: str,
    department: str,
    specialization: Optional[str] = None,
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[int], str]:
    """
    Self-registration for Field Workers through the registration interface.
    Saves worker details into the database with initial approval_status = 'PENDING'.
    The worker account cannot log in or access worker features until approved by an administrator.
    """
    fn = sanitize_text(full_name)
    em = sanitize_text(email).lower()
    ph = sanitize_text(phone)
    un = sanitize_text(username).lower()
    dept = sanitize_text(department)
    spec = sanitize_text(specialization)

    if not fn or len(fn) < 2:
        return False, None, "Worker full name must be at least 2 characters."

    ok_u, msg_u = validate_username(un)
    if not ok_u:
        return False, None, msg_u

    ok_e, msg_e = validate_email(em)
    if not ok_e:
        return False, None, msg_e

    ok_p, msg_p = validate_phone(ph)
    if not ok_p:
        return False, None, msg_p

    if not dept:
        return False, None, "Department selection is required."

    if password != confirm_password:
        return False, None, "Passwords do not match."

    ok_pwd, msg_pwd = validate_password_strength(password)
    if not ok_pwd:
        return False, None, msg_pwd

    # Check for duplicate username or email across all Users
    existing = fetch_one(
        "SELECT id, username, email FROM Users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;",
        (un, em),
        db_path=db_path
    )
    if existing:
        if existing["username"].lower() == un:
            return False, None, f"Username '{un}' is already taken. Please choose another."
        if existing["email"].lower() == em:
            return False, None, f"An account with email '{em}' is already registered."

    pwd_hash, salt = hash_password(password)

    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO Users (username, email, password_hash, salt, role, is_active)
                VALUES (?, ?, ?, ?, 'WORKER', 1);
                """,
                (un, em, pwd_hash, salt)
            )
            worker_user_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization, is_available, approval_status)
                VALUES (?, ?, ?, ?, ?, 1, 'PENDING');
                """,
                (worker_user_id, fn, ph, dept, spec)
            )

            # Record initial notification
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, title, message, notification_type)
                VALUES (?, 'Registration Submitted', 'Your field worker account application has been received and is waiting for administrator approval.', 'REGISTRATION_PENDING');
                """,
                (worker_user_id,)
            )

        return True, worker_user_id, "Registration submitted successfully! Your application is waiting for administrator approval."
    except Exception as exc:
        return False, None, f"Database error during worker registration: {exc}"


def create_admin_account(
    full_name: str,
    email: str,
    username: str,
    password: str,
    db_path: str = DB_PATH
) -> Tuple[bool, Optional[int], str]:
    """
    Creates an Administrator account. Used primarily for initial provisioning and setup.
    """
    fn = sanitize_text(full_name)
    em = sanitize_text(email).lower()
    un = sanitize_text(username).lower()

    existing = fetch_one(
        "SELECT id FROM Users WHERE username = ? COLLATE NOCASE OR email = ? COLLATE NOCASE;",
        (un, em),
        db_path=db_path
    )
    if existing:
        return False, None, "Admin user or email already exists."

    pwd_hash, salt = hash_password(password)
    try:
        user_id = execute_query(
            """
            INSERT INTO Users (username, email, password_hash, salt, role, is_active)
            VALUES (?, ?, ?, ?, 'ADMIN', 1);
            """,
            (un, em, pwd_hash, salt),
            db_path=db_path
        )
        return True, user_id, f"Admin account '{un}' created."
    except Exception as exc:
        return False, None, f"Database error: {exc}"


authenticate_user = authenticate
