import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import Task, User, Notification, EvidenceFile, WorkflowActivity
from backend.security import get_current_user, RoleChecker
from backend.utils import log_audit
from backend.smtp_helper import send_smtp_email

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

class TaskCreate(BaseModel):
    task_title: str = Field(..., min_length=1, max_length=255)
    task_description: Optional[str] = None
    module: Optional[str] = None  # Backward compatibility parameter
    category: Optional[str] = None  # New phase 2 parameter
    sla_days: Optional[int] = Field(default=7, ge=1)
    planned_due_date: Optional[datetime] = None

class TaskEdit(BaseModel):
    task_title: str = Field(..., min_length=1, max_length=255)
    task_description: Optional[str] = None

class Stage1Complete(BaseModel):
    comments: str = Field(..., min_length=1)
    evidence_file_id: Optional[int] = None

class Stage2Complete(BaseModel):
    comments: str = Field(..., min_length=1)

class Stage3Complete(BaseModel):
    comments: str = Field(..., min_length=1)

class RejectionRequest(BaseModel):
    comments: str = Field(..., min_length=1)
    target_stage: Optional[str] = None  # 'Payroll' or 'NM Finance' (Only for CFO)

# Digital signature helper
def generate_approval_hash(task_id: int, username: str, role: str, timestamp: datetime, comments: str, ip: str, device: str) -> str:
    salt = "enterprise_digital_signature_salt_key_8899"
    raw_str = f"{task_id}:{username}:{role}:{timestamp.isoformat()}:{comments}:{ip or ''}:{device or ''}:{salt}"
    return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

# Timeline logging helper
def log_workflow_activity(
    db: Session,
    task: Task,
    user_id: int,
    username: str,
    role: str,
    action: str,
    comments: str,
    request: Request = None,
    evidence_file_id: int = None,
    digital_signature_hash: str = None
) -> WorkflowActivity:
    now = datetime.utcnow()
    
    # Calculate duration since last activity
    last_act = db.query(WorkflowActivity).filter(WorkflowActivity.task_id == task.id).order_by(WorkflowActivity.timestamp.desc()).first()
    duration = 0.0
    if last_act:
        duration = (now - last_act.timestamp).total_seconds()
        
    ip_address = None
    device_info = None
    if request:
        ip_address = request.client.host if request.client else None
        device_info = request.headers.get("user-agent", "Unknown Device")
        
    activity = WorkflowActivity(
        task_id=task.id,
        user_id=user_id,
        username=username,
        user_role=role,
        timestamp=now,
        action=action,
        comments=comments,
        evidence_file_id=evidence_file_id,
        duration=duration,
        ip_address=ip_address,
        device_info=device_info,
        digital_signature_hash=digital_signature_hash
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity

def create_workflow_notifications(db: Session, task: Task, target_role: str, title: str, message: str):
    """
    Creates notification records for users of a specific role
    """
    users = db.query(User).filter(User.role == target_role, User.is_active == True).all()
    for u in users:
        notification = Notification(
            user_id=u.id,
            title=title,
            message=message,
            is_read=False
        )
        db.add(notification)
    db.commit()

# Helper to map task status code details
def map_task_details(t: Task, now: datetime):
    # SLA Math
    planned = t.planned_due_date
    completed = t.actual_completion_date
    
    overdue_days = 0
    days_remaining = 0
    
    if planned:
        if completed:
            if completed > planned:
                overdue_days = (completed - planned).days
            else:
                days_remaining = (planned - completed).days
        else:
            if now > planned:
                overdue_days = (now - planned).days
            else:
                days_remaining = (planned - now).days
                
    # SLA Status Determine
    sla_status = "On Track"
    if planned:
        if completed:
            if completed > planned:
                sla_status = "Overdue"
            else:
                sla_status = "On Track"
        else:
            if now > planned:
                if (now - planned).days > 3 or (now - t.created_at).days > 7:
                    sla_status = "Critical"
                else:
                    sla_status = "Overdue"
            elif (planned - now).days <= 2:
                sla_status = "Due Soon"
                
    return {
        "id": t.id,
        "task_title": t.task_title,
        "task_description": t.task_description,
        "department": t.department,
        "category": t.category,
        "status": t.status,
        "created_by": t.created_by.username if t.created_by else "System",
        "created_at": t.created_at.isoformat(),
        "is_edited_flag": t.is_edited_flag,
        "edited_by": t.edited_by.username if t.edited_by else None,
        "edited_at": t.edited_at.isoformat() if t.edited_at else None,
        
        # SLA Fields
        "planned_due_date": t.planned_due_date.isoformat() if t.planned_due_date else None,
        "target_completion_date": t.target_completion_date.isoformat() if t.target_completion_date else None,
        "actual_completion_date": t.actual_completion_date.isoformat() if t.actual_completion_date else None,
        "sla_days": t.sla_days,
        "days_remaining": days_remaining,
        "overdue_days": overdue_days,
        "sla_status": sla_status,
        
        # Rejection fields
        "rejection_count": t.rejection_count,
        "last_rejected_by": t.last_rejected_by.username if t.last_rejected_by else None,
        "last_rejected_at": t.last_rejected_at.isoformat() if t.last_rejected_at else None,
        "last_rejected_stage": t.last_rejected_stage,
        "last_rejection_reason": t.last_rejection_reason,
        
        # Approvals cache
        "payroll_completed_at": t.payroll_completed_at.isoformat() if t.payroll_completed_at else None,
        "payroll_completed_by": t.payroll_completed_by.username if t.payroll_completed_by else None,
        "payroll_comments": t.payroll_comments,
        "payroll_evidence_file_id": t.payroll_evidence_file_id,
        "payroll_processing_time": t.payroll_processing_time,
        
        "nm_finance_approved_at": t.nm_finance_approved_at.isoformat() if t.nm_finance_approved_at else None,
        "nm_finance_approved_by": t.nm_finance_approved_by.username if t.nm_finance_approved_by else None,
        "nm_finance_comments": t.nm_finance_comments,
        "nm_finance_processing_time": t.nm_finance_processing_time,
        
        "gmcfo_approved_at": t.gmcfo_approved_at.isoformat() if t.gmcfo_approved_at else None,
        "gmcfo_approved_by": t.gmcfo_approved_by.username if t.gmcfo_approved_by else None,
        "gmcfo_comments": t.gmcfo_comments,
        "gmcfo_processing_time": t.gmcfo_processing_time,
        
        "total_completion_time": t.total_completion_time,
        "is_archived": t.is_archived
    }

@router.post("", response_model=dict)
def create_task(
    request_data: TaskCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Category maps to requested category or backward compatibility module parameter
    category_val = request_data.category or request_data.module
    if not category_val:
        raise HTTPException(status_code=400, detail="Category/Module is required.")
        
    valid_categories = ["Payroll", "Fund Accounting", "Factory Petty Cash", "Audit Schedules"]
    if category_val not in valid_categories:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Category. Must be one of {valid_categories}"
        )
        
    now = datetime.utcnow()
    planned_due = request_data.planned_due_date
    if not planned_due:
        planned_due = now + timedelta(days=request_data.sla_days)
        
    task = Task(
        task_title=request_data.task_title,
        task_description=request_data.task_description,
        department="Finance & Payroll",
        category=category_val,
        status="Pending",
        created_by_id=current_user.id,
        created_at=now,
        planned_due_date=planned_due,
        target_completion_date=planned_due,
        sla_days=request_data.sla_days,
        is_archived=False,
        is_edited_flag=False,
        rejection_count=0
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    
    # Timeline initial logger
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="Created",
        comments="Task initiated in pipeline.",
        request=request
    )
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Creation",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Task #{task.id} '{task.task_title}' created under category '{task.category}'."
    )
    
    # Send notification email using helper
    create_workflow_notifications(
        db=db,
        task=task,
        target_role="Payroll Team",
        title="New Task Created",
        message=f"Task #{task.id} '{task.task_title}' is assigned to Payroll Team Stage 1 queue."
    )
    
    # Dispatch email
    payroll_users = db.query(User).filter(User.role == "Payroll Team", User.is_active == True).all()
    for u in payroll_users:
         send_smtp_email(
             db=db,
             event_type="New Task Assigned",
             recipient=f"{u.username}@company.com",
             subject=f"New Task Assigned: Task #{task.id}",
             body=f"Task #{task.id} '{task.task_title}' has been registered and is pending your Stage 1 sign-off."
         )
         
    return {"message": "Task created successfully", "task_id": task.id}

@router.get("")
def get_tasks(
    category: Optional[str] = None,
    module: Optional[str] = None,  # Backward compatibility
    status: Optional[str] = None,
    archived: bool = False,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Task).filter(Task.is_archived == archived)
    
    # Filter category (or compatibility module param)
    cat_filter = category or module
    if cat_filter:
        query = query.filter(Task.category == cat_filter)
        
    if status:
        query = query.filter(Task.status == status)
        
    if search:
        query = query.filter(
            (Task.task_title.ilike(f"%{search}%")) | 
            (Task.task_description.ilike(f"%{search}%"))
        )
        
    tasks = query.order_by(Task.created_at.desc()).all()
    now = datetime.utcnow()
    
    return [map_task_details(t, now) for t in tasks]

@router.get("/{task_id}")
def get_task_by_id(task_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    now = datetime.utcnow()
    result = map_task_details(task, now)
    
    # Include activities list for timeline rendering
    acts = db.query(WorkflowActivity).filter(WorkflowActivity.task_id == task.id).order_by(WorkflowActivity.timestamp.asc()).all()
    activities_list = []
    for a in acts:
        activities_list.append({
            "id": a.id,
            "username": a.username,
            "user_role": a.user_role,
            "timestamp": a.timestamp.isoformat(),
            "action": a.action,
            "comments": a.comments,
            "evidence_file_id": a.evidence_file_id,
            "duration": a.duration,
            "ip_address": a.ip_address,
            "device_info": a.device_info,
            "digital_signature_hash": a.digital_signature_hash
        })
    result["activities"] = activities_list
    return result

@router.put("/{task_id}")
def edit_task(
    task_id: int,
    request_data: TaskEdit,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status == "GM/CFO Approved":
        raise HTTPException(status_code=400, detail="Completed task is locked and cannot be edited")
        
    if current_user.role != "Administrator" and task.created_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Permission denied to edit this task")
        
    old_title = task.task_title
    old_description = task.task_description
    
    task.task_title = request_data.task_title
    task.task_description = request_data.task_description
    task.is_edited_flag = True
    task.edited_by_id = current_user.id
    task.edited_at = datetime.utcnow()
    
    db.commit()
    
    # Timeline
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="Edited Details",
        comments=f"Changed Title to '{task.task_title}'",
        request=request
    )
    
    # Audit log
    details_log = []
    if old_title != request_data.task_title:
        details_log.append(f"Title: '{old_title}' -> '{request_data.task_title}'")
    if old_description != request_data.task_description:
        details_log.append("Description modified")
        
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Editing",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Task #{task.id} updated. " + "; ".join(details_log),
        old_value=f"Title: {old_title}, Description: {old_description}",
        new_value=f"Title: {task.task_title}, Description: {task.task_description}"
    )
    
    return {"message": "Task updated successfully"}

@router.post("/{task_id}/complete-payroll")
def complete_payroll_stage(
    task_id: int,
    request_data: Stage1Complete,
    request: Request,
    current_user: User = Depends(RoleChecker(["Payroll Team", "Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "Pending":
        raise HTTPException(status_code=400, detail="Task is not in 'Pending' stage")
        
    # Link evidence
    if request_data.evidence_file_id:
        file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == request_data.evidence_file_id).first()
        if not file_entry:
            raise HTTPException(status_code=400, detail="Selected evidence file does not exist")
        file_entry.task_id = task.id
        file_entry.workflow_stage = "Payroll"
        file_entry.status = "Pending Review"
        task.payroll_evidence_file_id = request_data.evidence_file_id
        
    now = datetime.utcnow()
    task.status = "Payroll Completed"
    task.payroll_completed_at = now
    task.payroll_completed_by_id = current_user.id
    task.payroll_comments = request_data.comments
    
    # Calculate Stage 1 duration
    duration = (now - task.created_at).total_seconds()
    task.payroll_processing_time = duration
    
    # Generate Digital Signature Hash
    sig_hash = generate_approval_hash(
        task_id=task.id,
        username=current_user.username,
        role=current_user.role,
        timestamp=now,
        comments=request_data.comments,
        ip=request.client.host if request.client else None,
        device=request.headers.get("user-agent", "Unknown Device")
    )
    
    # Log Workflow Timeline activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="Payroll Completed (Stage 1 Sign-off)",
        comments=request_data.comments,
        request=request,
        evidence_file_id=request_data.evidence_file_id,
        digital_signature_hash=sig_hash
    )
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Workflow Actions",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Stage 1 (Payroll) completed. Remarks: '{request_data.comments}'"
    )
    
    # Notify NM Finance
    create_workflow_notifications(
        db=db,
        task=task,
        target_role="NM Finance",
        title="Task Pending NM Finance Review",
        message=f"Task #{task.id} is pending NM Finance Stage 2 review."
    )
    
    # Dispatch email
    finance_users = db.query(User).filter(User.role == "NM Finance", User.is_active == True).all()
    for u in finance_users:
         send_smtp_email(
             db=db,
             event_type="Task Approved",
             recipient=f"{u.username}@company.com",
             subject=f"Action Required: Task #{task.id} Forwarded to NM Finance",
             body=f"Task #{task.id} '{task.task_title}' was signed off by Payroll Team and is pending your Stage 2 approval."
         )
         
    return {"message": "Stage 1 (Payroll) completed successfully"}

@router.post("/{task_id}/approve-nmfinance")
def approve_nmfinance_stage(
    task_id: int,
    request_data: Stage2Complete,
    request: Request,
    current_user: User = Depends(RoleChecker(["NM Finance", "Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "Payroll Completed":
        raise HTTPException(status_code=400, detail="Task is not in 'Payroll Completed' stage")
        
    now = datetime.utcnow()
    task.status = "NM Finance Approved"
    task.nm_finance_approved_at = now
    task.nm_finance_approved_by_id = current_user.id
    task.nm_finance_comments = request_data.comments
    
    # Calculate Stage 2 duration
    duration = (now - task.payroll_completed_at).total_seconds()
    task.nm_finance_processing_time = duration
    
    # Generate Digital Signature Hash
    sig_hash = generate_approval_hash(
        task_id=task.id,
        username=current_user.username,
        role=current_user.role,
        timestamp=now,
        comments=request_data.comments,
        ip=request.client.host if request.client else None,
        device=request.headers.get("user-agent", "Unknown Device")
    )
    
    # Log Workflow activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="NM Finance Approved (Stage 2 Sign-off)",
        comments=request_data.comments,
        request=request,
        digital_signature_hash=sig_hash
    )
    
    # Set evidence file status to Approved if attached
    if task.payroll_evidence_file_id:
        file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == task.payroll_evidence_file_id).first()
        if file_entry:
            file_entry.status = "Approved"
            file_entry.approved_by_id = current_user.id
            file_entry.approved_at = now
            
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Workflow Actions",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Stage 2 (NM Finance) approved. Remarks: '{request_data.comments}'"
    )
    
    # Notify GM/CFO
    create_workflow_notifications(
        db=db,
        task=task,
        target_role="GM/CFO",
        title="Task Pending GM/CFO Approval",
        message=f"Task #{task.id} is pending GM/CFO Stage 3 release."
    )
    
    # Dispatch email
    cfo_users = db.query(User).filter(User.role == "GM/CFO", User.is_active == True).all()
    for u in cfo_users:
         send_smtp_email(
             db=db,
             event_type="Task Approved",
             recipient=f"{u.username}@company.com",
             subject=f"Action Required: Task #{task.id} Forwarded to GM/CFO",
             body=f"Task #{task.id} '{task.task_title}' was verified by NM Finance and is pending your final Stage 3 approval release."
         )
         
    return {"message": "Stage 2 (NM Finance) approved successfully"}

@router.post("/{task_id}/approve-gmcfo")
def approve_gmcfo_stage(
    task_id: int,
    request_data: Stage3Complete,
    request: Request,
    current_user: User = Depends(RoleChecker(["GM/CFO", "Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "NM Finance Approved":
        raise HTTPException(status_code=400, detail="Task is not in 'NM Finance Approved' stage")
        
    now = datetime.utcnow()
    task.status = "GM/CFO Approved"
    task.gmcfo_approved_at = now
    task.gmcfo_approved_by_id = current_user.id
    task.gmcfo_comments = request_data.comments
    task.actual_completion_date = now
    
    # Calculate Stage 3 duration
    duration = (now - task.nm_finance_approved_at).total_seconds()
    task.gmcfo_processing_time = duration
    
    # Calculate total duration
    total_duration = (now - task.created_at).total_seconds()
    task.total_completion_time = total_duration
    
    # Generate Digital Signature Hash
    sig_hash = generate_approval_hash(
        task_id=task.id,
        username=current_user.username,
        role=current_user.role,
        timestamp=now,
        comments=request_data.comments,
        ip=request.client.host if request.client else None,
        device=request.headers.get("user-agent", "Unknown Device")
    )
    
    # Log Workflow activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="GM/CFO Released (Stage 3 Complete)",
        comments=request_data.comments,
        request=request,
        digital_signature_hash=sig_hash
    )
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Workflow Actions",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Stage 3 (GM/CFO) approved. Remarks: '{request_data.comments}'"
    )
    
    # Notify Task Creator
    creator = db.query(User).filter(User.id == task.created_by_id).first()
    if creator:
        notification = Notification(
            user_id=creator.id,
            title="Task Fully Completed",
            message=f"Your task #{task.id} has been fully completed and closed by GM/CFO."
        )
        db.add(notification)
        db.commit()
        
        # Dispatch email
        send_smtp_email(
            db=db,
            event_type="Task Approved",
            recipient=f"{creator.username}@company.com",
            subject=f"Completed: Task #{task.id} Fully Released",
            body=f"Your compliance task #{task.id} '{task.task_title}' has been fully approved by GM/CFO and released."
        )
        
    return {"message": "Stage 3 (GM/CFO) approved and task fully completed successfully"}

@router.post("/{task_id}/reject-nmfinance")
def reject_nmfinance_stage(
    task_id: int,
    request_data: RejectionRequest,
    request: Request,
    current_user: User = Depends(RoleChecker(["NM Finance", "Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "Payroll Completed":
        raise HTTPException(status_code=400, detail="Task is not in 'Payroll Completed' stage to reject")
        
    now = datetime.utcnow()
    
    # Cache old state details for logging
    old_status = task.status
    
    # Increment rejection count and cache values
    task.status = "Pending"  # Return to Payroll queue
    task.rejection_count += 1
    task.last_rejected_by_id = current_user.id
    task.last_rejected_at = now
    task.last_rejected_stage = "NM Finance"
    task.last_rejection_reason = request_data.comments
    
    # Soft reset Stage 1 details so Payroll can resubmit
    task.payroll_completed_at = None
    task.payroll_completed_by_id = None
    
    db.commit()
    
    # Log Workflow timeline activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="NM Finance Rejected (Returned to Payroll)",
        comments=request_data.comments,
        request=request
    )
    
    # Set evidence status to Rejected if exists
    if task.payroll_evidence_file_id:
        file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == task.payroll_evidence_file_id).first()
        if file_entry:
            file_entry.status = "Rejected"
            file_entry.rejection_reason = request_data.comments
            
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Workflow Actions",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"NM Finance rejected Task #{task.id} back to Payroll. Reason: '{request_data.comments}'",
        old_value=f"Status: {old_status}",
        new_value="Status: Pending (Returned)"
    )
    
    # Notify Payroll Team
    create_workflow_notifications(
        db=db,
        task=task,
        target_role="Payroll Team",
        title="Task Rejected / Returned",
        message=f"Task #{task.id} was returned to your queue by NM Finance. Reason: '{request_data.comments}'"
    )
    
    # Dispatch email alert
    payroll_users = db.query(User).filter(User.role == "Payroll Team", User.is_active == True).all()
    for u in payroll_users:
         send_smtp_email(
             db=db,
             event_type="Task Returned",
             recipient=f"{u.username}@company.com",
             subject=f"TASK RETURNED: Task #{task.id} Rejected by NM Finance",
             body=f"Task #{task.id} '{task.task_title}' was rejected by NM Finance and returned to your queue.\n\nReason: {request_data.comments}"
         )
         
    return {"message": "Task rejected back to Payroll successfully"}

@router.post("/{task_id}/reject-gmcfo")
def reject_gmcfo_stage(
    task_id: int,
    request_data: RejectionRequest,
    request: Request,
    current_user: User = Depends(RoleChecker(["GM/CFO", "Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    if task.status != "NM Finance Approved":
        raise HTTPException(status_code=400, detail="Task is not in 'NM Finance Approved' stage to reject")
        
    if request_data.target_stage not in ["Payroll", "NM Finance"]:
        raise HTTPException(
            status_code=400,
            detail="CFO rejection must target either 'Payroll' or 'NM Finance'"
        )
        
    now = datetime.utcnow()
    old_status = task.status
    
    # Set targets
    action_lbl = ""
    target_role_notif = ""
    email_subject = ""
    
    if request_data.target_stage == "Payroll":
         task.status = "Pending"
         task.payroll_completed_at = None
         task.payroll_completed_by_id = None
         task.nm_finance_approved_at = None
         task.nm_finance_approved_by_id = None
         action_lbl = "GM/CFO Rejected (Returned to Payroll)"
         target_role_notif = "Payroll Team"
         email_subject = f"TASK RETURNED: Task #{task.id} Rejected by GM/CFO"
    else: # NM Finance
         task.status = "Payroll Completed"
         task.nm_finance_approved_at = None
         task.nm_finance_approved_by_id = None
         action_lbl = "GM/CFO Rejected (Returned to NM Finance)"
         target_role_notif = "NM Finance"
         email_subject = f"TASK RETURNED: Task #{task.id} Rejected back to NM Finance"
         
    task.rejection_count += 1
    task.last_rejected_by_id = current_user.id
    task.last_rejected_at = now
    task.last_rejected_stage = "GM/CFO"
    task.last_rejection_reason = request_data.comments
    
    db.commit()
    
    # Log Workflow timeline activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action=action_lbl,
        comments=request_data.comments,
        request=request
    )
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Workflow Actions",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"GM/CFO rejected Task #{task.id} back to {request_data.target_stage}. Reason: '{request_data.comments}'",
        old_value=f"Status: {old_status}",
        new_value=f"Status: {task.status} (Returned)"
    )
    
    # Notify target
    create_workflow_notifications(
        db=db,
        task=task,
        target_role=target_role_notif,
        title="Task Rejected / Returned",
        message=f"Task #{task.id} was returned to your stage by GM/CFO. Reason: '{request_data.comments}'"
    )
    
    # Dispatch email
    target_users = db.query(User).filter(User.role == target_role_notif, User.is_active == True).all()
    for u in target_users:
         send_smtp_email(
             db=db,
             event_type="Task Returned",
             recipient=f"{u.username}@company.com",
             subject=email_subject,
             body=f"Task #{task.id} '{task.task_title}' was rejected by GM/CFO and returned to your queue stage.\n\nReason: {request_data.comments}"
         )
         
    return {"message": f"Task successfully rejected back to {request_data.target_stage}"}

@router.post("/{task_id}/archive")
def archive_task(
    task_id: int,
    request: Request,
    current_user: User = Depends(RoleChecker(["Administrator"])),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    task.is_archived = True
    db.commit()
    
    # Log timeline event
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="Archived",
        comments="Task soft archived by Administrator.",
        request=request
    )
    
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Task Editing",
        request=request,
        user_id=current_user.id,
        task_id=task.id,
        details=f"Task #{task.id} soft archived by Admin."
    )
    
    return {"message": "Task soft archived successfully"}
