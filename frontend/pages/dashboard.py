import streamlit as st
import plotly.express as px
from datetime import datetime
from frontend.api_client import APIClient
from backend.utils import format_duration

def render_page():
    st.markdown("<h1 style='color: #4F46E5;'>📊 Executive Dashboard</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.1rem; color: var(--text-color); opacity: 0.7;'>Real-time operational overview, category compliance metrics, and SLA timing analytics.</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    # Fetch tasks from backend
    resp = APIClient.get("/api/tasks")
    if not resp or resp.status_code != 200:
        st.warning("Unable to fetch metrics from the backend. Make sure the API service is active.")
        return
        
    tasks = resp.json()
    if not tasks:
        st.info("No tasks registered in the workspace yet. Navigate to 'Workflows & Tasks' to get started!")
        return
        
    # Basic Counts using pure Python
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t["status"] == "GM/CFO Approved"])
    pending_tasks = total_tasks - completed_tasks
    
    # SLA calculations
    critical_sla = len([t for t in tasks if t.get("sla_status") == "Critical"])
    overdue_sla = len([t for t in tasks if t.get("sla_status") == "Overdue"])
    due_soon_sla = len([t for t in tasks if t.get("sla_status") == "Due Soon"])
    
    # Due Today & Due This Week calculations
    due_today_count = 0
    due_this_week_count = 0
    now = datetime.utcnow()
    
    for t in tasks:
        if t["status"] != "GM/CFO Approved" and t.get("planned_due_date"):
            try:
                due_dt = datetime.fromisoformat(t["planned_due_date"].replace("Z", ""))
                days_diff = (due_dt.date() - now.date()).days
                if days_diff == 0:
                    due_today_count += 1
                    due_this_week_count += 1
                elif 0 < days_diff <= 7:
                    due_this_week_count += 1
            except ValueError:
                pass
                
    # Average completion speeds using pure Python
    s1_times = [t["payroll_processing_time"] for t in tasks if t.get("payroll_processing_time") is not None]
    s2_times = [t["nm_finance_processing_time"] for t in tasks if t.get("nm_finance_processing_time") is not None]
    s3_times = [t["gmcfo_processing_time"] for t in tasks if t.get("gmcfo_processing_time") is not None]
    total_times = [t["total_completion_time"] for t in tasks if t.get("total_completion_time") is not None]
    
    avg_s1 = sum(s1_times) / len(s1_times) if s1_times else None
    avg_s2 = sum(s2_times) / len(s2_times) if s2_times else None
    avg_s3 = sum(s3_times) / len(s3_times) if s3_times else None
    avg_total = sum(total_times) / len(total_times) if total_times else None
    
    # 1. Show Top Row KPI metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #4F46E5; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Total Pipeline Tasks</div>
                <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{total_tasks}</div>
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
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Pending Review</div>
                <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{pending_tasks}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col4:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 20px; border-radius: 8px; border-left: 5px solid #EF4444; box-shadow: 0 4px 6px rgba(0,0,0,0.05);'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem; font-weight: 500; text-transform: uppercase;'>Critical & Overdue SLA</div>
                <div style='color: var(--text-color); font-size: 2rem; font-weight: 700; margin-top: 5px;'>{critical_sla + overdue_sla}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # SLA Urgency Metrics Row
    st.markdown("### 🚨 SLA Urgency Status")
    uc1, uc2, uc3, uc4 = st.columns(4)
    with uc1:
        st.metric(label="⏰ Due Today", value=due_today_count)
    with uc2:
        st.metric(label="📅 Due This Week", value=due_this_week_count)
    with uc3:
        st.metric(label="⚡ Critical Overdue", value=critical_sla)
    with uc4:
        st.metric(label="⚠️ Due Soon (<= 2 Days)", value=due_soon_sla)

    st.markdown("---")
    
    # Category Completion Rates Dashboard
    st.markdown("### 📈 Category Completion Rates")
    
    categories = ["Payroll", "Fund Accounting", "Petty Cash", "Audit Schedules"]
    cat_columns = st.columns(4)
    
    for idx, cat in enumerate(categories):
        cat_tasks = [t for t in tasks if t["category"] == cat]
        total_cat = len(cat_tasks)
        completed_cat = len([t for t in cat_tasks if t["status"] == "GM/CFO Approved"])
        rate = (completed_cat / total_cat * 100) if total_cat > 0 else 0.0
        
        with cat_columns[idx]:
            # Custom gradient bar color based on completion rate
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
            "GM/CFO Approved": "#10B981"
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
            plot_bgcolor='rgba(0,0,0,0)'
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
            color_discrete_sequence=["#4F46E5", "#3B82F6", "#10B981", "#F59E0B"]
        )
        fig_cat.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_cat, use_container_width=True)
        
    st.markdown("---")
    
    # 3. Time Performance Section
    st.markdown("### ⏱️ SLA Process Timing Analysis")
    
    tc1, tc2, tc3, tc4 = st.columns(4)
    with tc1:
        st.markdown(
            f"""
            <div style='background: var(--secondary-background-color); padding: 15px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); text-align: center;'>
                <div style='color: var(--text-color); opacity: 0.7; font-size: 0.8rem;'>Avg Payroll Processing Time</div>
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
    
    # 4. User Productivity Ranking
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
            plot_bgcolor='rgba(0,0,0,0)'
        )
        st.plotly_chart(fig_prod, use_container_width=True)
    else:
        st.info("No approval actions recorded yet. Contributions will appear once workflow actions are completed.")
