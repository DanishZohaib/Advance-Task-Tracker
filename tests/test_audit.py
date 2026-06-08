import pytest
from datetime import datetime, timedelta

def test_audit_logs_listing_and_filtering(client, admin_headers, payroll_headers):
    # Perform an action (e.g. login) to generate audit logs
    client.post("/api/auth/login", data={"username": "payroll_user", "password": "Payroll@123"})
    
    # 1. Non-authorized user tries to retrieve audit logs - should fail
    resp = client.get("/api/audit", headers=payroll_headers)
    assert resp.status_code == 403
    
    # 2. Administrator retrieves all logs - should succeed
    resp_admin = client.get("/api/audit", headers=admin_headers)
    assert resp_admin.status_code == 200
    logs = resp_admin.json()
    assert len(logs) > 0
    
    # 3. Filter by username
    resp_user = client.get("/api/audit?username=payroll_user", headers=admin_headers)
    assert resp_user.status_code == 200
    for l in resp_user.json():
         assert "payroll_user" in l["username"].lower()
         
    # 4. Filter by action type
    resp_action = client.get("/api/audit?action_type=Login", headers=admin_headers)
    assert resp_action.status_code == 200
    for l in resp_action.json():
         assert l["action_type"] == "Login"
         
    # 5. Filter by date range
    start_dt = (datetime.utcnow() - timedelta(days=1)).isoformat()
    end_dt = (datetime.utcnow() + timedelta(days=1)).isoformat()
    resp_date = client.get(f"/api/audit?start_date={start_dt}&end_date={end_dt}", headers=admin_headers)
    assert resp_date.status_code == 200
    
    # 6. Invalid date format - should fail
    resp_bad = client.get("/api/audit?start_date=invalid-date", headers=admin_headers)
    assert resp_bad.status_code == 400
