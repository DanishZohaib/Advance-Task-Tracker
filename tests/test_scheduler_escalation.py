import os
import pytest
from datetime import datetime, timedelta
from database.models import Task, User, AuditLog
from backend.scheduler import run_task_escalations, ESCALATION_LOG_FILE

def test_task_escalation_rules(db_session):
    # Find payroll user
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    
    # 1. Create a task that is NOT overdue (only 2 days old)
    recent_task = Task(
        task_title="Recent Compliance Check",
        module="Payroll",
        status="Pending",
        created_by_id=u.id,
        created_at=datetime.utcnow() - timedelta(days=2),
        is_archived=False
    )
    
    # 2. Create a task that IS overdue (8 days old)
    overdue_task = Task(
        task_title="Overdue Compliance Report",
        module="Payroll",
        status="Pending",
        created_by_id=u.id,
        created_at=datetime.utcnow() - timedelta(days=8),
        is_archived=False
    )
    
    db_session.add_all([recent_task, overdue_task])
    db_session.commit()
    
    # Clean previous log file for clean check
    if os.path.exists(ESCALATION_LOG_FILE):
        os.remove(ESCALATION_LOG_FILE)
        
    # Run task escalations scan
    run_task_escalations(db_session)
    
    # Verify:
    # Overdue task should trigger escalation audit log
    overdue_logs = db_session.query(AuditLog).filter(
        AuditLog.task_id == overdue_task.id,
        AuditLog.action_type == "Email Notifications"
    ).all()
    assert len(overdue_logs) == 1
    assert "Sent escalation email alert" in overdue_logs[0].details
    
    # Recent task should NOT trigger escalation audit log
    recent_logs = db_session.query(AuditLog).filter(
        AuditLog.task_id == recent_task.id,
        AuditLog.action_type == "Email Notifications"
    ).all()
    assert len(recent_logs) == 0
    
    # Confirm file entry written to storage/escalations.log
    assert os.path.exists(ESCALATION_LOG_FILE) is True
    with open(ESCALATION_LOG_FILE, "r") as f:
         log_content = f.read()
         assert f"Task #{overdue_task.id}" in log_content
         assert "Overdue Compliance Report" in log_content
         
    # 3. Running escalation scan AGAIN immediately should NOT send duplicate email
    run_task_escalations(db_session)
    overdue_logs_twice = db_session.query(AuditLog).filter(
        AuditLog.task_id == overdue_task.id,
        AuditLog.action_type == "Email Notifications"
    ).all()
    assert len(overdue_logs_twice) == 1  # Count should remain 1 (no duplicate sent)
