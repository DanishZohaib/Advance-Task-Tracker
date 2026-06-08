import streamlit as st

def inject_custom_css():
    """
    Injects custom styles to render an Enterprise Grade Finance ERP interface
    """
    css = """
    <style>
    /* Main Layout Customizations */
    .stApp {
        background-color: #0F172A; /* Rich Slate Dark Background */
        color: #F8FAFC;
    }
    
    /* Custom Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    
    /* Primary Typography Customization */
    h1, h2, h3, h4, h5, h6 {
        color: #F1F5F9 !important;
        font-family: 'Outfit', 'Inter', sans-serif !important;
    }
    
    /* Glassmorphism KPI Container */
    .kpi-card {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-left: 4px solid #4F46E5; /* Indigo Accent */
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        margin-bottom: 15px;
        transition: transform 0.2s ease-in-out;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(79, 70, 229, 0.15);
    }
    .kpi-title {
        font-size: 0.85rem;
        text-transform: uppercase;
        color: #94A3B8;
        font-weight: 600;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-top: 5px;
    }
    
    /* Module Card styling */
    .module-card {
        background: #1E293B;
        border: 1px solid #334155;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        transition: all 0.3s ease;
        cursor: pointer;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .module-card:hover {
        border-color: #4F46E5;
        background: #24324D;
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.1);
        transform: translateY(-3px);
    }
    .module-icon {
        font-size: 2.5rem;
        margin-bottom: 12px;
    }
    .module-name {
        font-size: 1.25rem;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 8px;
    }
    .module-desc {
        font-size: 0.85rem;
        color: #94A3B8;
    }
    
    /* Task Timeline Info */
    .workflow-timeline {
        border-left: 2px solid #334155;
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
        color: #E2E8F0;
    }
    .timeline-time {
        font-size: 0.75rem;
        color: #94A3B8;
    }
    
    /* Corporate Styled Alert Bar */
    .compliance-alert {
        background-color: rgba(239, 68, 68, 0.1);
        border: 1px solid rgba(239, 68, 68, 0.2);
        color: #FCA5A5;
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
        background-color: rgba(255,255,255,0.02);
        border: 1px solid rgba(255,255,255,0.05);
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 20px;
    }
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)
