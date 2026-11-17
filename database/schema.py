"""
CivicFix Database Schema Definition
Contains the complete, normalized SQLite schema for all 14 core entities,
referential integrity constraints, check constraints, and performance indexes.
"""

from database.db_connection import get_connection, DB_PATH

SCHEMA_SQL = """
-- 1. Users Table
CREATE TABLE IF NOT EXISTS Users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    email TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('CITIZEN', 'ADMIN', 'WORKER')),
    is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Citizen Profiles Table
CREATE TABLE IF NOT EXISTS CitizenProfiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    address TEXT,
    locality TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 3. Worker Profiles Table
CREATE TABLE IF NOT EXISTS WorkerProfiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    department TEXT NOT NULL,
    specialization TEXT,
    is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0, 1)),
    approval_status TEXT NOT NULL DEFAULT 'APPROVED' CHECK(approval_status IN ('PENDING', 'APPROVED', 'REJECTED')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 4. Complaints Table
CREATE TABLE IF NOT EXISTS Complaints (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id TEXT UNIQUE NOT NULL, -- e.g. CFX-2026-000001
    citizen_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    category TEXT NOT NULL,
    location TEXT NOT NULL,
    locality TEXT NOT NULL,
    ward_number TEXT,
    is_emergency INTEGER NOT NULL DEFAULT 0 CHECK(is_emergency IN (0, 1)),
    is_anonymous INTEGER NOT NULL DEFAULT 0 CHECK(is_anonymous IN (0, 1)),
    priority TEXT NOT NULL DEFAULT 'MEDIUM' CHECK(priority IN ('LOW', 'MEDIUM', 'HIGH', 'EMERGENCY')),
    suggested_priority TEXT,
    priority_reason TEXT,
    department TEXT,
    status TEXT NOT NULL DEFAULT 'NEW' CHECK(status IN (
        'NEW',
        'UNDER_REVIEW',
        'VERIFIED',
        'REJECTED',
        'ASSIGNED',
        'ACKNOWLEDGED',
        'IN_PROGRESS',
        'DELAYED',
        'COMPLETED_PENDING_VERIFICATION',
        'RESOLVED',
        'CLOSED',
        'REOPENED'
    )),
    due_date DATETIME,
    support_count INTEGER NOT NULL DEFAULT 0,
    admin_remarks TEXT,
    rejection_reason TEXT,
    reopen_reason TEXT,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    verified_at DATETIME,
    assigned_at DATETIME,
    completed_at DATETIME,
    resolved_at DATETIME,
    closed_at DATETIME,
    reopened_at DATETIME
);

-- 5. Complaint Images Table (Evidence, Progress, Completion Proofs)
CREATE TABLE IF NOT EXISTS ComplaintImages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    image_path TEXT NOT NULL,
    image_type TEXT NOT NULL CHECK(image_type IN ('EVIDENCE', 'PROGRESS', 'COMPLETION')),
    uploaded_by INTEGER REFERENCES Users(id) ON DELETE SET NULL,
    caption TEXT,
    uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 6. Worker Assignments Table
CREATE TABLE IF NOT EXISTS WorkerAssignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    assigned_by INTEGER NOT NULL REFERENCES Users(id),
    assigned_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_date DATETIME,
    is_current INTEGER NOT NULL DEFAULT 1 CHECK(is_current IN (0, 1)),
    acknowledged_at DATETIME,
    estimated_completion_date DATETIME,
    delay_reason TEXT,
    completion_remarks TEXT,
    completed_at DATETIME
);

-- 7. Complaint Status History Table
CREATE TABLE IF NOT EXISTS ComplaintStatusHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    previous_status TEXT,
    new_status TEXT NOT NULL,
    changed_by INTEGER NOT NULL REFERENCES Users(id),
    remarks TEXT,
    changed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 8. Worker Progress Updates Table
CREATE TABLE IF NOT EXISTS WorkerProgressUpdates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES WorkerAssignments(id) ON DELETE CASCADE,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    worker_id INTEGER NOT NULL REFERENCES Users(id),
    progress_notes TEXT NOT NULL,
    status_snapshot TEXT NOT NULL,
    progress_image_path TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 9. Feedback Table
CREATE TABLE IF NOT EXISTS Feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER UNIQUE NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    citizen_id INTEGER NOT NULL REFERENCES Users(id),
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comments TEXT,
    suggestions TEXT,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 10. Complaint Supports Table ("I ALSO FACE THIS ISSUE")
CREATE TABLE IF NOT EXISTS ComplaintSupports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    citizen_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    supported_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(complaint_id, citizen_id)
);

-- 11. Admin Action History Table (Audit Trail)
CREATE TABLE IF NOT EXISTS AdminActionHistory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL REFERENCES Users(id),
    complaint_id INTEGER REFERENCES Complaints(id) ON DELETE SET NULL,
    action_type TEXT NOT NULL,
    details TEXT,
    performed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 12. Work Checklist Items Table
CREATE TABLE IF NOT EXISTS WorkChecklistItems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES WorkerAssignments(id) ON DELETE CASCADE,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    item_text TEXT NOT NULL,
    is_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_completed IN (0, 1)),
    completed_at DATETIME
);

-- 13. Material Requirements Table
CREATE TABLE IF NOT EXISTS MaterialRequirements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assignment_id INTEGER NOT NULL REFERENCES WorkerAssignments(id) ON DELETE CASCADE,
    complaint_id INTEGER NOT NULL REFERENCES Complaints(id) ON DELETE CASCADE,
    item_name TEXT NOT NULL,
    quantity TEXT NOT NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 14. Notifications Table
CREATE TABLE IF NOT EXISTS Notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES Users(id) ON DELETE CASCADE,
    complaint_id INTEGER REFERENCES Complaints(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    notification_type TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Performance & Lookup Indexes
CREATE INDEX IF NOT EXISTS idx_users_username ON Users(username);
CREATE INDEX IF NOT EXISTS idx_users_email ON Users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON Users(role);

CREATE INDEX IF NOT EXISTS idx_complaints_complaint_id ON Complaints(complaint_id);
CREATE INDEX IF NOT EXISTS idx_complaints_citizen ON Complaints(citizen_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON Complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON Complaints(priority);
CREATE INDEX IF NOT EXISTS idx_complaints_category ON Complaints(category);
CREATE INDEX IF NOT EXISTS idx_complaints_department ON Complaints(department);
CREATE INDEX IF NOT EXISTS idx_complaints_locality ON Complaints(locality);

CREATE INDEX IF NOT EXISTS idx_assignments_worker ON WorkerAssignments(worker_id);
CREATE INDEX IF NOT EXISTS idx_assignments_complaint ON WorkerAssignments(complaint_id);
CREATE INDEX IF NOT EXISTS idx_assignments_current ON WorkerAssignments(is_current);

CREATE INDEX IF NOT EXISTS idx_status_history_complaint ON ComplaintStatusHistory(complaint_id);
CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON Notifications(user_id, is_read);
CREATE INDEX IF NOT EXISTS idx_supports_complaint_citizen ON ComplaintSupports(complaint_id, citizen_id);
CREATE INDEX IF NOT EXISTS idx_admin_action_admin ON AdminActionHistory(admin_id);
"""


def init_db(db_path: str = DB_PATH) -> bool:
    """
    Initializes the SQLite database with all 14 tables and indexes.
    Safe to execute multiple times (idempotent - does not erase existing data).
    Returns True if initialization succeeds.
    """
    conn = get_connection(db_path)
    try:
        with conn:
            conn.executescript(SCHEMA_SQL)
            # Automatic schema migration for WorkerProfiles.approval_status
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(WorkerProfiles);")
            cols = [row[1] for row in cursor.fetchall()]
            if "approval_status" not in cols:
                cursor.execute(
                    "ALTER TABLE WorkerProfiles ADD COLUMN approval_status TEXT NOT NULL DEFAULT 'APPROVED';"
                )
        return True
    except Exception as exc:
        print(f"[Database Error] Failed to initialize database: {exc}")
        raise exc
    finally:
        conn.close()


def get_table_names(db_path: str = DB_PATH) -> list:
    """Returns a list of all user-defined table names in the database."""
    conn = get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row[0] for row in cursor.fetchall()]
    finally:
        conn.close()
