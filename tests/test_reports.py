import pytest

def test_reports_endpoints(client, admin_headers, payroll_headers):
    # 1. Non-authorized user tries to get reports - should fail (403)
    resp = client.get("/api/reports/excel", headers=payroll_headers)
    assert resp.status_code == 403
    
    # 2. Excel workbook compilation - should succeed
    resp_excel = client.get("/api/reports/excel", headers=admin_headers)
    assert resp_excel.status_code == 200
    assert resp_excel.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert len(resp_excel.content) > 0
    
    # 3. PDF compilation - should succeed
    resp_pdf = client.get("/api/reports/pdf", headers=admin_headers)
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 0
    
    # 4. CSV compilation cases
    for rtype in ["tasks", "audit", "evidence"]:
        resp_csv = client.get(f"/api/reports/csv?report_type={rtype}", headers=admin_headers)
        assert resp_csv.status_code == 200
        assert resp_csv.headers["content-type"] == "text/csv; charset=utf-8"
        assert len(resp_csv.content) > 0
        
    # 5. Invalid CSV report type - should fail (400)
    resp_bad = client.get("/api/reports/csv?report_type=invalid_type", headers=admin_headers)
    assert resp_bad.status_code == 400
