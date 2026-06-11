import pytest
from datetime import datetime
from database.models import User, Task, WorkflowActivity, RecurringTaskMaster

def test_whatsapp_nudge_endpoint(client, admin_headers):
    # 1. Create a task to test on
    create_resp = client.post(
        "/api/tasks",
        json={
            "task_title": "Test Task for WhatsApp Nudge",
            "task_description": "Nudge testing",
            "category": "Payroll",
            "sla_days": 5
        },
        headers=admin_headers
    )
    assert create_resp.status_code == 200
    task_id = create_resp.json()["task_id"]

    # 2. Call WhatsApp nudge API
    nudge_resp = client.post(
        f"/api/tasks/{task_id}/whatsapp-nudge",
        json={
            "recipient_phone": "+923001234567",
            "message": "Nudging you for Test Task"
        },
        headers=admin_headers
    )
    assert nudge_resp.status_code == 200
    assert nudge_resp.json()["message"] == "WhatsApp nudge logged successfully"

    # 3. Retrieve task details and verify workflow activity history
    detail_resp = client.get(f"/api/tasks/{task_id}", headers=admin_headers)
    assert detail_resp.status_code == 200
    activities = detail_resp.json().get("activities", [])
    
    # Find WhatsApp nudge activity
    nudge_activity = next((a for a in activities if a["action"] == "WhatsApp Nudge Initiated"), None)
    assert nudge_activity is not None
    assert "phone: +923001234567" in nudge_activity["comments"]


def test_template_field_editing(client, admin_headers):
    # 1. Fetch user ID for template
    u_resp = client.get("/api/auth/users", headers=admin_headers)
    u_id = u_resp.json()[0]["id"]

    # 2. Create a template
    start_time = datetime.utcnow().isoformat()
    create_resp = client.post(
        "/api/recurring",
        json={
            "task_name": "Original Name",
            "department": "Payroll",
            "description": "Original guidelines",
            "responsible_person_id": u_id,
            "start_date": start_time,
            "frequency": "Monthly",
            "reminder_days": 1
        },
        headers=admin_headers
    )
    assert create_resp.status_code == 200
    temp_id = create_resp.json()["id"]

    # 3. Edit template parameters
    new_start_time = datetime.utcnow().isoformat()
    edit_resp = client.put(
        f"/api/recurring/{temp_id}",
        json={
            "task_name": "Fully Updated Name",
            "department": "Fund Accounting",
            "description": "Completely new guidelines",
            "responsible_person_id": u_id,
            "start_date": new_start_time,
            "frequency": "Weekly",
            "reminder_days": 5,
            "is_active": True
        },
        headers=admin_headers
    )
    assert edit_resp.status_code == 200

    # 4. Verify updates
    list_resp = client.get("/api/recurring", headers=admin_headers)
    assert list_resp.status_code == 200
    temp_data = next((t for t in list_resp.json() if t["id"] == temp_id), None)
    assert temp_data is not None
    assert temp_data["task_name"] == "Fully Updated Name"
    assert temp_data["category"] == "Fund Accounting"
    assert temp_data["description"] == "Completely new guidelines"
    assert temp_data["frequency"] == "Weekly"
    assert temp_data["reminder_days"] == 5
