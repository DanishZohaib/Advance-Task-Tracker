from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import AuditLog, User
from backend.security import get_current_user, RoleChecker

router = APIRouter(prefix="/api/audit", tags=["audit"])

@router.get("")
def get_audit_logs(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    username: Optional[str] = None,
    action_type: Optional[str] = None,
    task_id: Optional[int] = None,
    current_user: User = Depends(RoleChecker(["Administrator", "Auditor", "GM/CFO"])),
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date)
            query = query.filter(AuditLog.timestamp >= start_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_date format. Use ISO format.")
            
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date)
            query = query.filter(AuditLog.timestamp <= end_dt)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_date format. Use ISO format.")
            
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username}%"))
        
    if action_type:
        query = query.filter(AuditLog.action_type == action_type)
        
    if task_id:
        query = query.filter(AuditLog.task_id == task_id)
        
    logs = query.order_by(desc(AuditLog.timestamp)).all()
    
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "user_id": log.user_id,
            "username": log.username,
            "timestamp": log.timestamp.isoformat(),
            "ip_address": log.ip_address,
            "device_info": log.device_info,
            "action_type": log.action_type,
            "task_id": log.task_id,
            "details": log.details,
            "old_value": log.old_value,
            "new_value": log.new_value
        })
        
    return result
