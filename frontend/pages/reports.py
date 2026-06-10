import streamlit as st
from frontend.api_client import APIClient, BACKEND_URL

def render_page():
    st.title("📁 Advanced Compliance Reporting Center")
    st.write("Generate and download compliance records, audit journals, and workflow timing metrics.")
    st.markdown("---")
    
    role = st.session_state["user_role"]
    if role not in ["Administrator", "Auditor", "GM/CFO", "NM Finance"]:
        st.warning("You do not have administrative reporting permissions to download documents.")
        return
        
    st.markdown("### 📋 Executive Reporting Station")
    st.write("Select the report package format below to compile the database logs.")
    
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
                resp = APIClient.get("/api/reports/pdf")
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
                resp = APIClient.get("/api/reports/excel")
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
                resp = APIClient.get(f"/api/reports/csv?report_type={csv_type}")
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
