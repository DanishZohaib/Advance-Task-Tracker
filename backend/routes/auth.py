from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import User
from backend.security import (
    hash_password,
    verify_password,
    validate_password_complexity,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
    get_current_user
)
from backend.utils import log_audit

router = APIRouter(prefix="/api/auth", tags=["auth"])

class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(...)
    role: str = Field(...)  # 'Manager', 'Assistant Manager', 'Executive Payroll', 'Executive Petty Cash', 'Junior Support Staff', 'NM Finance', 'GM/CFO', 'Administrator', 'Auditor'

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    username: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

@router.post("/register", response_model=TokenResponse)
def register(request_data: UserRegister, request: Request, db: Session = Depends(get_db)):
    # Validate role
    valid_roles = ["Manager", "Assistant Manager", "Executive Payroll", "Executive Petty Cash", "Junior Support Staff", "NM Finance", "GM/CFO", "Administrator", "Auditor", "Payroll Team"]
    if request_data.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of {valid_roles}"
        )
        
    role_to_save = request_data.role
        
    # Check if username exists
    existing_user = db.query(User).filter(User.username == request_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )
        
    # Validate password complexity
    if not validate_password_complexity(request_data.password):
        raise HTTPException(
            status_code=400,
            detail="Password does not meet complexity rules: at least 8 characters, with 1 uppercase, 1 lowercase, 1 digit, and 1 special character."
        )
        
    # Create user
    user = User(
        username=request_data.username,
        password_hash=hash_password(request_data.password),
        role=role_to_save,
        is_active=True
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Audit log registration
    log_audit(
        db=db,
        username=user.username,
        action_type="User Registration",
        request=request,
        user_id=user.id,
        details=f"Registered user '{user.username}' with role '{user.role}'."
    )
    
    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username
    }

@router.post("/login", response_model=TokenResponse)
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        # Audit failed login attempt
        log_audit(
            db=db,
            username=form_data.username,
            action_type="Login Failed",
            request=request,
            details=f"Failed login attempt for username '{form_data.username}'."
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User is inactive")
        
    # Generate tokens
    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    
    # Audit successful login
    log_audit(
        db=db,
        username=user.username,
        action_type="Login",
        request=request,
        user_id=user.id,
        details=f"User '{user.username}' logged in successfully."
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "role": user.role,
        "username": user.username
    }

@router.post("/refresh")
def refresh_token(request_data: TokenRefreshRequest, db: Session = Depends(get_db)):
    payload = verify_refresh_token(request_data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
        
    new_access_token = create_access_token(data={"sub": username})
    new_refresh_token = create_refresh_token(data={"sub": username})
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "role": user.role,
        "username": user.username
    }

@router.post("/logout")
def logout(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Logout",
        request=request,
        user_id=current_user.id,
        details=f"User '{current_user.username}' logged out."
    )
    return {"message": "Logged out successfully"}

@router.get("/users")
def get_users(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    users = db.query(User).filter(User.is_active == True).all()
    return [{"id": u.id, "username": u.username, "role": u.role} for u in users]

