import io
import pytest
from database.models import EvidenceFile

def test_evidence_file_uploads_and_deduplication(client, payroll_headers):
    # 1. Invalid extension upload
    bad_file = {"file": ("test.txt", b"dummy content", "text/plain")}
    resp = client.post("/api/files/upload", files=bad_file, headers=payroll_headers)
    assert resp.status_code == 400
    assert "Invalid file type" in resp.json()["detail"]
    
    # 2. Valid extension upload
    img_data = b"fake_png_data_signature_bytes_1234"
    valid_file = {"file": ("screenshot.png", img_data, "image/png")}
    resp = client.post("/api/files/upload", files=valid_file, headers=payroll_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["message"] == "File uploaded successfully"
    assert data["duplicate"] is False
    file_id = data["file_id"]
    
    # 3. Duplicate upload (same bytes)
    dup_file = {"file": ("screenshot_dup.png", img_data, "image/png")}
    resp_dup = client.post("/api/files/upload", files=dup_file, headers=payroll_headers)
    assert resp_dup.status_code == 200
    dup_data = resp_dup.json()
    assert "duplicate" in dup_data
    assert dup_data["duplicate"] is True
    assert dup_data["file_id"] == file_id
    
    # 4. Info fetch
    info_resp = client.get(f"/api/files/info/{file_id}", headers=payroll_headers)
    assert info_resp.status_code == 200
    assert info_resp.json()["filename"] == "screenshot.png"
    
    # 5. Download verification
    dl_resp = client.get(f"/api/files/download/{file_id}", headers=payroll_headers)
    assert dl_resp.status_code == 200
    assert dl_resp.content == img_data
