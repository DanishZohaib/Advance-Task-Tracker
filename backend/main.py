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



def initialize_default_users():
    """
    Creates mock roles in database for testing and verification convenience
    """
    db = SessionLocal()
    try:
        users = [
            ("admin", "Admin@123", "Administrator"),
            ("payroll_user", "Payroll@123", "Payroll Team"),
            ("finance_user", "Finance@123", "NM Finance"),
            ("cfo_user", "CfoPass@123", "GM/CFO"),
            ("auditor_user", "Auditor@123", "Auditor")
        ]
        for name, pwd, role in users:
            existing = db.query(User).filter(User.username == name).first()
            if not existing:
                u = User(
                    username=name,
                    password_hash=hash_password(pwd),
                    role=role,
                    is_active=True
                )
                db.add(u)
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
