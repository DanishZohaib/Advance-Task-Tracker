import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from frontend.api_client import APIClient

def render_page():
    st.title("🔒 Security & Audit Trail Journal")
    st.write("Browse, inspect, and export system-wide historical activity logs.")
    st.markdown("---")
    
    # Restrict to Administrator, Auditor, GM/CFO
    role = st.session_state["user_role"]
    if role not in ["Administrator", "Auditor", "GM/CFO"]:
        st.error("Access Denied. You do not have permissions to view audit trails.")
        return
        
    st.markdown("### 🔍 Filter activity journal")
    
    # Filters layout
    col1, col2, col3 = st.columns(3)
    
    with col1:
        username_filter = st.text_input("Operator Username")
        action_filter = st.selectbox(
            "Action Type",
            options=[
                "All", "Login", "Login Failed", "Logout", "User Registration", 
                "Task Creation", "Task Editing", "Workflow Actions", 
                "Evidence Upload", "Email Notifications", "Report Downloads"
            ]
        )
        
    with col2:
        start_date = st.date_input("Start Date", value=datetime.today() - timedelta(days=7))
        end_date = st.date_input("End Date", value=datetime.today() + timedelta(days=1))
        
    with col3:
        task_filter = st.text_input("Filter by Task ID")
        
    # Compile parameters
    params = {}
    if username_filter:
        params["username"] = username_filter
    if action_filter != "All":
        params["action_type"] = action_filter
    if task_filter:
        try:
            params["task_id"] = int(task_filter)
        except ValueError:
            st.error("Task ID must be an integer.")
            
    # Convert dates to ISO format
    start_dt = datetime.combine(start_date, datetime.min.time()).isoformat()
    end_dt = datetime.combine(end_date, datetime.max.time()).isoformat()
    params["start_date"] = start_dt
    params["end_date"] = end_dt
    
    # Query logs
    resp = APIClient.get("/api/audit", params=params)
    if not resp or resp.status_code != 200:
        st.error("Failed to retrieve audit trail logs.")
        return
        
    logs = resp.json()
    
    if not logs:
        st.info("No matching audit logs found.")
    else:
        df = pd.DataFrame(logs)
        
        # Structure for grid display
        display_df = df.copy()
        
        # Clean formatting
        display_df["timestamp"] = display_df["timestamp"].apply(
            lambda x: datetime.fromisoformat(x.replace("Z", "")).strftime('%Y-%m-%d %H:%M:%S')
        )
        
        # Select columns to display
        grid_df = display_df[[
            "id", "timestamp", "username", "action_type", "task_id", "details", "ip_address", "device_info"
        ]]
        grid_df.columns = ["Log ID", "Timestamp", "Operator User", "Action Group", "Task ID", "Operation Details", "IP Address", "Client Browser Details"]
        
        # Show log count
        st.markdown(f"**Found {len(logs)} activity records**")
        st.dataframe(grid_df, use_container_width=True, hide_index=True)
        
        # Detailed inspector drawer/expander for selected log ID
        st.markdown("#### 🔬 Detailed Change Inspector")
        sel_log_id = st.selectbox("Select Log ID to inspect old/new values:", options=df["id"].tolist())
        if sel_log_id:
            log_detail = next(l for l in logs if l["id"] == sel_log_id)
            d1, d2 = st.columns(2)
            with d1:
                st.markdown("**Old State values:**")
                st.info(log_detail["old_value"] or "*No previous values recorded (new record)*")
            with d2:
                st.markdown("**New State values:**")
                st.success(log_detail["new_value"] or "*No subsequent values recorded (deleted/action)*")
