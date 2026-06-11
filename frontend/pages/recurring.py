import streamlit as st
import time
import pandas as pd
from datetime import datetime
from frontend.api_client import APIClient

def render_page():
    st.title("⚙️ Recurring Task Master")
    st.write("Configure schedules for automatic creation of compliance and payroll workflows.")
    st.markdown("---")
    
    # Check authorization (only Administrator, GM/CFO, NM Finance should manage templates)
    role = st.session_state["user_role"]
    if role not in ["Administrator", "GM/CFO", "NM Finance"]:
        st.warning("You only have read-only view access to recurring task configurations.")
        
    # Fetch recurring templates
    temp_resp = APIClient.get("/api/recurring")
    if not temp_resp or temp_resp.status_code != 200:
        st.error("Failed to load recurring task templates.")
        return
        
    templates = temp_resp.json()
    
    # Fetch users directory
    users_resp = APIClient.get("/api/auth/users")
    if not users_resp or users_resp.status_code != 200:
        st.error("Failed to load user directory.")
        return
    users = users_resp.json()
    user_options = {u["username"]: u["id"] for u in users}
    
    # Tabs
    tab_list, tab_create = st.tabs(["📋 Scheduled Templates", "➕ Add Schedule Template"])
    
    # Tab 1: Scheduled Templates List
    with tab_list:
        if not templates:
            st.info("No recurring templates are configured. Click the 'Add Schedule Template' tab to create one!")
        else:
            df = pd.DataFrame(templates)
            
            # Format display df
            display_df = df.copy()
            display_df["status"] = display_df["is_active"].map({True: "🟢 Active", False: "🔴 Inactive"})
            display_df = display_df[[
                "id", "task_name", "department", "frequency", "responsible_person", "status", "last_generated_at"
            ]]
            display_df.columns = ["ID", "Task Name", "Module/Dept", "Frequency", "Responsible Person", "Status", "Last Auto Run"]
            
            st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Management actions (If authorized)
            if role in ["Administrator", "GM/CFO", "NM Finance"]:
                st.markdown("#### Manage Schedule Templates")
                col_sel, col_action = st.columns([1, 2])
                with col_sel:
                    selected_id = st.selectbox("Select Template ID to Manage", options=[t["id"] for t in templates])
                with col_action:
                    # Find template
                    temp = next(t for t in templates if t["id"] == selected_id)
                    btn_lbl = "Deactivate Template" if temp["is_active"] else "Activate Template"
                    
                    if st.button(btn_lbl, use_container_width=True):
                        # Toggle state
                        resp = APIClient.put(
                            f"/api/recurring/{selected_id}",
                            json={
                                "task_name": temp["task_name"],
                                "department": temp["category"],
                                "description": temp["description"],
                                "responsible_person_id": temp["responsible_person_id"],
                                "start_date": temp["start_date"],
                                "frequency": temp["frequency"],
                                "reminder_days": temp["reminder_days"],
                                "is_active": not temp["is_active"]
                            }
                        )
                        if resp and resp.status_code == 200:
                            st.success("Template state toggled successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to update template.")

                # Edit Template form below the selection controls
                st.markdown("---")
                st.markdown(f"### ✏️ Edit Template ID: {selected_id}")
                
                default_user = temp.get("responsible_person")
                user_list = list(user_options.keys())
                try:
                    user_idx = user_list.index(default_user)
                except ValueError:
                    user_idx = 0
                    
                dept_options = ["Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules"]
                current_dept = temp.get("category") or temp.get("department")
                if current_dept not in dept_options:
                    dept_options.append(current_dept)
                try:
                    dept_idx = dept_options.index(current_dept)
                except ValueError:
                    dept_idx = 0
                    
                try:
                    start_date_parsed = datetime.fromisoformat(temp["start_date"].replace("Z", "")).date()
                except Exception:
                    start_date_parsed = datetime.today()
                    
                freq_options = ["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Every 2 Years"]
                current_freq = temp.get("frequency")
                if current_freq not in freq_options:
                    freq_options.append(current_freq)
                try:
                    freq_idx = freq_options.index(current_freq)
                except ValueError:
                    freq_idx = 0
                    
                with st.form(f"edit_recurring_form_{selected_id}", clear_on_submit=False):
                    edit_name = st.text_input("Task Name *", value=temp["task_name"])
                    edit_dept = st.selectbox(
                        "Target Pipeline Module *", 
                        options=dept_options,
                        index=dept_idx
                    )
                    edit_desc = st.text_area("Detailed Guidelines & Steps", value=temp["description"] or "")
                    edit_resp_user = st.selectbox("Responsible Person Signature *", options=user_list, index=user_idx)
                    edit_start_date = st.date_input("Start Schedule Date", value=start_date_parsed)
                    edit_freq = st.selectbox(
                        "Frequency Interval *",
                        options=freq_options,
                        index=freq_idx
                    )
                    edit_reminder = st.number_input("Reminder Buffer (Days)", min_value=0, max_value=30, value=int(temp["reminder_days"]))
                    edit_is_active = st.checkbox("Is Active", value=temp["is_active"])
                    
                    edit_submit_btn = st.form_submit_button("Save Changes")
                    
                    if edit_submit_btn:
                        if not edit_name.strip():
                            st.error("Task Name is mandatory.")
                        else:
                            # Convert start_date to datetime ISO string
                            start_dt = datetime.combine(edit_start_date, datetime.min.time()).isoformat()
                            
                            resp = APIClient.put(
                                f"/api/recurring/{selected_id}",
                                json={
                                    "task_name": edit_name.strip(),
                                    "department": edit_dept,
                                    "description": edit_desc.strip(),
                                    "responsible_person_id": user_options[edit_resp_user],
                                    "start_date": start_dt,
                                    "frequency": edit_freq,
                                    "reminder_days": edit_reminder,
                                    "is_active": edit_is_active
                                }
                            )
                            if resp and resp.status_code == 200:
                                st.success("Recurring template updated successfully!")
                                time.sleep(1.0)
                                st.rerun()
                            else:
                                detail = resp.json().get("detail", "Error updating template.") if resp else "Backend unreachable."
                                st.error(detail)
                            
    # Tab 2: Create Template (Role-restricted)
    with tab_create:
        if role not in ["Administrator", "GM/CFO", "NM Finance"]:
            st.error("You are not authorized to create scheduling rules.")
        else:
            st.markdown("### Create New Compliance Routine Template")
            with st.form("create_recurring_form", clear_on_submit=True):
                t_name = st.text_input("Task Name *", placeholder="e.g. Monthly VAT Reconciliation")
                t_dept = st.selectbox(
                    "Target Pipeline Module *", 
                    options=["Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules"]
                )
                t_desc = st.text_area("Detailed Guidelines & Steps")
                t_resp_user = st.selectbox("Responsible Person Signature *", options=list(user_options.keys()))
                t_start_date = st.date_input("Start Schedule Date", value=datetime.today())
                t_freq = st.selectbox(
                    "Frequency Interval *",
                    options=["Daily", "Weekly", "Monthly", "Quarterly", "Half-Yearly", "Yearly", "Every 2 Years"]
                )
                t_reminder = st.number_input("Reminder Buffer (Days)", min_value=0, max_value=30, value=1)
                
                submit_btn = st.form_submit_button("Generate Master Schedule Rule")
                
                if submit_btn:
                    if not t_name.strip():
                        st.error("Task Name is mandatory.")
                    else:
                        # Convert start_date to datetime ISO string
                        start_dt = datetime.combine(t_start_date, datetime.min.time()).isoformat()
                        
                        resp = APIClient.post(
                            "/api/recurring",
                            json={
                                "task_name": t_name.strip(),
                                "department": t_dept,
                                "description": t_desc.strip(),
                                "responsible_person_id": user_options[t_resp_user],
                                "start_date": start_dt,
                                "frequency": t_freq,
                                "reminder_days": t_reminder,
                                "is_active": True
                            }
                        )
                        if resp and resp.status_code == 200:
                            from frontend.styles import show_animated_checkmark
                            show_animated_checkmark("Recurring Template Master created successfully!")
                            time.sleep(1.5)
                            st.rerun()
                        else:
                            detail = resp.json().get("detail", "Error creating template.") if resp else "Backend unreachable."
                            st.error(detail)
