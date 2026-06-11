import os
import time
import streamlit as st
from datetime import datetime
from frontend.api_client import APIClient, BACKEND_URL
from backend.utils import format_duration
from frontend.styles import show_animated_bell

def upload_evidence(uploaded_file):
    """
    Helper to upload evidence files to the backend and return file ID
    """
    if not uploaded_file:
        return None
    try:
        files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
        resp = APIClient.post("/api/files/upload", auth_required=True, files=files)
        if resp and resp.status_code == 200:
            return resp.json().get("file_id")
        else:
            detail = resp.json().get("detail", "File upload failed.") if resp else "Failed to connect to backend."
            st.error(detail)
    except Exception as e:
        st.error(f"Error uploading file: {e}")
    return None

def render_page():
    st.markdown("<h1 style='color: #4F46E5;'>📝 Workflows & Tasks Workspace</h1>", unsafe_allow_html=True)
    st.write(f"Logged in as: **{st.session_state['username']}** | Access Level: **{st.session_state['user_role']}**")
    st.markdown("---")
    
    # Same-Day Due check for logged-in user
    all_resp = APIClient.get("/api/tasks")
    if all_resp and all_resp.status_code == 200:
        all_tasks = all_resp.json()
        now_date = datetime.utcnow().date()
        user_role = st.session_state["user_role"]
        due_today_actions = []
        for t in all_tasks:
            if t["status"] != "GM/CFO Approved" and t.get("planned_due_date"):
                try:
                    due_date = datetime.fromisoformat(t["planned_due_date"].replace("Z", "")).date()
                    if due_date == now_date:
                        # Check if action is pending for user's role
                        is_pending = False
                        if t["status"] == "Pending" and user_role in ["Payroll Team", "Administrator"]:
                            is_pending = True
                        elif t["status"] == "Payroll Completed" and user_role in ["NM Finance", "Administrator"]:
                            is_pending = True
                        elif t["status"] == "NM Finance Approved" and user_role in ["GM/CFO", "Administrator"]:
                            is_pending = True
                        
                        if is_pending:
                            due_today_actions.append(t)
                except ValueError:
                    pass
                    
        if due_today_actions:
            show_animated_bell(due_today_actions)
    
    # 1. Four Core Modules Cards (Representing Categories in Phase 2)
    st.markdown("### 🗂️ Select Compliance Category")
    
    categories = [
        {"name": "Payroll", "icon": "💰", "desc": "Payroll Processing & Disbursement"},
        {"name": "Fund Accounting", "icon": "📊", "desc": "Allocations, Ledgers & Bank Recs"},
        {"name": "Petty Cash", "icon": "💵", "desc": "Cash Disbursements & Vouchers"},
        {"name": "Audit Schedules", "icon": "🛡️", "desc": "Internal Controls & Verification"}
    ]
    
    # Track selected category in session state
    if "selected_category" not in st.session_state:
        st.session_state["selected_category"] = "Payroll"
        
    m_cols = st.columns(4)
    for idx, c in enumerate(categories):
        with m_cols[idx]:
            card_class = "module-card"
            border_style = "border-color: #4F46E5; background: rgba(79, 70, 229, 0.15);" if st.session_state["selected_category"] == c["name"] else ""
            
            st.markdown(
                f"""
                <div class="{card_class}" style="{border_style}">
                    <div class="module-icon">{c['icon']}</div>
                    <div class="module-name">{c['name']}</div>
                    <div class="module-desc">{c['desc']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            # Standard Streamlit button fallback to handle category state change
            if st.button(f"Activate {c['name']}", key=f"cat_btn_{c['name']}", use_container_width=True):
                st.session_state["selected_category"] = c["name"]
                st.rerun()

    st.markdown("---")
    st.subheader(f"Workspace: Finance & Payroll Department → {st.session_state['selected_category']} Pipeline")
    
    # Load tasks for selected category
    resp = APIClient.get(f"/api/tasks?category={st.session_state['selected_category']}")
    if not resp or resp.status_code != 200:
        st.error("Could not fetch tasks for this category.")
        return
        
    tasks = resp.json()
    
    # Check tabs permissions
    tabs_list = ["📋 Tasks Pipeline Board", "➕ Create New Task"]
    if st.session_state["user_role"] in ["Administrator", "GM/CFO"]:
        tabs_list.append("📤 Bulk Excel Import")
        
    tabs = st.tabs(tabs_list)
    tab_board = tabs[0]
    tab_create = tabs[1]
    tab_import = tabs[2] if len(tabs) > 2 else None
    
    # Tab 1: Pipeline Board
    with tab_board:
        # Search & Filter
        col_search, col_filter = st.columns([2, 1])
        with col_search:
            search_query = st.text_input("Search tasks by title/description", placeholder="Type keywords...", key="task_search_input")
        with col_filter:
            status_filter = st.selectbox("Stage Filter", options=["All", "Pending", "Payroll Completed", "NM Finance Approved", "GM/CFO Approved"])
            
        # Apply local UI filtering
        filtered_tasks = tasks
        if search_query:
            filtered_tasks = [t for t in filtered_tasks if search_query.lower() in t["task_title"].lower() or (t["task_description"] and search_query.lower() in t["task_description"].lower())]
        if status_filter != "All":
            filtered_tasks = [t for t in filtered_tasks if t["status"] == status_filter]
            
        if not filtered_tasks:
            st.info("No active tasks found matching the criteria.")
        else:
            # Separate active (pending approval steps) and completed (GM/CFO Approved)
            active_tasks = [t for t in filtered_tasks if t["status"] != "GM/CFO Approved"]
            completed_tasks = [t for t in filtered_tasks if t["status"] == "GM/CFO Approved"]
            
            c_left, c_right = st.columns(2)
            
            # LEFT: Active Tasks in Workflow
            with c_left:
                st.markdown("### ⏳ Active Workflows (In Progress)")
                if not active_tasks:
                    st.success("🎉 No active tasks in this category. All compliance gates completed!")
                else:
                    for t in active_tasks:
                        edited_label = " :green-background[Edited]" if t["is_edited_flag"] else ""
                        status_label = f" :blue-background[{t['status']}]"
                        expander_title = f"Task #{t['id']}: **{t['task_title']}**{edited_label}{status_label}"
                        
                        # Set priority indicator based on SLA status
                        sla_status = t.get("sla_status", "On Track")
                        priority_icon = "🟢"
                        if sla_status == "Critical":
                            priority_icon = "🔴 (SLA Critical Overdue)"
                        elif sla_status == "Overdue":
                            priority_icon = "🟠 (SLA Overdue)"
                        elif sla_status == "Due Soon":
                            priority_icon = "🟡 (SLA Due Soon)"
                            
                        with st.expander(f"{priority_icon} {expander_title}", expanded=False):
                            st.markdown(f"**Description:**\n{t['task_description'] or '*No description provided.*'}")
                            st.markdown(f"**SLA Status:** `{sla_status}` (Days remaining: `{t['days_remaining']}` | Overdue: `{t['overdue_days']}` days)")
                            st.markdown(f"**Target Due Date:** `{t['planned_due_date'][:16] if t['planned_due_date'] else 'N/A'}`")
                            
                            if t["rejection_count"] > 0:
                                st.markdown(
                                    f"""
                                    <div style='background: rgba(239, 68, 68, 0.08); border: 1px solid rgba(239, 68, 68, 0.25); border-radius: 6px; padding: 10px; margin-bottom: 12px;'>
                                        <span style='color: #EF4444; font-weight: bold;'>⚠️ REJECTION HISTORY DETECTED</span><br>
                                        <span style='font-size:0.85rem; color:var(--text-color); opacity: 0.85;'>Total Rejections count: <b>{t['rejection_count']}</b></span><br>
                                        <span style='font-size:0.85rem; color:var(--text-color); opacity: 0.7;'>Last Rejected by: <b>{t['last_rejected_by']}</b> ({t['last_rejected_stage']})</span><br>
                                        <span style='font-size:0.85rem; color:var(--text-color); opacity: 0.7;'>Reason: <span style='font-style:italic; color:var(--text-color);'>\"{t['last_rejection_reason']}\"</span></span>
                                    </div>
                                    """,
                                    unsafe_allow_html=True
                                )
                                
                            # Query detailed activity timeline log history for this task
                            st.markdown("#### 🏁 Approval Timeline & Activity Logs")
                            detail_resp = APIClient.get(f"/api/tasks/{t['id']}")
                            if detail_resp and detail_resp.status_code == 200:
                                t_details = detail_resp.json()
                                activities = t_details.get("activities", [])
                                
                                for act in activities:
                                    # Format timestamp
                                    act_time = datetime.fromisoformat(act["timestamp"].replace("Z", "")).strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    # Determine visual style based on action
                                    icon_color = "#4F46E5"
                                    if "Rejected" in act["action"] or "Returned" in act["action"] or "Return" in act["action"]:
                                        icon_color = "#EF4444"
                                    elif "Completed" in act["action"] or "Approved" in act["action"] or "Released" in act["action"]:
                                        icon_color = "#10B981"
                                        
                                    duration_lbl = ""
                                    if act["duration"] > 0:
                                        duration_lbl = f" | <span style='color:var(--text-color); opacity: 0.7;'>Time in stage:</span> {format_duration(act['duration'])}"
                                        
                                    sig_box = ""
                                    if act["digital_signature_hash"]:
                                        sig_box = f"""
                                        <div style='background: rgba(16, 185, 129, 0.06); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 6px; padding: 8px; margin-top: 6px;'>
                                            <span style='color: #10B981; font-weight: bold; font-size: 0.75rem;'>🛡️ SECURE DIGITAL APPROVAL SIGNATURE</span><br>
                                            <span style='font-size:0.7rem; color:var(--text-color); opacity: 0.7;'>Hash:</span> <code style='font-size:0.68rem; color:var(--text-color); font-family: monospace; background: rgba(128,128,128,0.1); padding: 2px 4px; border-radius: 4px;'>{act['digital_signature_hash']}</code><br>
                                            <span style='font-size:0.7rem; color:var(--text-color); opacity: 0.7;'>IP:</span> <code style='font-size:0.7rem; color:var(--text-color); font-family: monospace; background: rgba(128,128,128,0.1); padding: 2px 4px; border-radius: 4px;'>{act['ip_address'] or 'Localhost'}</code> | <span style='font-size:0.7rem; color:var(--text-color); opacity: 0.7;'>Device:</span> <span style='font-size:0.7rem; color:var(--text-color); opacity: 0.85;'>{act['device_info'][:60] + '...' if len(act['device_info']) > 60 else act['device_info']}</span>
                                        </div>
                                        """
                                        
                                    evidence_lbl = ""
                                    if act.get("evidence_file_id"):
                                        file_id = act["evidence_file_id"]
                                        evidence_lbl = f"""
                                        <div style='margin-top: 6px;'>
                                            📄 <span style='font-size: 0.8rem; color: var(--text-color); opacity: 0.85;'>Attached Stage Evidence:</span> 
                                            <a href='{BACKEND_URL}/api/files/download/{file_id}' target='_blank' style='font-size: 0.8rem; font-weight: 600; color: #4F46E5;'>📥 Download Evidence File</a>
                                        </div>
                                        """
                                        
                                    st.markdown(
                                        f"""
                                        <div style='border-left: 3px solid {icon_color}; padding-left: 12px; margin-bottom: 10px;'>
                                            <div style='font-weight: 600; font-size: 0.9rem; color: {icon_color};'>{act['action']}</div>
                                            <div style='font-size: 0.8rem; color: var(--text-color); opacity: 0.7;'>
                                                By <b>{act['username']}</b> ({act['user_role']}) on {act_time}{duration_lbl}
                                            </div>
                                            <div style='font-size: 0.85rem; color: var(--text-color); opacity: 0.85; margin-top: 4px; font-style: italic;'>
                                                Remarks: "{act['comments']}"
                                            </div>
                                            {evidence_lbl}
                                            {sig_box}
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                    
                            # Render Evidence files if present
                            if t["payroll_evidence_file_id"]:
                                st.markdown("##### 📁 Attached Evidence Verification File")
                                file_info_resp = APIClient.get(f"/api/files/info/{t['payroll_evidence_file_id']}")
                                if file_info_resp and file_info_resp.status_code == 200:
                                    file_meta = file_info_resp.json()
                                    st.write(f"📄 **File:** `{file_meta['filename']}`")
                                    # Serve download link
                                    st.markdown(f"[📥 Download Evidence Screenshot]({BACKEND_URL}/api/files/download/{t['payroll_evidence_file_id']})")
                                    # If image file, show small preview
                                    _, ext = os.path.splitext(file_meta['filename'].lower())
                                    if ext in {".png", ".jpg", ".jpeg"}:
                                        st.image(f"{BACKEND_URL}/api/files/download/{t['payroll_evidence_file_id']}", caption="Evidence Screenshot Preview", width=300)
                                        
                            st.markdown("---")
                            
                            # STAGE ACTION TRIGGERS (Restricted by user role)
                            role = st.session_state["user_role"]
                            status_val = t["status"]
                            
                            if status_val in ["Pending", "Returned to Initiator"] and (role in ["Payroll Team", "Manager", "Administrator"]):
                                st.markdown("##### ⚙️ Action Panel: Complete Payroll (Stage 1)")
                                with st.form(key=f"stage1_form_{t['id']}", clear_on_submit=True):
                                    s1_comments = st.text_area("Payroll Remarks (Mandatory)", placeholder="Describe actions performed...")
                                    s1_file = st.file_uploader("Upload Evidence Screenshot/Worksheet (Mandatory)", type=["png", "jpg", "jpeg", "pdf", "xlsx", "xls"], key=f"s1_file_{t['id']}")
                                    s1_submit = st.form_submit_button("Complete Stage 1 & Sign-off", use_container_width=True)
                                    
                                    if s1_submit:
                                        if not s1_comments.strip():
                                            st.error("Remarks comments field is mandatory.")
                                        elif not s1_file:
                                            st.error("Verification file upload is mandatory.")
                                        else:
                                            file_id = upload_evidence(s1_file)
                                            # Complete Stage 1 via generic endpoint
                                            act_resp = APIClient.post(
                                                f"/api/tasks/{t['id']}/action",
                                                json={"action": "Forward", "comments": s1_comments, "evidence_file_id": file_id}
                                            )
                                            if act_resp and act_resp.status_code == 200:
                                                from frontend.styles import show_animated_checkmark
                                                show_animated_checkmark("Stage 1 Payroll sign-off completed!")
                                                time.sleep(1.5)
                                                st.rerun()
                                            else:
                                                det = act_resp.json().get("detail", "Transaction failed.") if act_resp else "Backend unreachable."
                                                st.error(det)
                                                
                            elif status_val == "Payroll Completed" and (role in ["NM Finance", "Administrator"]):
                                st.markdown("##### ⚙️ Action Panel: Approve or Reject (Stage 2)")
                                approve_col, reject_col = st.columns(2)
                                
                                with approve_col:
                                    with st.form(key=f"stage2_approve_form_{t['id']}", clear_on_submit=True):
                                        st.markdown("<h6 style='color:#10B981;'>Forward Task</h6>", unsafe_allow_html=True)
                                        s2_comments = st.text_area("Approval Remarks", placeholder="Add review verification notes...")
                                        s2_file = st.file_uploader("Upload Verification File (Mandatory)", type=["png", "jpg", "jpeg", "pdf", "xlsx", "xls"], key=f"s2_file_{t['id']}")
                                        s2_submit = st.form_submit_button("Approve Stage 2", use_container_width=True)
                                        
                                        if s2_submit:
                                            if not s2_comments.strip():
                                                st.error("Approval remarks are mandatory.")
                                            elif not s2_file:
                                                st.error("Verification file upload is mandatory.")
                                            else:
                                                file_id = upload_evidence(s2_file)
                                                act_resp = APIClient.post(
                                                    f"/api/tasks/{t['id']}/action",
                                                    json={"action": "Forward", "comments": s2_comments, "evidence_file_id": file_id}
                                                )
                                                if act_resp and act_resp.status_code == 200:
                                                    from frontend.styles import show_animated_checkmark
                                                    show_animated_checkmark("Stage 2 NM Finance approved!")
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    det = act_resp.json().get("detail", "Transaction failed.") if act_resp else "Backend unreachable."
                                                    st.error(det)
                                                    
                                with reject_col:
                                    with st.form(key=f"stage2_reject_form_{t['id']}", clear_on_submit=True):
                                        st.markdown("<h6 style='color:#EF4444;'>Reject and Return to Payroll Team</h6>", unsafe_allow_html=True)
                                        s2_reject_comments = st.text_area("Rejection Comments", placeholder="Explain the corrections required...")
                                        s2_reject_submit = st.form_submit_button("Reject back to Stage 1", use_container_width=True)
                                        
                                        if s2_reject_submit:
                                            if not s2_reject_comments.strip():
                                                st.error("Rejection reason comments are mandatory.")
                                            else:
                                                act_resp = APIClient.post(
                                                    f"/api/tasks/{t['id']}/action",
                                                    json={"action": "Return", "comments": s2_reject_comments}
                                                )
                                                if act_resp and act_resp.status_code == 200:
                                                    from frontend.styles import show_animated_checkmark
                                                    show_animated_checkmark("Task returned to Payroll!")
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    det = act_resp.json().get("detail", "Rejection failed.") if act_resp else "Backend unreachable."
                                                    st.error(det)
                                                    
                            elif status_val == "NM Finance Approved" and (role in ["GM/CFO", "Administrator"]):
                                st.markdown("##### ⚙️ Action Panel: Final Release or Reject (Stage 3)")
                                approve_col3, reject_col3 = st.columns(2)
                                
                                with approve_col3:
                                    with st.form(key=f"stage3_approve_form_{t['id']}", clear_on_submit=True):
                                        st.markdown("<h6 style='color:#10B981;'>Finalize & Complete Task</h6>", unsafe_allow_html=True)
                                        s3_comments = st.text_area("Final Release Remarks", placeholder="Final release release instructions...")
                                        s3_file = st.file_uploader("Upload Verification File (Mandatory)", type=["png", "jpg", "jpeg", "pdf", "xlsx", "xls"], key=f"s3_file_{t['id']}")
                                        s3_submit = st.form_submit_button("Approve & Close Task", use_container_width=True)
                                        
                                        if s3_submit:
                                            if not s3_comments.strip():
                                                st.error("Approval remarks are mandatory.")
                                            elif not s3_file:
                                                st.error("Verification file upload is mandatory.")
                                            else:
                                                file_id = upload_evidence(s3_file)
                                                act_resp = APIClient.post(
                                                    f"/api/tasks/{t['id']}/action",
                                                    json={"action": "Complete", "comments": s3_comments, "evidence_file_id": file_id}
                                                )
                                                if act_resp and act_resp.status_code == 200:
                                                    from frontend.styles import show_animated_checkmark
                                                    show_animated_checkmark("Stage 3 GM/CFO approved & closed!")
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    det = act_resp.json().get("detail", "Transaction failed.") if act_resp else "Backend unreachable."
                                                    st.error(det)
                                                    
                                with reject_col3:
                                    with st.form(key=f"stage3_reject_form_{t['id']}", clear_on_submit=True):
                                        st.markdown("<h6 style='color:#EF4444;'>Reject Task</h6>", unsafe_allow_html=True)
                                        target_stage = st.radio("Target Stage for Rejection", options=["NM Finance", "Payroll"], help="Choose which stage queue to return the task to.")
                                        s3_reject_comments = st.text_area("Rejection Comments", placeholder="Explain corrections required...")
                                        s3_reject_submit = st.form_submit_button("Reject Task", use_container_width=True)
                                        
                                        if s3_reject_submit:
                                            if not s3_reject_comments.strip():
                                                st.error("Rejection reason comments are mandatory.")
                                            else:
                                                mapped_target = "Manager" if target_stage == "Payroll" else target_stage
                                                act_resp = APIClient.post(
                                                    f"/api/tasks/{t['id']}/action",
                                                    json={"action": "Return", "comments": s3_reject_comments, "target_stage": mapped_target}
                                                )
                                                if act_resp and act_resp.status_code == 200:
                                                    from frontend.styles import show_animated_checkmark
                                                    show_animated_checkmark(f"Task returned to {target_stage}!")
                                                    time.sleep(1.5)
                                                    st.rerun()
                                                else:
                                                    det = act_resp.json().get("detail", "Rejection failed.") if act_resp else "Backend unreachable."
                                                    st.error(det)
                            else:
                                # User does not have access permissions for this stage
                                current_step_owner = "Manager / Payroll Team"
                                if status_val == "Payroll Completed":
                                    current_step_owner = "NM Finance"
                                elif status_val == "NM Finance Approved":
                                    current_step_owner = "GM/CFO"
                                st.warning(f"Waiting for action from **{current_step_owner}** role. You do not have permissions for this stage.")
                                
                            st.markdown("---")
                            st.markdown("##### 💬 Send WhatsApp Nudge Alert")
                            
                            owner_role = "Payroll Team"
                            if status_val == "Payroll Completed":
                                owner_role = "NM Finance"
                            elif status_val == "NM Finance Approved":
                                owner_role = "GM/CFO"
                                
                            default_msg = f"Task Alert: Task #{t['id']} '{t['task_title']}' is pending action from the {owner_role} stage. Please review and sign off."
                            
                            wa_col1, wa_col2 = st.columns([1, 2])
                            with wa_col1:
                                wa_phone = st.text_input(
                                    "Recipient Phone", 
                                    value="", 
                                    placeholder="e.g. +923001234567", 
                                    key=f"wa_phone_{t['id']}"
                                )
                            with wa_col2:
                                wa_msg = st.text_area("Custom Message", value=default_msg, key=f"wa_msg_{t['id']}")
                                
                            if st.button("Generate WhatsApp Nudge", key=f"wa_nudge_btn_{t['id']}", use_container_width=True):
                                if not wa_phone.strip():
                                    st.error("Recipient phone number is required.")
                                else:
                                    nudge_resp = APIClient.post(
                                        f"/api/tasks/{t['id']}/whatsapp-nudge",
                                        json={
                                            "recipient_phone": wa_phone.strip(),
                                            "message": wa_msg
                                        }
                                    )
                                    if nudge_resp and nudge_resp.status_code == 200:
                                        import urllib.parse
                                        clean_phone = wa_phone.replace('+', '').replace(' ', '').strip()
                                        encoded_msg = urllib.parse.quote(wa_msg)
                                        wa_web_url = f"https://wa.me/{clean_phone}?text={encoded_msg}"
                                        
                                        st.success("WhatsApp nudge logged in audit log!")
                                        st.markdown(
                                            f'<a href="{wa_web_url}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366; color:white; border:none; padding:12px; border-radius:8px; text-align:center; font-weight:bold; cursor:pointer; font-size:1rem; margin-top:10px;">👉 Click here to send message via WhatsApp Web</div></a>', 
                                            unsafe_allow_html=True
                                        )
                                    else:
                                        st.error("Failed to log WhatsApp nudge on the server.")
                                
                            # ADMINISTRATOR OPTIONS: EDIT & SOFT ARCHIVE
                            if role == "Administrator":
                                st.markdown("##### 🔒 Admin Controls")
                                edit_toggle = st.toggle("Edit Fields", key=f"edit_toggle_{t['id']}")
                                if edit_toggle:
                                    with st.form(key=f"edit_form_{t['id']}", clear_on_submit=True):
                                        e_title = st.text_input("Task Title", value=t["task_title"])
                                        e_desc = st.text_area("Task Description", value=t["task_description"] or "")
                                        e_submit = st.form_submit_button("Save Edits")
                                        if e_submit:
                                            edit_resp = APIClient.put(
                                                f"/api/tasks/{t['id']}",
                                                json={"task_title": e_title, "task_description": e_desc}
                                            )
                                            if edit_resp and edit_resp.status_code == 200:
                                                from frontend.styles import show_animated_checkmark
                                                show_animated_checkmark("Task details updated!")
                                                time.sleep(1.5)
                                                st.rerun()
                                            else:
                                                det = edit_resp.json().get("detail", "Edit failed.") if edit_resp else "Backend unreachable."
                                                st.error(det)
                                                
                                if st.button("Archive Task (Soft Delete)", key=f"archive_btn_{t['id']}", use_container_width=True):
                                    arc_resp = APIClient.post(f"/api/tasks/{t['id']}/archive")
                                    if arc_resp and arc_resp.status_code == 200:
                                        from frontend.styles import show_animated_checkmark
                                        show_animated_checkmark("Task archived successfully!")
                                        time.sleep(1.5)
                                        st.rerun()
                                    else:
                                        st.error("Failed to archive task.")
                                        
            # RIGHT: Completed Tasks Registry (Locked)
            with c_right:
                st.markdown("### ✅ Completed Registry (Read Only / Locked)")
                if not completed_tasks:
                    st.info("No tasks in completed status yet.")
                else:
                    for t in completed_tasks:
                        edited_label = " :green-background[Edited]" if t["is_edited_flag"] else ""
                        with st.expander(f"🔒 Task #{t['id']}: **{t['task_title']}**{edited_label}", expanded=False):
                            st.markdown(f"**Description:**\n{t['task_description'] or '*No description provided.*'}")
                            st.markdown(f"**Status:** `GM/CFO Approved` (Fully Completed)")
                            st.markdown(f"**Total Completion Duration:** `{format_duration(t['total_completion_time'])}`")
                            
                            # Fetch full timeline including digital signature certificate card stamps for completed tasks
                            st.markdown("#### 🏁 Verification & Approvals Audit History")
                            detail_resp = APIClient.get(f"/api/tasks/{t['id']}")
                            if detail_resp and detail_resp.status_code == 200:
                                t_details = detail_resp.json()
                                activities = t_details.get("activities", [])
                                
                                for act in activities:
                                    act_time = datetime.fromisoformat(act["timestamp"].replace("Z", "")).strftime('%Y-%m-%d %H:%M:%S')
                                    
                                    # Signature Box stamp
                                    sig_box = ""
                                    if act["digital_signature_hash"]:
                                        sig_box = f"""
                                        <div style='background: rgba(16, 185, 129, 0.08); border: 1px solid rgba(16, 185, 129, 0.25); border-radius: 6px; padding: 10px; margin-top: 8px;'>
                                            <span style='color: #10B981; font-weight: bold; font-size: 0.78rem;'>🛡️ SECURE DIGITAL APPROVAL STAMP</span><br>
                                            <span style='font-size:0.75rem; color:var(--text-color); opacity: 0.7;'>Certificate Hash:</span> <code style='font-size:0.72rem; color:var(--text-color); font-family: monospace; background: rgba(128,128,128,0.1); padding: 2px 4px; border-radius: 4px;'>{act['digital_signature_hash']}</code><br>
                                            <span style='font-size:0.75rem; color:var(--text-color); opacity: 0.7;'>Verified IP:</span> <code style='font-size:0.75rem; color:var(--text-color); font-family: monospace; background: rgba(128,128,128,0.1); padding: 2px 4px; border-radius: 4px;'>{act['ip_address'] or 'Localhost'}</code> | <span style='font-size:0.75rem; color:var(--text-color); opacity: 0.7;'>Device:</span> <span style='font-size:0.75rem; color:var(--text-color); opacity: 0.85;'>{act['device_info']}</span>
                                        </div>
                                        """
                                        
                                    st.markdown(
                                        f"""
                                        <div style='border-left: 3px solid #10B981; padding-left: 12px; margin-bottom: 12px;'>
                                            <div style='font-weight: 600; font-size: 0.9rem; color: #10B981;'>{act['action']}</div>
                                            <div style='font-size: 0.8rem; color: var(--text-color); opacity: 0.7;'>
                                                By <b>{act['username']}</b> ({act['user_role']}) on {act_time}
                                            </div>
                                            <div style='font-size: 0.85rem; color: var(--text-color); opacity: 0.85; margin-top: 4px; font-style: italic;'>
                                                Remarks: "{act['comments']}"
                                            </div>
                                            {sig_box}
                                        </div>
                                        """,
                                        unsafe_allow_html=True
                                    )
                                    
                            if t["payroll_evidence_file_id"]:
                                st.markdown("##### 📁 Evidence Screenshot Proof")
                                st.markdown(f"[📥 Download Evidence Screenshot]({BACKEND_URL}/api/files/download/{t['payroll_evidence_file_id']})")
                                st.image(f"{BACKEND_URL}/api/files/download/{t['payroll_evidence_file_id']}", caption="Evidence Screenshot Preview", width=300)
                                
    # Tab 2: Create Task
    with tab_create:
        st.markdown("### ➕ Add Compliance Task to Pipeline")
        with st.form("create_task_form", clear_on_submit=True):
            new_title = st.text_input("Task Title *")
            new_description = st.text_area("Task Description / Instructions")
            sla_days = st.number_input("SLA Completion Days Limit", min_value=1, max_value=90, value=7)
            submit = st.form_submit_button("Insert Task into Workflow")
            
            if submit:
                if not new_title.strip():
                    st.error("Task Title is mandatory.")
                else:
                    resp = APIClient.post(
                        "/api/tasks",
                        json={
                            "task_title": new_title.strip(),
                            "task_description": new_description.strip(),
                            "category": st.session_state["selected_category"],
                            "sla_days": int(sla_days)
                        }
                    )
                    if resp and resp.status_code == 200:
                        from frontend.styles import show_animated_checkmark
                        show_animated_checkmark("Task registered successfully!")
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        detail = resp.json().get("detail", "Creation failed.") if resp else "Backend unreachable."
                        st.error(detail)
                        
    # Tab 3: Bulk Import (Only if tab_import is defined)
    if tab_import is not None:
        with tab_import:
            st.markdown("### 📥 Bulk Excel Import - Recurring Master Templates")
            st.write("Upload an Excel worksheet populated with recurring task compliance requirements to bulk import them as templates.")
            
            # Serve download template file
            csv_template = "Task Name,Category,Frequency,Description,Responsible Role,Reminder Days,Start Date,End Date,Priority\n" \
                           "Weekly payroll run check,Payroll,Weekly,Verify payroll sheets against banks,Payroll Team,1,2026-06-10,,Normal\n" \
                           "Petty Cash Balance Count,Petty Cash,Daily,Count factory safe petty cash reserves,Payroll Team,1,2026-06-10,,High\n" \
                           "Quarterly GST Return,Fund Accounting,Quarterly,Compile ledgers and file GST returns,NM Finance,3,2026-06-10,,Normal\n"
                           
            st.download_button(
                label="📥 Download Template Import Sample (CSV)",
                data=csv_template,
                file_name="recurring_task_template_import_sample.csv",
                mime="text/csv"
            )
            
            st.markdown("---")
            
            uploaded_excel = st.file_uploader("Upload Excel Template File (.xlsx, .xls)", type=["xlsx", "xls"])
            if uploaded_excel:
                if st.button("Execute Bulk Import", use_container_width=True):
                    try:
                        files_payload = {"file": (uploaded_excel.name, uploaded_excel.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
                        with st.spinner("Processing templates and importing..."):
                            imp_resp = APIClient.post("/api/import/recurring", auth_required=True, files=files_payload)
                            
                            if imp_resp and imp_resp.status_code == 200:
                                result_data = imp_resp.json()
                                if result_data['failure_count'] > 0:
                                    st.success(f"Successfully imported **{result_data['success_count']}** templates!")
                                    st.warning(f"Failed to import **{result_data['failure_count']}** templates due to format/validation errors.")
                                    
                                    # Render errors table
                                    errors_table = []
                                    for err in result_data['errors']:
                                        errors_table.append({
                                            "Excel Row": err["row"],
                                            "Validation Failures": ", ".join(err["errors"])
                                        })
                                    st.table(errors_table)
                                else:
                                    from frontend.styles import show_animated_checkmark
                                    show_animated_checkmark(f"All {result_data['success_count']} templates imported successfully!")
                                    time.sleep(1.5)
                                    st.rerun()
                            else:
                                detail = imp_resp.json().get("detail", "Excel validation failed.") if imp_resp else "Backend connection error."
                                st.error(detail)
                    except Exception as e:
                        st.error(f"Error during import process execution: {e}")
