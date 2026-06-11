import streamlit as st
from frontend.api_client import APIClient, BACKEND_URL

def render_page():
    st.title("📁 Advanced Compliance Reporting Center")
    st.write("Generate, filter, and download compliance records, audit journals, and workflow timing metrics.")
    st.markdown("---")
    
    role = st.session_state["user_role"]
    if role not in ["Administrator", "Auditor", "GM/CFO", "NM Finance"]:
        st.warning("You do not have administrative reporting permissions to download documents.")
        return
        
    st.markdown("### 🔍 Live Filter & Compliance Preview")
    
    # Grid of report filters
    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        category = st.selectbox("Category Filter", options=["All", "Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules", "General Support Activities"])
        completed_by = st.selectbox("Completed By State", options=["All", "Manager", "NM Finance", "GM/CFO"])
    with col_f2:
        returned = st.selectbox("Returned Flag", options=["All", "Yes", "No"])
        rejected = st.selectbox("Rejected Flag", options=["All", "Yes", "No"])
    with col_f3:
        overdue = st.selectbox("Overdue SLA", options=["All", "Yes", "No"])
        escalated = st.selectbox("Escalated SLA", options=["All", "Yes", "No"])
    with col_f4:
        has_evidence = st.selectbox("Has Evidence", options=["All", "Yes", "No"])
        interval = st.selectbox("Time Interval", options=["All", "Monthly", "Quarterly", "Half-Yearly", "Yearly"])

    # Build params dict
    params = {}
    if category != "All":
        params["category"] = category
    if completed_by != "All":
        params["completed_by"] = completed_by
    if returned != "All":
        params["returned"] = str(returned == "Yes").lower()
    if rejected != "All":
        params["rejected"] = str(rejected == "Yes").lower()
    if overdue != "All":
        params["overdue"] = str(overdue == "Yes").lower()
    if escalated != "All":
        params["escalated"] = str(escalated == "Yes").lower()
    if has_evidence != "All":
        params["has_evidence"] = str(has_evidence == "Yes").lower()
    if interval != "All":
        params["interval"] = interval

    # Fetch live preview list
    with st.spinner("Fetching matching compliance records..."):
        resp_tasks = APIClient.get("/api/reports/tasks", params=params)
        
    if resp_tasks and resp_tasks.status_code == 200:
        tasks_list = resp_tasks.json()
        st.markdown(f"**Found {len(tasks_list)} tasks matching the selected compliance criteria.**")
        
        if len(tasks_list) > 0:
            preview_data = []
            for t in tasks_list[:10]: # Top 10 preview
                preview_data.append({
                    "ID": t["id"],
                    "Title": t["task_title"],
                    "Category": t["category"],
                    "Status": t["status"],
                    "Created By": t["created_by"],
                    "Created At": t["created_at"][:10] if t["created_at"] else "",
                    "Rejections": t["rejection_count"]
                })
            st.table(preview_data)
            if len(tasks_list) > 10:
                st.info(f"Showing first 10 of {len(tasks_list)} items. Generate a report below to download the full registry.")
        else:
            st.warning("No records match the current filter selection.")
    else:
        st.error("Failed to query reports preview from server API.")

    st.markdown("---")
    st.markdown("### 📋 Executive Export Station")
    st.write("Compile the matching records into one of the following premium formats:")
    
    col1, col2, col3 = st.columns(3)
    
    # PDF compilation
    with col1:
        st.markdown(
            """
            <div style='background: rgba(79, 70, 229, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(79, 70, 229, 0.1); min-height: 220px;'>
                <h4 style='color: #4F46E5; margin-top:0;'>📄 PDF Executive Report</h4>
                <p style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Styled letter-size document containing workflow metrics, open task lists, and summary diagrams for audit review.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Generate & Download PDF", key="pdf_dl_btn", use_container_width=True):
            with st.spinner("Compiling PDF document..."):
                resp = APIClient.get("/api/reports/pdf", params=params)
                if resp and resp.status_code == 200:
                    st.download_button(
                        label="💾 Save PDF File",
                        data=resp.content,
                        file_name="executive_compliance_summary.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate PDF.")
                    
    # Excel Workbook Compilation
    with col2:
        st.markdown(
            """
            <div style='background: rgba(16, 185, 129, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(16, 185, 129, 0.1); min-height: 220px;'>
                <h4 style='color: #10B981; margin-top:0;'>📊 Multi-Sheet Excel Report</h4>
                <p style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Complete data workbook containing sheets for: <b>Tasks Pipeline</b>, <b>User Productivity</b>, and <b>Audit Trail Journal</b>.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        if st.button("Generate & Download Excel", key="excel_dl_btn", use_container_width=True):
            with st.spinner("Compiling Excel workbook..."):
                resp = APIClient.get("/api/reports/excel", params=params)
                if resp and resp.status_code == 200:
                    st.download_button(
                        label="💾 Save Excel File",
                        data=resp.content,
                        file_name="enterprise_compliance_report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate Excel sheet.")
                    
    # CSV Raw Export
    with col3:
        st.markdown(
            """
            <div style='background: rgba(245, 158, 11, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(245, 158, 11, 0.1); min-height: 220px;'>
                <h4 style='color: #F59E0B; margin-top:0;'>📝 CSV Data Tables</h4>
                <p style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Raw comma-separated value tables. Choose to pull either the <b>Tasks list</b>, <b>Audit Trail</b>, or <b>Evidence registry</b>.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        csv_type = st.selectbox("CSV Target Data", options=["tasks", "audit", "evidence"])
        if st.button("Generate & Download CSV", key="csv_dl_btn", use_container_width=True):
            with st.spinner("Compiling CSV table..."):
                csv_params = params.copy()
                csv_params["report_type"] = csv_type
                resp = APIClient.get(f"/api/reports/csv", params=csv_params)
                if resp and resp.status_code == 200:
                    st.download_button(
                        label="💾 Save CSV File",
                        data=resp.content,
                        file_name=f"{csv_type}_report.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("Failed to generate CSV.")
