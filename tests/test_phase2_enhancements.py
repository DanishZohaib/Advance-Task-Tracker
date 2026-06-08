import io
import pytest
import openpyxl
from datetime import datetime, timedelta
from database.models import Task, User, SystemSetting, EmailDeliveryLog
from backend.smtp_helper import encrypt_smtp_password, decrypt_smtp_password, send_smtp_email

def create_mock_excel(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()

def test_settings_smtp_management(client, admin_headers):
    # 1. Get default settings (database has no settings yet)
    resp = client.get("/api/settings/smtp", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["smtp_host"] == ""
    assert data["smtp_port"] == 587
    assert data["has_password"] is False
    
    # 2. Save SMTP settings
    resp_save = client.post(
        "/api/settings/smtp",
        json={
            "smtp_host": "smtp.mailtrap.io",
            "smtp_port": 2525,
            "smtp_sender_email": "test@enterprise.com",
            "smtp_sender_password": "supersecretpassword",
            "smtp_use_tls": True,
            "smtp_use_ssl": False
        },
        headers=admin_headers
    )
    assert resp_save.status_code == 200
    assert resp_save.json()["message"] == "SMTP Settings updated successfully"
    
    # 3. Retrieve settings again
    resp_get = client.get("/api/settings/smtp", headers=admin_headers)
    assert resp_get.status_code == 200
    data_get = resp_get.json()
    assert data_get["smtp_host"] == "smtp.mailtrap.io"
    assert data_get["smtp_port"] == 2525
    assert data_get["smtp_sender_email"] == "test@enterprise.com"
    assert data_get["has_password"] is True
    
    # 4. Try updating without password change
    resp_save_no_pwd = client.post(
        "/api/settings/smtp",
        json={
            "smtp_host": "smtp.mailtrap.io",
            "smtp_port": 2525,
            "smtp_sender_email": "newtest@enterprise.com",
            "smtp_use_tls": True,
            "smtp_use_ssl": False
        },
        headers=admin_headers
    )
    assert resp_save_no_pwd.status_code == 200
    
    # Check updated email but password remains saved
    resp_get2 = client.get("/api/settings/smtp", headers=admin_headers)
    assert resp_get2.json()["smtp_sender_email"] == "newtest@enterprise.com"
    assert resp_get2.json()["has_password"] is True

    # 5. Get email delivery logs
    resp_logs = client.get("/api/settings/email-logs", headers=admin_headers)
    assert resp_logs.status_code == 200
    assert isinstance(resp_logs.json(), list)

def test_smtp_connection_testing(client, admin_headers):
    # Test connection endpoint
    # Send incorrect server details (socket connect should fail and return error message, not crash)
    resp_test = client.post(
        "/api/settings/smtp/test",
        json={
            "smtp_host": "invalid-smtp-host.local",
            "smtp_port": 9999,
            "smtp_sender_email": "test@enterprise.com",
            "smtp_sender_password": "mypassword",
            "smtp_use_tls": True,
            "smtp_use_ssl": False
        },
        headers=admin_headers
    )
    assert resp_test.status_code == 200
    assert resp_test.json()["success"] is False
    assert "Connection test failed" in resp_test.json()["message"]

    # Test with saved password but none exists in system_settings database
    resp_test_saved_fail = client.post(
        "/api/settings/smtp/test",
        json={
            "smtp_host": "invalid-smtp-host.local",
            "smtp_port": 9999,
            "smtp_sender_email": "test@enterprise.com",
            "smtp_use_tls": True,
            "smtp_use_ssl": False,
            "use_saved_password": True
        },
        headers=admin_headers
    )
    assert resp_test_saved_fail.status_code in [200, 400]

def test_rejection_workflows(client, payroll_headers, finance_headers, cfo_headers):
    # 1. Create a task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Rejection Flow Task", "category": "Payroll"},
        headers=payroll_headers
    )
    task_id = resp.json()["task_id"]
    
    # 2. Try rejecting Pending task (should fail)
    resp_fail = client.post(
        f"/api/tasks/{task_id}/reject-nmfinance",
        json={"comments": "Should fail"},
        headers=finance_headers
    )
    assert resp_fail.status_code == 400
    
    # 3. Complete Stage 1 (Payroll)
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Stage 1 done"}, headers=payroll_headers)
    
    # 4. NM Finance rejects task back to Stage 1
    resp_reject = client.post(
        f"/api/tasks/{task_id}/reject-nmfinance",
        json={"comments": "Disbursement sheets mismatch, verify again."},
        headers=finance_headers
    )
    assert resp_reject.status_code == 200
    
    # Check status returned to Pending and rejection count updated
    task_details = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_details["status"] == "Pending"
    assert task_details["rejection_count"] == 1
    assert task_details["last_rejected_stage"] == "NM Finance"
    assert task_details["last_rejection_reason"] == "Disbursement sheets mismatch, verify again."
    
    # 5. Complete Stage 1 again
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Corrected sheets and resubmitted"}, headers=payroll_headers)
    
    # NM Finance approves
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Looks good now"}, headers=finance_headers)
    
    # 6. CFO rejects back to NM Finance (Stage 2)
    resp_cfo_reject_s2 = client.post(
        f"/api/tasks/{task_id}/reject-gmcfo",
        json={"comments": "Check NM signature comments again.", "target_stage": "NM Finance"},
        headers=cfo_headers
    )
    assert resp_cfo_reject_s2.status_code == 200
    
    # Check status returned to Payroll Completed
    task_details_2 = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_details_2["status"] == "Payroll Completed"
    assert task_details_2["rejection_count"] == 2
    assert task_details_2["last_rejected_stage"] == "GM/CFO"
    
    # 7. NM Finance approves again
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Re-verified and approved"}, headers=finance_headers)
    
    # CFO rejects back to Payroll (Stage 1)
    resp_cfo_reject_s1 = client.post(
        f"/api/tasks/{task_id}/reject-gmcfo",
        json={"comments": "Full restart required.", "target_stage": "Payroll"},
        headers=cfo_headers
    )
    assert resp_cfo_reject_s1.status_code == 200
    
    task_details_3 = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_details_3["status"] == "Pending"
    assert task_details_3["rejection_count"] == 3

    # Try invalid target stage rejection (should fail)
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Stage 1 done"}, headers=payroll_headers)
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Stage 2 done"}, headers=finance_headers)
    resp_bad_cfo_reject = client.post(
        f"/api/tasks/{task_id}/reject-gmcfo",
        json={"comments": "Full restart required.", "target_stage": "Created"},
        headers=cfo_headers
    )
    assert resp_bad_cfo_reject.status_code == 400

def test_digital_signature_generation(client, payroll_headers, finance_headers, cfo_headers):
    # Create and approve task to completion
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Signature Task", "category": "Fund Accounting"},
        headers=payroll_headers
    )
    task_id = resp.json()["task_id"]
    
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Stage 1 comment"}, headers=payroll_headers)
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Stage 2 comment"}, headers=finance_headers)
    client.post(f"/api/tasks/{task_id}/approve-gmcfo", json={"comments": "Stage 3 comment"}, headers=cfo_headers)
    
    # Retrieve task and inspect timeline signatures
    resp_details = client.get(f"/api/tasks/{task_id}", headers=payroll_headers)
    assert resp_details.status_code == 200
    activities = resp_details.json()["activities"]
    
    # We should have created activity, complete-payroll, approve-nmfinance, and approve-gmcfo (total 4)
    assert len(activities) == 4
    
    # Approvals should have digital signature hashes
    assert activities[1]["digital_signature_hash"] is not None
    assert activities[2]["digital_signature_hash"] is not None
    assert activities[3]["digital_signature_hash"] is not None
    assert len(activities[3]["digital_signature_hash"]) == 64  # SHA-256 length

def test_excel_bulk_import_validation(client, admin_headers):
    # 1. Invalid file format
    resp_bad_format = client.post(
        "/api/import/recurring",
        files={"file": ("test.txt", b"random content", "text/plain")},
        headers=admin_headers
    )
    assert resp_bad_format.status_code == 400
    
    # 2. Empty Excel worksheet
    excel_data_empty = create_mock_excel([])
    resp_empty = client.post(
        "/api/import/recurring",
        files={"file": ("test.xlsx", excel_data_empty, "application/vnd.ms-excel")},
        headers=admin_headers
    )
    assert resp_empty.status_code == 400
    assert "empty" in resp_empty.json()["detail"]
    
    # 3. Missing header columns
    excel_data_bad_headers = create_mock_excel([
        ["Task Name", "Category", "Frequency"]  # Missing other expected columns
    ])
    resp_headers = client.post(
        "/api/import/recurring",
        files={"file": ("test.xlsx", excel_data_bad_headers, "application/vnd.ms-excel")},
        headers=admin_headers
    )
    assert resp_headers.status_code == 400
    assert "Missing expected template column" in resp_headers.json()["detail"]

    # 4. Valid and invalid rows parsing
    headers = ["Task Name", "Category", "Frequency", "Description", "Responsible Role", "Reminder Days", "Start Date", "End Date", "Priority"]
    
    # Valid row + multiple validation failures
    rows = [
        headers,
        ["Weekly Bank Rec", "Fund Accounting", "Weekly", "Reconcile general ledger", "NM Finance", 2, "2026-06-10", "", "Normal"],
        ["Daily Petty Cash", "BadCategory", "Daily", "Cash check", "BadRole", -5, "2026-06-10", "", "High"],
        ["", "Payroll", "Daily", "", "Payroll Team", "not-an-int", "bad-date", "bad-date", "BadPriority"]
    ]
    excel_data = create_mock_excel(rows)
    resp_import = client.post(
        "/api/import/recurring",
        files={"file": ("test.xlsx", excel_data, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=admin_headers
    )
    assert resp_import.status_code == 200
    report = resp_import.json()
    assert report["success_count"] == 1
    assert report["failure_count"] == 2
    assert len(report["errors"]) == 2
    assert report["errors"][0]["row"] == 3
    assert report["errors"][1]["row"] == 4

def test_advanced_reports_endpoints(client, admin_headers, payroll_headers, finance_headers, cfo_headers):
    # Pre-populate database with active items to cover loop bodies
    resp_task = client.post(
        "/api/tasks",
        json={"task_title": "Reporting Completed Task", "category": "Audit Schedules"},
        headers=payroll_headers
    )
    task_id = resp_task.json()["task_id"]
    
    # Run it through stages
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Stage 1 finished"}, headers=payroll_headers)
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Stage 2 finished"}, headers=finance_headers)
    client.post(f"/api/tasks/{task_id}/approve-gmcfo", json={"comments": "Stage 3 finished"}, headers=cfo_headers)
    
    # Upload evidence file to populate evidence list
    files = {"file": ("audit_evidence.png", b"fake data content", "image/png")}
    client.post("/api/files/upload", headers=payroll_headers, files=files)
    
    # Trigger some audit log actions
    client.get("/api/auth/users", headers=admin_headers)

    # Test CSV report downloads
    resp_csv_tasks = client.get("/api/reports/csv?report_type=tasks", headers=admin_headers)
    assert resp_csv_tasks.status_code == 200
    assert resp_csv_tasks.headers["content-type"] == "text/csv; charset=utf-8"
    
    resp_csv_audit = client.get("/api/reports/csv?report_type=audit", headers=admin_headers)
    assert resp_csv_audit.status_code == 200
    
    resp_csv_evidence = client.get("/api/reports/csv?report_type=evidence", headers=admin_headers)
    assert resp_csv_evidence.status_code == 200
    
    resp_csv_invalid = client.get("/api/reports/csv?report_type=invalid", headers=admin_headers)
    assert resp_csv_invalid.status_code == 400
    
    # Test Excel workbook export
    resp_excel = client.get("/api/reports/excel", headers=admin_headers)
    assert resp_excel.status_code == 200
    assert "spreadsheet" in resp_excel.headers["content-type"]
    
    # Test PDF Summary export
    resp_pdf = client.get("/api/reports/pdf", headers=admin_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"

def test_smtp_helper_encryption():
    raw_pass = "my-secure-smtp-password"
    enc = encrypt_smtp_password(raw_pass)
    dec = decrypt_smtp_password(enc)
    assert raw_pass == dec

def test_smtp_helper_email_logger(db_session):
    # Tests database logging of notifications fallback when SMTP server is not set up
    send_smtp_email(
        db=db_session,
        event_type="Task Approved",
        recipient="test@example.com",
        subject="Test Fallback",
        body="Body of test message."
    )
    # Check that log entry exists
    log = db_session.query(EmailDeliveryLog).filter(EmailDeliveryLog.recipient == "test@example.com").first()
    assert log is not None
    assert log.subject == "Test Fallback"
    assert log.status == "Sent (Mock Logging)"
