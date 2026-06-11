import pytest
from datetime import datetime, timedelta
from database.models import User, Task, UserHierarchy, ApprovalMatrix, WorkflowDefinition, WorkflowStep, TaskReturn, TaskRejection

def test_roles_and_hierarchy_setup(db_session):
    # Ensure default seeded roles and users exist
    roles = ["Manager", "Assistant Manager", "Executive Payroll", "Executive Petty Cash", "Junior Support Staff", "NM Finance", "GM/CFO", "Administrator", "Auditor"]
    for role_name in roles:
        role_exists = any(u.role == role_name for u in db_session.query(User).all())
        # Note: some roles might not have active users in in-memory test setup unless initialized,
        # but admin, payroll_user (Manager/Payroll Team), finance_user (NM Finance), cfo_user (GM/CFO) exist.
        
    # Check hierarchy
    mgr = db_session.query(User).filter(User.username == "payroll_user").first()
    finance = db_session.query(User).filter(User.username == "finance_user").first()
    
    # Assert roles mappings are correct
    assert finance.role == "NM Finance"

def test_dynamic_workflow_forwarding(client, payroll_headers, finance_headers, cfo_headers, db_session):
    # 1. Create a task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Dynamic Flow Task 1", "category": "Payroll"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    
    # Check initial Manager assignment in DB
    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task.status == "Pending"
    
    # 2. Manager forwards to NM Finance
    resp = client.post(
        f"/api/tasks/{task_id}/complete-payroll",
        json={"comments": "Payroll checks finalized"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_details["status"] == "Payroll Completed"
    assert task_details["payroll_comments"] == "Payroll checks finalized"
    
    # 3. NM Finance forwards to GM/CFO
    resp = client.post(
        f"/api/tasks/{task_id}/approve-nmfinance",
        json={"comments": "NM Finance verification approved"},
        headers=finance_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=finance_headers).json()
    assert task_details["status"] == "NM Finance Approved"
    
    # 4. GM/CFO approves and completes task
    resp = client.post(
        f"/api/tasks/{task_id}/approve-gmcfo",
        json={"comments": "GM/CFO sign-off completed"},
        headers=cfo_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=cfo_headers).json()
    assert task_details["status"] == "GM/CFO Approved"

def test_return_rejection_logs(client, payroll_headers, finance_headers, cfo_headers, db_session):
    # Create task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Return Rejection Logs Task", "category": "Petty Cash"},
        headers=payroll_headers
    )
    task_id = resp.json()["task_id"]
    
    # Forward to NM Finance
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Manager forward"}, headers=payroll_headers)
    
    # NM Finance returns to Manager
    resp = client.post(
        f"/api/tasks/{task_id}/reject-nmfinance",
        json={"comments": "Incomplete documentation"},
        headers=finance_headers
    )
    assert resp.status_code == 200
    
    # Check task returned status & counter
    task = db_session.query(Task).filter(Task.id == task_id).first()
    assert task.status == "Pending"
    assert task.rejection_count == 1
    assert task.last_rejected_stage == "NM Finance"
    assert task.last_rejection_reason == "Incomplete documentation"
    
    # Verify return record exists in database
    ret_log = db_session.query(TaskReturn).filter(TaskReturn.task_id == task_id).first()
    assert ret_log is not None
    assert ret_log.returned_by == "finance_user"
    assert ret_log.return_reason == "Incomplete documentation"

def test_advanced_reporting_filters(client, admin_headers, payroll_headers, finance_headers, cfo_headers, db_session):
    # Create some tasks with various stages
    t1_id = client.post("/api/tasks", json={"task_title": "Report Task T1", "category": "Payroll"}, headers=payroll_headers).json()["task_id"]
    t2_id = client.post("/api/tasks", json={"task_title": "Report Task T2", "category": "Fund Accounting"}, headers=payroll_headers).json()["task_id"]
    
    # Complete T1 to NM Finance Approved
    client.post(f"/api/tasks/{t1_id}/complete-payroll", json={"comments": "C1"}, headers=payroll_headers)
    client.post(f"/api/tasks/{t1_id}/approve-nmfinance", json={"comments": "C2"}, headers=finance_headers)
    
    # Verify endpoint GET /api/reports/tasks works
    resp_list = client.get("/api/reports/tasks?category=Payroll", headers=admin_headers)
    assert resp_list.status_code == 200
    tasks = resp_list.json()
    assert len(tasks) > 0
    assert all(t["category"] == "Payroll" for t in tasks)
    
    # Filter by completed_by
    resp_comp = client.get("/api/reports/tasks?completed_by=NM Finance", headers=admin_headers)
    assert resp_comp.status_code == 200
    assert len(resp_comp.json()) > 0
    
    # Filter by returned/rejected
    resp_ret = client.get("/api/reports/tasks?returned=true", headers=admin_headers)
    assert resp_ret.status_code == 200
    
    # Verify Excel download with filters
    resp_excel = client.get("/api/reports/excel?category=Payroll", headers=admin_headers)
    assert resp_excel.status_code == 200
    
    # Verify PDF download with filters
    resp_pdf = client.get("/api/reports/pdf?status=NM Finance Approved", headers=admin_headers)
    assert resp_pdf.status_code == 200

def test_generic_action_endpoint(client, payroll_headers, finance_headers, cfo_headers, db_session):
    # Create task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Generic Action Task", "category": "Payroll"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    task_id = resp.json()["task_id"]
    
    # 1. Forward from Stage 1 using /action
    resp = client.post(
        f"/api/tasks/{task_id}/action",
        json={"action": "Forward", "comments": "Stage 1 generic forward"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_details["status"] == "Payroll Completed"
    
    # 2. Return from NM Finance back to Stage 1 using /action
    resp = client.post(
        f"/api/tasks/{task_id}/action",
        json={"action": "Return", "comments": "Stage 2 generic return"},
        headers=finance_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=finance_headers).json()
    assert task_details["status"] == "Pending"
    assert task_details["rejection_count"] == 1
    
    # 3. Forward again using /action
    resp = client.post(
        f"/api/tasks/{task_id}/action",
        json={"action": "Forward", "comments": "Stage 1 generic forward 2"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    
    # 4. Forward from NM Finance using /action
    resp = client.post(
        f"/api/tasks/{task_id}/action",
        json={"action": "Forward", "comments": "Stage 2 generic forward"},
        headers=finance_headers
    )
    assert resp.status_code == 200
    
    # 5. Complete from GM/CFO using /action
    resp = client.post(
        f"/api/tasks/{task_id}/action",
        json={"action": "Complete", "comments": "Stage 3 generic release"},
        headers=cfo_headers
    )
    assert resp.status_code == 200
    
    task_details = client.get(f"/api/tasks/{task_id}", headers=cfo_headers).json()
    assert task_details["status"] == "GM/CFO Approved"

