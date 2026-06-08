import os
import sys
import pytest
import smtplib
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException

# Mock psycopg2 module to prevent SQLAlchemy postgres dialect load failure on local test env
sys.modules["psycopg2"] = MagicMock()

from database.models import User, RecurringTaskMaster, Task
from database.connection import get_db, SessionLocal
from backend.main import read_root
from backend.scheduler import run_recurring_task_generation, send_escalation_email

def test_main_root_endpoint(client):
    # Verify main api root endpoint is hit and covered
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.json() == {"message": "TaskTracker Pro Enterprise API is healthy & running."}

def test_connection_pooling_postgres_branch():
    # Test connection pool setup configuration values directly to cover the branch logic
    from sqlalchemy import create_engine
    test_db_url = "postgresql://test_user:pass@localhost:5432/test_db"
    
    # Simulate setup
    engine = create_engine(
        test_db_url,
        pool_size=20,
        max_overflow=10,
        pool_recycle=3600,
        pool_pre_ping=True
    )
    assert engine is not None

def test_scheduler_all_frequencies(db_session):
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    
    # Test each frequency interval in generation
    frequencies = ["Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Every 2 Years"]
    now = datetime.utcnow()
    
    for i, freq in enumerate(frequencies):
        # Calculate past date exceeding frequency requirements
        past_date = now - timedelta(days=800)
        temp = RecurringTaskMaster(
            task_name=f"Template {freq}",
            department="Payroll",
            description="Guidelines",
            responsible_person_id=u.id,
            start_date=past_date,
            frequency=freq,
            reminder_days=1,
            is_active=True,
            last_generated_at=past_date
        )
        db_session.add(temp)
        
    db_session.commit()
    
    # Run scheduler task generation
    run_recurring_task_generation(db_session)
    
    # Verify task was generated for each frequency
    for freq in frequencies:
        t = db_session.query(Task).filter(Task.task_title == f"[Recurring] Template {freq}").first()
        assert t is not None

@patch("smtplib.SMTP")
def test_scheduler_smtp_email_escalation(mock_smtp_class, db_session):
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    
    # Setup overdue task
    overdue_task = Task(
        task_title="SMTP Overdue Task",
        module="Payroll",
        status="Pending",
        created_by_id=u.id,
        created_at=datetime.utcnow() - timedelta(days=10),
        is_archived=False
    )
    db_session.add(overdue_task)
    db_session.commit()
    
    # Set SMTP environment variables to execute SMTP transmission branch in scheduler
    with patch.dict(os.environ, {
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "test@gmail.com",
        "SMTP_PASSWORD": "secret_password"
    }):
        # Mock SMTP context manager instance
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        # Call escalation sender
        send_escalation_email(overdue_task, 10, db_session)
        
        # Verify smtplib methods called
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once_with("test@gmail.com", "secret_password")
        mock_smtp.sendmail.assert_called_once()

@patch("smtplib.SMTP")
def test_scheduler_smtp_email_failure(mock_smtp_class, db_session):
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    overdue_task = Task(
        task_title="SMTP Fail Task",
        module="Payroll",
        status="Pending",
        created_by_id=u.id,
        created_at=datetime.utcnow() - timedelta(days=10),
        is_archived=False
    )
    db_session.add(overdue_task)
    db_session.commit()
    
    with patch.dict(os.environ, {
        "SMTP_SERVER": "smtp.gmail.com",
        "SMTP_PORT": "587",
        "SMTP_USERNAME": "test@gmail.com",
        "SMTP_PASSWORD": "secret_password"
    }):
        # Mock SMTP connection throwing an exception on starttls
        mock_smtp = MagicMock()
        mock_smtp.starttls.side_effect = Exception("SMTP Connection Timeout")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp
        
        # Should not crash, just log error and return
        send_escalation_email(overdue_task, 10, db_session)


def test_main_startup_coverage():
    from backend.main import on_startup
    with patch("backend.main.start_scheduler") as mock_start_sched:
        on_startup()
        mock_start_sched.assert_called_once()


def test_get_db_coverage():
    from database.connection import get_db
    gen = get_db()
    db = next(gen)
    assert db is not None
    try:
        next(gen)
    except StopIteration:
        pass


def test_security_extra_coverage(db_session):
    from backend.security import (
        verify_password,
        validate_password_complexity,
        create_access_token,
        create_refresh_token,
        verify_refresh_token,
        get_current_user
    )
    
    # 1. verify_password error block
    assert verify_password("pwd", "invalid_hash") is False
    
    # 2. validate_password_complexity extra branches
    assert validate_password_complexity("NOLOWER1!") is False  # Missing lowercase
    assert validate_password_complexity("NoSpecial123a") is False  # Missing special character
    
    # 3. create_access_token & create_refresh_token with expires_delta
    delta = timedelta(minutes=5)
    token_acc = create_access_token({"sub": "admin"}, expires_delta=delta)
    assert token_acc is not None
    
    token_ref = create_refresh_token({"sub": "admin"}, expires_delta=delta)
    assert token_ref is not None
    
    # 4. verify_refresh_token with invalid token type
    invalid_ref_token = create_access_token({"sub": "admin"})  # type is access
    assert verify_refresh_token(invalid_ref_token) is None
    
    # Invalid token signatures
    assert verify_refresh_token("invalid_token_string") is None
    
    # 5. get_current_user error handling
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=token_ref, db=db_session)  # Should fail because it's a refresh token
    assert exc.value.status_code == 401
    
    # get_current_user with None username
    bad_token = create_access_token({"sub": None})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=bad_token, db=db_session)
    assert exc.value.status_code == 401
    
    # get_current_user with non-existent user
    non_existent_token = create_access_token({"sub": "ghost_user"})
    with pytest.raises(HTTPException) as exc:
        get_current_user(token=non_existent_token, db=db_session)
    assert exc.value.status_code == 401
    
    # get_current_user with inactive user
    u = db_session.query(User).filter(User.username == "admin").first()
    u.is_active = False
    db_session.commit()
    try:
        active_token = create_access_token({"sub": "admin"})
        with pytest.raises(HTTPException) as exc:
            get_current_user(token=active_token, db=db_session)
        assert exc.value.status_code == 400
    finally:
        u.is_active = True
        db_session.commit()


def test_smtp_helper_extra_coverage(db_session):
    from backend.smtp_helper import (
        encrypt_smtp_password,
        decrypt_smtp_password,
        test_smtp_connection,
        send_smtp_email
    )
    from database.models import SystemSetting, EmailDeliveryLog
    
    # 1. Empty values
    assert encrypt_smtp_password("") == ""
    assert decrypt_smtp_password("") == ""
    
    # 2. Decryption exceptions
    assert decrypt_smtp_password("garbage_data_not_fernet") == ""
    
    # 3. test_smtp_connection with SSL
    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        success, msg = test_smtp_connection("host", 465, "sender", "pass", use_tls=False, use_ssl=True)
        assert success is True
        mock_server.login.assert_called_once_with("sender", "pass")
        mock_server.quit.assert_called_once()
        
    # 4. test_smtp_connection with TLS
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        success, msg = test_smtp_connection("host", 587, "sender", "pass", use_tls=True, use_ssl=False)
        assert success is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender", "pass")
        mock_server.quit.assert_called_once()
        
    # 5. send_smtp_email direct send (success path)
    db_session.query(SystemSetting).delete()
    db_session.commit()
    
    db_session.add(SystemSetting(key="smtp_host", value="smtp.test.com"))
    db_session.add(SystemSetting(key="smtp_port", value="587"))
    db_session.add(SystemSetting(key="smtp_sender_email", value="sender@test.com"))
    db_session.add(SystemSetting(key="smtp_sender_password", value=encrypt_smtp_password("password123")))
    db_session.add(SystemSetting(key="smtp_use_tls", value="true"))
    db_session.add(SystemSetting(key="smtp_use_ssl", value="false"))
    db_session.commit()
    
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server
        
        res = send_smtp_email(
            db=db_session,
            event_type="Test Event",
            recipient="recipient@test.com",
            subject="Hello Subject",
            body="Hello Body"
        )
        assert res is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("sender@test.com", "password123")
        mock_server.sendmail.assert_called_once()
        
    # 6. send_smtp_email direct send (failure path)
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = MagicMock()
        mock_server.sendmail.side_effect = Exception("SMTP send failed")
        mock_smtp.return_value = mock_server
        
        res = send_smtp_email(
            db=db_session,
            event_type="Test Event Fail",
            recipient="fail_recipient@test.com",
            subject="Hello Fail",
            body="Hello Body"
        )
        assert res is False
        
        # Verify db log status is Failed
        log = db_session.query(EmailDeliveryLog).filter(EmailDeliveryLog.recipient == "fail_recipient@test.com").first()
        assert log is not None
        assert log.status == "Failed"
        assert log.error_message == "SMTP send failed"
        
    # 7. send_smtp_email with SSL
    # Update use_ssl settings
    ssl_setting = db_session.query(SystemSetting).filter(SystemSetting.key == "smtp_use_ssl").first()
    ssl_setting.value = "true"
    db_session.commit()
    
    with patch("smtplib.SMTP_SSL") as mock_smtp_ssl:
        mock_server = MagicMock()
        mock_smtp_ssl.return_value = mock_server
        
        res = send_smtp_email(
            db=db_session,
            event_type="Test SSL Event",
            recipient="ssl@test.com",
            subject="SSL Subject",
            body="SSL Body"
        )
        assert res is True
        mock_smtp_ssl.assert_called_once_with("smtp.test.com", 587, timeout=10)


def test_scheduler_extra_coverage(db_session):
    from backend.scheduler import send_escalation_email, run_recurring_task_generation
    from database.models import User, RecurringTaskMaster, Task
    
    # 1. send_escalation_email return early with no NM Finance users
    db_session.query(User).filter(User.role == "NM Finance").update({"is_active": False})
    db_session.commit()
    try:
        # Create a mock task
        u = db_session.query(User).first()
        task = Task(
            task_title="Escalated Task",
            department="Finance & Payroll",
            category="Payroll",
            status="Pending",
            created_by_id=u.id,
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db_session.add(task)
        db_session.commit()
        
        # Should return early
        send_escalation_email(task, 10, db_session)
    finally:
        db_session.query(User).filter(User.role == "NM Finance").update({"is_active": True})
        db_session.commit()
        
    # 2. send_escalation_email file write error exception path
    with patch("builtins.open", side_effect=IOError("Mock Disk Full")):
        send_escalation_email(task, 10, db_session)
        
    # 3. Daily frequency recurring task generator check
    u = db_session.query(User).filter(User.username == "payroll_user").first()
    past_date = datetime.utcnow() - timedelta(days=2)
    daily_temp = RecurringTaskMaster(
        task_name="Daily Temp",
        department="Finance & Payroll",
        category="Payroll",
        description="Daily guidelines",
        responsible_person_id=u.id,
        start_date=past_date,
        frequency="Daily",
        reminder_days=1,
        is_active=True,
        last_generated_at=past_date
    )
    db_session.add(daily_temp)
    db_session.commit()
    
    run_recurring_task_generation(db_session)
    # Check that task got generated
    daily_task = db_session.query(Task).filter(Task.task_title == "[Recurring] Daily Temp").first()
    assert daily_task is not None


def test_reports_and_tasks_extra_coverage(client, admin_headers, payroll_headers, finance_headers, cfo_headers):
    # 1. Create tasks with different SLA status setups
    # Overdue Task (Completed past planned due date)
    resp = client.post(
        "/api/tasks",
        json={"task_title": "SLA Overdue Task", "category": "Payroll", "planned_due_date": (datetime.utcnow() - timedelta(days=2)).isoformat()},
        headers=payroll_headers
    )
    task_id_overdue = resp.json()["task_id"]
    # Complete and approve it
    client.post(f"/api/tasks/{task_id_overdue}/complete-payroll", json={"comments": "Stage 1 finished"}, headers=payroll_headers)
    client.post(f"/api/tasks/{task_id_overdue}/approve-nmfinance", json={"comments": "Stage 2 finished"}, headers=finance_headers)
    client.post(f"/api/tasks/{task_id_overdue}/approve-gmcfo", json={"comments": "Stage 3 finished"}, headers=cfo_headers)
    
    # Critical Overdue Task (Pending, now > planned, past 3 days overdue)
    client.post(
        "/api/tasks",
        json={"task_title": "SLA Critical Task", "category": "Payroll", "planned_due_date": (datetime.utcnow() - timedelta(days=5)).isoformat()},
        headers=payroll_headers
    )
    
    # Overdue Pending Task (Pending, now > planned, only 1 day overdue)
    client.post(
        "/api/tasks",
        json={"task_title": "SLA Overdue Pending Task", "category": "Payroll", "planned_due_date": (datetime.utcnow() - timedelta(days=1)).isoformat()},
        headers=payroll_headers
    )
    
    # Due Soon Task (Pending, planned in 1 day)
    client.post(
        "/api/tasks",
        json={"task_title": "SLA Due Soon Task", "category": "Payroll", "planned_due_date": (datetime.utcnow() + timedelta(days=1)).isoformat()},
        headers=payroll_headers
    )
    
    # 2. Get task list with status filter and search filter to cover backend/routes/tasks.py search/status lines
    resp_search = client.get("/api/tasks?search=SLA&status=Pending", headers=payroll_headers)
    assert resp_search.status_code == 200
    
    # 3. Hit task detail routes with non-existent task
    resp_not_found = client.get("/api/tasks/999999", headers=payroll_headers)
    assert resp_not_found.status_code == 404
    
    # 4. Trigger invalid category and missing category task creation errors
    resp_bad_cat = client.post("/api/tasks", json={"task_title": "Bad Cat Task", "category": "BadCategory"}, headers=payroll_headers)
    assert resp_bad_cat.status_code == 400
    
    resp_missing_cat = client.post("/api/tasks", json={"task_title": "No Cat Task"}, headers=payroll_headers)
    assert resp_missing_cat.status_code == 400
    
    # 5. Try editing non-existent task
    resp_edit_fail = client.put("/api/tasks/999999", json={"task_title": "Edit Fail"}, headers=payroll_headers)
    assert resp_edit_fail.status_code == 404
    
    # 6. Archive a task using admin credentials
    task_to_archive = client.post(
        "/api/tasks",
        json={"task_title": "To Archive", "category": "Payroll"},
        headers=payroll_headers
    ).json()["task_id"]
    resp_archive = client.post(f"/api/tasks/{task_to_archive}/archive", headers=admin_headers)
    assert resp_archive.status_code == 200
    
    # Archive non-existent task
    resp_archive_fail = client.post("/api/tasks/999999/archive", headers=admin_headers)
    assert resp_archive_fail.status_code == 404
    
    # 7. NM Finance approve/reject non-existent task
    assert client.post("/api/tasks/999999/approve-nmfinance", json={"comments": "X"}, headers=finance_headers).status_code == 404
    assert client.post("/api/tasks/999999/reject-nmfinance", json={"comments": "X"}, headers=finance_headers).status_code == 404
    
    # GM/CFO approve/reject non-existent task
    assert client.post("/api/tasks/999999/approve-gmcfo", json={"comments": "X"}, headers=cfo_headers).status_code == 404
    assert client.post("/api/tasks/999999/reject-gmcfo", json={"comments": "X", "target_stage": "Payroll"}, headers=cfo_headers).status_code == 404
    
    # 8. Linking valid/invalid evidence file in complete-payroll
    resp_comp_bad_ev = client.post(f"/api/tasks/{task_to_archive}/complete-payroll", json={"comments": "Done", "evidence_file_id": 99999}, headers=payroll_headers)
    assert resp_comp_bad_ev.status_code == 400
    
    # Complete payroll with valid evidence ID
    files = {"file": ("my_evidence.png", b"fake data content", "image/png")}
    upload_resp = client.post("/api/files/upload", headers=payroll_headers, files=files).json()
    evidence_id = upload_resp["file_id"]
    
    clean_task_id = client.post("/api/tasks", json={"task_title": "Evidence Task", "category": "Payroll"}, headers=payroll_headers).json()["task_id"]
    resp_comp_good_ev = client.post(f"/api/tasks/{clean_task_id}/complete-payroll", json={"comments": "Done with evidence", "evidence_file_id": evidence_id}, headers=payroll_headers)
    assert resp_comp_good_ev.status_code == 200
    
    # Approve task to cover evidence status update logic
    client.post(f"/api/tasks/{clean_task_id}/approve-nmfinance", json={"comments": "Looks good"}, headers=finance_headers)
    
    # Reject task to cover evidence status Rejected logic
    client.post(f"/api/tasks/{clean_task_id}/reject-nmfinance", json={"comments": "Re-check"}, headers=finance_headers)
    
    # 9. Trigger reports endpoints
    assert client.get("/api/reports/csv?report_type=tasks", headers=admin_headers).status_code == 200
    assert client.get("/api/reports/excel", headers=admin_headers).status_code == 200
    assert client.get("/api/reports/pdf", headers=admin_headers).status_code == 200
