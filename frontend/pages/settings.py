import streamlit as st
from datetime import datetime
from frontend.api_client import APIClient

def render_page():
    st.markdown("<h1 style='color: #4F46E5;'>⚙️ SMTP Admin Settings</h1>", unsafe_allow_html=True)
    st.write("Configure and verify the enterprise SMTP server settings for automated workflow notifications and escalations.")
    st.markdown("---")
    
    # Check authorization
    if st.session_state.get("user_role") != "Administrator":
        st.error("Access Denied: SMTP settings are restricted to Administrators only.")
        return
        
    tab_smtp, tab_logs = st.tabs(["📧 SMTP Configuration", "📊 Email Delivery Logs"])
    
    with tab_smtp:
        # Load existing settings
        resp = APIClient.get("/api/settings/smtp")
        if not resp or resp.status_code != 200:
            st.error("Failed to retrieve current SMTP settings.")
            return
            
        settings = resp.json()
        
        st.markdown(
            """
            <div style='background: rgba(79, 70, 229, 0.05); padding: 20px; border-radius: 10px; border: 1px solid rgba(79, 70, 229, 0.15); margin-bottom: 20px;'>
                <h4 style='margin:0; color: #4F46E5;'>🔒 Secure SMTP Credentials Encryption</h4>
                <p style='margin-top: 5px; margin-bottom: 0; font-size: 0.85rem; color: #94A3B8;'>
                    All SMTP credentials, including passwords, are symmetrically encrypted on the server before storage to prevent unauthorized corporate access.
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
        
        # SMTP Form
        with st.form("smtp_config_form"):
            host = st.text_input("SMTP Host Server", value=settings.get("smtp_host", ""))
            port = st.number_input("SMTP Port", min_value=1, max_value=65535, value=settings.get("smtp_port", 587))
            sender = st.text_input("Sender Email Address", value=settings.get("smtp_sender_email", ""))
            
            pwd_label = "Sender Password (Leave blank to keep current saved password)" if settings.get("has_password") else "Sender Password"
            password = st.text_input(pwd_label, type="password", help="The authentication password for the SMTP sender account.")
            
            col_ssl, col_tls = st.columns(2)
            with col_ssl:
                use_ssl = st.checkbox("Use SSL Connection", value=settings.get("smtp_use_ssl", False))
            with col_tls:
                use_tls = st.checkbox("Use TLS Connection (Recommended)", value=settings.get("smtp_use_tls", True))
                
            submit_btn = st.form_submit_button("Save SMTP Settings", use_container_width=True)
            
            if submit_btn:
                payload = {
                    "smtp_host": host,
                    "smtp_port": int(port),
                    "smtp_sender_email": sender,
                    "smtp_use_tls": use_tls,
                    "smtp_use_ssl": use_ssl
                }
                if password:
                    payload["smtp_sender_password"] = password
                    
                upd_resp = APIClient.post("/api/settings/smtp", json=payload)
                if upd_resp and upd_resp.status_code == 200:
                    from frontend.styles import show_animated_checkmark
                    show_animated_checkmark("SMTP Configuration saved successfully!")
                    import time
                    time.sleep(1.5)
                    st.rerun()
                else:
                    detail = upd_resp.json().get("detail", "Failed to save settings.") if upd_resp else "Server connection error."
                    st.error(detail)
                    
        # Test connection panel
        st.markdown("### 🔌 Test Mail Server Connection")
        col_test_btn, col_test_info = st.columns([1, 2])
        with col_test_btn:
            test_pwd = st.text_input("Temporary Test Password", type="password", help="Required if password is not saved or to test a new password before saving.", key="test_pwd_field")
            run_test = st.button("Execute Connection Test", use_container_width=True)
        with col_test_info:
            st.markdown("<p style='font-size:0.85rem; color:#94A3B8; margin-top:28px;'>Performs a socket connection check, initiates TLS/SSL, and validates SMTP login credentials against the parameters above.</p>", unsafe_allow_html=True)
            
        if run_test:
            test_payload = {
                "smtp_host": host,
                "smtp_port": int(port),
                "smtp_sender_email": sender,
                "smtp_use_tls": use_tls,
                "smtp_use_ssl": use_ssl,
                "use_saved_password": not bool(test_pwd)
            }
            if test_pwd:
                test_payload["smtp_sender_password"] = test_pwd
                
            with st.spinner("Connecting to SMTP server..."):
                t_resp = APIClient.post("/api/settings/smtp/test", json=test_payload)
                if t_resp and t_resp.status_code == 200:
                    t_data = t_resp.json()
                    if t_data.get("success"):
                        st.success(t_data.get("message", "Success! Connection verified."))
                    else:
                        st.error(t_data.get("message", "Test failed."))
                else:
                    detail = t_resp.json().get("detail", "Connection test failed.") if t_resp else "Network connection error."
                    st.error(detail)
                    
    with tab_logs:
        st.subheader("📋 Delivery Log History (Last 100 Entries)")
        
        # Load Logs
        log_resp = APIClient.get("/api/settings/email-logs")
        if not log_resp or log_resp.status_code != 200:
            st.error("Failed to load email delivery logs.")
            return
            
        logs_list = log_resp.json()
        
        if not logs_list:
            st.info("No email transmission logs available.")
        else:
            for l in logs_list:
                log_time = datetime.fromisoformat(l["sent_at"].replace("Z", "")).strftime('%Y-%m-%d %H:%M:%S')
                
                status_color = "#10B981" if l["status"] == "Sent" else "#EF4444"
                status_badge = f"<span style='color: {status_color}; font-weight: bold;'>● {l['status'].upper()}</span>"
                
                box_border = "border-left: 4px solid #10B981;" if l["status"] == "Sent" else "border-left: 4px solid #EF4444;"
                
                err_detail = ""
                if l["error_message"]:
                    err_detail = f"<div style='margin-top:5px; font-size: 0.8rem; color: #FDA4AF;'><b>Error:</b> {l['error_message']}</div>"
                    
                st.markdown(
                    f"""
                    <div style='border: 1px solid #334155; padding: 12px; border-radius: 6px; margin-bottom: 8px; background-color: rgba(255, 255, 255, 0.01); {box_border}'>
                        <div style='display: flex; justify-content: space-between;'>
                            <span>📧 To: <b>{l['recipient']}</b></span>
                            <span style='font-size:0.8rem; color:#94A3B8;'>{log_time}</span>
                        </div>
                        <div style='margin-top: 4px; font-size:0.9rem;'>
                            Subject: <span style='color:#F1F5F9;'>{l['subject']}</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; margin-top:6px; font-size: 0.8rem;'>
                            <span>Event Type: <code>{l['event_type']}</code></span>
                            {status_badge}
                        </div>
                        {err_detail}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
