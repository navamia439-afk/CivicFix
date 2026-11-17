"""
CivicFix Analytics, Reporting & CSV Export Service Layer
Aggregates statistical KPIs, generates chart data for embedded Matplotlib,
detects potential duplicate complaints, identifies overdue tasks, and exports CSV reports.
"""

import csv
import datetime
from typing import List, Dict, Any, Optional, Tuple
from database.db_connection import get_connection, DB_PATH
from database.database_operations import fetch_all, fetch_one


def get_admin_kpis(db_path: str = DB_PATH) -> Dict[str, int]:
    """
    Computes all administrative dashboard statistics directly from SQLite.
    """
    conn = get_connection(db_path)
    try:
        cur = conn.cursor()

        # Total Complaints
        cur.execute("SELECT COUNT(*) FROM Complaints;")
        total = cur.fetchone()[0]

        # By individual lifecycle statuses
        cur.execute("SELECT status, COUNT(*) FROM Complaints GROUP BY status;")
        status_map = dict(cur.fetchall())

        # Overdue Complaints (Past due_date and not resolved/closed/rejected)
        cur.execute(
            """
            SELECT COUNT(*) FROM Complaints 
            WHERE due_date IS NOT NULL 
              AND datetime(due_date) < datetime('now')
              AND status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED');
            """
        )
        overdue = cur.fetchone()[0]

        # Emergency Flagged
        cur.execute(
            "SELECT COUNT(*) FROM Complaints WHERE is_emergency = 1 OR priority = 'EMERGENCY';"
        )
        emergency = cur.fetchone()[0]

        return {
            "total": total,
            "new": status_map.get("NEW", 0),
            "under_review": status_map.get("UNDER_REVIEW", 0),
            "verified": status_map.get("VERIFIED", 0),
            "assigned": status_map.get("ASSIGNED", 0),
            "in_progress": status_map.get("IN_PROGRESS", 0) + status_map.get("ACKNOWLEDGED", 0),
            "pending_verification": status_map.get("COMPLETED_PENDING_VERIFICATION", 0),
            "resolved": status_map.get("RESOLVED", 0),
            "closed": status_map.get("CLOSED", 0),
            "rejected": status_map.get("REJECTED", 0),
            "reopened": status_map.get("REOPENED", 0),
            "overdue": overdue,
            "emergency": emergency
        }
    finally:
        conn.close()


def get_status_distribution(db_path: str = DB_PATH) -> Dict[str, int]:
    """Returns frequency of complaints per status for chart plotting."""
    rows = fetch_all("SELECT status, COUNT(*) as cnt FROM Complaints GROUP BY status;", db_path=db_path)
    return {r["status"]: r["cnt"] for r in rows}


def get_category_distribution(db_path: str = DB_PATH) -> Dict[str, int]:
    """Returns complaint counts categorized by issue type."""
    rows = fetch_all("SELECT category, COUNT(*) as cnt FROM Complaints GROUP BY category ORDER BY cnt DESC;", db_path=db_path)
    return {r["category"]: r["cnt"] for r in rows}


def get_department_distribution(db_path: str = DB_PATH) -> Dict[str, int]:
    """Returns complaint counts grouped by assigned municipal department."""
    rows = fetch_all(
        "SELECT COALESCE(department, 'Unassigned') as dept, COUNT(*) as cnt FROM Complaints GROUP BY dept ORDER BY cnt DESC;",
        db_path=db_path
    )
    return {r["dept"]: r["cnt"] for r in rows}


def get_department_efficiency(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Computes resolution efficiency, turnaround hours, and completion rate
    for each municipal department.
    """
    sql = """
        SELECT COALESCE(c.department, 'Unassigned') as department,
               COUNT(c.id) as total_complaints,
               SUM(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_count,
               SUM(CASE WHEN c.status IN ('ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'DELAYED', 'COMPLETED_PENDING_VERIFICATION') THEN 1 ELSE 0 END) as active_count,
               SUM(CASE WHEN c.due_date IS NOT NULL AND datetime(c.due_date) < datetime('now') AND c.status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED') THEN 1 ELSE 0 END) as overdue_count,
               ROUND(AVG(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') AND c.resolved_at IS NOT NULL 
                         THEN (julianday(c.resolved_at) - julianday(c.submitted_at)) * 24.0 ELSE NULL END), 1) as avg_turnaround_hours
        FROM Complaints c
        GROUP BY department
        ORDER BY total_complaints DESC;
    """
    rows = fetch_all(sql, db_path=db_path)
    for r in rows:
        tot = r["total_complaints"]
        res = r["resolved_count"]
        r["resolution_rate_pct"] = round((res / tot * 100.0), 1) if tot > 0 else 0.0
        if r["avg_turnaround_hours"] is None:
            r["avg_turnaround_hours"] = 0.0
    return rows


def get_category_resolution_stats(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns resolution metrics and average turnaround breakdown by issue category.
    """
    sql = """
        SELECT c.category,
               COUNT(c.id) as total_count,
               SUM(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_count,
               SUM(CASE WHEN c.status IN ('ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN 1 ELSE 0 END) as in_progress_count,
               SUM(CASE WHEN c.status = 'DELAYED' THEN 1 ELSE 0 END) as delayed_count,
               SUM(CASE WHEN c.is_emergency = 1 OR c.priority = 'EMERGENCY' THEN 1 ELSE 0 END) as emergency_count,
               ROUND(AVG(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') AND c.resolved_at IS NOT NULL 
                         THEN (julianday(c.resolved_at) - julianday(c.submitted_at)) * 24.0 ELSE NULL END), 1) as avg_resolution_hours
        FROM Complaints c
        GROUP BY c.category
        ORDER BY total_count DESC;
    """
    rows = fetch_all(sql, db_path=db_path)
    for r in rows:
        tot = r["total_count"]
        res = r["resolved_count"]
        r["resolution_rate_pct"] = round((res / tot * 100.0), 1) if tot > 0 else 0.0
        if r["avg_resolution_hours"] is None:
            r["avg_resolution_hours"] = 0.0
    return rows


def get_locality_distribution(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns locality hotspot complaint distribution and emergency issue counts.
    """
    sql = """
        SELECT c.locality,
               COUNT(c.id) as total_complaints,
               SUM(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as resolved_count,
               SUM(CASE WHEN c.status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED') THEN 1 ELSE 0 END) as open_count,
               SUM(CASE WHEN c.is_emergency = 1 OR c.priority = 'EMERGENCY' THEN 1 ELSE 0 END) as emergency_count
        FROM Complaints c
        GROUP BY c.locality
        ORDER BY total_complaints DESC;
    """
    return fetch_all(sql, db_path=db_path)


def get_satisfaction_metrics(db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Computes citizen satisfaction ratings distribution and overall average rating.
    """
    sql = """
        SELECT COUNT(*) as total_feedback,
               ROUND(AVG(rating), 2) as avg_rating,
               SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as stars_5,
               SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as stars_4,
               SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as stars_3,
               SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as stars_2,
               SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as stars_1
        FROM Feedback;
    """
    row = fetch_one(sql, db_path=db_path)
    if not row or not row["total_feedback"]:
        return {
            "total_feedback": 0,
            "avg_rating": 0.0,
            "stars_5": 0,
            "stars_4": 0,
            "stars_3": 0,
            "stars_2": 0,
            "stars_1": 0,
            "satisfaction_pct": 0.0
        }

    total = row["total_feedback"]
    avg = row["avg_rating"] or 0.0
    sat_pct = round((avg / 5.0) * 100.0, 1)

    return {
        "total_feedback": total,
        "avg_rating": avg,
        "stars_5": row["stars_5"] or 0,
        "stars_4": row["stars_4"] or 0,
        "stars_3": row["stars_3"] or 0,
        "stars_2": row["stars_2"] or 0,
        "stars_1": row["stars_1"] or 0,
        "satisfaction_pct": sat_pct
    }


def get_before_after_photos(complaint_id_or_code: Any, db_path: str = DB_PATH) -> Dict[str, Any]:
    """
    Retrieves initial citizen evidence (Before) and worker completion proof (After)
    for side-by-side photographic comparison with turnaround metrics.
    """
    if isinstance(complaint_id_or_code, int) or str(complaint_id_or_code).isdigit():
        sql = "SELECT * FROM Complaints WHERE id = ?;"
        param = int(complaint_id_or_code)
    else:
        sql = "SELECT * FROM Complaints WHERE complaint_id = ?;"
        param = str(complaint_id_or_code)

    comp = fetch_one(sql, (param,), db_path=db_path)
    if not comp:
        return {"exists": False, "has_pair": False}

    cid = comp["id"]
    images = fetch_all(
        "SELECT * FROM ComplaintImages WHERE complaint_id = ? ORDER BY uploaded_at ASC;",
        (cid,),
        db_path=db_path
    )

    before_img = next((img for img in images if img["image_type"] == "EVIDENCE"), None)
    after_img = next((img for img in images if img["image_type"] == "COMPLETION"), None)

    # Worker info
    worker = fetch_one(
        """
        SELECT wp.full_name as worker_name, wp.department, wa.completed_at, wa.completion_remarks
        FROM WorkerAssignments wa
        JOIN WorkerProfiles wp ON wa.worker_id = wp.user_id
        WHERE wa.complaint_id = ? AND wa.is_current = 1;
        """,
        (cid,),
        db_path=db_path
    )

    # Calculate turnaround hours
    turnaround_hours = None
    if comp.get("submitted_at") and (comp.get("completed_at") or comp.get("resolved_at")):
        end_time_str = comp.get("completed_at") or comp.get("resolved_at")
        try:
            fmt = "%Y-%m-%d %H:%M:%S"
            t1 = datetime.datetime.strptime(comp["submitted_at"].split(".")[0], fmt)
            t2 = datetime.datetime.strptime(end_time_str.split(".")[0], fmt)
            turnaround_hours = round((t2 - t1).total_seconds() / 3600.0, 1)
        except Exception:
            pass

    return {
        "exists": True,
        "complaint_id": comp["complaint_id"],
        "title": comp["title"],
        "category": comp["category"],
        "status": comp["status"],
        "submitted_at": comp["submitted_at"],
        "completed_at": comp["completed_at"],
        "resolved_at": comp["resolved_at"],
        "turnaround_hours": turnaround_hours,
        "has_pair": bool(before_img and after_img),
        "before_image": before_img,
        "after_image": after_img,
        "worker": worker
    }


def get_worker_performance_stats(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Returns worker performance metrics: total assigned, completed, pending,
    delayed tasks, and average completion duration in hours.
    """
    sql = """
        SELECT u.id, u.username, wp.full_name, wp.department, wp.phone, wp.specialization,
               COUNT(wa.id) as total_assigned,
               SUM(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') THEN 1 ELSE 0 END) as completed,
               SUM(CASE WHEN c.status IN ('ASSIGNED', 'ACKNOWLEDGED', 'IN_PROGRESS') THEN 1 ELSE 0 END) as pending,
               SUM(CASE WHEN c.status = 'DELAYED' OR (wa.due_date IS NOT NULL AND datetime(wa.due_date) < datetime('now') AND c.status NOT IN ('RESOLVED', 'CLOSED')) THEN 1 ELSE 0 END) as delayed
        FROM Users u
        JOIN WorkerProfiles wp ON u.id = wp.user_id
        LEFT JOIN WorkerAssignments wa ON u.id = wa.worker_id
        LEFT JOIN Complaints c ON wa.complaint_id = c.id
        WHERE u.role = 'WORKER'
        GROUP BY u.id, u.username, wp.full_name, wp.department, wp.phone, wp.specialization
        ORDER BY completed DESC, pending ASC;
    """
    rows = fetch_all(sql, db_path=db_path)
    for r in rows:
        tot = r["total_assigned"]
        comp = r["completed"]
        r["completion_rate_pct"] = round((comp / tot * 100.0), 1) if tot > 0 else 0.0
    return rows


def get_overdue_complaints(db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Retrieves all complaints whose deadline has elapsed without resolution,
    including the days overdue and assigned field worker.
    """
    sql = """
        SELECT c.id, c.complaint_id, c.title, c.category, c.location, c.locality,
               c.status, c.priority, c.due_date, c.department,
               ROUND((julianday('now') - julianday(c.due_date)), 1) as days_overdue,
               COALESCE(wp.full_name, 'Unassigned') as worker_name,
               wp.phone as worker_phone
        FROM Complaints c
        LEFT JOIN WorkerAssignments wa ON c.id = wa.complaint_id AND wa.is_current = 1
        LEFT JOIN WorkerProfiles wp ON wa.worker_id = wp.user_id
        WHERE c.due_date IS NOT NULL 
          AND datetime(c.due_date) < datetime('now')
          AND c.status NOT IN ('RESOLVED', 'CLOSED', 'REJECTED')
        ORDER BY days_overdue DESC;
    """
    return fetch_all(sql, db_path=db_path)


def detect_potential_duplicates(target_complaint_id: int, db_path: str = DB_PATH) -> List[Dict[str, Any]]:
    """
    Identifies potential duplicate complaints using category, locality,
    and text keyword token similarity.
    """
    target = fetch_one("SELECT * FROM Complaints WHERE id = ?;", (target_complaint_id,), db_path=db_path)
    if not target:
        return []

    target_tokens = set(target["title"].lower().split() + target["location"].lower().split())
    # Remove common stop words
    stop_words = {"the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with", "is", "near"}
    target_tokens = target_tokens - stop_words

    # Find candidates with same category OR same locality
    candidates = fetch_all(
        """
        SELECT c.*, cp.full_name as citizen_name
        FROM Complaints c
        JOIN CitizenProfiles cp ON c.citizen_id = cp.user_id
        WHERE c.id != ? AND (c.category = ? OR c.locality = ?)
          AND c.status NOT IN ('CLOSED', 'REJECTED');
        """,
        (target_complaint_id, target["category"], target["locality"]),
        db_path=db_path
    )

    matches = []
    for cand in candidates:
        cand_tokens = set(cand["title"].lower().split() + cand["location"].lower().split()) - stop_words
        if not target_tokens or not cand_tokens:
            continue

        overlap = len(target_tokens & cand_tokens)
        similarity = (2.0 * overlap) / (len(target_tokens) + len(cand_tokens))

        # Check locality and category match bonus
        score = similarity * 60
        if cand["category"] == target["category"]:
            score += 25
        if cand["locality"].lower() == target["locality"].lower():
            score += 15

        score = min(100, int(score))

        # Include if score >= 40%
        if score >= 40:
            cand["similarity_score"] = score
            matches.append(cand)

    matches.sort(key=lambda x: x["similarity_score"], reverse=True)
    return matches


def export_complaints_to_csv(
    filepath: str,
    department_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db_path: str = DB_PATH
) -> Tuple[bool, int, str]:
    """
    Exports comprehensive complaint records to a CSV spreadsheet with custom filters.
    Includes citizen details, turnaround hours, rating, and feedback comments.
    """
    sql = """
        SELECT c.complaint_id, c.title, c.category, c.location, c.locality, c.ward_number,
               c.priority, c.is_emergency, COALESCE(c.department, 'Unassigned') as department,
               COALESCE(wp.full_name, 'Unassigned') as assigned_worker,
               COALESCE(cp.full_name, u.username) as citizen_name,
               COALESCE(cp.phone, 'N/A') as citizen_phone,
               c.status, c.support_count, c.submitted_at, c.verified_at, c.assigned_at,
               c.completed_at, c.resolved_at, c.due_date,
               ROUND(CASE WHEN c.status IN ('RESOLVED', 'CLOSED') AND c.resolved_at IS NOT NULL 
                          THEN (julianday(c.resolved_at) - julianday(c.submitted_at)) * 24.0 ELSE NULL END, 1) as turnaround_hours,
               fb.rating as citizen_rating,
               fb.comments as citizen_comments,
               c.admin_remarks
        FROM Complaints c
        JOIN Users u ON c.citizen_id = u.id
        LEFT JOIN CitizenProfiles cp ON u.id = cp.user_id
        LEFT JOIN WorkerAssignments wa ON c.id = wa.complaint_id AND wa.is_current = 1
        LEFT JOIN WorkerProfiles wp ON wa.worker_id = wp.user_id
        LEFT JOIN Feedback fb ON c.id = fb.complaint_id
        WHERE 1=1
    """
    params = []

    if department_filter and department_filter != "All Departments":
        sql += " AND c.department = ?"
        params.append(department_filter)

    if status_filter and status_filter != "All Statuses":
        sql += " AND c.status = ?"
        params.append(status_filter)

    if start_date:
        sql += " AND date(c.submitted_at) >= date(?)"
        params.append(start_date)

    if end_date:
        sql += " AND date(c.submitted_at) <= date(?)"
        params.append(end_date)

    sql += " ORDER BY c.submitted_at DESC;"

    rows = fetch_all(sql, tuple(params), db_path=db_path)

    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write Comprehensive Headers
            writer.writerow([
                "Complaint ID", "Title", "Category", "Location", "Locality", "Ward",
                "Priority", "Emergency Flag", "Department", "Assigned Worker",
                "Citizen Name", "Citizen Phone", "Status", "Supporters",
                "Submitted At", "Verified At", "Assigned At", "Completed At", "Resolved At", "Due Date",
                "Turnaround Hours", "Citizen Rating (1-5)", "Citizen Feedback", "Admin Remarks"
            ])

            for r in rows:
                writer.writerow([
                    r["complaint_id"], r["title"], r["category"], r["location"], r["locality"], r["ward_number"] or "N/A",
                    r["priority"], "YES" if r["is_emergency"] else "NO", r["department"], r["assigned_worker"],
                    r["citizen_name"], r["citizen_phone"], r["status"], r["support_count"],
                    r["submitted_at"], r["verified_at"] or "N/A", r["assigned_at"] or "N/A",
                    r["completed_at"] or "N/A", r["resolved_at"] or "N/A", r["due_date"] or "N/A",
                    r["turnaround_hours"] if r["turnaround_hours"] is not None else "N/A",
                    r["citizen_rating"] if r["citizen_rating"] is not None else "N/A",
                    r["citizen_comments"] or "N/A",
                    r["admin_remarks"] or "N/A"
                ])

        return True, len(rows), f"Successfully exported {len(rows)} records to {filepath}."
    except Exception as exc:
        return False, 0, f"Error writing CSV file: {exc}"


def export_worker_performance_csv(filepath: str, db_path: str = DB_PATH) -> Tuple[bool, int, str]:
    """
    Exports field worker workload and completion statistics to CSV.
    """
    workers = get_worker_performance_stats(db_path=db_path)
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Worker ID", "Username", "Full Name", "Department", "Specialization",
                "Contact Phone", "Total Tasks Assigned", "Resolved Tasks", "Pending Tasks",
                "Delayed Tasks", "Completion Rate (%)"
            ])
            for w in workers:
                writer.writerow([
                    w["id"], w["username"], w["full_name"], w["department"], w["specialization"] or "N/A",
                    w["phone"], w["total_assigned"], w["completed"], w["pending"],
                    w["delayed"], f"{w['completion_rate_pct']}%"
                ])
        return True, len(workers), f"Exported {len(workers)} worker records to {filepath}."
    except Exception as exc:
        return False, 0, f"Error writing worker CSV: {exc}"


def export_department_kpi_csv(filepath: str, db_path: str = DB_PATH) -> Tuple[bool, int, str]:
    """
    Exports municipal department performance metrics to CSV.
    """
    depts = get_department_efficiency(db_path=db_path)
    try:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Department", "Total Complaints", "Resolved Count", "Active Count",
                "Overdue Count", "Resolution Rate (%)", "Average Turnaround (Hours)"
            ])
            for d in depts:
                writer.writerow([
                    d["department"], d["total_complaints"], d["resolved_count"], d["active_count"],
                    d["overdue_count"], f"{d['resolution_rate_pct']}%", f"{d['avg_turnaround_hours']} hrs"
                ])
        return True, len(depts), f"Exported {len(depts)} department KPI records to {filepath}."
    except Exception as exc:
        return False, 0, f"Error writing department CSV: {exc}"
