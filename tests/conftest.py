import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.connection import Base, get_db
from database.models import User
from backend.main import app
from backend.security import hash_password

# Use separate in-memory database for testing
TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def init_test_db():
    # Setup schemas in the memory DB
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Generate default roles
        users = [
            ("admin", "Admin@123", "Administrator"),
            ("payroll_user", "Payroll@123", "Payroll Team"),
            ("finance_user", "Finance@123", "NM Finance"),
            ("cfo_user", "CfoPass@123", "GM/CFO"),
            ("auditor_user", "Auditor@123", "Auditor")
        ]
        for name, pwd, role in users:
            u = User(
                username=name,
                password_hash=hash_password(pwd),
                role=role,
                is_active=True
            )
            db.add(u)
        db.commit()
    finally:
        db.close()
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db_session():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    # Override FastAPI dependency
    def override_get_db():
        try:
            yield session
        finally:
            session.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db_session):
    return TestClient(app)

@pytest.fixture
def admin_headers(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "Admin@123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def payroll_headers(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "payroll_user", "password": "Payroll@123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def finance_headers(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "finance_user", "password": "Finance@123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def cfo_headers(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "cfo_user", "password": "CfoPass@123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def auditor_headers(client):
    resp = client.post(
        "/api/auth/login",
        data={"username": "auditor_user", "password": "Auditor@123"}
    )
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
