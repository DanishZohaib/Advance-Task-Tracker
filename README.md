# 📋 TaskTracker Pro: Enterprise Edition

[![Python Version](https://img.shields.io/badge/python-3.14+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111.0-green.svg)](https://fastapi.tiangolo.com/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35.0+-red.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-Proprietary-orange.svg)](#)

An enterprise-grade, highly secure, modular Task Management, Compliance Tracking, and Audit Monitoring system designed for Finance, Payroll, Audit, and Management teams. 

TaskTracker Pro replaces basic tracking sheets with a multi-stage workflow pipeline, real-time SMTP notifications, digital approval verification, audit trail logs, and custom report compilers.

---

## 👨‍💻 System Architect & Lead Developer
Designed and built by **Danish Zohaib**.

---

## 🚀 Key Features

### 1. Departmental Category Pipeline Hierarchy
* **Department:** `Finance & Payroll`
* **Workflow Categories:**
  * 💰 **Payroll:** Payroll Processing & Disbursement
  * 📊 **Fund Accounting:** Allocations, Ledgers & Bank Reconciliations
  * 💵 **Factory Petty Cash:** Cash Disbursements & Vouchers
  * 🛡️ **Audit Schedules:** Internal Controls & Verification

### 2. Secure Multi-Stage Workflow Gateways
Sequential progress gating with automated role checks:
* **Stage 1 (Payroll Team):** Sign-off and upload verification screenshots/evidence.
* **Stage 2 (NM Finance):** Review, Approve, or Reject back to Stage 1.
* **Stage 3 (GM/CFO):** Review, Approve, or Reject back to Stage 2 or directly back to Stage 1.

### 3. Digital Approvals & Cryptographic Signatures
* Generates a **SHA-256 Approval Certificate Hash** for every task transition.
* Automatically stamps the approver's name, role, timestamp, IP address, device fingerprint, and approval remarks on the task timeline drawer.

### 4. Real-time SMTP Notification Dispatcher
* Sends email alerts for new tasks, approvals, returns, and overdue items.
* Supports **Microsoft 365, Exchange, Gmail, and Custom SMTP** servers.
* Derives a symmetric encryption key from the system JWT secret to encrypt SMTP passwords in the database.
* Maintains a detailed email delivery history log.

### 5. Advanced Auditing & Change Inspectors
* Logs system events, logins, logouts, task edits, and workflow transitions.
* Provides a side-by-side comparison dashboard of altered fields showing old and new values.

### 6. Excel Bulk Import
* Allows Administrators and GM/CFOs to bulk upload recurring tasks using a standardized Excel template.
* Performs full row-by-row structural and date validation before import.

---

## 🛠️ Technology Stack & Architecture

```
TaskTracker-Pro/
│
├── frontend/             # Streamlit SPA UI client
│   ├── app.py            # Session management, inactivity timeout, routing
│   ├── api_client.py     # JWT token auto-rotator REST client
│   ├── styles.py         # Corporate HSL Slate & Indigo styling stylesheet
│   └── pages/            # Page-views (Dashboard, Tasks, Reports, settings, notifications)
│
├── backend/              # FastAPI Server APIs
│   ├── main.py           # Endpoint routers & startup handlers
│   ├── security.py       # Bcrypt, JWT auth, and RBAC auth dependencies
│   ├── scheduler.py      # Background worker scanning overdue SLA targets
│   ├── smtp_helper.py    # Symmetric encryption & SMTP mailing
│   └── routes/           # REST endpoints
│
├── database/             # Storage Layer
│   ├── connection.py     # Connection pool loader (SQLite fallback)
│   └── models.py         # SQLAlchemy schemas
│
└── deployment/           # Production & Devops
    ├── backup.py         # Postgres & SQLite backup dumper utility
    ├── restore.py        # Database loader utility
    └── production.conf   # Nginx Reverse Proxy routing setup
```

---

## 📦 Local Installation & Setup

### 1. Prerequisites
Ensure you have Python 3.14+ installed on your system.

### 2. Setup Database & Python Virtual Environment
Initialize virtual environment and install packages:
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment (Windows)
.\venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 3. Run FastAPI Backend Server
```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```
*The backend API documentation is available at `http://127.0.0.1:8000/docs`.*

### 4. Run Streamlit Frontend Application
Open a new terminal session, activate the venv, and run:
```powershell
python -m streamlit run frontend/app.py --server.port 8501 --server.address 127.0.0.1
```
*Access the application at `http://127.0.0.1:8501`.*

---

## 👥 Default Operator Credentials
For testing and onboarding convenience, the application initiates the database with the following default credentials:

| Username | Password | Role | Access Level |
| :--- | :--- | :--- | :--- |
| `admin` | `XXXX` | `Administrator` | System Settings & Full Access |
| `payroll_user` | `XXXX` | `Payroll Team` | Stage 1 Completion |
| `finance_user` | `XXXX` | `NM Finance` | Stage 2 Approvals & Rejections |
| `cfo_user` | `XXXX` | `GM/CFO` | Stage 3 Release & Full Rejections |
| `auditor_user` | `XXXX` | `Auditor` | Audit Trail & Reports Registry |

---

## 📖 Recommended User Manual Outline

To maintain clean operational standards, users can refer to the full **Operator Manual** available in [technical_documentation.md](file:///e:/Antigravity/Advance-Task-Tracker/docs/technical_documentation.md#L45-L120).

### Recommended Manual Checklist for Operators:
1. **First-time Onboarding:**
   - Log in as `admin`.
   - Navigate to `⚙️ SMTP Admin Settings` and save SMTP details.
2. **Assigning Tasks:**
   - Navigate to `⚙️ Recurring Task Master` and register a template, or upload templates in bulk via Excel in the `Workflows & Tasks` import tab.
3. **Stage 1 (Payroll Processing):**
   - Logging in as `Payroll Team`, select a task, write required comments, upload evidence, and sign off.
4. **Stage 2 (Review & Approvals):**
   - The task will appear in the `NM Finance` dashboard queue. Verify comments and evidence, then sign off (Approve) or send back to the Payroll Team with comments (Reject).
5. **Stage 3 (GM/CFO Release):**
   - Once approved by NM Finance, the GM/CFO user opens the task, reviews the full chronological timeline showing previous signatures/remarks, and issues the final release (Complete) or returns it to a previous stage.
