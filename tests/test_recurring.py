import pytest
from datetime import datetime, timedelta
from database.models import RecurringTaskMaster, Task, User
from backend.scheduler import run_recurring_task_generation, run_task_escalations

def test_recurring_crud_and_toggles(client, admin_headers):
    # Fetch payroll user id
    u_resp = client.get("/api/auth/users", headers=admin_headers)
    u_id = u_resp.json()[1]["id"]  # payroll_user
    
    # Create template
    start_time = datetime.utcnow().isoformat()
    resp = client.post(
        "/api/recurring",
        json={
            "task_name": "Audit Payroll Check",
            "department": "Payroll",
            "description": "Routine checks",
            "responsible_person_id": u_id,
            "start_date": start_time,
            "frequency": "Monthly",
            "reminder_days": 2
        },
        headers=admin_headers
    )
    assert resp.status_code == 200
    temp_id = resp.json()["id"]
    
    # List templates
    list_resp = client.get("/api/recurring", headers=admin_headers)
    assert list_resp.status_code == 200
    temps = list_resp.json()
    assert len(temps) > 0
    assert temps[0]["id"] == temp_id
    
    # Deactivate template
    upd_resp = client.put(
        f"/api/recurring/{temp_id}",
        json={
            "task_name": "Audit Payroll Check",
            "department": "Payroll",
            "description": "Routine checks",
            "responsible_person_id": u_id,
            "start_date": start_time,
            "frequency": "Monthly",
            "reminder_days": 2,
            "is_active": False
        },
        headers=admin_headers
    )
    assert upd_resp.status_code == 200
    
    # Check updated active state
    list_resp2 = client.get("/api/recurring", headers=admin_headers)
    assert list_resp2.json()[0]["is_active"] is False

def test_scheduler_task_generation(db_session):
    # Find payroll user
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    
    # Add an active recurring template due for generation
    past_date = datetime.utcnow() - timedelta(days=2)
    template = RecurringTaskMaster(
        task_name="Scheduled Petty Cash Audit",
        department="Factory Petty Cash",
        description="Verify cash book",
        responsible_person_id=u.id,
        start_date=past_date,
        frequency="Daily",
        reminder_days=1,
        is_active=True,
        last_generated_at=None
    )
    db_session.add(template)
    db_session.commit()
    
    # Run scheduler generation job
    run_recurring_task_generation(db_session)
    
    # Query database to confirm Task was generated
    generated_task = db_session.query(Task).filter(Task.recurring_task_master_id == template.id).first()
    assert generated_task is not None
    assert generated_task.task_title == "[Recurring] Scheduled Petty Cash Audit"
    assert generated_task.status == "Pending"
    assert template.last_generated_at is not None
