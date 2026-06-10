from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import RecurringTaskMaster, User
from backend.security import get_current_user, RoleChecker
from backend.utils import log_audit

router = APIRouter(prefix="/api/recurring", tags=["recurring"])

class RecurringCreate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    department: str = Field(...)  # 'Payroll', 'Fund Accounting', 'Factory Petty Cash', 'Audit Schedules'
    description: Optional[str] = None
    responsible_person_id: int
    start_date: datetime
    frequency: str  # 'Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly', 'Every 2 Years'
    reminder_days: int = Field(default=1, ge=0)
    is_active: bool = True

class RecurringUpdate(BaseModel):
    task_name: str = Field(..., min_length=1, max_length=255)
    department: str
    description: Optional[str] = None
    responsible_person_id: int
    start_date: datetime
    frequency: str
    reminder_days: int = Field(default=1, ge=0)
    is_active: bool

@router.post("", response_model=dict)
def create_recurring_task(
    request_data: RecurringCreate,
    request: Request,
    current_user: User = Depends(RoleChecker(["Administrator", "GM/CFO", "NM Finance"])),
    db: Session = Depends(get_db)
):
    # Verify user responsible person exists
    responsible_user = db.query(User).filter(User.id == request_data.responsible_person_id).first()
    if not responsible_user:
        raise HTTPException(status_code=404, detail="Responsible person user not found")
        
    valid_freqs = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Every 2 Years"]
    if request_data.frequency not in valid_freqs:
        raise HTTPException(status_code=400, detail=f"Invalid frequency. Must be one of {valid_freqs}")
        
    valid_departments = ["Payroll", "Fund Accounting", "Factory Petty Cash", "Petty Cash", "Audit Schedules"]
    if request_data.department not in valid_departments:
        raise HTTPException(status_code=400, detail=f"Invalid department. Must be one of {valid_departments}")
        
    recurring = RecurringTaskMaster(
        task_name=request_data.task_name,
        department="Finance & Payroll",
        category=request_data.department,
        description=request_data.description,
        responsible_person_id=request_data.responsible_person_id,
        start_date=request_data.start_date,
        frequency=request_data.frequency,
        reminder_days=request_data.reminder_days,
        is_active=request_data.is_active,
        created_at=datetime.utcnow()
    )
    db.add(recurring)
    db.commit()
    db.refresh(recurring)
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Creation",
        request=request,
        user_id=current_user.id,
        details=f"Created recurring task template '{recurring.task_name}' frequency: '{recurring.frequency}'."
    )
    
    return {"message": "Recurring task template created successfully", "id": recurring.id}

@router.get("")
def get_recurring_tasks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    templates = db.query(RecurringTaskMaster).all()
    result = []
    for r in templates:
        result.append({
            "id": r.id,
            "task_name": r.task_name,
            "department": r.department,
            "category": r.category,
            "module": r.category,  # backward compatibility
            "description": r.description,
            "responsible_person_id": r.responsible_person_id,
            "responsible_person": r.responsible_person.username if r.responsible_person else "Unknown",
            "start_date": r.start_date.isoformat(),
            "frequency": r.frequency,
            "reminder_days": r.reminder_days,
            "is_active": r.is_active,
            "last_generated_at": r.last_generated_at.isoformat() if r.last_generated_at else None,
            "created_at": r.created_at.isoformat()
        })
    return result

@router.put("/{recurring_id}")
def update_recurring_task(
    recurring_id: int,
    request_data: RecurringUpdate,
    request: Request,
    current_user: User = Depends(RoleChecker(["Administrator", "GM/CFO", "NM Finance"])),
    db: Session = Depends(get_db)
):
    recurring = db.query(RecurringTaskMaster).filter(RecurringTaskMaster.id == recurring_id).first()
    if not recurring:
        raise HTTPException(status_code=404, detail="Recurring task master template not found")
        
    responsible_user = db.query(User).filter(User.id == request_data.responsible_person_id).first()
    if not responsible_user:
        raise HTTPException(status_code=404, detail="Responsible person user not found")
        
    old_state = f"Active: {recurring.is_active}, Freq: {recurring.frequency}, Name: {recurring.task_name}"
    
    recurring.task_name = request_data.task_name
    recurring.department = "Finance & Payroll"
    recurring.category = request_data.department
    recurring.description = request_data.description
    recurring.responsible_person_id = request_data.responsible_person_id
    recurring.start_date = request_data.start_date
    recurring.frequency = request_data.frequency
    recurring.reminder_days = request_data.reminder_days
    recurring.is_active = request_data.is_active
    
    db.commit()
    
    new_state = f"Active: {recurring.is_active}, Freq: {recurring.frequency}, Name: {recurring.task_name}"
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Editing",
        request=request,
        user_id=current_user.id,
        details=f"Updated recurring task template #{recurring_id}.",
        old_value=old_state,
        new_value=new_state
    )
    
    return {"message": "Recurring task template updated successfully"}
