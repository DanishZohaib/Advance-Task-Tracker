import time
from datetime import datetime
import streamlit as st
from frontend.styles import inject_custom_css
from frontend.api_client import APIClient, BACKEND_URL

# Session Timeout Inactivity Threshold: 15 minutes
SESSION_TIMEOUT_SECONDS = 900

# Initialize Session State
if "access_token" not in st.session_state:
    st.session_state["access_token"] = None
if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = None
if "username" not in st.session_state:
    st.session_state["username"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = None
if "last_activity" not in st.session_state:
    st.session_state["last_activity"] = None

# Configure page metadata
st.set_page_config(
    page_title="TaskTracker Pro Enterprise Edition",
    page_icon="📋",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply customized corporate style sheets
inject_custom_css()

# Security: Inactivity Session Auto-Logout Check
if st.session_state["access_token"] is not None:
    now = time.time()
    last_act = st.session_state.get("last_activity")
    if last_act and (now - last_act > SESSION_TIMEOUT_SECONDS):
        # Session expired
        st.session_state["access_token"] = None
        st.session_state["refresh_token"] = None
        st.session_state["user_role"] = None
        st.session_state["username"] = None
        st.session_state["last_activity"] = None
        st.error("You have been automatically logged out due to inactivity.", icon="🔒")
        st.button("Re-login", key="re_login_btn")
        st.stop()
    else:
        st.session_state["last_activity"] = now

def run_login():
    st.markdown("<h1 style='text-align: center; color: #4F46E5;'>📋 TaskTracker Pro</h1>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: var(--text-color); opacity: 0.7; font-weight: 400;'>Enterprise Grade Task Tracking & Audit Monitoring</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown(
            """
            <div style='background: rgba(79, 70, 229, 0.05); padding: 25px; border-radius: 12px; border: 1px solid rgba(79, 70, 229, 0.1);'>
                <h3 style='margin-top:0; color: #4F46E5;'>🔑 User Authentication</h3>
                <p style='color: var(--text-color); opacity: 0.7; font-size: 0.9rem;'>Access the system workspace using your corporate credentials.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        login_user = st.text_input("Username", key="login_username_input")
        login_pass = st.text_input("Password", type="password", key="login_password_input")
        
        if st.button("Authenticate", key="login_submit_btn", use_container_width=True):
            if login_user and login_pass:
                # Call backend auth API (which uses FastAPI OAuth2 Form style)
                resp = APIClient.post(
                    "/api/auth/login",
                    auth_required=False,
                    data={"username": login_user, "password": login_pass}
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.session_state["access_token"] = data["access_token"]
                    st.session_state["refresh_token"] = data["refresh_token"]
                    st.session_state["username"] = data["username"]
                    st.session_state["user_role"] = data["role"]
                    st.session_state["last_activity"] = time.time()
                    st.success("Successfully logged in!")
                    st.rerun()
                else:
                    detail = resp.json().get("detail", "Authentication failed.") if resp else "Failed to connect to backend."
                    st.error(detail)
            else:
                st.error("Please provide both Username and Password.")
                
    with col2:
        st.markdown(
            """
            <div style='background: rgba(16, 185, 129, 0.05); padding: 25px; border-radius: 12px; border: 1px solid rgba(16, 185, 129, 0.1);'>
                <h3 style='margin-top:0; color: #10B981;'>📝 Register Profile</h3>
                <p style='color: var(--text-color); opacity: 0.7; font-size: 0.9rem;'>Create a new security identity. Hashed usingbcrypt.</p>
            </div>
            """,
            unsafe_allow_html=True
        )
        reg_user = st.text_input("Username", key="reg_username_input").strip()
        reg_pass = st.text_input("Password", type="password", key="reg_password_input", help="Must be >= 8 chars, 1 Upper, 1 Lower, 1 Digit, 1 Special Char")
        reg_role = st.selectbox(
            "Access Role",
            options=["Payroll Team", "NM Finance", "GM/CFO", "Auditor", "Administrator"]
        )
        
        if st.button("Create Account & Access", key="reg_submit_btn", use_container_width=True):
            if reg_user and reg_pass:
                resp = APIClient.post(
                    "/api/auth/register",
                    auth_required=False,
                    json={
                        "username": reg_user,
                        "password": reg_pass,
                        "role": reg_role
                    }
                )
                if resp and resp.status_code == 200:
                    data = resp.json()
                    st.session_state["access_token"] = data["access_token"]
                    st.session_state["refresh_token"] = data["refresh_token"]
                    st.session_state["username"] = data["username"]
                    st.session_state["user_role"] = data["role"]
                    st.session_state["last_activity"] = time.time()
                    st.success("Registered profile successfully!")
                    st.rerun()
                else:
                    detail = resp.json().get("detail", "Registration failed.") if resp else "Failed to connect to backend."
                    st.error(detail)
            else:
                st.error("Please enter both Username and Password.")

    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div style='text-align: center; color: var(--text-color); opacity: 0.6; font-size: 0.85rem; border-top: 1px solid rgba(128, 128, 128, 0.2); padding-top: 20px;'>
            Enterprise Grade Compliance Platform | Server API: <code>{BACKEND_URL}</code>
        </div>
        """,
        unsafe_allow_html=True
    )

def handle_logout():
    # Attempt api logout to write audit log
    APIClient.post("/api/auth/logout", auth_required=True)
    st.session_state["access_token"] = None
    st.session_state["refresh_token"] = None
    st.session_state["username"] = None
    st.session_state["user_role"] = None
    st.session_state["last_activity"] = None
    st.rerun()

def run_main_app():
    # Retrieve notification badge count
    unread_count = 0
    notif_resp = APIClient.get("/api/notifications?unread_only=true")
    if notif_resp and notif_resp.status_code == 200:
        unread_count = notif_resp.json().get("unread_count", 0)
        
    badge = f" ({unread_count})" if unread_count > 0 else ""
    
    # Navigation mapping
    pages = {
        "📊 Executive Dashboard": "dashboard",
        "📝 Workflows & Tasks": "tasks",
        "📖 Operator Manual": "manual",
        "⚙️ Recurring Task Master": "recurring",
        "📁 Advanced Reports": "reports",
        "🔒 Security & Audit Trail": "audit",
        f"🔔 Notification Alerts{badge}": "notifications"
    }
    if st.session_state["user_role"] in ["Administrator"]:
        pages["⚙️ SMTP Admin Settings"] = "settings"
    
    # Navigation workspaces menu at the top
    selected_page = st.sidebar.radio("Workspaces", list(pages.keys()))
    page_key = pages[selected_page]
    
    st.sidebar.markdown("---")
    
    # User session banner and logout button under the workspaces menu
    st.sidebar.markdown(
        f"""
        <div class='sidebar-user'>
            👤 <b>Logged in:</b> {st.session_state['username']}<br>
            🛡️ <b>Role:</b> {st.session_state['user_role']}
        </div>
        """,
        unsafe_allow_html=True
    )
    
    if st.sidebar.button("Logout Profile", key="logout_sidebar_btn", use_container_width=True):
        handle_logout()
        
    # Spacer and branding moved to the bottom of the menu
    st.sidebar.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)
    st.sidebar.markdown("---")
    st.sidebar.markdown("<h3 style='margin-bottom:0; font-size: 1.2rem; color:#4F46E5;'>📋 TaskTracker Pro</h3>", unsafe_allow_html=True)
    st.sidebar.markdown("<code style='color:var(--text-color); opacity: 0.6; font-size: 0.8rem;'>Enterprise Edition v1.0</code>", unsafe_allow_html=True)
        
    # Dynamically load the page
    if page_key == "dashboard":
        from frontend.pages.dashboard import render_page
        render_page()
    elif page_key == "tasks":
        from frontend.pages.tasks import render_page
        render_page()
    elif page_key == "manual":
        from frontend.pages.manual import render_page
        render_page()
    elif page_key == "recurring":
        from frontend.pages.recurring import render_page
        render_page()
    elif page_key == "reports":
        from frontend.pages.reports import render_page
        render_page()
    elif page_key == "audit":
        from frontend.pages.audit import render_page
        render_page()
    elif page_key == "notifications":
        from frontend.pages.notifications import render_page
        render_page()
    elif page_key == "settings":
        from frontend.pages.settings import render_page
        render_page()

# Direct application traffic
if st.session_state["access_token"] is None:
    run_login()
else:
    run_main_app()
