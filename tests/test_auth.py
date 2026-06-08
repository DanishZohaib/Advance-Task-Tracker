import pytest

def test_register_password_complexity(client):
    # Weak password - should fail
    resp = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "123", "role": "Payroll Team"}
    )
    assert resp.status_code == 400
    assert "Password does not meet complexity rules" in resp.json()["detail"]

    # No numbers - should fail
    resp = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "Password!", "role": "Payroll Team"}
    )
    assert resp.status_code == 400

    # No uppercase - should fail
    resp = client.post(
        "/api/auth/register",
        json={"username": "newuser", "password": "password1!", "role": "Payroll Team"}
    )
    assert resp.status_code == 400

    # Complex password - should succeed
    resp = client.post(
        "/api/auth/register",
        json={"username": "valid_user", "password": "ComplexPassword123!", "role": "Payroll Team"}
    )
    assert resp.status_code == 200
    assert "access_token" in resp.json()
    assert resp.json()["role"] == "Payroll Team"

def test_login_and_logout(client):
    # Invalid login
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "WrongPassword"}
    )
    assert resp.status_code == 401
    
    # Valid login
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "Admin@123"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["role"] == "Administrator"
    
    # Logout using token
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    logout_resp = client.post("/api/auth/logout", headers=headers)
    assert logout_resp.status_code == 200
    assert logout_resp.json()["message"] == "Logged out successfully"

def test_refresh_token(client):
    login_resp = client.post(
        "/api/auth/login",
        data={"username": "payroll_user", "password": "Payroll@123"}
    )
    ref_token = login_resp.json()["refresh_token"]
    
    # Call refresh
    refresh_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": ref_token}
    )
    assert refresh_resp.status_code == 200
    assert "access_token" in refresh_resp.json()
    assert "refresh_token" in refresh_resp.json()
    
    # Invalid refresh
    bad_resp = client.post(
        "/api/auth/refresh",
        json={"refresh_token": "invalid_refresh_token_string"}
    )
    assert bad_resp.status_code == 401
