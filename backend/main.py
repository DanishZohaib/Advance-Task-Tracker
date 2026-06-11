import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from database.connection import Base, engine, SessionLocal
from database.models import User
from backend.security import hash_password
from backend.routes import auth, tasks, recurring, notifications, audit, files, reports, settings, import_tasks
from backend.scheduler import start_scheduler

app = FastAPI(
    title="TaskTracker Pro Enterprise Edition API",
    description="Secured backend REST APIs for Enterprise Task Management & Audit Monitoring System",
    version="1.0.0"
)

# Enable CORS for the frontend Streamlit client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all endpoint routers
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(recurring.router)
app.include_router(notifications.router)
app.include_router(audit.router)
app.include_router(files.router)
app.include_router(reports.router)
app.include_router(settings.router)
app.include_router(import_tasks.router)



from database.models import User, Role, UserHierarchy, ApprovalMatrix, WorkflowDefinition, WorkflowStep

def initialize_default_users():
    """
    Creates default roles, users, hierarchies, and approval matrices for Finance & Payroll workflow
    """
    db = SessionLocal()
    try:
        # 1. Seed Roles
        roles_to_seed = [
            ("Manager", "Finance & Payroll Department Manager"),
            ("Assistant Manager", "Fund Accounting Assistant Manager"),
            ("Executive Payroll", "Payroll Processing Executive"),
            ("Executive Petty Cash", "Petty Cash Disbursements Executive"),
            ("Junior Support Staff", "General Support Activities Staff"),
            ("NM Finance", "NM Finance Approver"),
            ("GM/CFO", "GM/CFO Approver"),
            ("Administrator", "System Administrator"),
            ("Auditor", "Compliance Auditor")
        ]
        role_map = {}
        for role_name, desc in roles_to_seed:
            existing_role = db.query(Role).filter(Role.name == role_name).first()
            if not existing_role:
                r = Role(name=role_name, description=desc)
                db.add(r)
                db.flush()
                role_map[role_name] = r.id
            else:
                role_map[role_name] = existing_role.id

        # 2. Seed Users
        users = [
            ("admin", "Admin@123", "Administrator"),
            ("payroll_user", "Payroll@123", "Manager"),
            ("assistant_manager", "AMPass@123", "Assistant Manager"),
            ("executive_payroll", "ExecPay@123", "Executive Payroll"),
            ("executive_pettycash", "ExecPetty@123", "Executive Petty Cash"),
            ("junior_support", "JuniorPass@123", "Junior Support Staff"),
            ("finance_user", "Finance@123", "NM Finance"),
            ("cfo_user", "CfoPass@123", "GM/CFO"),
            ("auditor", "Auditor@123", "Auditor"),
            ("auditor_user", "Auditor@123", "Auditor") # Legacy test compatibility
        ]
        
        user_id_map = {}
        for name, pwd, role_name in users:
            existing = db.query(User).filter(User.username == name).first()
            if not existing:
                u = User(
                    username=name,
                    password_hash=hash_password(pwd),
                    role=role_name,
                    is_active=True
                )
                db.add(u)
                db.flush()
                user_id_map[name] = u.id
            else:
                # Update role string just in case
                existing.role = role_name
                user_id_map[name] = existing.id
        db.commit()

        # 3. Seed User Hierarchy (AM, Exec Payroll, Exec Petty Cash, Junior Support report to Manager)
        manager_id = user_id_map.get("payroll_user")
        subordinates = ["assistant_manager", "executive_payroll", "executive_pettycash", "junior_support"]
        for sub_name in subordinates:
            sub_id = user_id_map.get(sub_name)
            if manager_id and sub_id:
                existing_rel = db.query(UserHierarchy).filter(
                    UserHierarchy.user_id == sub_id,
                    UserHierarchy.reports_to_id == manager_id
                ).first()
                if not existing_rel:
                    rel = UserHierarchy(user_id=sub_id, reports_to_id=manager_id)
                    db.add(rel)

        # 4. Seed Approval Matrix & Workflows
        categories = ["Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules", "General Support Activities"]
        for cat in categories:
            # Seed WorkflowDefinition
            existing_wf = db.query(WorkflowDefinition).filter(WorkflowDefinition.category == cat).first()
            if not existing_wf:
                wf = WorkflowDefinition(name=f"{cat} Workflow", category=cat)
                db.add(wf)
                db.flush()
                # Seed steps
                # All follow Manager -> NM Finance -> GM/CFO escalations
                db.add(WorkflowStep(workflow_definition_id=wf.id, step_number=1, role="Manager"))
                db.add(WorkflowStep(workflow_definition_id=wf.id, step_number=2, role="NM Finance"))
                db.add(WorkflowStep(workflow_definition_id=wf.id, step_number=3, role="GM/CFO"))
            
            # Seed Approval Matrix
            # payroll_user initiates Payroll Category
            if cat == "Payroll":
                initiator = "Manager"
            elif cat == "Fund Accounting":
                initiator = "Assistant Manager"
            elif cat == "Petty Cash":
                initiator = "Executive Petty Cash"
            elif cat == "Audit Schedules":
                initiator = "Executive Payroll"
            else:
                initiator = "Junior Support Staff"
                
            steps = ["Manager", "NM Finance", "GM/CFO"]
            for idx, step_role in enumerate(steps, start=1):
                existing_matrix = db.query(ApprovalMatrix).filter(
                    ApprovalMatrix.category == cat,
                    ApprovalMatrix.initiator_role == initiator,
                    ApprovalMatrix.approver_role == step_role,
                    ApprovalMatrix.sequence == idx
                ).first()
                if not existing_matrix:
                    matrix = ApprovalMatrix(
                        category=cat,
                        initiator_role=initiator,
                        approver_role=step_role,
                        sequence=idx
                    )
                    db.add(matrix)
                    
        db.commit()
    finally:
        db.close()

@app.on_event("startup")
def on_startup():
    # Automatically initialize SQLite tables if not using PostgreSQL migration runner
    # For PostgreSQL in prod, Alembic handles migrations.
    Base.metadata.create_all(bind=engine)
    initialize_default_users()
    
    # Start background scheduler
    start_scheduler()

@app.get("/")
def read_root():
    return {"message": "TaskTracker Pro Enterprise API is healthy & running."}
