import pytest

def test_task_creation_and_filtering(client, payroll_headers):
    # Create task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Payroll Run Jan", "task_description": "Run monthly payroll", "module": "Payroll"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    assert resp.json()["message"] == "Task created successfully"
    task_id = resp.json()["task_id"]
    
    # Query tasks
    list_resp = client.get("/api/tasks?module=Payroll", headers=payroll_headers)
    assert list_resp.status_code == 200
    tasks = list_resp.json()
    assert len(tasks) > 0
    assert tasks[0]["id"] == task_id
    assert tasks[0]["status"] == "Pending"

def test_approval_workflow_gating_and_roles(client, payroll_headers, finance_headers, cfo_headers, auditor_headers):
    # Create a task
    resp = client.post(
        "/api/tasks",
        json={"task_title": "Workflow Gate Task", "task_description": "Test staging gates", "module": "Fund Accounting"},
        headers=payroll_headers
    )
    task_id = resp.json()["task_id"]
    
    # 1. NM Finance tries to approve Stage 2 early (status is Pending) - should fail
    resp = client.post(
        f"/api/tasks/{task_id}/approve-nmfinance",
        json={"comments": "Premature approval"},
        headers=finance_headers
    )
    assert resp.status_code == 400
    assert "not in 'Payroll Completed' stage" in resp.json()["detail"]
    
    # 2. GM/CFO tries to approve Stage 3 early - should fail
    resp = client.post(
        f"/api/tasks/{task_id}/approve-gmcfo",
        json={"comments": "Premature approval"},
        headers=cfo_headers
    )
    assert resp.status_code == 400
    
    # 3. Auditor tries to complete Stage 1 - should fail (forbidden)
    resp = client.post(
        f"/api/tasks/{task_id}/complete-payroll",
        json={"comments": "Auditor comment"},
        headers=auditor_headers
    )
    assert resp.status_code == 403
    
    # 4. Payroll completes Stage 1 without comments - should fail
    resp = client.post(
        f"/api/tasks/{task_id}/complete-payroll",
        json={"comments": ""},
        headers=payroll_headers
    )
    assert resp.status_code == 422 # Pydantic min_length=1 error
    
    # 5. Payroll completes Stage 1 with comments - should succeed
    resp = client.post(
        f"/api/tasks/{task_id}/complete-payroll",
        json={"comments": "Stage 1 Payroll logs reconciled"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    
    # Check status
    task_detail = client.get(f"/api/tasks/{task_id}", headers=payroll_headers).json()
    assert task_detail["status"] == "Payroll Completed"
    assert task_detail["payroll_processing_time"] is not None
    assert task_detail["payroll_comments"] == "Stage 1 Payroll logs reconciled"
    
    # 6. NM Finance completes Stage 2 - should succeed
    resp = client.post(
        f"/api/tasks/{task_id}/approve-nmfinance",
        json={"comments": "Finance verification completed"},
        headers=finance_headers
    )
    assert resp.status_code == 200
    
    # Check status
    task_detail = client.get(f"/api/tasks/{task_id}", headers=finance_headers).json()
    assert task_detail["status"] == "NM Finance Approved"
    assert task_detail["nm_finance_processing_time"] is not None
    
    # 7. GM/CFO completes Stage 3 - should succeed
    resp = client.post(
        f"/api/tasks/{task_id}/approve-gmcfo",
        json={"comments": "GM Release Approved"},
        headers=cfo_headers
    )
    assert resp.status_code == 200
    
    # Check completed status
    task_detail = client.get(f"/api/tasks/{task_id}", headers=cfo_headers).json()
    assert task_detail["status"] == "GM/CFO Approved"
    assert task_detail["gmcfo_processing_time"] is not None
    assert task_detail["total_completion_time"] is not None

def test_task_edit_restrictions(client, payroll_headers, finance_headers):
    # Payroll user creates task
    task_id = client.post(
        "/api/tasks",
        json={"task_title": "Edit Task Test", "module": "Factory Petty Cash"},
        headers=payroll_headers
    ).json()["task_id"]
    
    # Finance user tries to edit (is not creator, nor admin) - should fail
    resp = client.put(
        f"/api/tasks/{task_id}",
        json={"task_title": "Hacked Title"},
        headers=finance_headers
    )
    assert resp.status_code == 403
    
    # Creator edits - should succeed
    resp = client.put(
        f"/api/tasks/{task_id}",
        json={"task_title": "Re-titled Task", "task_description": "Cleaned up instructions"},
        headers=payroll_headers
    )
    assert resp.status_code == 200
    
    # Complete the task
    client.post(f"/api/tasks/{task_id}/complete-payroll", json={"comments": "Stage 1 remarks"}, headers=payroll_headers)
    client.post(f"/api/tasks/{task_id}/approve-nmfinance", json={"comments": "Stage 2 remarks"}, headers=finance_headers)
    
    # Verify that edits on locked completed tasks fail
    # Note: complete it by CFO first
    resp = client.post(
        "/api/auth/login",
        data={"username": "cfo_user", "password": "CfoPass@123"}
    )
    cfo_tkn = resp.json()["access_token"]
    client.post(f"/api/tasks/{task_id}/approve-gmcfo", json={"comments": "Stage 3 remarks"}, headers={"Authorization": f"Bearer {cfo_tkn}"})
    
    # Now try to edit (should fail)
    resp = client.put(
        f"/api/tasks/{task_id}",
        json={"task_title": "Edit completed"},
        headers=payroll_headers
    )
    assert resp.status_code == 400
