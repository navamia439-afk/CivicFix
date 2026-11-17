"""
CivicFix Input Validation Utilities
Validates user registrations, credentials, emails, phone numbers,
and prevents malformed or malicious input.
"""

import re
from typing import Tuple, Optional


# Regular Expressions for Validation
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_]{3,30}$")
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")


def sanitize_text(value: Optional[str]) -> str:
    """Safely strips leading/trailing whitespace from string inputs."""
    if value is None:
        return ""
    return str(value).strip()


def validate_username(username: str) -> Tuple[bool, str]:
    """Validates that a username is 3-30 characters and alphanumeric/underscore."""
    u = sanitize_text(username)
    if not u:
        return False, "Username cannot be empty."
    if not USERNAME_REGEX.match(u):
        return False, "Username must be 3-30 characters long and contain only letters, numbers, or underscores."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    """Validates standard email format."""
    e = sanitize_text(email)
    if not e:
        return False, "Email address cannot be empty."
    if not EMAIL_REGEX.match(e):
        return False, "Please enter a valid email address (e.g., user@example.com)."
    return True, ""


def validate_phone(phone: str) -> Tuple[bool, str]:
    """Validates phone number (10 to 15 digits, optional leading +)."""
    p = sanitize_text(phone).replace(" ", "").replace("-", "")
    if not p:
        return False, "Phone number cannot be empty."
    if not PHONE_REGEX.match(p):
        return False, "Phone number must be between 10 and 15 digits."
    return True, ""


def validate_citizen_registration(
    full_name: str,
    email: str,
    phone: str,
    username: str,
    password: str,
    confirm_password: str,
    locality: str
) -> Tuple[bool, str]:
    """
    Performs comprehensive validation on all citizen registration input fields.
    """
    fn = sanitize_text(full_name)
    if not fn or len(fn) < 2:
        return False, "Full name must be at least 2 characters long."

    ok_user, msg_user = validate_username(username)
    if not ok_user:
        return False, msg_user

    ok_email, msg_email = validate_email(email)
    if not ok_email:
        return False, msg_email

    ok_phone, msg_phone = validate_phone(phone)
    if not ok_phone:
        return False, msg_phone

    loc = sanitize_text(locality)
    if not loc:
        return False, "Locality / Area cannot be empty."

    if not password:
        return False, "Password cannot be empty."

    if password != confirm_password:
        return False, "Password and Confirm Password do not match."

    from authentication.password_manager import validate_password_strength
    ok_pwd, msg_pwd = validate_password_strength(password)
    if not ok_pwd:
        return False, msg_pwd

    return True, ""
