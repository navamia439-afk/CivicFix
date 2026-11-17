"""
CivicFix State Machine & Lifecycle Transition Service
Provides strict, centralized state transition enforcement, role-based transition
guards, automatic multi-party notifications, and immutable audit trail logging.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import datetime

from database.db_connection import get_db, DB_PATH
from database.database_operations import fetch_one, fetch_all

# ============================================================================
# 1. STATUS & ROLE CONSTANTS
# ============================================================================

STATUS_NEW = "NEW"
STATUS_UNDER_REVIEW = "UNDER_REVIEW"
STATUS_VERIFIED = "VERIFIED"
STATUS_REJECTED = "REJECTED"
STATUS_ASSIGNED = "ASSIGNED"
STATUS_ACKNOWLEDGED = "ACKNOWLEDGED"
STATUS_IN_PROGRESS = "IN_PROGRESS"
STATUS_DELAYED = "DELAYED"
STATUS_COMPLETED_PENDING_VERIFICATION = "COMPLETED_PENDING_VERIFICATION"
STATUS_RESOLVED = "RESOLVED"
STATUS_CLOSED = "CLOSED"
STATUS_REOPENED = "REOPENED"

ALL_STATUSES = [
    STATUS_NEW,
    STATUS_UNDER_REVIEW,
    STATUS_VERIFIED,
    STATUS_REJECTED,
    STATUS_ASSIGNED,
    STATUS_ACKNOWLEDGED,
    STATUS_IN_PROGRESS,
    STATUS_DELAYED,
    STATUS_COMPLETED_PENDING_VERIFICATION,
    STATUS_RESOLVED,
    STATUS_CLOSED,
    STATUS_REOPENED,
]

ROLE_CITIZEN = "CITIZEN"
ROLE_WORKER = "WORKER"
ROLE_ADMIN = "ADMIN"

ALL_ROLES = [ROLE_CITIZEN, ROLE_WORKER, ROLE_ADMIN]

# ============================================================================
# 2. STATE TRANSITION RULES MATRIX
# ============================================================================

# Valid Next States from each state
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    STATUS_NEW: {STATUS_UNDER_REVIEW, STATUS_VERIFIED, STATUS_REJECTED},
    STATUS_UNDER_REVIEW: {STATUS_VERIFIED, STATUS_REJECTED},
    STATUS_VERIFIED: {STATUS_ASSIGNED, STATUS_REJECTED},
    STATUS_ASSIGNED: {STATUS_ACKNOWLEDGED, STATUS_IN_PROGRESS, STATUS_DELAYED},
    STATUS_ACKNOWLEDGED: {STATUS_IN_PROGRESS, STATUS_DELAYED},
    STATUS_IN_PROGRESS: {STATUS_DELAYED, STATUS_COMPLETED_PENDING_VERIFICATION},
    STATUS_DELAYED: {STATUS_IN_PROGRESS, STATUS_ASSIGNED, STATUS_COMPLETED_PENDING_VERIFICATION},
    STATUS_COMPLETED_PENDING_VERIFICATION: {STATUS_RESOLVED, STATUS_IN_PROGRESS},
    STATUS_RESOLVED: {STATUS_CLOSED, STATUS_REOPENED},
    STATUS_CLOSED: {STATUS_REOPENED},
    STATUS_REJECTED: {STATUS_UNDER_REVIEW, STATUS_REOPENED},
    STATUS_REOPENED: {STATUS_UNDER_REVIEW, STATUS_VERIFIED, STATUS_ASSIGNED},
}

# Role-specific Allowed State Transitions: role -> {current_state: {allowed_next_states}}
ROLE_PERMITTED_TRANSITIONS: Dict[str, Dict[str, Set[str]]] = {
    ROLE_CITIZEN: {
        STATUS_RESOLVED: {STATUS_CLOSED, STATUS_REOPENED},
        STATUS_CLOSED: {STATUS_REOPENED},
        STATUS_REJECTED: {STATUS_REOPENED},
    },
    ROLE_WORKER: {
        STATUS_ASSIGNED: {STATUS_ACKNOWLEDGED, STATUS_IN_PROGRESS, STATUS_DELAYED},
        STATUS_ACKNOWLEDGED: {STATUS_IN_PROGRESS, STATUS_DELAYED},
        STATUS_IN_PROGRESS: {STATUS_DELAYED, STATUS_COMPLETED_PENDING_VERIFICATION},
        STATUS_DELAYED: {STATUS_IN_PROGRESS, STATUS_COMPLETED_PENDING_VERIFICATION},
    },
    ROLE_ADMIN: {
        STATUS_NEW: {STATUS_UNDER_REVIEW, STATUS_VERIFIED, STATUS_REJECTED},
        STATUS_UNDER_REVIEW: {STATUS_VERIFIED, STATUS_REJECTED},
        STATUS_VERIFIED: {STATUS_ASSIGNED, STATUS_REJECTED},
        STATUS_ASSIGNED: {STATUS_ACKNOWLEDGED, STATUS_IN_PROGRESS, STATUS_DELAYED},
        STATUS_ACKNOWLEDGED: {STATUS_IN_PROGRESS, STATUS_DELAYED},
        STATUS_IN_PROGRESS: {STATUS_DELAYED, STATUS_COMPLETED_PENDING_VERIFICATION},
        STATUS_DELAYED: {STATUS_IN_PROGRESS, STATUS_ASSIGNED, STATUS_COMPLETED_PENDING_VERIFICATION},
        STATUS_COMPLETED_PENDING_VERIFICATION: {STATUS_RESOLVED, STATUS_IN_PROGRESS},
        STATUS_RESOLVED: {STATUS_CLOSED, STATUS_REOPENED},
        STATUS_CLOSED: {STATUS_REOPENED},
        STATUS_REJECTED: {STATUS_UNDER_REVIEW, STATUS_REOPENED},
        STATUS_REOPENED: {STATUS_UNDER_REVIEW, STATUS_VERIFIED, STATUS_ASSIGNED},
    },
}

# ============================================================================
# 3. STATUS BADGE & DISPLAY METADATA (Theme-Aligned)
# ============================================================================

STATUS_METADATA = {
    STATUS_NEW: {
        "label": "New Reported",
        "bg": "#DCEEFF",      # Light Blue
        "fg": "#263B50",      # Dark Navy
        "icon": "📝",
        "stage": "Intake"
    },
    STATUS_UNDER_REVIEW: {
        "label": "Under Review",
        "bg": "#EAF4FC",      # Light Accent
        "fg": "#355C7D",      # Deep Navy Blue
        "icon": "🔍",
        "stage": "Triage"
    },
    STATUS_VERIFIED: {
        "label": "Verified",
        "bg": "#D6E4F0",      # Misty Blue
        "fg": "#355C7D",
        "icon": "✓",
        "stage": "Verified"
    },
    STATUS_REJECTED: {
        "label": "Rejected",
        "bg": "#F2C9D0",      # Danger Pastel
        "fg": "#7A202E",
        "icon": "✗",
        "stage": "Closed"
    },
    STATUS_ASSIGNED: {
        "label": "Worker Assigned",
        "bg": "#DCEEFF",
        "fg": "#355C7D",
        "icon": "👤",
        "stage": "Dispatched"
    },
    STATUS_ACKNOWLEDGED: {
        "label": "Acknowledged",
        "bg": "#EAF4FC",
        "fg": "#355C7D",
        "icon": "📋",
        "stage": "Field Work"
    },
    STATUS_IN_PROGRESS: {
        "label": "In Progress",
        "bg": "#5B9BD5",      # Primary Sky Blue
        "fg": "#FFFFFF",
        "icon": "⚡",
        "stage": "Field Work"
    },
    STATUS_DELAYED: {
        "label": "Delayed",
        "bg": "#F8D6B5",      # Soft Peach
        "fg": "#7D4A18",
        "icon": "⏳",
        "stage": "Field Work"
    },
    STATUS_COMPLETED_PENDING_VERIFICATION: {
        "label": "Pending Inspection",
        "bg": "#DCEEFF",
        "fg": "#355C7D",
        "icon": "📸",
        "stage": "Inspection"
    },
    STATUS_RESOLVED: {
        "label": "Resolved",
        "bg": "#A8D5D8",      # Success Soft Blue-Green
        "fg": "#1B4F52",
        "icon": "★",
        "stage": "Resolved"
    },
    STATUS_CLOSED: {
        "label": "Closed",
        "bg": "#D6E4F0",
        "fg": "#263B50",
        "icon": "🔒",
        "stage": "Archived"
    },
    STATUS_REOPENED: {
        "label": "Reopened",
        "bg": "#F8D6B5",
        "fg": "#7D4A18",
        "icon": "↺",
        "stage": "Reopened"
    },
}


def get_status_metadata(status: str) -> Dict[str, Any]:
    """Returns visual badge styling and stage for any given complaint status."""
    return STATUS_METADATA.get(status, {
        "label": status,
        "bg": "#EAF4FC",
        "fg": "#263B50",
        "icon": "•",
        "stage": "Unknown"
    })


# ============================================================================
# 4. TRANSITION VALIDATION ENGINE
# ============================================================================

def can_transition(
    complaint_id: int,
    target_status: str,
    actor_id: int,
    actor_role: str,
    db_path: str = DB_PATH
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates whether an actor with a given role can transition the complaint to target_status.
    
    Checks:
    1. Target status is a valid system status.
    2. Complaint exists in the database.
    3. Status is not identical to current status.
    4. Transition is allowed in the state graph.
    5. Actor role has permission for this transition.
    6. Specific actor identity checks:
       - Citizen must own the complaint.
       - Worker must be currently assigned to the complaint.
       - Admin must be an active administrator.
       
    Returns:
        (is_allowed: bool, reason: str, complaint_dict: Optional[Dict])
    """
    if target_status not in ALL_STATUSES:
        return False, f"Invalid target status '{target_status}'.", None

    if actor_role not in ALL_ROLES:
        return False, f"Invalid actor role '{actor_role}'.", None

    # Retrieve complaint record
    comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
    if not comp:
        return False, f"Complaint with ID {complaint_id} does not exist.", None

    current_status = comp["status"]

    if current_status == target_status:
        return False, f"Complaint is already in '{target_status}' status.", comp

    # Check structural transition validity
    allowed_next_states = VALID_TRANSITIONS.get(current_status, set())
    if target_status not in allowed_next_states:
        return (
            False,
            f"Invalid transition from '{current_status}' to '{target_status}'. Allowed transitions: {sorted(list(allowed_next_states))}.",
            comp
        )

    # Check role-level authorization
    role_allowed_map = ROLE_PERMITTED_TRANSITIONS.get(actor_role, {})
    role_allowed_targets = role_allowed_map.get(current_status, set())
    if target_status not in role_allowed_targets:
        return (
            False,
            f"Role '{actor_role}' is not authorized to transition from '{current_status}' to '{target_status}'.",
            comp
        )

    # Check user-level authorization & ownership
    if actor_role == ROLE_CITIZEN:
        if comp["citizen_id"] != actor_id:
            return False, "Citizens can only transition their own reported complaints.", comp

    elif actor_role == ROLE_WORKER:
        # Worker must have an active assignment to this complaint
        assignment = fetch_one(
            "SELECT * FROM WorkerAssignments WHERE complaint_id = ? AND worker_id = ? AND is_current = 1;",
            (complaint_id, actor_id),
            db_path=db_path
        )
        if not assignment:
            return False, "Field worker is not currently assigned to this complaint.", comp

    elif actor_role == ROLE_ADMIN:
        admin_user = fetch_one(
            "SELECT id, is_active FROM Users WHERE id = ? AND role = 'ADMIN';",
            (actor_id,),
            db_path=db_path
        )
        if not admin_user or not admin_user["is_active"]:
            return False, "Actor is not an active system administrator.", comp

    return True, "Transition is valid.", comp


def get_allowed_transitions(
    complaint_id: int,
    actor_id: int,
    actor_role: str,
    db_path: str = DB_PATH
) -> List[str]:
    """
    Returns the list of valid target statuses the current actor can transition this complaint to.
    Useful for populating dynamic action buttons in the UI.
    """
    comp = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (complaint_id,), db_path=db_path)
    if not comp:
        return []

    current_status = comp["status"]
    candidates = VALID_TRANSITIONS.get(current_status, set())
    allowed = []
    for target in candidates:
        ok, _, _ = can_transition(complaint_id, target, actor_id, actor_role, db_path=db_path)
        if ok:
            allowed.append(target)
    return sorted(allowed)


# ============================================================================
# 5. ATOMIC STATE TRANSITION EXECUTION ENGINE
# ============================================================================

def transition_status(
    complaint_id: int,
    target_status: str,
    actor_id: int,
    actor_role: str,
    remarks: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    db_path: str = DB_PATH
) -> Tuple[bool, str]:
    """
    Executes a formal lifecycle status transition with ACID guarantees:
    1. Validates preconditions through can_transition().
    2. Updates Complaint status and timestamp column.
    3. Records immutable audit log into ComplaintStatusHistory.
    4. If actor is ADMIN, records audit log into AdminActionHistory.
    5. Dispatches multi-party in-app Notifications to Citizen, Worker, and Admins.
    
    Returns:
        (success: bool, message: str)
    """
    metadata = metadata or {}
    ok, err_msg, comp = can_transition(complaint_id, target_status, actor_id, actor_role, db_path=db_path)
    if not ok:
        return False, err_msg

    cfx_code = comp["complaint_id"]
    current_status = comp["status"]
    clean_remarks = (remarks or "").strip()

    # Determine specific column update based on target status
    timestamp_clause = ""
    extra_sets = []
    extra_params = []

    if target_status == STATUS_VERIFIED:
        timestamp_clause = ", verified_at = CURRENT_TIMESTAMP"
        if metadata.get("priority"):
            extra_sets.append("priority = ?")
            extra_params.append(metadata["priority"])
        if metadata.get("department"):
            extra_sets.append("department = ?")
            extra_params.append(metadata["department"])
        if metadata.get("due_date"):
            extra_sets.append("due_date = ?")
            extra_params.append(metadata["due_date"])
        if clean_remarks:
            extra_sets.append("admin_remarks = ?")
            extra_params.append(clean_remarks)

    elif target_status == STATUS_REJECTED:
        extra_sets.append("rejection_reason = ?")
        extra_params.append(clean_remarks or "No rejection reason specified.")
        if clean_remarks:
            extra_sets.append("admin_remarks = ?")
            extra_params.append(clean_remarks)

    elif target_status == STATUS_ASSIGNED:
        timestamp_clause = ", assigned_at = CURRENT_TIMESTAMP"
        if metadata.get("due_date"):
            extra_sets.append("due_date = ?")
            extra_params.append(metadata["due_date"])

    elif target_status == STATUS_COMPLETED_PENDING_VERIFICATION:
        timestamp_clause = ", completed_at = CURRENT_TIMESTAMP"

    elif target_status == STATUS_RESOLVED:
        timestamp_clause = ", resolved_at = CURRENT_TIMESTAMP"
        if clean_remarks:
            extra_sets.append("admin_remarks = COALESCE(admin_remarks || ' | ', '') || ?")
            extra_params.append(f"Admin Approval: {clean_remarks}")

    elif target_status == STATUS_CLOSED:
        timestamp_clause = ", closed_at = CURRENT_TIMESTAMP"

    elif target_status == STATUS_REOPENED:
        timestamp_clause = ", reopened_at = CURRENT_TIMESTAMP"
        extra_sets.append("reopen_reason = ?")
        extra_params.append(clean_remarks or "Reopened by user.")

    # Execute atomic transaction
    try:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            # 1. Update Complaints
            extra_sql = (", " + ", ".join(extra_sets)) if extra_sets else ""
            sql_update = f"UPDATE Complaints SET status = ? {timestamp_clause} {extra_sql} WHERE id = ?;"
            params_update = [target_status] + extra_params + [complaint_id]
            cursor.execute(sql_update, tuple(params_update))

            # 2. Append to ComplaintStatusHistory (Immutable Lifecycle Audit Log)
            history_remarks = clean_remarks or f"Status changed from {current_status} to {target_status} by {actor_role}."
            cursor.execute(
                """
                INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                VALUES (?, ?, ?, ?, ?);
                """,
                (complaint_id, current_status, target_status, actor_id, history_remarks)
            )

            # 3. If Admin, append to AdminActionHistory
            if actor_role == ROLE_ADMIN:
                action_name = f"TRANSITION_{target_status}"
                if target_status == STATUS_VERIFIED:
                    action_name = "VERIFY"
                elif target_status == STATUS_REJECTED:
                    action_name = "REJECT"
                elif target_status == STATUS_RESOLVED:
                    action_name = "RESOLVE"
                elif target_status == STATUS_CLOSED:
                    action_name = "CLOSE"
                elif target_status == STATUS_REOPENED:
                    action_name = "REOPEN"

                audit_details = f"Transitioned {cfx_code} from {current_status} to {target_status}. {clean_remarks}".strip()
                cursor.execute(
                    """
                    INSERT INTO AdminActionHistory (admin_id, complaint_id, action_type, details)
                    VALUES (?, ?, ?, ?);
                    """,
                    (actor_id, complaint_id, action_name, audit_details)
                )

            # 4. Trigger In-App Notifications
            _dispatch_transition_notifications(
                cursor=cursor,
                complaint=comp,
                target_status=target_status,
                actor_id=actor_id,
                actor_role=actor_role,
                remarks=clean_remarks,
                metadata=metadata
            )

        return True, f"Complaint {cfx_code} successfully transitioned to '{target_status}'."

    except Exception as exc:
        return False, f"Database transaction failed: {exc}"


# ============================================================================
# 6. AUTOMATED NOTIFICATION DISPATCH HELPER
# ============================================================================

def _dispatch_transition_notifications(
    cursor,
    complaint: Dict[str, Any],
    target_status: str,
    actor_id: int,
    actor_role: str,
    remarks: str,
    metadata: Dict[str, Any]
) -> None:
    """
    Dispatches contextual in-app notifications inside the active transaction cursor.
    Notifies Citizen, Assigned Worker, and Admins appropriately based on the transition.
    """
    cid = complaint["id"]
    cfx = complaint["complaint_id"]
    citizen_id = complaint["citizen_id"]

    # 1. Citizen Notifications
    citizen_title = f"Complaint Update: {target_status}"
    citizen_msg = None
    notif_type = "STATUS_UPDATE"

    if target_status == STATUS_UNDER_REVIEW:
        citizen_title = "Complaint Under Review"
        citizen_msg = f"Your complaint {cfx} is currently being triaged by municipal administration."
    elif target_status == STATUS_VERIFIED:
        citizen_title = "Complaint Inspected & Verified"
        citizen_msg = f"Your complaint {cfx} has been verified by the municipal authority and approved for field resolution."
    elif target_status == STATUS_REJECTED:
        citizen_title = "Complaint Rejected"
        citizen_msg = f"Your complaint {cfx} could not be approved. Reason: {remarks or 'See administrator remarks.'}"
    elif target_status == STATUS_ASSIGNED:
        citizen_title = "Field Worker Assigned"
        citizen_msg = f"A municipal field specialist has been dispatched to address your complaint {cfx}."
    elif target_status == STATUS_ACKNOWLEDGED:
        citizen_title = "Task Acknowledged by Worker"
        citizen_msg = f"The assigned field technician has acknowledged {cfx} and scheduled on-site inspection."
    elif target_status == STATUS_IN_PROGRESS:
        citizen_title = "Work In Progress"
        citizen_msg = f"Active resolution work has commenced on {cfx}: {remarks or 'Field technicians are working on-site.'}"
    elif target_status == STATUS_DELAYED:
        citizen_title = "Resolution Delayed"
        citizen_msg = f"Notice: Resolution work on {cfx} has encountered a temporary delay: {remarks or 'Pending supplies or weather conditions.'}"
    elif target_status == STATUS_COMPLETED_PENDING_VERIFICATION:
        citizen_title = "Physical Repair Completed"
        citizen_msg = f"Field repairs on {cfx} have finished and proof photo submitted. Awaiting administrative quality audit."
    elif target_status == STATUS_RESOLVED:
        citizen_title = "Issue Resolved! Please Rate"
        citizen_msg = f"Your issue {cfx} has been officially verified as resolved. Please open your complaint to rate our service."
    elif target_status == STATUS_CLOSED:
        citizen_title = "Complaint Closed"
        citizen_msg = f"Complaint {cfx} is officially archived. Thank you for helping keep our community safe and clean."
    elif target_status == STATUS_REOPENED:
        citizen_title = "Complaint Reopened"
        citizen_msg = f"Complaint {cfx} has been reopened for further administrative action and inspection."

    if citizen_msg:
        cursor.execute(
            """
            INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
            VALUES (?, ?, ?, ?, ?);
            """,
            (citizen_id, cid, citizen_title, citizen_msg, notif_type)
        )

    # 2. Field Worker Notifications (if worker is assigned)
    cursor.execute(
        "SELECT worker_id FROM WorkerAssignments WHERE complaint_id = ? AND is_current = 1;",
        (cid,)
    )
    assigned_worker_row = cursor.fetchone()
    worker_id = assigned_worker_row[0] if assigned_worker_row else metadata.get("worker_id")

    if worker_id:
        worker_title = None
        worker_msg = None

        if target_status == STATUS_ASSIGNED:
            worker_title = "New Field Assignment"
            worker_msg = f"You have been assigned to civic complaint {cfx} ({complaint['category']})."
            notif_type = "WORKER_ASSIGNMENT"
        elif target_status == STATUS_RESOLVED:
            worker_title = "Work Approved & Resolved"
            worker_msg = f"Administrator has approved your completion proof for {cfx}. Great job!"
        elif target_status == STATUS_CLOSED:
            worker_title = "Task Closed"
            worker_msg = f"Complaint {cfx} has been finalized and closed."
        elif target_status == STATUS_REOPENED:
            worker_title = "Task Reopened"
            worker_msg = f"Citizen has requested reopening for {cfx}: {remarks or 'Further work requested.'}"
        elif target_status == STATUS_IN_PROGRESS and actor_role == ROLE_ADMIN:
            # Admin sent back for rework
            worker_title = "Rework Requested"
            worker_msg = f"Administrator requested rework on {cfx}: {remarks or 'Please re-inspect work.'}"

        if worker_msg and worker_id != actor_id:
            cursor.execute(
                """
                INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                VALUES (?, ?, ?, ?, ?);
                """,
                (worker_id, cid, worker_title, worker_msg, notif_type)
            )

    # 3. Administrator Notifications (Notify all active admins when action is needed)
    if target_status in (STATUS_COMPLETED_PENDING_VERIFICATION, STATUS_DELAYED, STATUS_REOPENED):
        admin_title = f"Admin Action Needed: {target_status}"
        admin_msg = ""
        if target_status == STATUS_COMPLETED_PENDING_VERIFICATION:
            admin_title = "Audit Required: Work Completed"
            admin_msg = f"Worker submitted completion proof for {cfx}. Audit and sign-off required."
        elif target_status == STATUS_DELAYED:
            admin_title = "Task Delayed Notice"
            admin_msg = f"Worker reported delay on {cfx}: {remarks or 'Operational delay.'}"
        elif target_status == STATUS_REOPENED:
            admin_title = "Complaint Reopened by Citizen"
            admin_msg = f"Citizen reopened {cfx}: {remarks or 'Unsatisfactory resolution.'}"

        # Fetch active admin user IDs
        cursor.execute("SELECT id FROM Users WHERE role = 'ADMIN' AND is_active = 1;")
        admin_rows = cursor.fetchall()
        for a_row in admin_rows:
            a_id = a_row[0]
            # Don't notify the admin if they triggered it themselves
            if a_id != actor_id:
                cursor.execute(
                    """
                    INSERT INTO Notifications (user_id, complaint_id, title, message, notification_type)
                    VALUES (?, ?, ?, ?, 'ADMIN_ALERT');
                    """,
                    (a_id, cid, admin_title, admin_msg)
                )
