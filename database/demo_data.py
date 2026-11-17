"""
CivicFix Demo Data Seeding Module
Initializes standard demonstration accounts, sample complaints across various
categories, priorities, and workflow statuses for testing and evaluation.
"""

import os
from typing import Dict, Any
from database.db_connection import get_db, DB_PATH
from database.database_operations import fetch_one, execute_query, record_status_change, fetch_all
from authentication.auth import register_citizen, create_worker_account, create_admin_account
from utils.image_handler import COMPLAINT_IMAGES_DIR, COMPLETION_IMAGES_DIR


def ensure_sample_demo_images():
    """Generates visual sample Before and After demonstration images if absent."""
    try:
        from PIL import Image, ImageDraw
        before_path = os.path.join(COMPLAINT_IMAGES_DIR, "sample_pothole_before.png")
        after_path = os.path.join(COMPLETION_IMAGES_DIR, "sample_pothole_after.png")

        if not os.path.exists(before_path):
            img = Image.new("RGB", (420, 260), color="#E2E8F0")
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 40, 400, 220], fill="#4A5568")
            draw.line([20, 130, 400, 130], fill="#ED8936", width=4)
            draw.ellipse([150, 90, 270, 170], fill="#1A202C", outline="#CBD5E0", width=2)
            draw.rectangle([20, 10, 400, 36], fill="#FDE8E8")
            draw.text((30, 14), "BEFORE: Hazardous Pothole on 100ft Rd", fill="#900C1E")
            img.save(before_path)

        if not os.path.exists(after_path):
            img = Image.new("RGB", (420, 260), color="#E2E8F0")
            draw = ImageDraw.Draw(img)
            draw.rectangle([20, 40, 400, 220], fill="#4A5568")
            draw.line([20, 130, 400, 130], fill="#ED8936", width=4)
            draw.rectangle([140, 80, 280, 180], fill="#2D3748", outline="#A8D5D8", width=3)
            draw.rectangle([20, 10, 400, 36], fill="#E6F4EA")
            draw.text((30, 14), "AFTER: Asphalt Resurfaced & Level Compacted", fill="#137333")
            img.save(after_path)
    except Exception as exc:
        pass


DEMO_CREDENTIALS = [
    {
        "role": "Administrator",
        "username": "admin",
        "email": "admin@civicfix.org",
        "password": "Admin@123",
        "notes": "Full administrative control, verification, worker assignment, and reporting."
    },
    {
        "role": "Field Worker (Roads)",
        "username": "worker_raj",
        "email": "raj.sharma@civicfix.org",
        "password": "Worker@123",
        "notes": "Department: Roads | Specialization: Asphalt & Pothole Repair."
    },
    {
        "role": "Field Worker (Electrical)",
        "username": "worker_anita",
        "email": "anita.desai@civicfix.org",
        "password": "Worker@123",
        "notes": "Department: Electrical Maintenance | Specialization: Streetlights."
    },
    {
        "role": "Citizen 1",
        "username": "citizen_rahul",
        "email": "rahul.verma@example.com",
        "password": "Citizen@123",
        "notes": "Locality: Indiranagar | Reported pothole and water leak issues."
    },
    {
        "role": "Citizen 2",
        "username": "citizen_priya",
        "email": "priya.nair@example.com",
        "password": "Citizen@123",
        "notes": "Locality: Koramangala | Reported broken streetlight issue."
    },
    {
        "role": "Citizen 3",
        "username": "citizen_arun",
        "email": "arun.kumar@example.com",
        "password": "Citizen@123",
        "notes": "Locality: Whitefield | Reported illegal garbage dumping."
    }
]


def seed_demo_data(db_path: str = DB_PATH) -> bool:
    """
    Seeds demo users, sample complaints, assignments, and feedback into the database.
    Idempotent: skips seeding if demo users already exist.
    """
    # 1. Seed Administrator
    admin_user = fetch_one("SELECT id FROM Users WHERE username = 'admin';", db_path=db_path)
    if not admin_user:
        ok, admin_id, _ = create_admin_account(
            full_name="Chief Municipal Officer",
            email="admin@civicfix.org",
            username="admin",
            password="Admin@123",
            db_path=db_path
        )
    else:
        admin_id = admin_user["id"]

    # 2. Seed Field Workers
    worker1 = fetch_one("SELECT id FROM Users WHERE username = 'worker_raj';", db_path=db_path)
    if not worker1:
        ok, w1_id, _ = create_worker_account(
            admin_id=admin_id,
            full_name="Rajesh Sharma",
            email="raj.sharma@civicfix.org",
            phone="9876543211",
            username="worker_raj",
            password="Worker@123",
            department="Roads",
            specialization="Asphalt & Pothole Repair",
            db_path=db_path
        )
    else:
        w1_id = worker1["id"]

    worker2 = fetch_one("SELECT id FROM Users WHERE username = 'worker_anita';", db_path=db_path)
    if not worker2:
        ok, w2_id, _ = create_worker_account(
            admin_id=admin_id,
            full_name="Anita Desai",
            email="anita.desai@civicfix.org",
            phone="9876543212",
            username="worker_anita",
            password="Worker@123",
            department="Electrical Maintenance",
            specialization="Streetlights & Cable Network",
            db_path=db_path
        )
    else:
        w2_id = worker2["id"]

    # 3. Seed Citizens
    cit1 = fetch_one("SELECT id FROM Users WHERE username = 'citizen_rahul';", db_path=db_path)
    if not cit1:
        ok, c1_id, _ = register_citizen(
            full_name="Rahul Verma",
            email="rahul.verma@example.com",
            phone="9876543221",
            username="citizen_rahul",
            password="Citizen@123",
            confirm_password="Citizen@123",
            address="#42, 5th Cross, 100ft Road",
            locality="Indiranagar",
            db_path=db_path
        )
    else:
        c1_id = cit1["id"]

    cit2 = fetch_one("SELECT id FROM Users WHERE username = 'citizen_priya';", db_path=db_path)
    if not cit2:
        ok, c2_id, _ = register_citizen(
            full_name="Priya Nair",
            email="priya.nair@example.com",
            phone="9876543222",
            username="citizen_priya",
            password="Citizen@123",
            confirm_password="Citizen@123",
            address="#108, 4th Block, 80ft Road",
            locality="Koramangala",
            db_path=db_path
        )
    else:
        c2_id = cit2["id"]

    cit3 = fetch_one("SELECT id FROM Users WHERE username = 'citizen_arun';", db_path=db_path)
    if not cit3:
        ok, c3_id, _ = register_citizen(
            full_name="Arun Kumar",
            email="arun.kumar@example.com",
            phone="9876543223",
            username="citizen_arun",
            password="Citizen@123",
            confirm_password="Citizen@123",
            address="#215, ITPL Main Road",
            locality="Whitefield",
            db_path=db_path
        )
    else:
        c3_id = cit3["id"]

    # 4. Seed Sample Complaints if table is currently empty
    existing_complaints = fetch_one("SELECT COUNT(*) as count FROM Complaints;", db_path=db_path)
    if existing_complaints and existing_complaints["count"] == 0:
        with get_db(db_path) as conn:
            cursor = conn.cursor()

            # Complaint 1: RESOLVED (Pothole)
            cursor.execute(
                """
                INSERT INTO Complaints (
                    complaint_id, citizen_id, title, description, category,
                    location, locality, ward_number, is_emergency, is_anonymous,
                    priority, department, status, support_count, admin_remarks,
                    submitted_at, verified_at, assigned_at, completed_at, resolved_at, closed_at
                ) VALUES (
                    'CFX-2026-000001', ?, 'Deep hazardous pothole near metro pillar 45',
                    'A 2-foot wide pothole is causing vehicular damage and risk to two-wheelers.',
                    'Road damage / pothole', '100ft Road near Metro Pillar 45', 'Indiranagar',
                    'Ward 74', 0, 0, 'HIGH', 'Roads', 'RESOLVED', 4,
                    'Inspected and verified. High traffic corridor.',
                    datetime('now', '-5 days'), datetime('now', '-4 days'), datetime('now', '-3 days'),
                    datetime('now', '-1 days'), datetime('now', '-1 days'), datetime('now', '-1 days')
                );
                """,
                (c1_id,)
            )
            comp1_id = cursor.lastrowid

            # Assignment for Complaint 1
            cursor.execute(
                """
                INSERT INTO WorkerAssignments (
                    complaint_id, worker_id, assigned_by, assigned_at,
                    is_current, acknowledged_at, completion_remarks, completed_at
                ) VALUES (
                    ?, ?, ?, datetime('now', '-3 days'), 1,
                    datetime('now', '-3 days', '+2 hours'),
                    'Asphalt resurfacing completed and compacted with heavy roller.',
                    datetime('now', '-1 days')
                );
                """,
                (comp1_id, w1_id, admin_id)
            )
            asgn1_id = cursor.lastrowid

            # Status history for Complaint 1
            cursor.execute(
                """
                INSERT INTO ComplaintStatusHistory (complaint_id, previous_status, new_status, changed_by, remarks)
                VALUES 
                    (?, NULL, 'NEW', ?, 'Complaint submitted by citizen.'),
                    (?, 'NEW', 'VERIFIED', ?, 'Verified by administrator.'),
                    (?, 'VERIFIED', 'ASSIGNED', ?, 'Assigned to Rajesh Sharma (Roads).'),
                    (?, 'ASSIGNED', 'IN_PROGRESS', ?, 'Worker started resurfacing.'),
                    (?, 'IN_PROGRESS', 'COMPLETED_PENDING_VERIFICATION', ?, 'Work completed, proof uploaded.'),
                    (?, 'COMPLETED_PENDING_VERIFICATION', 'RESOLVED', ?, 'Admin verified quality and closed issue.');
                """,
                (comp1_id, c1_id, comp1_id, admin_id, comp1_id, admin_id, comp1_id, w1_id, comp1_id, w1_id, comp1_id, admin_id)
            )

            # Citizen Feedback for Complaint 1
            cursor.execute(
                """
                INSERT INTO Feedback (complaint_id, citizen_id, rating, comments, suggestions)
                VALUES (?, ?, 5, 'Quick response! Road was repaired within two days.', 'Please also repaint the zebra crossing line.');
                """,
                (comp1_id, c1_id)
            )

            # Sample Before & After Images for Complaint 1
            ensure_sample_demo_images()
            cursor.execute(
                """
                INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption)
                VALUES 
                    (?, 'uploads/complaint_images/sample_pothole_before.png', 'EVIDENCE', ?, 'Initial citizen evidence photo of pothole on 100ft Rd.'),
                    (?, 'uploads/completion_images/sample_pothole_after.png', 'COMPLETION', ?, 'Field worker resolution proof photo of compacted asphalt.');
                """,
                (comp1_id, c1_id, comp1_id, w1_id)
            )

            # Complaint 2: IN_PROGRESS (Broken Streetlight)
            cursor.execute(
                """
                INSERT INTO Complaints (
                    complaint_id, citizen_id, title, description, category,
                    location, locality, ward_number, is_emergency, is_anonymous,
                    priority, department, status, support_count, admin_remarks,
                    submitted_at, verified_at, assigned_at
                ) VALUES (
                    'CFX-2026-000002', ?, 'Broken streetlight pole flickering at night',
                    'Streetlight #L-14 is damaged and sparks during rainfall. Dark corner prone to accidents.',
                    'Broken streetlight', '80ft Road, 4th Block cross', 'Koramangala',
                    'Ward 68', 0, 0, 'MEDIUM', 'Electrical Maintenance', 'IN_PROGRESS', 2,
                    'Verified for electrical safety.',
                    datetime('now', '-3 days'), datetime('now', '-2 days'), datetime('now', '-1 days')
                );
                """,
                (c2_id,)
            )
            comp2_id = cursor.lastrowid

            # Assignment for Complaint 2
            cursor.execute(
                """
                INSERT INTO WorkerAssignments (
                    complaint_id, worker_id, assigned_by, assigned_at,
                    is_current, acknowledged_at, estimated_completion_date
                ) VALUES (
                    ?, ?, ?, datetime('now', '-1 days'), 1,
                    datetime('now', '-1 days', '+1 hour'),
                    datetime('now', '+1 days')
                );
                """,
                (comp2_id, w2_id, admin_id)
            )

            # Progress note for Complaint 2
            cursor.execute(
                """
                INSERT INTO WorkerProgressUpdates (
                    assignment_id, complaint_id, worker_id, progress_notes, status_snapshot
                ) VALUES (
                    ?, ?, ?, 'Inspected wiring. Transformer fuse replaced. New LED fixture ordered.', 'IN_PROGRESS'
                );
                """,
                (cursor.lastrowid, comp2_id, w2_id)
            )

            # Complaint 3: VERIFIED (Illegal Garbage Dumping)
            cursor.execute(
                """
                INSERT INTO Complaints (
                    complaint_id, citizen_id, title, description, category,
                    location, locality, ward_number, is_emergency, is_anonymous,
                    priority, department, status, support_count, admin_remarks,
                    submitted_at, verified_at
                ) VALUES (
                    'CFX-2026-000003', ?, 'Piles of construction debris dumped on footpath',
                    'Illegal dumping of concrete waste and garbage blocking pedestrian pathway.',
                    'Illegal dumping', 'Near Inner Circle Park gate 3', 'Whitefield',
                    'Ward 84', 0, 0, 'MEDIUM', 'Sanitation', 'VERIFIED', 5,
                    'Verified. Scheduling heavy sanitation loader vehicle.',
                    datetime('now', '-2 days'), datetime('now', '-1 days')
                );
                """,
                (c3_id,)
            )

            # Complaint 4: NEW / EMERGENCY (Water Pipe Leakage)
            cursor.execute(
                """
                INSERT INTO Complaints (
                    complaint_id, citizen_id, title, description, category,
                    location, locality, ward_number, is_emergency, is_anonymous,
                    priority, suggested_priority, priority_reason, department, status,
                    support_count, submitted_at
                ) VALUES (
                    'CFX-2026-000004', ?, 'High pressure water main leakage flooding street',
                    'Potable drinking water pipe has burst under pavement. Gushing water reaching doorsteps.',
                    'Water leakage', '12th Main Road, Corner plot 30', 'Indiranagar',
                    'Ward 74', 1, 0, 'EMERGENCY', 'EMERGENCY', 'Marked emergency by citizen with severe flooding risk.',
                    'Water Supply', 'NEW', 8, datetime('now', '-4 hours')
                );
                """,
                (c1_id,)
            )

    # Ensure Complaint 1 in an existing database has Before/After images
    ensure_sample_demo_images()
    c1 = fetch_one("SELECT id, citizen_id FROM Complaints WHERE complaint_id = 'CFX-2026-000001';", db_path=db_path)
    if c1:
        img_cnt = fetch_one("SELECT COUNT(*) as cnt FROM ComplaintImages WHERE complaint_id = ?;", (c1["id"],), db_path=db_path)
        if img_cnt and img_cnt["cnt"] == 0:
            execute_query(
                """
                INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption)
                VALUES 
                    (?, 'uploads/complaint_images/sample_pothole_before.png', 'EVIDENCE', ?, 'Initial citizen evidence photo of pothole on 100ft Rd.'),
                    (?, 'uploads/completion_images/sample_pothole_after.png', 'COMPLETION', ?, 'Field worker resolution proof photo of compacted asphalt.');
                """,
                (c1["id"], c1["citizen_id"], c1["id"], c1["citizen_id"]),
                db_path=db_path
            )

    return True
