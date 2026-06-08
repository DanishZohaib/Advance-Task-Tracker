import math
from datetime import datetime
from fastapi import Request
from sqlalchemy.orm import Session
from database.models import AuditLog

def log_audit(
    db: Session,
    username: str,
    action_type: str,
    request: Request = None,
    user_id: int = None,
    task_id: int = None,
    details: str = None,
    old_value: str = None,
    new_value: str = None
):
    ip_address = None
    device_info = None
    if request:
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", "Unknown Device")
    
    audit_entry = AuditLog(
        user_id=user_id,
        username=username,
        timestamp=datetime.utcnow(),
        ip_address=ip_address,
        device_info=device_info,
        action_type=action_type,
        task_id=task_id,
        details=details,
        old_value=old_value,
        new_value=new_value
    )
    db.add(audit_entry)
    db.commit()

def format_duration(seconds: float) -> str:
    """
    Format duration in seconds into 'X days, Y hours, Z minutes'
    """
    if seconds is None:
        return "N/A"
    
    seconds = max(0.0, seconds)
    days = int(seconds // 86400)
    remaining_seconds = seconds % 86400
    hours = int(remaining_seconds // 3600)
    remaining_seconds %= 3600
    minutes = int(remaining_seconds // 60)
    
    parts = []
    if days > 0:
        parts.append(f"{days} day{'s' if days != 1 else ''}")
    if hours > 0 or days > 0:
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
    parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    
    return ", ".join(parts)
