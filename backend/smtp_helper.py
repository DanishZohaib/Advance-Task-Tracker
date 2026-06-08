import os
import smtplib
import logging
import base64
from email.mime.text import MIMEText
from datetime import datetime
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from database.models import SystemSetting, EmailDeliveryLog

logger = logging.getLogger("SMTPHelper")

ESCALATION_LOG_FILE = "e:/Antigravity/Advance-Task-Tracker/storage/escalations.log"
os.makedirs(os.path.dirname(ESCALATION_LOG_FILE), exist_ok=True)

# Derive symmetric encryption key from JWT Secret Key
def get_fernet_key() -> bytes:
    secret_key = os.getenv("JWT_SECRET_KEY", "enterprise_super_secret_key_123456789_dont_leak")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"smtp_encryption_salt_123",
        iterations=10000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode('utf-8')))
    return key

def encrypt_smtp_password(password: str) -> str:
    if not password:
        return ""
    f = Fernet(get_fernet_key())
    return f.encrypt(password.encode('utf-8')).decode('utf-8')

def decrypt_smtp_password(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        f = Fernet(get_fernet_key())
        return f.decrypt(cipher_text.encode('utf-8')).decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to decrypt SMTP password: {e}")
        return ""

def test_smtp_connection(host: str, port: int, sender: str, password: str, use_tls: bool, use_ssl: bool) -> tuple[bool, str]:
    """
    Tests direct SMTP connection parameters
    """
    try:
        if use_ssl:
            server = smtplib.SMTP_SSL(host, port, timeout=10)
        else:
            server = smtplib.SMTP(host, port, timeout=10)
            
        if use_tls and not use_ssl:
            server.starttls()
            
        if password:
            server.login(sender, password)
            
        server.quit()
        return True, "Connection Successful"
    except Exception as e:
        return False, str(e)

def send_smtp_email(db: Session, event_type: str, recipient: str, subject: str, body: str) -> bool:
    """
    Sends email notification using database SMTP configurations.
    Fails over to local logging if settings are not defined.
    """
    # Load SMTP settings from database
    settings = {}
    db_settings = db.query(SystemSetting).all()
    for s in db_settings:
        settings[s.key] = s.value
        
    smtp_host = settings.get("smtp_host")
    smtp_port = settings.get("smtp_port")
    smtp_sender = settings.get("smtp_sender_email")
    smtp_password_enc = settings.get("smtp_sender_password")
    smtp_use_tls = settings.get("smtp_use_tls", "true").lower() == "true"
    smtp_use_ssl = settings.get("smtp_use_ssl", "false").lower() == "true"
    
    # Decrypt password
    smtp_password = decrypt_smtp_password(smtp_password_enc) if smtp_password_enc else ""
    
    # 1. Fallback mock logging if settings are missing
    if not smtp_host or not smtp_sender:
        logger.info(f"SMTP not configured. Fallback log for {event_type} to {recipient}.")
        try:
            with open(ESCALATION_LOG_FILE, "a") as f:
                f.write(f"[{datetime.now().isoformat()}] EVENT: {event_type} | To: {recipient}\nSubject: {subject}\n{body}\n\n")
            
            # Log successful local log save in DB logs
            log_entry = EmailDeliveryLog(
                recipient=recipient,
                subject=subject,
                event_type=event_type,
                status="Sent (Mock Logging)",
                sent_at=datetime.utcnow()
            )
            db.add(log_entry)
            db.commit()
            return True
        except Exception as e:
            logger.error(f"Failed mock logging: {e}")
            return False
            
    # 2. Direct SMTP send
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = smtp_sender
        msg['To'] = recipient
        
        if smtp_use_ssl:
            server = smtplib.SMTP_SSL(smtp_host, int(smtp_port), timeout=10)
        else:
            server = smtplib.SMTP(smtp_host, int(smtp_port), timeout=10)
            
        if smtp_use_tls and not smtp_use_ssl:
            server.starttls()
            
        if smtp_password:
            server.login(smtp_sender, smtp_password)
            
        server.sendmail(smtp_sender, [recipient], msg.as_string())
        server.quit()
        
        # Log successful delivery
        log_entry = EmailDeliveryLog(
            recipient=recipient,
            subject=subject,
            event_type=event_type,
            status="Sent",
            sent_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        return True
    except Exception as e:
        logger.error(f"SMTP delivery failed: {e}")
        # Log failure
        log_entry = EmailDeliveryLog(
            recipient=recipient,
            subject=subject,
            event_type=event_type,
            status="Failed",
            error_message=str(e),
            sent_at=datetime.utcnow()
        )
        db.add(log_entry)
        db.commit()
        return False
