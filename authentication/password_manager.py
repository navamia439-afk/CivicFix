"""
CivicFix Cryptographic Password Manager
Implements secure password hashing using PBKDF2-HMAC-SHA256 with unique 256-bit salts
and constant-time hash comparisons to prevent timing attacks.
"""

import os
import hashlib
import hmac
from typing import Tuple

# PBKDF2 configuration
PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 32


def generate_salt() -> str:
    """Generates a secure random 32-byte (256-bit) salt as a hexadecimal string."""
    return os.urandom(SALT_BYTES).hex()


def hash_password(password: str, salt: str = None) -> Tuple[str, str]:
    """
    Hashes a plaintext password using PBKDF2-HMAC-SHA256 with 100,000 iterations.
    
    Args:
        password: The plaintext password string.
        salt: Optional hex string salt. If None, a new random salt is generated.
        
    Returns:
        A tuple of (password_hash_hex, salt_hex).
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")

    if salt is None:
        salt = generate_salt()

    salt_bytes = bytes.fromhex(salt)
    password_bytes = password.encode("utf-8")

    derived_key = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password_bytes,
        salt_bytes,
        PBKDF2_ITERATIONS
    )

    return derived_key.hex(), salt


def verify_password(plain_password: str, stored_hash: str, stored_salt: str) -> bool:
    """
    Verifies a plaintext password against a stored PBKDF2 hash and salt.
    Uses hmac.compare_digest for constant-time comparison to prevent timing attacks.
    """
    if not plain_password or not stored_hash or not stored_salt:
        return False

    try:
        calculated_hash, _ = hash_password(plain_password, stored_salt)
        return hmac.compare_digest(calculated_hash, stored_hash)
    except Exception:
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validates password strength criteria:
    - Minimum 8 characters
    - Must contain at least one letter and one number
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    
    has_letter = any(c.isalpha() for c in password)
    has_digit = any(c.isdigit() for c in password)

    if not has_letter:
        return False, "Password must contain at least one alphabetical letter."
    if not has_digit:
        return False, "Password must contain at least one numeric digit."

    return True, "Password is valid."
