import os
import hashlib
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from database.connection import get_db
from database.models import EvidenceFile, User
from backend.security import get_current_user
from backend.utils import log_audit

router = APIRouter(prefix="/api/files", tags=["files"])

# Define absolute storage directory
STORAGE_DIR = "e:/Antigravity/Advance-Task-Tracker/storage/evidence"
os.makedirs(STORAGE_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".xlsx", ".xls"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Check extension
    filename = file.filename
    _, ext = os.path.splitext(filename.lower())
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed extensions: {list(ALLOWED_EXTENSIONS)}"
        )
        
    # Read file content to compute hash and check size
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum size of 10MB."
        )
        
    # Compute SHA-256
    file_hash = hashlib.sha256(content).hexdigest()
    
    # Check duplicate hash in DB
    existing_file = db.query(EvidenceFile).filter(EvidenceFile.file_hash == file_hash).first()
    if existing_file:
        # File is duplicate, prevent re-saving but return existing record detail
        log_audit(
            db=db,
            username=current_user.username,
            action_type="Evidence Upload",
            request=request,
            user_id=current_user.id,
            details=f"Duplicate file uploaded: '{filename}'. Linked to existing file #{existing_file.id}."
        )
        return {
            "message": "File already exists (duplicate hash detected)",
            "file_id": existing_file.id,
            "filename": existing_file.filename,
            "filepath": existing_file.filepath,
            "duplicate": True
        }
        
    # Unique name to store on disk
    unique_filename = f"{uuid.uuid4()}{ext}"
    dest_path = os.path.join(STORAGE_DIR, unique_filename)
    
    # Write to local file storage
    with open(dest_path, "wb") as f:
        f.write(content)
        
    # Save to database
    file_entry = EvidenceFile(
        filename=filename,
        filepath=dest_path,
        file_hash=file_hash,
        uploaded_by_id=current_user.id,
        uploaded_at=datetime.utcnow()
    )
    db.add(file_entry)
    db.commit()
    db.refresh(file_entry)
    
    # Audit log
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Evidence Upload",
        request=request,
        user_id=current_user.id,
        details=f"Uploaded evidence file '{filename}' (ID: {file_entry.id}). Hash: {file_hash}."
    )
    
    return {
        "message": "File uploaded successfully",
        "file_id": file_entry.id,
        "filename": file_entry.filename,
        "filepath": file_entry.filepath,
        "duplicate": False
    }

@router.get("/download/{file_id}")
def download_file(
    file_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == file_id).first()
    if not file_entry:
        raise HTTPException(status_code=404, detail="File record not found")
        
    if not os.path.exists(file_entry.filepath):
        raise HTTPException(status_code=404, detail="File content missing on server storage disk")
        
    # Log audit download event
    log_audit(
        db=db,
        username=current_user.username,
        action_type="Report Downloads",  # Fits Report Downloads context
        request=request,
        user_id=current_user.id,
        details=f"Downloaded file '{file_entry.filename}' (File ID: {file_id})."
    )
    
    return FileResponse(
        path=file_entry.filepath,
        filename=file_entry.filename,
        media_type="application/octet-stream"
    )

@router.get("/info/{file_id}")
def get_file_info(
    file_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    file_entry = db.query(EvidenceFile).filter(EvidenceFile.id == file_id).first()
    if not file_entry:
        raise HTTPException(status_code=404, detail="File record not found")
        
    return {
        "id": file_entry.id,
        "filename": file_entry.filename,
        "uploaded_by": file_entry.uploaded_by.username if file_entry.uploaded_by else "Unknown",
        "uploaded_at": file_entry.uploaded_at.isoformat(),
        "file_hash": file_entry.file_hash
    }
from datetime import datetime
