"""
CivicFix Database Connection Manager
Provides centralized, safe SQLite database connections with context management,
foreign key enforcement, and transactional integrity.
"""

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator

# Define database location relative to application root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "civicfix.db")


def get_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Creates and returns a new SQLite connection with:
    - Foreign key constraints enabled
    - Row factory configured to sqlite3.Row for dictionary-like column access
    - Timeout configured to handle concurrent file locks gracefully
    """
    conn = sqlite3.connect(db_path, timeout=10.0)
    # Ensure foreign keys are strictly enforced in SQLite
    conn.execute("PRAGMA foreign_keys = ON;")
    # Set journal mode to WAL (Write-Ahead Logging) for better concurrency
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db_cursor(db_path: str = DB_PATH) -> Generator[sqlite3.Cursor, None, None]:
    """
    Context manager that yields a cursor and automatically commits transactions
    or rolls back changes in case of exceptions.
    
    Usage:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT ...")
    """
    conn = get_connection(db_path)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        cursor.close()
        conn.close()


@contextmanager
def get_db(db_path: str = DB_PATH) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding the connection itself for multi-step transactions.
    
    Usage:
        with get_db() as conn:
            conn.execute("...")
    """
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as exc:
        conn.rollback()
        raise exc
    finally:
        conn.close()
