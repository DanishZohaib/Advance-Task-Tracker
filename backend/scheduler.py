import os
import smtplib
import time
import logging
import threading
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from sqlalchemy.orm import Session
from database.connection import SessionLocal
from database.models import RecurringTaskMaster, Task, User, Notification, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TaskTrackerScheduler")

ESCALATION_LOG_FILE = "e:/Antigravity/Advance-Task-Tracker/storage/escalations.log"
os.makedirs(os.path.dirname(ESCALATION_LOG_FILE), exist_ok=True)

def send_escalation_email(task: Task, age_days: int, db: Session):
    """
    Sends an escalation email to NM Finance users.
    If SMTP env is not configured, logs to storage/escalations.log.
    """
    # Find all NM Finance users
    nm_users = db.query(User).filter(User.role == "NM Finance", User.is_active == True).all()
    if not nm_users:
        logger.warning("No active NM Finance users found to send email escalation.")
        return
        
    recipient_emails = [f"{u.username}@company.com" for u in nm_users]
    
    subject = f"ESCALATION ALERT: Task #{task.id} '{task.task_title}' Overdue ({age_days} days)"
    body = f"""
============================================================
Task Number: Task #{task.id}
Task Name: {task.task_title}
Created Date: {task.created_at.strftime('%Y-%m-%d %H:%M:%S')}
Current Age: {age_days} days
Pending Stage: {task.status}
Direct Link: http://localhost:8501/tasks?task_id={task.id}
============================================================
This task has exceeded the 7-day completion SLA and is escalated to NM Finance.
"""
    
    # 1. Write email details to local file
    try:
        with open(ESCALATION_LOG_FILE, "a") as f:
            f.write(f"[{datetime.now().isoformat()}] To: {', '.join(recipient_emails)}\nSubject: {subject}\n{body}\n\n")
    except Exception as e:
        logger.error(f"Failed to write escalation log: {e}")
        
    # 2. Attempt SMTP transmission if variables are defined
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = os.getenv("SMTP_PORT")
    smtp_username = os.getenv("SMTP_USERNAME")
    smtp_password = os.getenv("SMTP_PASSWORD")
    
    if smtp_server and smtp_port and smtp_username and smtp_password:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = smtp_username
            msg['To'] = ", ".join(recipient_emails)
            
            with smtplib.SMTP(smtp_server, int(smtp_port)) as server:
                server.starttls()
                server.login(smtp_username, smtp_password)
                server.sendmail(smtp_username, recipient_emails, msg.as_string())
            logger.info(f"Escalation email successfully sent for Task #{task.id}.")
        except Exception as e:
            logger.error(f"Failed to send email via SMTP for Task #{task.id}: {e}")
    else:
        logger.info(f"Escalation email logged to logfile (SMTP variables missing) for Task #{task.id}.")

def run_recurring_task_generation(db: Session):
    """
    Checks RecurringTaskMaster templates and generates new tasks if their frequency cycle is hit.
    """
    templates = db.query(RecurringTaskMaster).filter(RecurringTaskMaster.is_active == True).all()
    now = datetime.utcnow()
    
    for temp in templates:
        due = False
        if not temp.last_generated_at:
            # First time generation
            if now >= temp.start_date:
                due = True
        else:
            # Check elapsed time depending on frequency
            elapsed = now - temp.last_generated_at
            freq = temp.frequency
            
            if freq == "Daily" and elapsed >= timedelta(days=1):
                due = True
            elif freq == "Weekly" and elapsed >= timedelta(weeks=1):
                due = True
            elif freq == "Monthly" and elapsed >= timedelta(days=30):
                due = True
            elif freq == "Quarterly" and elapsed >= timedelta(days=90):
                due = True
            elif freq == "Half-Yearly" and elapsed >= timedelta(days=180):
                due = True
            elif freq == "Yearly" and elapsed >= timedelta(days=365):
                due = True
            elif freq == "Every 2 Years" and elapsed >= timedelta(days=730):
                due = True
                
        if due:
            # Generate new Task
            new_task = Task(
                task_title=f"[Recurring] {temp.task_name}",
                task_description=temp.description,
                department=temp.department,
                category=temp.category,
                status="Pending",
                created_by_id=temp.responsible_person_id,
                created_at=now,
                is_archived=False,
                is_edited_flag=False,
                recurring_task_master_id=temp.id
            )
            db.add(new_task)
            
            # Update last generated date
            temp.last_generated_at = now
            
            # Notify Payroll Team & Manager about new task
            payroll_users = db.query(User).filter(User.role.in_(["Payroll Team", "Manager"]), User.is_active == True).all()
            for u in payroll_users:
                notification = Notification(
                    user_id=u.id,
                    title="Recurring Task Generated",
                    message=f"Recurring Task template #{temp.id} generated new Task #{new_task.id}: '{new_task.task_title}'."
                )
                db.add(notification)
                
            # Log audit trail
            audit_log = AuditLog(
                username="System Scheduler",
                timestamp=now,
                action_type="Task Creation",
                task_id=new_task.id,
                details=f"Auto-generated recurring task from template #{temp.id} '{temp.task_name}'."
            )
            db.add(audit_log)
            db.commit()
            logger.info(f"Generated task from template #{temp.id}.")

def run_task_escalations(db: Session):
    """
    Finds tasks pending for more than 7 days, and fires off escalations.
    """
    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)
    
    # Get all pending or in-progress tasks older than 7 days
    overdue_tasks = db.query(Task).filter(
        Task.status != "GM/CFO Approved",
        Task.is_archived == False,
        Task.created_at <= seven_days_ago
    ).all()
    
    for task in overdue_tasks:
        # Avoid duplicate escalations within 24 hours
        one_day_ago = now - timedelta(hours=24)
        duplicate_check = db.query(AuditLog).filter(
            AuditLog.task_id == task.id,
            AuditLog.action_type == "Email Notifications",
            AuditLog.timestamp >= one_day_ago
        ).first()
        
        if not duplicate_check:
            age_days = (now - task.created_at).days
            
            # Send escalation email
            send_escalation_email(task, age_days, db)
            
            # Log notification history in DB
            audit_log = AuditLog(
                username="System Scheduler",
                timestamp=now,
                action_type="Email Notifications",
                task_id=task.id,
                details=f"Sent escalation email alert to NM Finance. Task Age: {age_days} days."
            )
            db.add(audit_log)
            db.commit()
            logger.info(f"Sent escalation alert for Task #{task.id}.")

def scheduler_loop():
    logger.info("Background Scheduler Service Started.")
    while True:
        db = SessionLocal()
        try:
            run_recurring_task_generation(db)
            run_task_escalations(db)
        except Exception as e:
            logger.error(f"Error in scheduler job loop run: {e}")
        finally:
            db.close()
        # Sleep for 1 minute (for demonstration/fast testing) or 3600 seconds for production
        time.sleep(60)

def start_scheduler():
    t = threading.Thread(target=scheduler_loop, daemon=True)
    t.start()
