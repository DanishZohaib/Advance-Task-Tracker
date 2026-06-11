import streamlit as st
import plotly.express as px
from datetime import datetime
from frontend.api_client import APIClient
from backend.utils import format_duration

def render_page():
    role = st.session_state.get("user_role", "Manager")
    username = st.session_state.get("username", "User")
    
    st.markdown(f"<h1 style='color: #4F46E5;'>📊 {role} Dashboard</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size: 1.1rem; color: var(--text-color); opacity: 0.7;'>Welcome back, {username}! Real-time operational overview tailored to your organizational role.</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Fetch tasks from backend
    resp = APIClient.get("/api/tasks")
    if not resp or resp.status_code != 200:
        st.warning("Unable to fetch metrics from the backend. Make sure the API service is active.")
        return
        
    all_tasks = resp.json()
    if not all_tasks:
        st.info("No tasks registered in the workspace yet. Navigate to 'Workflows & Tasks' to get started!")
        return

    # Filter tasks based on role category scope if applicable
    role_category_map = {
        "Assistant Manager": "Fund Accounting",
        "Executive Payroll": "Audit Schedules",
        "Executive Petty Cash": "Petty Cash",
        "Junior Support Staff": "General Support Activities"
    }

    category_scope = role_category_map.get(role)
    if category_scope:
        tasks = [t for t in all_tasks if t["category"] == category_scope]
        st.info(f"Viewing tasks scoped to your category: **{category_scope}**.")
    else:
        tasks = all_tasks

    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t["status"] == "GM/CFO Approved"])
    pending_tasks = total_tasks - completed_tasks
    
    # Category task counts
    s1_queue = len([t for t in tasks if t["status"] in ["Pending", "Returned to Initiator"]])
    s2_queue = len([t for t in tasks if t["status"] == "Payroll Completed"])
    s3_queue = len([t for t in tasks if t["status"] == "NM Finance Approved"])
    rejected_count = len([t for t in tasks if t["status"] == "Rejected"])

    # Overdue calculations
    critical_sla = len([t for t in tasks if t.get("sla_status") == "Critical"])
    overdue_sla = len([t for t in tasks if t.get("sla_status") == "Overdue"])
    due_soon_sla = len([t for t in tasks if t.get("sla_status") == "Due Soon"])

    # Show Top Row KPI metrics dynamically based on Role
    col1, col2, col3, col4 = st.columns(4)

    if role in ["Manager", "Payroll Team", "Administrator", "Auditor"]:
        # Manager / Admin Overview
        with col1:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Manager Queue (Pending)</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{s1_queue}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Fully Completed</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{completed_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #F59E0B; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Total Pending Pipeline</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{pending_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #EF4444; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Overdue & Critical SLA</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{critical_sla + overdue_sla}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    elif role == "NM Finance":
        # NM Finance Overview
        with col1:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #3B82F6; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>NM Finance Queue</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{s2_queue}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>NM Approved Tasks</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{len([t for t in tasks if t.get("nm_finance_approved_by") is not None])}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #F59E0B; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Rejected / Returned</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{rejected_count}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #EF4444; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>SLA Overdue</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{overdue_sla}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    elif role == "GM/CFO":
        # GM/CFO Overview
        with col1:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #8B5CF6; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>GM/CFO Queue</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{s3_queue}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>GM Approved/Closed</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{completed_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #F59E0B; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Returned/Rejected</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{rejected_count}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #EF4444; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Critical Overdue</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{critical_sla}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    else:
        # Operational Category Dashboard (AM, Executive, Junior Support Staff)
        with col1:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Total Category Tasks</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{total_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #10B981; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Completed Tasks</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{completed_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #F59E0B; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Pending Approvals</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{pending_tasks}</div>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                f"""
                <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #EF4444; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                    <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Returned / Rejected</div>
                    <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{rejected_count}</div>
                </div>
                """,
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)
    
    # SLA Urgency Metrics Row
    st.markdown("### 🚨 SLA Urgency Status")
    uc1, uc2, uc3, uc4 = st.columns(4)
    with uc1:
        st.metric(label="⏰ Due Today", value=len([t for t in tasks if t["status"] != "GM/CFO Approved" and t.get("sla_status") == "Due Today"]))
    with uc2:
        st.metric(label="📅 Due Soon", value=due_soon_sla)
    with uc3:
        st.metric(label="⚡ Critical Overdue", value=critical_sla)
    with uc4:
        st.metric(label="⚠️ Overdue SLA", value=overdue_sla)

    st.markdown("---")
    
    # Category Completion Rates Dashboard (Only show categories relevant or all if Manager/Admin)
    if not category_scope:
        st.markdown("### 📈 Category Completion Rates")
        categories = ["Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules", "General Support Activities"]
        cat_columns = st.columns(5)
        
        for idx, cat in enumerate(categories):
            cat_tasks = [t for t in tasks if t["category"] == cat]
            total_cat = len(cat_tasks)
            completed_cat = len([t for t in cat_tasks if t["status"] == "GM/CFO Approved"])
            rate = (completed_cat / total_cat * 100) if total_cat > 0 else 0.0
            
            with cat_columns[idx]:
                if rate >= 75:
                    bar_color = "linear-gradient(90deg, #10B981, #059669)"
                elif rate >= 40:
                    bar_color = "linear-gradient(90deg, #F59E0B, #D97706)"
                else:
                    bar_color = "linear-gradient(90deg, #EF4444, #DC2626)"
                    
                st.markdown(
                    f"""
                    <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); height: 140px;'>
                        <div style='color: var(--text-color); font-size: 0.95rem; font-weight: bold;'>{cat}</div>
                        <div style='display: flex; justify-content: space-between; margin-top: 10px;'>
                            <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>{completed_cat}/{total_cat} Tasks</span>
                            <span style='color: var(--text-color); font-size: 1.1rem; font-weight: bold;'>{rate:.1f}%</span>
                        </div>
                        <div style='background-color: rgba(128,128,128,0.15); border-radius: 10px; height: 10px; width: 100%; margin-top: 12px; overflow: hidden;'>
                            <div style='background: {bar_color}; height: 100%; width: {rate}%; border-radius: 10px;'></div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
        st.markdown("---")
        
    # Charts Section
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown("#### Task Status Distribution")
        status_map = {}
        for t in tasks:
            status_map[t["status"]] = status_map.get(t["status"], 0) + 1
        statuses = list(status_map.keys())
        counts = list(status_map.values())
        
        color_map = {
            "Pending": "#4F46E5",
            "Payroll Completed": "#8B5CF6",
            "NM Finance Approved": "#F59E0B",
            "GM/CFO Approved": "#10B981",
            "Returned to Initiator": "#3B82F6",
            "Rejected": "#EF4444"
        }
        fig_status = px.pie(
            names=statuses,
            values=counts,
            color=statuses,
            color_discrete_map=color_map,
            hole=0.4
        )
        fig_status.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="gray"
        )
        st.plotly_chart(fig_status, use_container_width=True)
        
    with chart_col2:
        st.markdown("#### Category Distribution & Volume")
        category_map = {}
        for t in tasks:
            category_map[t["category"]] = category_map.get(t["category"], 0) + 1
        categories_list = list(category_map.keys())
        category_counts = list(category_map.values())
        
        fig_cat = px.bar(
            x=categories_list,
            y=category_counts,
            labels={"x": "Category", "y": "Task Count"},
            color=categories_list,
            color_discrete_sequence=["#4F46E5", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"]
        )
        fig_cat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="gray"
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
    st.markdown("---")
    
    # Time Performance Section
    st.markdown("### ⏱️ SLA Process Timing Analysis")
    
    s1_times = [t["payroll_processing_time"] for t in tasks if t.get("payroll_processing_time") is not None]
    s2_times = [t["nm_finance_processing_time"] for t in tasks if t.get("nm_finance_processing_time") is not None]
    s3_times = [t["gmcfo_processing_time"] for t in tasks if t.get("gmcfo_processing_time") is not None]
    total_times = [t["total_completion_time"] for t in tasks if t.get("total_completion_time") is not None]
    
    avg_s1 = sum(s1_times) / len(s1_times) if s1_times else None
    avg_s2 = sum(s2_times) / len(s2_times) if s2_times else None
    avg_s3 = sum(s3_times) / len(s3_times) if s3_times else None
    avg_total = sum(total_times) / len(total_times) if total_times else None

    tc1, tc2, tc3, tc4 = st.columns(4)
    with tc1:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.8rem;'>Avg Manager Processing Time</div>
                <div style='color: #3B82F6; font-size: 1.25rem; font-weight: 700; margin-top: 5px;'>{format_duration(avg_s1)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with tc2:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.8rem;'>Avg NM Finance Review Time</div>
                <div style='color: #8B5CF6; font-size: 1.25rem; font-weight: 700; margin-top: 5px;'>{format_duration(avg_s2)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with tc3:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.8rem;'>Avg GM/CFO Approval Time</div>
                <div style='color: #F59E0B; font-size: 1.25rem; font-weight: 700; margin-top: 5px;'>{format_duration(avg_s3)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with tc4:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.8rem;'>Avg Total Completion Time</div>
                <div style='color: #10B981; font-size: 1.25rem; font-weight: 700; margin-top: 5px;'>{format_duration(avg_total)}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # User Productivity Ranking
    st.markdown("#### User Workflow Contributions (Productivity)", unsafe_allow_html=True)
    
    contributions = {}
    for t in tasks:
        p_c = t.get("payroll_completed_by")
        if p_c:
            contributions[p_c] = contributions.get(p_c, 0) + 1
        n_c = t.get("nm_finance_approved_by")
        if n_c:
            contributions[n_c] = contributions.get(n_c, 0) + 1
        g_c = t.get("gmcfo_approved_by")
        if g_c:
            contributions[g_c] = contributions.get(g_c, 0) + 1
            
    if contributions:
        sorted_contrib = sorted(contributions.items(), key=lambda x: x[1], reverse=True)
        usernames = [x[0] for x in sorted_contrib]
        approved_counts = [x[1] for x in sorted_contrib]
        
        fig_prod = px.bar(
            x=usernames,
            y=approved_counts,
            labels={"x": "Username", "y": "Approved Steps count"},
            color=approved_counts,
            color_continuous_scale="Viridis"
        )
        fig_prod.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font_color="gray"
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("No approval actions recorded yet. Contributions will appear once workflow actions are completed.")
