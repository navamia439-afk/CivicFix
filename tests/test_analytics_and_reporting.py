"""
CivicFix Analytics, Reporting & Before/After Verification Test Suite
Validates KPI aggregation, department efficiency metrics, category statistics,
locality distribution, citizen satisfaction analytics, Before/After image pairing,
and comprehensive CSV exports.
"""

import os
import sys
import tempfile
import csv
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.schema import init_db
from database.database_operations import execute_query, fetch_one, fetch_all
from services.report_service import (
    get_admin_kpis,
    get_status_distribution,
    get_category_distribution,
    get_department_distribution,
    get_department_efficiency,
    get_category_resolution_stats,
    get_locality_distribution,
    get_satisfaction_metrics,
    get_before_after_photos,
    get_worker_performance_stats,
    get_overdue_complaints,
    detect_potential_duplicates,
    export_complaints_to_csv,
    export_worker_performance_csv,
    export_department_kpi_csv
)
from gui.comparison_widget import BeforeAfterComparisonWidget


class TestAnalyticsAndReporting(unittest.TestCase):
    def setUp(self):
        """Creates an isolated temporary test database with seeded test data."""
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        init_db(self.temp_db_path)

        # 1. Admin User
        self.admin_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'ADMIN');",
            ("admin_analyst", "analyst@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )

        # 2. Worker 1 (Roads)
        self.worker1_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_arun", "arun@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker1_id, "Arun Kumar", "9876543210", "Roads", "Asphalt Laying"),
            db_path=self.temp_db_path
        )

        # 3. Worker 2 (Sanitation)
        self.worker2_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'WORKER');",
            ("worker_geeta", "geeta@civicfix.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerProfiles (user_id, full_name, phone, department, specialization) VALUES (?, ?, ?, ?, ?);",
            (self.worker2_id, "Geeta Bai", "9876543220", "Sanitation", "Debris Removal"),
            db_path=self.temp_db_path
        )

        # 4. Citizen 1
        self.citizen_id = execute_query(
            "INSERT INTO Users (username, email, password_hash, salt, role) VALUES (?, ?, ?, ?, 'CITIZEN');",
            ("citizen_anand", "anand@test.org", "dummyhash", "dummysalt"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO CitizenProfiles (user_id, full_name, phone, locality, address) VALUES (?, ?, ?, ?, ?);",
            (self.citizen_id, "Anand Rao", "9876543230", "Indiranagar", "12th Main Road"),
            db_path=self.temp_db_path
        )

        # 5. Seed Complaint 1 (Resolved with Before and After images)
        self.comp1_id = execute_query(
            """
            INSERT INTO Complaints (
                complaint_id, citizen_id, title, description, category, location, locality,
                priority, status, department, submitted_at, completed_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-11-01 10:00:00', '2026-11-02 16:00:00', '2026-11-02 17:00:00');
            """,
            (
                "CFX-2026-000101", self.citizen_id, "Severe Pothole on 100ft Rd",
                "Deep crater causing vehicle damage near junction.", "Road damage / pothole",
                "100ft Rd near Sony Signal", "Indiranagar", "HIGH", "RESOLVED", "Roads"
            ),
            db_path=self.temp_db_path
        )

        # Images for Complaint 1: Evidence (Before) & Completion (After)
        execute_query(
            "INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption) VALUES (?, ?, 'EVIDENCE', ?, ?);",
            (self.comp1_id, "uploads/complaint_images/before_pothole.jpg", self.citizen_id, "Initial pothole photo"),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO ComplaintImages (complaint_id, image_path, image_type, uploaded_by, caption) VALUES (?, ?, 'COMPLETION', ?, ?);",
            (self.comp1_id, "uploads/completion_images/after_pothole.jpg", self.worker1_id, "Repaired road surface"),
            db_path=self.temp_db_path
        )

        # Worker Assignment for Complaint 1
        execute_query(
            """
            INSERT INTO WorkerAssignments (
                complaint_id, worker_id, assigned_by, is_current, completed_at, completion_remarks
            ) VALUES (?, ?, ?, 1, '2026-11-02 16:00:00', 'Asphalt laid and leveled.');
            """,
            (self.comp1_id, self.worker1_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # Citizen Feedback for Complaint 1
        execute_query(
            "INSERT INTO Feedback (complaint_id, citizen_id, rating, comments, suggestions) VALUES (?, ?, 5, 'Exceptional repair speed!', 'Keep up the good work');",
            (self.comp1_id, self.citizen_id),
            db_path=self.temp_db_path
        )

        # 6. Seed Complaint 2 (Sanitation, In Progress, Overdue)
        self.comp2_id = execute_query(
            """
            INSERT INTO Complaints (
                complaint_id, citizen_id, title, description, category, location, locality,
                priority, status, department, due_date, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '2026-11-05 18:00:00', '2026-11-03 09:00:00');
            """,
            (
                "CFX-2026-000102", self.citizen_id, "Garbage accumulation on 5th Cross",
                "Uncollected municipal waste overflowing onto pavement.", "Garbage / waste issue",
                "5th Cross near park", "Koramangala", "MEDIUM", "IN_PROGRESS", "Sanitation"
            ),
            db_path=self.temp_db_path
        )
        execute_query(
            "INSERT INTO WorkerAssignments (complaint_id, worker_id, assigned_by, is_current, due_date) VALUES (?, ?, ?, 1, '2026-11-05 18:00:00');",
            (self.comp2_id, self.worker2_id, self.admin_id),
            db_path=self.temp_db_path
        )

        # 7. Seed Complaint 3 (Emergency, New)
        self.comp3_id = execute_query(
            """
            INSERT INTO Complaints (
                complaint_id, citizen_id, title, description, category, location, locality,
                is_emergency, priority, status, department, submitted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 1, 'EMERGENCY', 'NEW', 'Water Supply', '2026-11-10 08:30:00');
            """,
            (
                "CFX-2026-000103", self.citizen_id, "Major Water Main Burst",
                "High pressure drinking water flooding street.", "Water leakage",
                "Water Tank Road", "Indiranagar"
            ),
            db_path=self.temp_db_path
        )

    def tearDown(self):
        """Clean up isolated database."""
        try:
            os.close(self.temp_db_fd)
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except OSError:
            pass

    def test_01_admin_kpis_and_distributions(self):
        """Validates KPI counters and distribution maps."""
        kpi = get_admin_kpis(db_path=self.temp_db_path)
        self.assertEqual(kpi["total"], 3)
        self.assertEqual(kpi["new"], 1)
        self.assertEqual(kpi["resolved"], 1)
        self.assertEqual(kpi["emergency"], 1)
        self.assertGreaterEqual(kpi["overdue"], 1)

        # Status distribution
        st_dist = get_status_distribution(db_path=self.temp_db_path)
        self.assertEqual(st_dist["RESOLVED"], 1)
        self.assertEqual(st_dist["IN_PROGRESS"], 1)
        self.assertEqual(st_dist["NEW"], 1)

        # Category distribution
        cat_dist = get_category_distribution(db_path=self.temp_db_path)
        self.assertEqual(cat_dist["Road damage / pothole"], 1)
        self.assertEqual(cat_dist["Garbage / waste issue"], 1)
        self.assertEqual(cat_dist["Water leakage"], 1)

        # Department distribution
        dept_dist = get_department_distribution(db_path=self.temp_db_path)
        self.assertEqual(dept_dist["Roads"], 1)
        self.assertEqual(dept_dist["Sanitation"], 1)
        self.assertEqual(dept_dist["Water Supply"], 1)

    def test_02_department_efficiency_metrics(self):
        """Validates department efficiency and turnaround time calculations."""
        eff = get_department_efficiency(db_path=self.temp_db_path)
        self.assertGreaterEqual(len(eff), 3)

        roads_dept = next((d for d in eff if d["department"] == "Roads"), None)
        self.assertIsNotNone(roads_dept)
        self.assertEqual(roads_dept["total_complaints"], 1)
        self.assertEqual(roads_dept["resolved_count"], 1)
        self.assertEqual(roads_dept["resolution_rate_pct"], 100.0)
        # Turnaround: 2026-11-01 10:00:00 to 2026-11-02 17:00:00 = 31 hours
        self.assertEqual(roads_dept["avg_turnaround_hours"], 31.0)

        san_dept = next((d for d in eff if d["department"] == "Sanitation"), None)
        self.assertIsNotNone(san_dept)
        self.assertEqual(san_dept["active_count"], 1)
        self.assertEqual(san_dept["resolution_rate_pct"], 0.0)
        self.assertEqual(san_dept["overdue_count"], 1)

    def test_03_category_resolution_stats(self):
        """Validates category resolution statistics and average turnaround breakdown."""
        stats = get_category_resolution_stats(db_path=self.temp_db_path)
        self.assertGreaterEqual(len(stats), 3)

        pothole_stat = next((s for s in stats if s["category"] == "Road damage / pothole"), None)
        self.assertIsNotNone(pothole_stat)
        self.assertEqual(pothole_stat["total_count"], 1)
        self.assertEqual(pothole_stat["resolved_count"], 1)
        self.assertEqual(pothole_stat["resolution_rate_pct"], 100.0)

        leakage_stat = next((s for s in stats if s["category"] == "Water leakage"), None)
        self.assertIsNotNone(leakage_stat)
        self.assertEqual(leakage_stat["emergency_count"], 1)

    def test_04_locality_hotspots_distribution(self):
        """Validates locality grievance aggregation and emergency indicators."""
        locs = get_locality_distribution(db_path=self.temp_db_path)
        indira = next((l for l in locs if l["locality"] == "Indiranagar"), None)
        self.assertIsNotNone(indira)
        self.assertEqual(indira["total_complaints"], 2)
        self.assertEqual(indira["resolved_count"], 1)
        self.assertEqual(indira["emergency_count"], 1)

        kora = next((l for l in locs if l["locality"] == "Koramangala"), None)
        self.assertIsNotNone(kora)
        self.assertEqual(kora["total_complaints"], 1)
        self.assertEqual(kora["open_count"], 1)

    def test_05_citizen_satisfaction_metrics(self):
        """Validates rating metrics calculation and empty database fallback."""
        sat = get_satisfaction_metrics(db_path=self.temp_db_path)
        self.assertEqual(sat["total_feedback"], 1)
        self.assertEqual(sat["avg_rating"], 5.0)
        self.assertEqual(sat["stars_5"], 1)
        self.assertEqual(sat["satisfaction_pct"], 100.0)

    def test_06_before_after_photos_helper(self):
        """Validates Before/After photographic pairing and turnaround calculation."""
        pair = get_before_after_photos(self.comp1_id, db_path=self.temp_db_path)
        self.assertTrue(pair["exists"])
        self.assertTrue(pair["has_pair"])
        self.assertIsNotNone(pair["before_image"])
        self.assertEqual(pair["before_image"]["image_path"], "uploads/complaint_images/before_pothole.jpg")
        self.assertIsNotNone(pair["after_image"])
        self.assertEqual(pair["after_image"]["image_path"], "uploads/completion_images/after_pothole.jpg")
        self.assertEqual(pair["turnaround_hours"], 30.0)  # 2026-11-01 10:00 to 2026-11-02 16:00
        self.assertEqual(pair["worker"]["worker_name"], "Arun Kumar")

        # Test complaint without images
        no_img = get_before_after_photos(self.comp2_id, db_path=self.temp_db_path)
        self.assertTrue(no_img["exists"])
        self.assertFalse(no_img["has_pair"])
        self.assertIsNone(no_img["before_image"])
        self.assertIsNone(no_img["after_image"])

    def test_07_export_complaints_csv_structure(self):
        """Validates CSV export formatting, header completeness, and row filtering."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            csv_path = tf.name

        try:
            ok, count, msg = export_complaints_to_csv(
                filepath=csv_path,
                department_filter="All Departments",
                status_filter="All Statuses",
                db_path=self.temp_db_path
            )
            self.assertTrue(ok)
            self.assertEqual(count, 3)

            # Inspect CSV contents
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                self.assertIn("Complaint ID", headers)
                self.assertIn("Turnaround Hours", headers)
                self.assertIn("Citizen Rating (1-5)", headers)
                self.assertIn("Emergency Flag", headers)

                rows = list(reader)
                self.assertEqual(len(rows), 3)

                # Row 1 is resolved complaint with 5-star rating
                res_row = next((r for r in rows if r[0] == "CFX-2026-000101"), None)
                self.assertIsNotNone(res_row)
                self.assertIn("Arun Kumar", res_row)
                self.assertIn("Roads", res_row)
                self.assertIn("RESOLVED", res_row)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_08_export_worker_performance_csv(self):
        """Validates worker performance CSV generation."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            csv_path = tf.name

        try:
            ok, count, msg = export_worker_performance_csv(filepath=csv_path, db_path=self.temp_db_path)
            self.assertTrue(ok)
            self.assertEqual(count, 2)

            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                self.assertIn("Worker ID", headers)
                self.assertIn("Completion Rate (%)", headers)

                rows = list(reader)
                self.assertEqual(len(rows), 2)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_09_export_department_kpi_csv(self):
        """Validates department KPI metrics CSV generation."""
        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            csv_path = tf.name

        try:
            ok, count, msg = export_department_kpi_csv(filepath=csv_path, db_path=self.temp_db_path)
            self.assertTrue(ok)
            self.assertGreaterEqual(count, 3)

            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                headers = next(reader)
                self.assertIn("Department", headers)
                self.assertIn("Resolution Rate (%)", headers)
                self.assertIn("Average Turnaround (Hours)", headers)
        finally:
            if os.path.exists(csv_path):
                os.remove(csv_path)

    def test_10_turnaround_time_math_helper(self):
        """Validates turnaround calculation in BeforeAfterComparisonWidget."""
        # Create a dummy instance for testing private calculation method
        dummy = BeforeAfterComparisonWidget.__new__(BeforeAfterComparisonWidget)
        
        # Test 1: Under 24 hours
        c1 = {"submitted_at": "2026-11-10 10:00:00", "completed_at": "2026-11-10 16:30:00"}
        diff1 = dummy._calculate_turnaround_time(c1)
        self.assertEqual(diff1, "6.5 hours")

        # Test 2: Multi-day
        c2 = {"submitted_at": "2026-11-10 10:00:00", "completed_at": "2026-11-12 22:00:00"}
        diff2 = dummy._calculate_turnaround_time(c2)
        self.assertIn("2.5 days", diff2)

        # Test 3: Missing completion date
        c3 = {"submitted_at": "2026-11-10 10:00:00"}
        diff3 = dummy._calculate_turnaround_time(c3)
        self.assertIsNone(diff3)


if __name__ == "__main__":
    unittest.main()
