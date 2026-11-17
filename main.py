"""
CivicFix - Local Issue Reporting and Resolution Tracking System
Main Application Entry Point

Launches the complete desktop application with:
- SQLite3 Database Initialization (14 Tables, Foreign Keys Enforced)
- PBKDF2 Hashed Demo Account Seeding (Admin, 2 Workers, 3 Citizens)
- Single Root Tkinter Window (1366x768 default, min 1100x650)
- Modern Accessible Civic Palette 🌿 (#789B83, #A3B18A, #F7F5EF, #405B4A)
- Welcome & Login Screen with Citizen Registration & Quick Demo Selectors
- Role-Based Dashboard Router (Citizen, Administrator, Field Worker)
"""

import sys
import os
import tkinter as tk

# Ensure project root is in the module search path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.schema import init_db
from database.demo_data import seed_demo_data
from gui.app import CivicFixApp


def main():
    """Initializes database, seeds demo credentials, and starts the GUI."""
    print("=" * 70)
    print("   CIVICFIX - LOCAL ISSUE REPORTING & RESOLUTION TRACKING SYSTEM")
    print("   PYTHON TKINTER DESKTOP APPLICATION")
    print("=" * 70)

    # 1. Initialize SQLite Database Schema
    print("[1/3] Initializing SQLite database schema (14 tables)...")
    init_db()

    # 2. Seed Demo Accounts & Complaints (Idempotent)
    print("[2/3] Seeding demo credentials & sample complaints...")
    seed_demo_data()

    # 3. Launch Main Desktop Tkinter Window
    print("[3/3] Launching CivicFix Desktop GUI...")
    print("-" * 70)
    print("DEMO CREDENTIALS FOR TESTING:")
    print(" • Administrator : Username: admin         | Password: Admin@123")
    print(" • Field Worker 1: Username: worker_raj    | Password: Worker@123 (Roads)")
    print(" • Field Worker 2: Username: worker_anita  | Password: Worker@123 (Electrical)")
    print(" • Citizen       : Username: citizen_rahul | Password: Citizen@123")
    print("=" * 70)

    root = tk.Tk()
    app = CivicFixApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
