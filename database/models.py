from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, Index
from sqlalchemy.orm import relationship, synonym
from database.connection import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'Payroll Team', 'NM Finance', 'GM/CFO', 'Administrator', 'Auditor'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    created_tasks = relationship("Task", foreign_keys="Task.created_by_id", back_populates="created_by")
    assigned_recurring = relationship("RecurringTaskMaster", back_populates="responsible_person")
    uploaded_files = relationship("EvidenceFile", foreign_keys="EvidenceFile.uploaded_by_id", back_populates="uploaded_by")

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    task_title = Column(String(255), index=True, nullable=False)
    task_description = Column(Text, nullable=True)
    
    # Hierarchical Business Structure Correction
    department = Column(String(100), default="Finance & Payroll", nullable=False, index=True)
    category = Column(String(100), nullable=False, index=True)  # 'Payroll', 'Fund Accounting', 'Petty Cash', 'Audit Schedules'
    module = synonym("category")
    
    def __init__(self, **kwargs):
        # Translate module to category
        if "module" in kwargs:
            kwargs["category"] = kwargs.pop("module")
        # If department is one of the category values, move it to category and set department to default
        legacy_departments = {"Payroll", "Fund Accounting", "Factory Petty Cash", "Petty Cash", "Audit Schedules"}
        if "department" in kwargs and kwargs["department"] in legacy_departments:
            kwargs["category"] = kwargs["department"]
            kwargs["department"] = "Finance & Payroll"
        super().__init__(**kwargs)

    status = Column(String(50), default="Pending", nullable=False, index=True)  # 'Pending', 'Payroll Completed', 'NM Finance Approved', 'GM/CFO Approved'
    
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    is_archived = Column(Boolean, default=False, nullable=False, index=True)
    is_edited_flag = Column(Boolean, default=False, nullable=False)
    edited_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    edited_at = Column(DateTime, nullable=True)

    # Due Date & SLA Management Columns
    planned_due_date = Column(DateTime, nullable=True, index=True)
    target_completion_date = Column(DateTime, nullable=True)
    actual_completion_date = Column(DateTime, nullable=True, index=True)
    sla_days = Column(Integer, nullable=True)

    # Rejection Cache Columns
    rejection_count = Column(Integer, default=0, nullable=False)
    last_rejected_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    last_rejected_at = Column(DateTime, nullable=True)
    last_rejected_stage = Column(String(50), nullable=True)
    last_rejection_reason = Column(Text, nullable=True)

    # Stage 1: Payroll Team
    payroll_completed_at = Column(DateTime, nullable=True)
    payroll_completed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    payroll_comments = Column(Text, nullable=True)
    payroll_evidence_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    payroll_processing_time = Column(Float, nullable=True)  # Store duration in seconds

    # Stage 2: NM Finance
    nm_finance_approved_at = Column(DateTime, nullable=True)
    nm_finance_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    nm_finance_comments = Column(Text, nullable=True)
    nm_finance_processing_time = Column(Float, nullable=True)  # Store duration in seconds

    # Stage 3: GM/CFO
    gmcfo_approved_at = Column(DateTime, nullable=True)
    gmcfo_approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    gmcfo_comments = Column(Text, nullable=True)
    gmcfo_processing_time = Column(Float, nullable=True)  # Store duration in seconds

    total_completion_time = Column(Float, nullable=True)  # Store duration in seconds
    
    # Recurring link
    recurring_task_master_id = Column(Integer, ForeignKey("recurring_task_masters.id"), nullable=True)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id], back_populates="created_tasks")
    edited_by = relationship("User", foreign_keys=[edited_by_id])
    payroll_completed_by = relationship("User", foreign_keys=[payroll_completed_by_id])
    nm_finance_approved_by = relationship("User", foreign_keys=[nm_finance_approved_by_id])
    gmcfo_approved_by = relationship("User", foreign_keys=[gmcfo_approved_by_id])
    last_rejected_by = relationship("User", foreign_keys=[last_rejected_by_id])
    
    evidence_file = relationship("EvidenceFile", foreign_keys=[payroll_evidence_file_id], back_populates="task_reference")
    recurring_master = relationship("RecurringTaskMaster", back_populates="generated_tasks")
    
    activities = relationship("WorkflowActivity", back_populates="task", cascade="all, delete-orphan")

class RecurringTaskMaster(Base):
    __tablename__ = "recurring_task_masters"

    id = Column(Integer, primary_key=True, index=True)
    task_name = Column(String(255), nullable=False)
    department = Column(String(100), default="Finance & Payroll", nullable=False)
    category = Column(String(100), nullable=False)  # 'Payroll', 'Fund Accounting', 'Petty Cash', 'Audit Schedules'
    module = synonym("category")
    
    def __init__(self, **kwargs):
        # Translate module to category
        if "module" in kwargs:
            kwargs["category"] = kwargs.pop("module")
        # If department is one of the category values, move it to category and set department to default
        legacy_departments = {"Payroll", "Fund Accounting", "Factory Petty Cash", "Petty Cash", "Audit Schedules"}
        if "department" in kwargs and kwargs["department"] in legacy_departments:
            kwargs["category"] = kwargs["department"]
            kwargs["department"] = "Finance & Payroll"
        super().__init__(**kwargs)

    description = Column(Text, nullable=True)
    responsible_person_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    frequency = Column(String(50), nullable=False)  # 'Daily', 'Weekly', 'Monthly', 'Quarterly', 'Half-Yearly', 'Yearly', 'Every 2 Years'
    reminder_days = Column(Integer, default=1)
    priority = Column(String(50), default="Normal")
    is_active = Column(Boolean, default=True)
    last_generated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    responsible_person = relationship("User", back_populates="assigned_recurring")
    generated_tasks = relationship("Task", back_populates="recurring_master")


class EvidenceFile(Base):
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(512), nullable=False)
    file_hash = Column(String(64), unique=True, index=True, nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Versioning & Approval Enhancement Center Columns
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    workflow_stage = Column(String(50), nullable=True)  # 'Payroll', 'NM Finance', 'GM/CFO'
    version = Column(Integer, default=1, nullable=False)
    status = Column(String(50), default="Pending Review", nullable=False)  # 'Pending Review', 'Approved', 'Rejected'
    approved_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)

    # Relationships
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id], back_populates="uploaded_files")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    task_reference = relationship("Task", foreign_keys=[task_id])

class WorkflowActivity(Base):
    __tablename__ = "workflow_activities"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(100), nullable=False)
    user_role = Column(String(50), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    # State transitions e.g., 'Created', 'Payroll Completed', 'NM Finance Approved', 'NM Finance Rejected', etc.
    action = Column(String(100), nullable=False)
    comments = Column(Text, nullable=True)
    evidence_file_id = Column(Integer, ForeignKey("files.id"), nullable=True)
    duration = Column(Float, nullable=True)  # in seconds from the previous event
    
    # Audit signatures
    ip_address = Column(String(45), nullable=True)
    device_info = Column(String(255), nullable=True)
    digital_signature_hash = Column(String(64), nullable=True)  # SHA-256 Approval Certificate Hash

    # Relationships
    task = relationship("Task", back_populates="activities")
    user = relationship("User")
    evidence = relationship("EvidenceFile", foreign_keys=[evidence_file_id])

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    user = relationship("User")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    username = Column(String(100), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45), nullable=True)
    device_info = Column(String(255), nullable=True)
    action_type = Column(String(100), nullable=False)
    task_id = Column(Integer, nullable=True)
    details = Column(Text, nullable=True)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)

class EmailDeliveryLog(Base):
    __tablename__ = "email_delivery_logs"

    id = Column(Integer, primary_key=True, index=True)
    recipient = Column(String(255), nullable=False)
    subject = Column(String(255), nullable=False)
    event_type = Column(String(100), nullable=False)  # e.g. 'Task Approved', 'Task Overdue'
    status = Column(String(50), nullable=False)  # 'Sent', 'Failed'
    error_message = Column(Text, nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)

# Indices for performance tuning under load
Index("ix_audit_logs_username_timestamp", AuditLog.username, AuditLog.timestamp)
Index("ix_audit_logs_action_type", AuditLog.action_type)
