from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import SystemSetting, EmailDeliveryLog, User
from backend.security import RoleChecker, get_current_user
from backend.smtp_helper import encrypt_smtp_password, decrypt_smtp_password, test_smtp_connection
from backend.utils import log_audit

router = APIRouter(prefix="/api/settings", tags=["settings"])

class SmtpUpdate(BaseModel):
    smtp_host: str = Field(..., min_length=1)
    smtp_port: int = Field(..., ge=1)
    smtp_sender_email: str = Field(..., min_length=1)
    smtp_sender_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False

class SmtpTest(BaseModel):
    smtp_host: str
    smtp_port: int
    smtp_sender_email: str
    smtp_sender_password: Optional[str] = None
    smtp_use_tls: bool
    smtp_use_ssl: bool
    use_saved_password: bool = False

@router.get("/smtp")
def get_smtp_settings(
    current_user: User = Depends(RoleChecker(["Administrator"])),
    db: Session = Depends(get_db)
):
    settings = db.query(SystemSetting).all()
    setting_map = {s.key: s.value for s in settings}
    
    return {
        "smtp_host": setting_map.get("smtp_host", ""),
        "smtp_port": int(setting_map.get("smtp_port", "587")),
        "smtp_sender_email": setting_map.get("smtp_sender_email", ""),
        "smtp_use_tls": setting_map.get("smtp_use_tls", "true").lower() == "true",
        "smtp_use_ssl": setting_map.get("smtp_use_ssl", "false").lower() == "true",
        "has_password": bool(setting_map.get("smtp_sender_password"))
    }

@router.post("/smtp")
def update_smtp_settings(
    request_data: SmtpUpdate,
    request: Request,
    current_user: User = Depends(RoleChecker(["Administrator"])),
    db: Session = Depends(get_db)
):
    def set_setting(key: str, value: str):
        s = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if s:
            s.value = value
        else:
            s = SystemSetting(key=key, value=value)
            db.add(s)
            
    set_setting("smtp_host", request_data.smtp_host)
    set_setting("smtp_port", str(request_data.smtp_port))
    set_setting("smtp_sender_email", request_data.smtp_sender_email)
    set_setting("smtp_use_tls", str(request_data.smtp_use_tls).lower())
    set_setting("smtp_use_ssl", str(request_data.smtp_use_ssl).lower())
    
    if request_data.smtp_sender_password is not None:
        enc_pwd = encrypt_smtp_password(request_data.smtp_sender_password)
        set_setting("smtp_sender_password", enc_pwd)
        
    db.commit()
    
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Editing", # Fits context of editing admin config
        request=request,
        user_id=current_user.id,
        details="Updated SMTP Mail server configuration settings."
    )
    return {"message": "SMTP Settings updated successfully"}

@router.post("/smtp/test")
def test_smtp_configuration(
    request_data: SmtpTest,
    current_user: User = Depends(RoleChecker(["Administrator"])),
    db: Session = Depends(get_db)
):
    password = request_data.smtp_sender_password
    
    # If using saved password, load and decrypt
    if request_data.use_saved_password:
        saved_pwd_setting = db.query(SystemSetting).filter(SystemSetting.key == "smtp_sender_password").first()
        if saved_pwd_setting and saved_pwd_setting.value:
            password = decrypt_smtp_password(saved_pwd_setting.value)
        else:
            raise HTTPException(status_code=400, detail="No saved SMTP password exists.")
            
    success, err_msg = test_smtp_connection(
        host=request_data.smtp_host,
        port=request_data.smtp_port,
        sender=request_data.smtp_sender_email,
        password=password,
        use_tls=request_data.smtp_use_tls,
        use_ssl=request_data.smtp_use_ssl
    )
    
    if success:
        return {"success": True, "message": "SMTP Connection test successful!"}
    else:
        return {"success": False, "message": f"SMTP Connection test failed: {err_msg}"}

@router.get("/email-logs")
def get_email_delivery_logs(
    current_user: User = Depends(RoleChecker(["Administrator", "Auditor"])),
    db: Session = Depends(get_db)
):
    logs = db.query(EmailDeliveryLog).order_by(EmailDeliveryLog.sent_at.desc()).limit(100).all()
    result = []
    for l in logs:
        result.append({
            "id": l.id,
            "recipient": l.recipient,
            "subject": l.subject,
            "event_type": l.event_type,
            "status": l.status,
            "error_message": l.error_message,
            "sent_at": l.sent_at.isoformat()
        })
    return result
