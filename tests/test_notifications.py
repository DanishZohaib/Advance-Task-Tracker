import pytest
from database.models import Notification, User

def test_notifications_endpoints(client, payroll_headers, db_session):
    user = db_session.query(User).filter(User.username == "payroll_user").first()
    
    # 1. Manually add notifications in the database
    n1 = Notification(user_id=user.id, title="Alert 1", message="Desc 1", is_read=False)
    n2 = Notification(user_id=user.id, title="Alert 2", message="Desc 2", is_read=True)
    db_session.add_all([n1, n2])
    db_session.commit()
    
    # 2. Get all notifications
    resp = client.get("/api/notifications", headers=payroll_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["unread_count"] == 1
    assert len(data["notifications"]) == 2
    
    # 3. Get unread only
    resp_unread = client.get("/api/notifications?unread_only=true", headers=payroll_headers)
    assert resp_unread.status_code == 200
    assert len(resp_unread.json()["notifications"]) == 1
    
    # 4. Mark specific as read
    notif_id = n1.id
    resp_read = client.post(f"/api/notifications/{notif_id}/read", headers=payroll_headers)
    assert resp_read.status_code == 200
    
    # Confirm updated count
    resp2 = client.get("/api/notifications", headers=payroll_headers)
    assert resp2.json()["unread_count"] == 0
    
    # Add another unread notif to test read-all
    n3 = Notification(user_id=user.id, title="Alert 3", message="Desc 3", is_read=False)
    db_session.add(n3)
    db_session.commit()
    
    # 5. Read all
    resp_all = client.post("/api/notifications/read-all", headers=payroll_headers)
    assert resp_all.status_code == 200
    assert client.get("/api/notifications", headers=payroll_headers).json()["unread_count"] == 0
    
    # 6. Read non-existent notification - should fail
    resp_bad = client.post("/api/notifications/99999/read", headers=payroll_headers)
    assert resp_bad.status_code == 404
