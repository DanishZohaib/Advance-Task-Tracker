# TaskTracker Pro Enterprise Edition - Technical Documentation & User Manual

Welcome to the technical documentation and operator guide for **TaskTracker Pro Enterprise Edition**, a highly secure, modular task management, compliance tracking, and audit monitoring system.

---

## 1. Modular System Architecture

The application separates frontend UI rendering from backend REST APIs to allow independent scaling, security, and deployments.

```
TaskTracker-Pro/
│
├── frontend/
│   ├── app.py              # Main dashboard framing & role security checks
│   ├── api_client.py       # REST API wrapper with transparent JWT refresh mechanics
│   ├── styles.py           # Enterprise CSS theme overrides
│   └── pages/              # Workspace interfaces (Dashboard, Tasks, etc.)
│
├── backend/
│   ├── main.py             # FastAPI entrypoint, middleware, and startup triggers
│   ├── security.py         # Bcrypt hashing, password validation, and RBAC auth dependencies
│   ├── scheduler.py        # Asynchronous background loop for escalations and templates
│   ├── utils.py            # Logger audit helpers and formatting functions
│   └── routes/             # REST Endpoints (Auth, Tasks, Recurring, Files, Reports, etc.)
│
├── database/
│   ├── connection.py       # Connection pool settings (supports Postgres, MySQL, Oracle, etc.)
│   └── models.py           # SQLAlchemy entity maps
│
└── storage/
    └── evidence/           # Server files repository for compliance uploads
```

---

## 2. Database ERD (Entity-Relationship Diagram)

The following Mermaid diagram shows the database architecture, linkages, and constraints:

```mermaid
erDiagram
    users {
        int id PK
        string username UNIQUE
        string password_hash
        string role
        boolean is_active
        datetime created_at
        datetime updated_at
    }
    tasks {
        int id PK
        string task_title
        string task_description
        string module
        string status
        int created_by_id FK
        datetime created_at
        boolean is_archived
        boolean is_edited_flag
        int edited_by_id FK
        datetime edited_at
        datetime payroll_completed_at
        int payroll_completed_by_id FK
        string payroll_comments
        int payroll_evidence_file_id FK
        float payroll_processing_time
        datetime nm_finance_approved_at
        int nm_finance_approved_by_id FK
        string nm_finance_comments
        float nm_finance_processing_time
        datetime gmcfo_approved_at
        int gmcfo_approved_by_id FK
        string gmcfo_comments
        float gmcfo_processing_time
        float total_completion_time
        int recurring_task_master_id FK
    }
    recurring_task_masters {
        int id PK
        string task_name
        string department
        string description
        int responsible_person_id FK
        datetime start_date
        string frequency
        int reminder_days
        boolean is_active
        datetime last_generated_at
        datetime created_at
    }
    files {
        int id PK
        string filename
        string filepath
        string file_hash UNIQUE
        int uploaded_by_id FK
        datetime uploaded_at
    }
    notifications {
        int id PK
        int user_id FK
        string title
        string message
        boolean is_read
        datetime created_at
    }
    audit_logs {
        int id PK
        int user_id FK
        string username
        datetime timestamp
        string ip_address
        string device_info
        string action_type
        int task_id
        string details
        string old_value
        string new_value
    }

    users ||--o{ tasks : "creates"
    users ||--o{ recurring_task_masters : "assigned_to"
    users ||--o{ files : "uploads"
    users ||--o{ notifications : "receives"
    tasks }o--|| users : "payroll_signed_off_by"
    tasks }o--|| users : "finance_approved_by"
    tasks }o--|| users : "cfo_released_by"
    tasks }o--|| files : "evidence_screenshot"
    tasks }o--|| recurring_task_masters : "instantiated_from"
```

---

## 3. Security Requirements & Roles Matrix

Authentication uses JWT access tokens (30 minutes duration) and refresh tokens (7 days duration). Inactivity auto-logout is enforced after 15 minutes of idling.

| User Role | Task Create | Stage 1 Complete | Stage 2 Approve | Stage 3 Approve | Audit Logs | Config Recur. |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Payroll Team** | Yes | **Yes** (With proof) | No | No | No | No |
| **NM Finance** | Yes | No | **Yes** | No | No | Read |
| **GM / CFO** | Yes | No | No | **Yes** | Read | **Yes** |
| **Auditor** | No | No | No | No | **Read** | Read |
| **Administrator**| **Yes** | **Yes** (Bypass) | **Yes** (Bypass) | **Yes** (Bypass) | **Yes** | **Yes** |

---

## 4. REST API Endpoint Catalog

All routes are prefixed with `/api`.

- **Authentication (`/auth`)**:
  - `POST /register`: Registers a profile (validates complexity).
  - `POST /login`: Validates user and yields access/refresh tokens.
  - `POST /refresh`: Rotates expired access tokens.
  - `GET /users`: Lists active accounts for scheduling assignments.
- **Task Pipelines (`/tasks`)**:
  - `GET /`: Queries tasks with modular and status filters.
  - `POST /`: Inserts a workflow task (Pending).
  - `PUT /{id}`: Modifies task texts (logs old/new diff).
  - `POST /{id}/complete-payroll`: Stage 1 sign-off (Payroll Team only).
  - `POST /{id}/approve-nmfinance`: Stage 2 verification (NM Finance only).
  - `POST /{id}/approve-gmcfo`: Stage 3 final approval (GM/CFO only).
  - `POST /{id}/archive`: Soft archives active tasks (deletes prohibited).
  - `POST /{id}/whatsapp-nudge`: Logs and registers a WhatsApp nudge alert in task timeline and audit logs.
- **Recurring Templates (`/recurring`)**:
  - `POST /`: Registers a master schedule template.
  - `GET /`: Lists all registered master schedule templates.
  - `PUT /{id}`: Modifies/updates scheduling template details (any field is fully editable).
- **Files (`/files`)**:
  - `POST /upload`: Uploads screenshot proof (deduplicates using SHA256).
  - `GET /download/{id}`: Streams the original file.
- **Reporting (`/reports`)**:
  - `GET /csv`: Compiles CSV files.
  - `GET /excel`: Builds multi-tab Excel files.
  - `GET /pdf`: Compiles ReportLab PDFs.

---

## 5. Deployment Guide

### Option A: Deployment Using Docker Compose (Recommended)

1. Navigate to the project root directory containing `docker-compose.yml`.
2. Launch the services:
   ```bash
   docker-compose up --build -d
   ```
3. This boots three containers:
   - `db`: PostgreSQL server on port `5432` with volume persistence.
   - `backend`: FastAPI app running on port `8000`.
   - `frontend`: Streamlit server running on port `8501`.
4. Open your browser and navigate to `http://localhost:8501`.

### Option B: Local Development Setup

1. **Database Initialization**: Ensure Python and a local DB (or SQLite default) are set up.
2. **Backend Startup**:
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   pip install -r requirements.txt
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
3. **Frontend Startup**:
   ```powershell
   .\venv\Scripts\activate
   streamlit run frontend/app.py --server.port=8501
   ```

---

## 6. User Manual & Verification Steps

To test the system complete the following walkthrough:

### Step 1: Default Test Logins
The system pre-provisions standard users on startup for testing:
- **Administrator**: `admin` / `Admin@123`
- **Payroll Team**: `payroll_user` / `Payroll@123`
- **NM Finance**: `finance_user` / `Finance@123`
- **GM/CFO**: `cfo_user` / `CfoPass@123`
- **Auditor**: `auditor_user` / `Auditor@123`

### Step 2: Creating a Task
1. Log in as `payroll_user`.
2. Under "Workflows & Tasks", click on the "Payroll" module card.
3. Choose the "Create New Task" tab, name it "Jan Disbursement", and save.
4. It appears in the "Active Workflows" column with a `Pending` status badge.

### Step 3: Moving Through the Three-Level Workflow
1. Expand the task card. You'll see the action panel: "Complete Payroll (Stage 1)".
2. Write remarks: "Disbursed wages successfully", optionally upload an evidence image file (PNG/JPG), and submit.
3. The task state transitions to `Payroll Completed` and moves down the line.
4. Log out and log in as `finance_user`. Open "Workflows & Tasks", view the task under "Active Workflows", write review comments, and click "Approve Stage 2". The task transitions to `NM Finance Approved`.
5. Log out and log in as `cfo_user`. Complete the GM/CFO final stage. The task transitions to `GM/CFO Approved` and is locked in the right column ("Completed Registry").

### Step 4: Verification of Audit Trails & Reports
1. Log in as `auditor_user`.
2. Navigate to "Security & Audit Trail" to view every single login, logout, workflow action, upload, and comment captured alongside operator IP, timestamp, and device.
3. Open "Advanced Reports" and download the compiled CSV, multi-sheet Excel, or formatted PDF documents.
