# CivicFix — Interactive Demonstration & Evaluation Guide

This guide provides a step-by-step walkthrough for evaluating the **CivicFix** desktop application across its three distinct actors: **Citizen**, **Field Worker**, and **Municipal Administrator**.

---

## 🔑 Demo Login Credentials

The local database (`civicfix.db`) is pre-seeded with sample municipal data and ready-to-use demo accounts:

| Role | Username | Password | Department / Locality | Key Capabilities |
|---|---|---|---|---|
| **Administrator** | `admin` | `Admin@123` | Municipal Governance | Oversight, verification queue, worker dispatch, duplicate detection, CSV exports, audit log |
| **Field Worker** | `worker_raj` | `Worker@123` | Roads & Infrastructure | Workload dashboard, task acknowledgment, progress notes, checklists, delay reporting, proof upload |
| **Field Worker** | `worker_anita` | `Worker@123` | Electrical Maintenance | Streetlights, electrical fixtures, cable repairs, completion proofs |
| **Citizen 1** | `citizen_rahul` | `Citizen@123` | Indiranagar | Report civic issues, photo upload, visual lifecycle tracking, community support, 5-star rating |
| **Citizen 2** | `citizen_priya` | `Citizen@123` | Koramangala | Neighborhood reports, timeline inspection, reopen appeals |
| **Citizen 3** | `citizen_arun` | `Citizen@123` | Whitefield | Community issue tracking, civic upvoting |

---

## 🚀 Starting the Application

Launch the desktop application using Python in your VS Code terminal:

```powershell
python main.py
```

The application opens to the **Two-Section Modern Login Window** featuring the civic building illustration, municipal branding on the left, and three horizontal role selection cards on the right (**Citizen**, **Field Worker**, **Admin**).

---

## 📋 Walkthrough Scenarios

### Scenario 1: Citizen Issue Reporting & Real-time Tracking

1. On the login screen, select **CITIZEN LOGIN**.
2. Enter username `citizen_rahul` and password `Citizen@123`. Click **Login**.
3. You are redirected to the **Citizen Dashboard**:
   - Notice the live KPI statistics cards (`My Complaints`, `Pending`, `Resolved`, `Community Supported`).
4. In the left navigation sidebar, click **📝 Report an Issue**:
   - **Title**: `Deep hazardous pothole on 100ft Road`
   - **Category**: Select `Road damage / pothole`
   - **Locality**: Select `Indiranagar`
   - **Street Landmark**: `Near Sony World Signal, 100ft Road`
   - **Description**: `Large crater in the middle of the road causing two-wheelers to lose balance.`
   - **Emergency Flag**: Check `Mark as Emergency Hazard`
   - **Photo Upload**: (Optional) Click `Attach Photo Evidence` to select an image.
   - Click **Submit Issue & Generate CFX ID →**.
5. Note the unique complaint ID generated (e.g. `CFX-2026-000005`).
6. Click **🔍 Track Complaint** in the sidebar:
   - Select your newly filed issue from the dropdown.
   - Inspect the **Visual Chronological Lifecycle Timeline** showing the status at `NEW` with date and time.
7. Click **👥 Community Issues**:
   - Browse other neighborhood issues and click **"+1 Support Issue"** to boost community priority.

---

### Scenario 2: Administrator Triage, Verification & Worker Dispatch

1. Click **Sign Out** in the top navigation bar.
2. Select **ADMIN LOGIN**. Enter `admin` / `Admin@123` and click **Login**.
3. You are redirected to the **Administrator Command Center**:
   - Review live metric cards (`Total Issues`, `New / Pending`, `Verified`, `In Progress`, `Overdue`, `Emergency Flagged`).
   - Review the embedded Matplotlib analytics (**Complaint Status Donut Chart** and **Category-wise Bar Chart**).
4. Click **🆕 New Complaints Queue** in the sidebar:
   - Select the complaint submitted in Scenario 1.
   - Click **🔍 Inspect / Verify Issue**.
5. In the **Verification & Inspection** screen:
   - Note the **Auto-Suggested Priority Card** recommending `EMERGENCY` or `HIGH` with rule-based justification.
   - Keep or adjust the **Approved Priority** to `HIGH`.
   - Set **Department** to `Roads`.
   - Enter **Inspection Remarks**: `Verified site hazard on primary corridor. Approved for field resolution.`
   - Click **✓ Verify & Approve Issue**.
6. The app automatically navigates to **📌 Assign Complaints**:
   - Select field worker `Rajesh Sharma (worker_raj)` from the Roads department.
   - The default completion deadline (3 days from now) is automatically populated.
   - Click **Dispatch Worker & Send Notification 🚀**.
7. Click **📜 Action Audit Log** in the sidebar:
   - Observe the double-entry audit records for `VERIFY` and `TRANSITION_ASSIGNED` with administrator timestamp.

---

### Scenario 3: Field Worker Execution & Completion Proof Upload

1. Sign out and select **FIELD WORKER LOGIN**.
2. Enter `worker_raj` / `Worker@123` and click **Login**.
3. You are redirected to the **Field Worker Portal**:
   - Observe the workload metrics (`Total Assigned Tasks`, `New`, `In Progress`, `Delayed`, `Completed`).
4. Click **📋 Assigned Tasks** in the sidebar:
   - Select the newly dispatched task from the table.
5. In the task operations view:
   - Click **✓ Acknowledge Task** $\rightarrow$ Status advances to `ACKNOWLEDGED`.
   - Click **🚀 Update Progress / Notes** $\rightarrow$ Enter: `Site inspected, barricades erected, asphalt roller deployed.` $\rightarrow$ Status advances to `IN_PROGRESS`.
   - Under **Work Checklist**, check off operational items (e.g. *Inspect road surface*, *Erect safety barricades*, *Arrange asphalt mix*).
   - Under **Material Requisition**, click **➕ Add Material Requirement** $\rightarrow$ Item: `Cold Mix Bitumen`, Quantity: `4 Bags (200kg)`.
6. Click **🏆 Complete Task & Upload Proof**:
   - Click **Browse Photo** and select an image file representing the completed physical repair.
   - Enter Final Remarks: `Asphalt resurfacing completed, roller compacted, and road reopened to traffic.`
   - Click **Submit Completion Proof →**.
   - Notice the status advances to `COMPLETED_PENDING_VERIFICATION`. Administrative inspection is required before the ticket is closed.

---

### Scenario 4: Administrator Visual Audit via Before/After Comparison Widget

1. Sign out and log back in as **Administrator** (`admin` / `Admin@123`).
2. Click **🔔 Notifications** or go to **✓ Verification & Inspection**:
   - Select the complaint marked `COMPLETED_PENDING_VERIFICATION`.
3. Observe the **Side-by-Side Resolution Verification Widget**:
   - **Left Card (🔴 BEFORE)**: Displays the citizen's initial hazard evidence photo with reporting timestamp and citizen name.
   - **Right Card (🟢 AFTER)**: Displays the worker's resolution proof photo with completion timestamp and worker remarks.
   - **Turnaround Badge**: Displays the exact resolution turnaround time (e.g. `⏱ Turnaround Time: 4.5 hours`).
   - Click on either photo or press **🔍 Click to Enlarge** to open the interactive high-resolution zoom inspection modal.
4. Decision Controls:
   - If work is satisfactory: Click **✓ Approve Completion & Resolve** $\rightarrow$ Status transitions to `RESOLVED`.
   - If work is deficient: Click **↺ Request Rework** $\rightarrow$ Enter corrective instructions and return task to worker.

---

### Scenario 5: Citizen Feedback & Final Ticket Closure

1. Sign out and log in as Citizen `citizen_rahul` (`Citizen@123`).
2. Click **📋 My Complaints**:
   - Select the resolved complaint.
   - Click **⭐ Rate & Give Feedback**.
3. In the satisfaction modal:
   - Select rating: `5 Stars ★★★★★`
   - Comments: `Outstanding prompt repair! The road is completely smooth and safe again.`
   - Suggestions: `Please also repaint the lane markings.`
   - Click **Submit Review & Close Ticket**.
4. The ticket is officially archived and status is updated to `CLOSED`.

---

### Scenario 6: Reopening Appeals, Duplicate Detection & Data Exports

1. **Reopening Appeal**:
   - In **My Complaints**, select any resolved or closed complaint and click **↺ Reopen Issue**.
   - Enter justification: `Gravel has loosened after heavy rain. Requesting re-inspection.`
   - Ticket status transitions to `REOPENED` and active administrators receive real-time alerts.
2. **Duplicate Complaint Detection & Merging**:
   - Log in as Administrator.
   - Click **👥 Duplicate Detection** in the sidebar.
   - Select an issue to inspect similarity matches against other complaints in the same locality.
   - Click **Merge Selected Duplicate** to transfer support counts and close the redundant report.
3. **Advanced Analytics & Multi-Table CSV Exports**:
   - Click **📈 Reports & CSV Export** in the sidebar.
   - Review the **Department Resolution Efficiency Table** (turnaround hours and resolution `%`).
   - Review the **Locality Hotspots Table** and **Citizen Satisfaction Index**.
   - Click **📥 Export Complaints CSV** to generate a 24-column spreadsheet report.
   - Click **📥 Export Workers CSV** and **📥 Export Department KPIs CSV** for municipal reporting.

---

## 🧪 Running the Complete Automated Test Suite

To verify all 44 unit and integration tests across the entire application:

```powershell
python scripts/run_all_tests.py
```

To run individual test suites:

```powershell
python -m unittest tests/test_workflow.py -v
python -m unittest tests/test_database_integrity.py -v
python -m unittest tests/test_state_machine.py -v
python -m unittest tests/test_analytics_and_reporting.py -v
python -m unittest tests/test_system_integration.py -v
```

To verify database health:

```powershell
python scripts/verify_database.py
```
