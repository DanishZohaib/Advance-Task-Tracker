import hashlib
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import (
    Task, User, Notification, EvidenceFile, WorkflowActivity,
    Role, TaskAssignment, TaskComment, TaskReturn, TaskRejection, TaskApproval, UserHierarchy, WorkflowDefinition, WorkflowStep
)
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

class TaskActionRequest(BaseModel):
    action: str  # 'Complete', 'Reject', 'Return', 'Forward'
    comments: str = Field(..., min_length=1)
    evidence_file_id: Optional[int] = None
    target_stage: Optional[str] = None  # 'NM Finance' or 'Manager' for returns

class WhatsAppNudgeRequest(BaseModel):
    recipient_phone: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)

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

def process_task_workflow_action(
    db: Session,
    task: Task,
    user: User,
    action: str,  # 'Complete', 'Reject', 'Return', 'Forward'
    comments: str,
    evidence_file_id: Optional[int] = None,
    target_stage: Optional[str] = None,
    request: Request = None
):
    if evidence_file_id:
        file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
        if not file_entry:
            raise HTTPException(status_code=400, detail="Evidence file not found")

    current_status = task.status
    if current_status in ["Pending", "Returned to Initiator"]:
        current_stage_role = "Manager"
        step_number = 1
    elif current_status == "Payroll Completed":
        current_stage_role = "NM Finance"
        step_number = 2
    elif current_status == "NM Finance Approved":
        current_stage_role = "GM/CFO"
        step_number = 3
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Task is in locked status '{current_status}' and cannot be actioned."
        )

    # Check user role authorization
    # Administrators can bypass
    if user.role != "Administrator" and user.role != current_stage_role:
        if user.role == "Payroll Team" and current_stage_role == "Manager":
            pass
        else:
            raise HTTPException(
                status_code=403,
                detail=f"Unauthorized to perform action. Required role: '{current_stage_role}', Your role: '{user.role}'."
            )

    now = datetime.utcnow()
    ip_addr = request.client.host if request and request.client else "Localhost"
    user_agent = request.headers.get("user-agent", "Unknown Device") if request else "System"

    # Validate comment (mandatory for all actions)
    if not comments or not comments.strip():
        raise HTTPException(status_code=400, detail="Remarks comments are mandatory for all workflow actions.")

    # 1. Log comment in task_comments table
    db_comment = TaskComment(
        task_id=task.id,
        user_id=user.id,
        username=user.username,
        user_role=user.role,
        comment_text=comments,
        action=action,
        timestamp=now
    )
    db.add(db_comment)

    # Generate Digital Signature Hash
    sig_hash = generate_approval_hash(
        task_id=task.id,
        username=user.username,
        role=user.role,
        timestamp=now,
        comments=comments,
        ip=ip_addr,
        device=user_agent
    )

    action_label = ""
    next_role = None

    if action == "Complete":
        if current_stage_role == "Manager":
            task.status = "Completed By Manager"
            task.payroll_completed_at = now
            task.payroll_completed_by_id = user.id
            task.payroll_comments = comments
            task.payroll_processing_time = (now - task.created_at).total_seconds()
            task.total_completion_time = task.payroll_processing_time
            action_label = "Completed By Manager"
        elif current_stage_role == "NM Finance":
            task.status = "Completed By NM Finance"
            task.nm_finance_approved_at = now
            task.nm_finance_approved_by_id = user.id
            task.nm_finance_comments = comments
            task.nm_finance_processing_time = (now - (task.payroll_completed_at or task.created_at)).total_seconds()
            task.total_completion_time = (now - task.created_at).total_seconds()
            action_label = "Completed By NM Finance"
        elif current_stage_role == "GM/CFO":
            task.status = "GM/CFO Approved"
            task.gmcfo_approved_at = now
            task.gmcfo_approved_by_id = user.id
            task.gmcfo_comments = comments
            task.gmcfo_processing_time = (now - (task.nm_finance_approved_at or task.created_at)).total_seconds()
            task.total_completion_time = (now - task.created_at).total_seconds()
            action_label = "Completed By GM/CFO"
            
        task.actual_completion_date = now

        # Add to task_approvals table
        approval = TaskApproval(
            task_id=task.id,
            approved_by=user.username,
            approved_stage=current_stage_role,
            approved_at=now,
            comments=comments
        )
        db.add(approval)

        # Log timeline event
        log_workflow_activity(
            db=db,
            task=task,
            user_id=user.id,
            username=user.username,
            role=user.role,
            action=f"Completed",
            comments=comments,
            request=request,
            digital_signature_hash=sig_hash
        )

        # Audit log completion
        log_audit(
            db=db,
            username=user.username,
            action_type="Workflow Actions",
            request=request,
            user_id=user.id,
            task_id=task.id,
            details=f"Task completed at stage {current_stage_role}. Status: {task.status}."
        )

        # Notify initiator
        creator = db.query(User).filter(User.id == task.created_by_id).first()
        if creator:
            notification = Notification(
                user_id=creator.id,
                title="Task Completed",
                message=f"Your task #{task.id} has been completed. Status: '{task.status}'."
            )
            db.add(notification)
            send_smtp_email(
                db=db,
                event_type="Task Approved",
                recipient=f"{creator.username}@company.com",
                subject=f"Completed: Task #{task.id}",
                body=f"Your task #{task.id} '{task.task_title}' has been marked as {task.status} by {user.username}."
            )

    elif action == "Forward":
        if current_stage_role == "Manager":
            task.status = "Payroll Completed"
            task.payroll_completed_at = now
            task.payroll_completed_by_id = user.id
            task.payroll_comments = comments
            task.payroll_processing_time = (now - task.created_at).total_seconds()
            
            if evidence_file_id:
                file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
                if file_entry:
                    file_entry.task_id = task.id
                    file_entry.workflow_stage = "Payroll"
                    file_entry.status = "Pending Review"
                    task.payroll_evidence_file_id = evidence_file_id
            
            next_role = "NM Finance"
            action_label = "Task Forwarded"
            
        elif current_stage_role == "NM Finance":
            task.status = "NM Finance Approved"
            task.nm_finance_approved_at = now
            task.nm_finance_approved_by_id = user.id
            task.nm_finance_comments = comments
            task.nm_finance_processing_time = (now - (task.payroll_completed_at or task.created_at)).total_seconds()
            
            if task.payroll_evidence_file_id:
                file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == task.payroll_evidence_file_id).first()
                if file_entry:
                    file_entry.status = "Approved"
                    file_entry.approved_by_id = user.id
                    file_entry.approved_at = now
                    
            next_role = "GM/CFO"
            action_label = "Task Forwarded"

        # Log timeline event
        log_workflow_activity(
            db=db,
            task=task,
            user_id=user.id,
            username=user.username,
            role=user.role,
            action=action_label,
            comments=comments,
            request=request,
            evidence_file_id=evidence_file_id or task.payroll_evidence_file_id,
            digital_signature_hash=sig_hash
        )

        # Audit log forward
        log_audit(
            db=db,
            username=user.username,
            action_type="Workflow Actions",
            request=request,
            user_id=user.id,
            task_id=task.id,
            details=f"Task forwarded at stage {current_stage_role}. Status: {task.status}. Next assignee: {next_role}."
        )

        # Create Assignment record
        assignment = TaskAssignment(
            task_id=task.id,
            assigned_role=next_role,
            assigned_at=now,
            status="Pending"
        )
        db.add(assignment)

        # Notify Next Role
        create_workflow_notifications(
            db=db,
            task=task,
            target_role=next_role,
            title="Task Assigned to your queue",
            message=f"Task #{task.id} is pending action at {next_role} stage."
        )

        next_users = db.query(User).filter(User.role == next_role, User.is_active == True).all()
        for nu in next_users:
            send_smtp_email(
                db=db,
                event_type="New Task Assigned",
                recipient=f"{nu.username}@company.com",
                subject=f"Action Required: Task #{task.id} Forwarded to {next_role}",
                body=f"Task #{task.id} '{task.task_title}' was forwarded to {next_role} queue and is pending review."
            )

    elif action == "Return":
        prev_returns = db.query(TaskReturn).filter(TaskReturn.task_id == task.id).count()
        return_count = prev_returns + 1

        # Update task rejection cache for backward compatibility
        task.rejection_count = task.rejection_count + 1
        task.last_rejected_by_id = user.id
        task.last_rejected_at = now
        task.last_rejected_stage = current_stage_role
        task.last_rejection_reason = comments

        returned_to_role = ""
        returned_to_user = None

        if current_stage_role == "Manager":
            initiator = db.query(User).filter(User.id == task.created_by_id).first()
            returned_to_role = initiator.role if initiator else "Assistant Manager"
            returned_to_user = initiator.username if initiator else "initiator"
            task.status = "Returned to Initiator"
            
        elif current_stage_role == "NM Finance":
            returned_to_role = "Manager"
            returned_to_user = "payroll_user"
            task.status = "Pending"
            task.payroll_completed_at = None
            task.payroll_completed_by_id = None
            
        elif current_stage_role == "GM/CFO":
            if target_stage in ["Manager", "Payroll"]:
                returned_to_role = "Manager"
                returned_to_user = "payroll_user"
                task.status = "Pending"
                task.payroll_completed_at = None
                task.payroll_completed_by_id = None
                task.nm_finance_approved_at = None
                task.nm_finance_approved_by_id = None
            else:
                returned_to_role = "NM Finance"
                returned_to_user = "finance_user"
                task.status = "Payroll Completed"
                task.nm_finance_approved_at = None
                task.nm_finance_approved_by_id = None

        # Create Return entry
        db_return = TaskReturn(
            task_id=task.id,
            returned_by=user.username,
            returned_to=returned_to_user,
            return_reason=comments,
            return_date=now,
            return_count=return_count
        )
        db.add(db_return)

        # Log timeline event
        log_workflow_activity(
            db=db,
            task=task,
            user_id=user.id,
            username=user.username,
            role=user.role,
            action=f"Task Returned",
            comments=comments,
            request=request
        )

        if task.payroll_evidence_file_id:
            file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == task.payroll_evidence_file_id).first()
            if file_entry:
                file_entry.status = "Rejected"
                file_entry.rejection_reason = comments

        log_audit(
            db=db,
            username=user.username,
            action_type="Workflow Actions",
            request=request,
            user_id=user.id,
            task_id=task.id,
            details=f"Task returned to {returned_to_role}. Return count: {return_count}."
        )

        if returned_to_role == "Manager":
            create_workflow_notifications(db=db, task=task, target_role="Manager", title="Task Returned", message=f"Task #{task.id} was returned to your stage. Reason: {comments}")
        elif returned_to_role == "NM Finance":
            create_workflow_notifications(db=db, task=task, target_role="NM Finance", title="Task Returned", message=f"Task #{task.id} was returned to your stage. Reason: {comments}")
        else:
            initiator = db.query(User).filter(User.id == task.created_by_id).first()
            if initiator:
                notification = Notification(
                    user_id=initiator.id,
                    title="Task Returned",
                    message=f"Your task #{task.id} was returned to you. Reason: '{comments}'"
                )
                db.add(notification)

        target_users = db.query(User).filter(User.role == returned_to_role, User.is_active == True).all()
        for tu in target_users:
            send_smtp_email(
                db=db,
                event_type="Task Returned",
                recipient=f"{tu.username}@company.com",
                subject=f"TASK RETURNED: Task #{task.id}",
                body=f"Task #{task.id} '{task.task_title}' was returned to your queue by {user.username}.\n\nReason: {comments}"
            )

    elif action == "Reject":
        prev_rejections = db.query(TaskRejection).filter(TaskRejection.task_id == task.id).count()
        rejection_count = prev_rejections + 1

        task.status = "Rejected"
        task.rejection_count = rejection_count
        task.last_rejected_by_id = user.id
        task.last_rejected_at = now
        task.last_rejected_stage = current_stage_role
        task.last_rejection_reason = comments

        # Create Rejection entry
        db_rejection = TaskRejection(
            task_id=task.id,
            rejected_by=user.username,
            rejected_date=now,
            rejection_reason=comments,
            rejection_stage=current_stage_role,
            rejection_count=rejection_count
        )
        db.add(db_rejection)

        # Log timeline event
        log_workflow_activity(
            db=db,
            task=task,
            user_id=user.id,
            username=user.username,
            role=user.role,
            action=f"Task Rejected",
            comments=comments,
            request=request
        )

        if task.payroll_evidence_file_id:
            file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == task.payroll_evidence_file_id).first()
            if file_entry:
                file_entry.status = "Rejected"
                file_entry.rejection_reason = comments

        log_audit(
            db=db,
            username=user.username,
            action_type="Workflow Actions",
            request=request,
            user_id=user.id,
            task_id=task.id,
            details=f"Task rejected at stage {current_stage_role}. Rejection count: {rejection_count}."
        )

        creator = db.query(User).filter(User.id == task.created_by_id).first()
        if creator:
            notification = Notification(
                user_id=creator.id,
                title="Task Rejected",
                message=f"Your task #{task.id} has been rejected by {user.username}. Reason: {comments}"
            )
            db.add(notification)
            send_smtp_email(
                db=db,
                event_type="Task Returned",
                recipient=f"{creator.username}@company.com",
                subject=f"TASK REJECTED: Task #{task.id}",
                body=f"Your task #{task.id} '{task.task_title}' was rejected by {user.username}.\n\nReason: {comments}"
            )

    db.commit()
    return {"message": "Action processed successfully", "status": task.status}

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
        
    valid_categories = ["Payroll", "Fund Accounting", "Factory Petty Cash", "Petty Cash", "Audit Schedules"]
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
    
    # 1. Create task assignment for Manager
    manager_user = db.query(User).filter(User.role == "Manager", User.is_active == True).first()
    assignment = TaskAssignment(
        task_id=task.id,
        assigned_role="Manager",
        assigned_user_id=manager_user.id if manager_user else None,
        assigned_at=now,
        status="Pending"
    )
    db.add(assignment)
    db.commit()
    
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
    
    # Send notification email using helper to Manager
    create_workflow_notifications(
        db=db,
        task=task,
        target_role="Manager",
        title="New Task Created",
        message=f"Task #{task.id} '{task.task_title}' is assigned to Manager queue."
    )
    
    # Dispatch email
    manager_users = db.query(User).filter(User.role == "Manager", User.is_active == True).all()
    for u in manager_users:
         send_smtp_email(
             db=db,
             event_type="New Task Assigned",
             recipient=f"{u.username}@company.com",
             subject=f"New Task Assigned: Task #{task.id}",
             body=f"Task #{task.id} '{task.task_title}' has been registered and is pending your sign-off/review."
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
    if task.status not in ["Pending", "Returned to Initiator"]:
        raise HTTPException(status_code=400, detail="Task is not in 'Pending' stage.")
    process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action="Forward",
        comments=request_data.comments,
        evidence_file_id=request_data.evidence_file_id,
        request=request
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
        raise HTTPException(status_code=400, detail="Task is not in 'Payroll Completed' stage.")
    process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action="Forward",
        comments=request_data.comments,
        request=request
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
        raise HTTPException(status_code=400, detail="Task is not in 'NM Finance Approved' stage.")
    process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action="Complete",
        comments=request_data.comments,
        request=request
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
        raise HTTPException(status_code=400, detail="Task is not in 'Payroll Completed' stage.")
    process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action="Return",
        comments=request_data.comments,
        request=request
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
        raise HTTPException(status_code=400, detail="Task is not in 'NM Finance Approved' stage.")
    if request_data.target_stage not in ["Payroll", "NM Finance", "Manager"]:
        raise HTTPException(status_code=400, detail="Invalid target stage.")
    process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action="Return",
        comments=request_data.comments,
        target_stage=request_data.target_stage,
        request=request
    )
    return {"message": f"Task successfully rejected back to {request_data.target_stage}"}

@router.post("/{task_id}/action")
def execute_task_action(
    task_id: int,
    request_data: TaskActionRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return process_task_workflow_action(
        db=db,
        task=task,
        user=current_user,
        action=request_data.action,
        comments=request_data.comments,
        evidence_file_id=request_data.evidence_file_id,
        target_stage=request_data.target_stage,
        request=request
    )

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

@router.post("/{task_id}/whatsapp-nudge")
def whatsapp_nudge(
    task_id: int,
    request_data: WhatsAppNudgeRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    # Log Workflow activity
    log_workflow_activity(
        db=db,
        task=task,
        user_id=current_user.id,
        username=current_user.username,
        role=current_user.role,
        action="WhatsApp Nudge Initiated",
        comments=f"WhatsApp notification initiated for task to phone: {request_data.recipient_phone}.",
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
        details=f"WhatsApp nudge initiated for Task #{task.id} to phone {request_data.recipient_phone}."
    )
    
    return {"message": "WhatsApp nudge logged successfully"}
