import streamlit as st

def inject_custom_css():
    """
    Injects custom styles to render an Enterprise Grade Finance ERP interface
    that seamlessly supports both Light and Dark Streamlit themes.
    """
    css = """
    <style>
    /* Main Layout Customizations adapting to light/dark themes */
    .stApp {
        background-color: var(--background-color);
        color: var(--text-color);
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: var(--secondary-background-color) !important;
        border-right: 1px solid rgba(128, 128, 128, 0.15);
    }
    
    /* Primary Typography Customization */
    h1, h2, h3, h4, h5, h6 {
        color: var(--text-color) !important;
        font-family: 'Outfit', 'Inter', sans-serif !important;
    }
    
    /* Glassmorphism KPI Container */
    .kpi-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-left: 4px solid #4F46E5; /* Indigo Accent */
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
        margin-bottom: 15px;
        transition: transform 0.2s ease-in-out;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.12);
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: var(--text-color);
        opacity: 0.7;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: var(--text-color);
        margin-top: 5px;
    }
    
    /* Module Card styling */
    .module-card {
        background: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.15);
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .module-card:hover {
        border-color: #4F46E5;
        background: rgba(79, 70, 229, 0.08);
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.15);
        transform: translateY(-3px);
    }
    .module-icon {
        font-size: 2.5rem;
        margin-bottom: 12px;
    }
    .module-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: var(--text-color);
        margin-bottom: 8px;
    }
    .module-desc {
        font-size: 0.85rem;
        color: var(--text-color);
        opacity: 0.7;
    }
    
    /* Task Timeline Info */
    .workflow-timeline {
        border-left: 2px solid rgba(128, 128, 128, 0.2);
        margin-left: 10px;
        padding-left: 20px;
        position: relative;
    }
    .timeline-node {
        margin-bottom: 20px;
    }
    .timeline-node::before {
        content: '';
        position: absolute;
        left: -6px;
        top: 4px;
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background-color: #4F46E5;
    }
    .timeline-node.completed::before {
        background-color: #10B981;
    }
    .timeline-title {
        font-weight: 600;
        color: var(--text-color);
    }
    .timeline-time {
        font-size: 0.75rem;
        color: var(--text-color);
        opacity: 0.7;
    }
    
    /* Corporate Styled Alert Bar */
    .compliance-alert {
        background-color: rgba(239, 68, 68, 0.08);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #EF4444;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 0.9rem;
    }
    
    /* Custom buttons */
    div.stButton > button {
        background-color: #4F46E5 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 8px 16px !important;
        font-weight: 600 !important;
        transition: background-color 0.2s !important;
    }
    div.stButton > button:hover {
        background-color: #4338CA !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.3) !important;
    }
    
    /* Sidebar user detail banner */
    .sidebar-user {
        background-color: rgba(128,128,128,0.05);
        border: 1px solid rgba(128,128,128,0.1);
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

def show_animated_checkmark(message="Action completed successfully!"):
    """
    Displays a smooth CSS-animated checkmark confirmation.
    """
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 20px 0; animation: fadeIn 0.5s ease-in-out;">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52" style="width: 56px; height: 56px; border-radius: 50%; display: block; stroke-width: 2; stroke: #fff; stroke-miterlimit: 10; box-shadow: inset 0px 0px 0px #10B981; animation: fill .4s ease-in-out .4s forwards, scale .3s ease-in-out .9s forwards;">
                <circle cx="26" cy="26" r="25" fill="none" style="stroke-dasharray: 166; stroke-dashoffset: 166; stroke-width: 2; stroke-miterlimit: 10; stroke: #10B981; fill: none; animation: stroke 0.6s cubic-bezier(0.65, 0, 0.45, 1) forwards;"/>
                <path fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8" style="transform-origin: 50% 50%; stroke-dasharray: 48; stroke-dashoffset: 48; animation: stroke 0.3s cubic-bezier(0.65, 0, 0.45, 1) 0.8s forwards;"/>
            </svg>
            <div style="margin-top: 15px; color: #10B981; font-weight: bold; font-size: 1.1rem; text-align: center;">{message}</div>
        </div>
        <style>
        @keyframes stroke {{
            100% {{
                stroke-dashoffset: 0;
            }}
        }}
        @keyframes scale {{
            0%, 100% {{
                transform: none;
            }}
            50% {{
                transform: scale3d(1.1, 1.1, 1);
            }}
        }}
        @keyframes fill {{
            100% {{
                box-shadow: inset 0px 0px 0px 30px #10B981;
            }}
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def show_animated_bell(task_list):
    """
    Displays a large, visual, CSS-animated bell component highlighting tasks
    that are due today and require user action.
    """
    tasks_html = ""
    for t in task_list:
        tasks_html += f"""
        <div style="background: rgba(255, 255, 255, 0.05); padding: 12px 18px; border-radius: 8px; margin: 10px 0; border-left: 5px solid #EF4444; text-align: left; width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span style="font-weight: bold; font-size: 1rem; color: var(--text-color);">Task #{t['id']}: {t['task_title']}</span>
                <span style="background: #EF4444; color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.75rem; font-weight: bold; text-transform: uppercase;">Due Today</span>
            </div>
            <div style="font-size: 0.85rem; color: var(--text-color); opacity: 0.75; margin-top: 5px;">
                Category: <b>{t['category']}</b> | Stage: <b>{t['status']}</b>
            </div>
        </div>
        """

    st.markdown(
        f"""
        <div class="bell-container">
            <div class="bell-icon">🔔</div>
            <div class="bell-title">Critical Tasks Due Today</div>
            <div class="bell-subtitle">The following tasks are due today and require your pending sign-off/action.</div>
            <div style="width: 100%; max-width: 700px;">
                {tasks_html}
            </div>
        </div>
        <style>
        .bell-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, rgba(239, 68, 68, 0.12), rgba(220, 38, 38, 0.05));
            border: 1px solid rgba(239, 68, 68, 0.25);
            border-radius: 16px;
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 10px 25px rgba(239, 68, 68, 0.08);
            animation: pulseBorder 2.5s infinite alternate;
        }}
        .bell-icon {{
            font-size: 4rem;
            animation: ringBell 2s ease-in-out infinite;
            transform-origin: top center;
            display: inline-block;
            filter: drop-shadow(0 4px 8px rgba(239, 68, 68, 0.3));
        }}
        .bell-title {{
            font-family: 'Outfit', 'Inter', sans-serif;
            font-weight: 800;
            font-size: 1.6rem;
            color: #EF4444;
            margin-top: 15px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        .bell-subtitle {{
            font-size: 0.95rem;
            color: var(--text-color);
            opacity: 0.8;
            margin: 5px 0 20px 0;
            text-align: center;
        }}
        @keyframes ringBell {{
            0% {{ transform: rotate(0); }}
            5% {{ transform: rotate(18deg); }}
            10% {{ transform: rotate(-14deg); }}
            15% {{ transform: rotate(12deg); }}
            20% {{ transform: rotate(-10deg); }}
            25% {{ transform: rotate(8deg); }}
            30% {{ transform: rotate(-6deg); }}
            35% {{ transform: rotate(4deg); }}
            40% {{ transform: rotate(-2deg); }}
            45% {{ transform: rotate(1deg); }}
            50%, 100% {{ transform: rotate(0); }}
        }}
        @keyframes pulseBorder {{
            0% {{
                border-color: rgba(239, 68, 68, 0.25);
                box-shadow: 0 10px 25px rgba(239, 68, 68, 0.05);
            }}
            100% {{
                border-color: rgba(239, 68, 68, 0.6);
                box-shadow: 0 10px 30px rgba(239, 68, 68, 0.25);
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
