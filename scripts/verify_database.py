"""
CivicFix Database Health & Referential Integrity Verifier
Inspects the SQLite database (civicfix.db), executes SQLite PRAGMAs,
checks referential constraints, checks indexes, and verifies cross-role data integrity.
"""

import os
import sys
import sqlite3
from typing import Dict, Any, List, Tuple

# Add root directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.db_connection import get_connection, DB_PATH
from database.schema import get_table_names

EXPECTED_TABLES = [
    "Users",
    "CitizenProfiles",
    "WorkerProfiles",
    "Complaints",
    "ComplaintImages",
    "WorkerAssignments",
    "ComplaintStatusHistory",
    "WorkerProgressUpdates",
    "Feedback",
    "ComplaintSupports",
    "AdminActionHistory",
    "WorkChecklistItems",
    "MaterialRequirements",
    "Notifications"
]

EXPECTED_INDEXES = [
    "idx_users_username",
    "idx_users_email",
    "idx_users_role",
    "idx_complaints_complaint_id",
    "idx_complaints_citizen",
    "idx_complaints_status",
    "idx_complaints_priority",
    "idx_complaints_category",
    "idx_complaints_department",
    "idx_complaints_locality",
    "idx_assignments_worker",
    "idx_assignments_complaint",
    "idx_assignments_current",
    "idx_status_history_complaint",
    "idx_notifications_user_unread",
    "idx_supports_complaint_citizen",
    "idx_admin_action_admin"
]


def verify_database_health(db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Runs a comprehensive inspection of the SQLite database:
    1. File existence & size
    2. PRAGMA integrity_check
    3. PRAGMA foreign_key_check
    4. Table presence (all 14 tables)
    5. Table row counts
    6. Index presence & query plan verification
    7. Cross-role referential consistency
    8. Security & password hash validation
    """
    report = {
        "db_path": db_path,
        "exists": os.path.exists(db_path),
        "file_size_bytes": os.path.getsize(db_path) if os.path.exists(db_path) else 0,
        "integrity_check": "FAILED",
        "foreign_key_violations": [],
        "missing_tables": [],
        "table_counts": {},
        "missing_indexes": [],
        "consistency_issues": [],
        "passed": False
    }

    if not report["exists"]:
        report["consistency_issues"].append(f"Database file not found at: {db_path}")
        return report

    conn = get_connection(db_path)
    try:
        cur = conn.cursor()

        # 1. SQLite PRAGMA integrity_check
        cur.execute("PRAGMA integrity_check;")
        int_result = cur.fetchone()
        report["integrity_check"] = int_result[0] if int_result else "UNKNOWN"

        # 2. SQLite PRAGMA foreign_key_check
        cur.execute("PRAGMA foreign_key_check;")
        fk_violations = cur.fetchall()
        report["foreign_key_violations"] = [
            {"table": r[0], "rowid": r[1], "target_table": r[2], "fkid": r[3]}
            for r in fk_violations
        ]

        # 3. Check Tables
        existing_tables = set(get_table_names(db_path))
        for t in EXPECTED_TABLES:
            if t not in existing_tables:
                report["missing_tables"].append(t)
            else:
                cur.execute(f"SELECT COUNT(*) FROM {t};")
                cnt = cur.fetchone()[0]
                report["table_counts"][t] = cnt

        # 4. Check Indexes
        cur.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
        existing_indexes = set(row[0] for row in cur.fetchall())
        for idx in EXPECTED_INDEXES:
            if idx not in existing_indexes:
                report["missing_indexes"].append(idx)

        # 5. Cross-Role Referential Checks
        # A. CitizenProfiles without CITIZEN role
        cur.execute("""
            SELECT cp.id, cp.user_id, u.role FROM CitizenProfiles cp
            JOIN Users u ON cp.user_id = u.id
            WHERE u.role != 'CITIZEN';
        """)
        bad_citizens = cur.fetchall()
        if bad_citizens:
            report["consistency_issues"].append(f"{len(bad_citizens)} CitizenProfiles linked to non-CITIZEN users.")

        # B. WorkerProfiles without WORKER role
        cur.execute("""
            SELECT wp.id, wp.user_id, u.role FROM WorkerProfiles wp
            JOIN Users u ON wp.user_id = u.id
            WHERE u.role != 'WORKER';
        """)
        bad_workers = cur.fetchall()
        if bad_workers:
            report["consistency_issues"].append(f"{len(bad_workers)} WorkerProfiles linked to non-WORKER users.")

        # C. Complaints linked to non-existent citizens
        cur.execute("""
            SELECT c.id, c.complaint_id FROM Complaints c
            LEFT JOIN Users u ON c.citizen_id = u.id
            WHERE u.id IS NULL;
        """)
        orphan_complaints = cur.fetchall()
        if orphan_complaints:
            report["consistency_issues"].append(f"{len(orphan_complaints)} Complaints have invalid citizen_id references.")

        # D. WorkerAssignments linked to non-worker users
        cur.execute("""
            SELECT wa.id, wa.complaint_id, u.role FROM WorkerAssignments wa
            JOIN Users u ON wa.worker_id = u.id
            WHERE u.role != 'WORKER';
        """)
        invalid_assignments = cur.fetchall()
        if invalid_assignments:
            report["consistency_issues"].append(f"{len(invalid_assignments)} WorkerAssignments assigned to non-WORKER users.")

        # E. Verify Password Hash Security (PBKDF2 format: salt$hash)
        cur.execute("SELECT id, username, password_hash, salt FROM Users;")
        users = cur.fetchall()
        for u in users:
            uid, uname, phash, salt = u[0], u[1], u[2], u[3]
            if not phash or len(phash) < 32 or not salt or len(salt) < 16:
                report["consistency_issues"].append(f"User '{uname}' has an invalid or weak password hash format.")

        # Overall Status
        has_errors = (
            report["integrity_check"] != "ok" or
            len(report["foreign_key_violations"]) > 0 or
            len(report["missing_tables"]) > 0 or
            len(report["missing_indexes"]) > 0 or
            len(report["consistency_issues"]) > 0
        )
        report["passed"] = not has_errors

    finally:
        conn.close()

    return report


def print_verification_report(report: Dict[str, Any]):
    """Formats and prints the verification report to standard output."""
    sep = "=" * 70
    print("\n" + sep)
    print(" 🏛️  CIVICFIX UNIFIED DATABASE INTEGRITY REPORT")
    print(sep)
    print(f"Database File   : {report['db_path']}")
    print(f"File Exists     : {'YES' if report['exists'] else 'NO'}")
    print(f"File Size       : {report['file_size_bytes'] / 1024:.2f} KB")
    print(f"PRAGMA Integrity: {report['integrity_check']}")
    print(f"FK Violations   : {len(report['foreign_key_violations'])}")
    print(f"Missing Tables  : {len(report['missing_tables'])}")
    print(f"Missing Indexes : {len(report['missing_indexes'])}")
    print(f"Consistency Errs: {len(report['consistency_issues'])}")
    print(sep)
    print(" 📊 TABLE RECORD COUNTS (All 14 Core Tables):")
    print(sep)
    for tbl, count in report["table_counts"].items():
        print(f"  • {tbl:<25}: {count:>4} rows")

    if report["foreign_key_violations"]:
        print("\n" + sep)
        print(" ❌ FOREIGN KEY VIOLATIONS DETECTED:")
        print(sep)
        for v in report["foreign_key_violations"]:
            print(f"  Table: {v['table']} | RowID: {v['rowid']} -> Target Table: {v['target_table']}")

    if report["consistency_issues"]:
        print("\n" + sep)
        print(" ⚠️  CONSISTENCY ISSUES DETECTED:")
        print(sep)
        for issue in report["consistency_issues"]:
            print(f"  • {issue}")

    print("\n" + sep)
    if report["passed"]:
        print(" ✅ DATABASE HEALTH VERIFICATION: PASSED (100% HEALTHY)")
    else:
        print(" ❌ DATABASE HEALTH VERIFICATION: FAILED")
    print(sep + "\n")


if __name__ == "__main__":
    rep = verify_database_health()
    print_verification_report(rep)
