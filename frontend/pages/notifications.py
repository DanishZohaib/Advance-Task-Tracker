import streamlit as st
import pandas as pd
from datetime import datetime
from frontend.api_client import APIClient

def render_page():
    st.title("🔔 Notification Center")
    st.write("Important system alerts, workflow action requests, and recurring schedule updates.")
    st.markdown("---")
    
    # Fetch notifications
    resp = APIClient.get("/api/notifications")
    if not resp or resp.status_code != 200:
        st.error("Failed to retrieve notifications.")
        return
        
    data = resp.json()
    notifications = data.get("notifications", [])
    unread_count = data.get("unread_count", 0)
    
    col_stat, col_btn = st.columns([2, 1])
    with col_stat:
        st.subheader(f"You have {unread_count} unread notifications")
    with col_btn:
        if unread_count > 0:
            if st.button("Mark All as Read", key="read_all_btn", use_container_width=True):
                read_resp = APIClient.post("/api/notifications/read-all")
                if read_resp and read_resp.status_code == 200:
                    st.success("All notifications cleared.")
                    st.rerun()
                    
    st.markdown("---")
    
    if not notifications:
        st.info("No notifications to display.")
    else:
        for n in notifications:
            # Format time
            notif_time = datetime.fromisoformat(n["created_at"].replace("Z", "")).strftime('%Y-%m-%d %H:%M:%S')
            
            # Badge styles depending on read status
            read_badge = "🟢 New" if not n["is_read"] else "⚪ Read"
            box_style = "border-left: 4px solid #4F46E5; background-color: rgba(79, 70, 229, 0.05);" if not n["is_read"] else "border-left: 4px solid #475569; background-color: rgba(255, 255, 255, 0.02);"
            
            st.markdown(
                f"""
                <div style='border: 1px solid #334155; padding: 15px; border-radius: 8px; margin-bottom: 12px; {box_style}'>
                    <div style='display: flex; justify-content: space-between;'>
                        <b>{n['title']}</b>
                        <span style='font-size: 0.8rem; color: #94A3B8;'>{read_badge} | {notif_time}</span>
                    </div>
                    <div style='font-size: 0.9rem; color: #F1F5F9; margin-top: 8px;'>{n['message']}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            if not n["is_read"]:
                # Individual mark read trigger
                if st.button("Clear Alert", key=f"read_notif_{n['id']}"):
                    APIClient.post(f"/api/notifications/{n['id']}/read")
                    st.rerun()
