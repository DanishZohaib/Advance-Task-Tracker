import streamlit as st

def render_page():
    # Page Header with credit to Danish Zohaib
    st.markdown("<h1 style='color: #4F46E5;'>📖 System Operator Manual</h1>", unsafe_allow_html=True)
    st.markdown(
        """
        <div style='background: rgba(79, 70, 229, 0.05); padding: 15px; border-radius: 8px; border: 1px solid rgba(79, 70, 229, 0.15); margin-bottom: 20px;'>
            <span style='color: var(--text-color); opacity: 0.7; font-size: 0.95rem;'>Lead Architect & Developer:</span>
            <span style='color: #4F46E5; font-weight: bold; font-size: 1.1rem;'>Danish Zohaib</span>
            <br>
            <span style='color: var(--text-color); opacity: 0.6; font-size: 0.85rem;'>Standard Operating Procedures (SOP) & Compliance Guidelines Registry</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Selector for Role SOPs
    st.markdown("### 👤 Select Your Access Role SOP")
    selected_role_sop = st.selectbox(
        "Choose a role manual to display:",
        options=["Payroll Team SOP", "NM Finance SOP", "GM/CFO SOP", "Auditor SOP", "Administrator SOP"]
    )
    
    st.markdown("---")
    
    if selected_role_sop == "Payroll Team SOP":
        st.markdown("<h2 style='color:#10B981;'>💰 Stage 1: Payroll Team Standard Operating Procedure</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            As a member of the **Payroll Team**, your primary responsibility is **Stage 1 (Payroll Processing & Disbursement)**. 
            You are responsible for executing compliance tasks, uploading required evidence, and signing off to move the tasks down the pipeline.
            """
        )
        
        # SOP Steps Cards
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>1. Select Pipeline</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Go to <b>Workflows & Tasks</b> and choose your category (e.g. Payroll, Petty Cash).</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>2. Complete Task</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Expand any task in the <b>Pending</b> stage. Add mandatory operational remarks.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>3. Evidence Upload</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Upload a verification file/screenshot and click <b>Complete Stage 1 & Sign-off</b>.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Visual diagram
        st.markdown("#### 🔄 Lifecycle Stage 1 Visual Flow")
        st.markdown(
            """
            ```
            ┌─────────────────┐       ┌──────────────────────┐       ┌─────────────────────┐
            │   Task Created  │ ────> │ Add Remarks/Evidence │ ────> │ Completed Stage 1   │
            │   (Status:      │       │ (File upload &       │       │ (Status changes to  │
            │   Pending)      │       │ comments required)   │       │ Payroll Completed)  │
            └─────────────────┘       └──────────────────────┘       └─────────────────────┘
            ```
            """
        )
        
        # Information alert
        st.markdown(
            """
            <div style='background-color: rgba(245, 158, 11, 0.1); border: 1px solid rgba(245, 158, 11, 0.2); color: #FBBF24; padding: 12px; border-radius: 8px;'>
                <b>💡 SLA Target & Rejections:</b> Tasks have a default 7-day completion limit. 
                If NM Finance or GM/CFO rejects your task, it will return to your queue as <b>Pending</b>, 
                and you must review their remarks in the task's timeline history before resubmitting.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif selected_role_sop == "NM Finance SOP":
        st.markdown("<h2 style='color:#F59E0B;'>📊 Stage 2: NM Finance Standard Operating Procedure</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            As an **NM Finance** officer, your primary responsibility is **Stage 2 (Review, Verification, and Approval)**. 
            You must review all evidence submitted by the Payroll Team, add verification remarks, and choose whether to forward or return the task.
            """
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>1. Access Queue</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Go to the <b>Workflows & Tasks</b> board. Look for tasks under status <b>Payroll Completed</b>.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>2. Verify Evidence</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Review Payroll Team comments and download/inspect the attached evidence file.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>3. Act on Task</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Enter comments and click <b>Approve Stage 2</b> to pass to CFO, or <b>Reject back to Stage 1</b>.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("#### 🔄 Lifecycle Stage 2 Visual Flow")
        st.markdown(
            """
            ```
                                                     ┌─────────────────────────┐
                                              ┌───>  │ Approve: moves to Stage3│
             ┌─────────────────────┐          │      │ (NM Finance Approved)   │
             │  Payroll Completed  │ ─────────┤      └─────────────────────────┘
             │  (Review Evidence)  │          │      ┌─────────────────────────┐
             └─────────────────────┘          └───>  │ Reject: moves to Stage 1│
                                                     │ (Pending)               │
                                                     └─────────────────────────┘
            ```
            """
        )
        
        st.markdown(
            """
            <div style='background-color: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.2); color: #FCA5A5; padding: 12px; border-radius: 8px;'>
                <b>⚠️ Digital Signature Validation:</b> Every approval creates a secure cryptographic SHA-256 seal. 
                Ensure your review comments are descriptive as they are hashed permanently into the audit trail timeline log.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif selected_role_sop == "GM/CFO SOP":
        st.markdown("<h2 style='color:#3B82F6;'>🛡️ Stage 3: GM/CFO Standard Operating Procedure</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            As the **GM/CFO**, you are the final authority for **Stage 3 (Final Release and Completion Sign-off)**. 
            You perform final validation of the entire approval chain before releasing the task to the Completed Registry.
            """
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>1. Full Audit Review</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Inspect active tasks under status <b>NM Finance Approved</b>. Check comments and timestamps.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>2. Final Sign-off</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Enter final release comments and click <b>Approve & Close Task</b> to finalize it.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>3. Direct Rejections</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>If corrections are needed, select the target stage (NM Finance or Payroll) and reject.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown("#### 🔄 Lifecycle Stage 3 Visual Flow")
        st.markdown(
            """
            ```
                                                       ┌───────────────────────────────┐
                                                ┌───>  │ Approve: Completed Registry   │
                                                │      │ (Status: GM/CFO Approved)     │
             ┌───────────────────────┐          │      └───────────────────────────────┘
             │  NM Finance Approved  │ ─────────┼───>  │ Reject: Back to Stage 2       │
             │  (Final Verification) │          │      │ (Status: Payroll Completed)   │
             └───────────────────────┘          │      └───────────────────────────────┘
                                                └───>  │ Reject: Back to Stage 1       │
                                                       │ (Status: Pending)             │
                                                       └───────────────────────────────┘
            ```
            """
        )
        
        st.markdown(
            """
            <div style='background-color: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.2); color: #93C5FD; padding: 12px; border-radius: 8px;'>
                <b>🛡️ Task Locking:</b> Once a task is approved and released by the GM/CFO, it moves to the 
                <b>Completed Registry</b> and becomes read-only (locked). No edits or adjustments can be made to it afterward.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif selected_role_sop == "Auditor SOP":
        st.markdown("<h2 style='color:#EC4899;'>🔒 Auditor Standard Operating Procedure</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            As an **Auditor**, your primary responsibility is **Independent Compliance Auditing & Reporting**.
            You have read-only view access across the workspace pipelines and full access to audit trails and exports.
            """
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>1. Audit Trail Registry</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Go to the <b>Security & Audit Trail</b> page. Filter by action types, dates, or task numbers.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>2. Inspect Timelines</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Review signatures, IP locations, device details, and side-by-side edits of fields.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>3. Compile Reports</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Go to <b>Advanced Reports</b> and compile compliance reports as PDF, Excel, or CSV.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(
            """
            <div style='background-color: rgba(236, 72, 153, 0.1); border: 1px solid rgba(236, 72, 153, 0.2); color: #F9A8D4; padding: 12px; border-radius: 8px;'>
                <b>📄 Report Formats:</b> CSV compilation offers raw data, Excel offers multi-sheet categorizations, 
                and PDF reports compile formatted documents utilizing ReportLab layouts including total completion speed statistics.
            </div>
            """,
            unsafe_allow_html=True
        )

    elif selected_role_sop == "Administrator SOP":
        st.markdown("<h2 style='color:#8B5CF6;'>⚙️ Administrator Standard Operating Procedure</h2>", unsafe_allow_html=True)
        st.markdown(
            """
            As the **System Administrator**, you have full operational override permissions. 
            Your responsibilities cover system settings, scheduling engines, bulk imports, and data archiving.
            """
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>1. Schedule Routines</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Configure and edit tasks generation templates (any field can be modified) using the <b>Recurring Task Master</b> interface.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>2. System SMTP Control</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Configure the global SMTP configuration settings for real-time compliance alert emails.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                """
                <div style='background: var(--secondary-background-color); padding: 18px; border-radius: 8px; border: 1px solid rgba(128,128,128,0.15); min-height: 150px;'>
                    <b style='color: #4F46E5; font-size: 1rem;'>3. Pipeline Override</b><br>
                    <span style='color: var(--text-color); opacity: 0.7; font-size: 0.85rem;'>Edit active workflow titles/descriptions or soft-archive records in <b>Workflows & Tasks</b>.</span>
                </div>
                """,
                unsafe_allow_html=True
            )
            
        st.markdown("<br>", unsafe_allow_html=True)
        
        st.markdown(
            """
            <div style='background-color: rgba(139, 92, 246, 0.1); border: 1px solid rgba(139, 92, 246, 0.2); color: #C084FC; padding: 12px; border-radius: 8px;'>
                <b>🔒 Cryptographic Safety Note:</b> When storing global SMTP passwords, the system automatically 
                encrypts it in the database using a symmetric key derived from the system JWT key. 
                Audit logs capture every setting adjustment alongside your admin IP and user agent.
            </div>
            """,
            unsafe_allow_html=True
        )

    # General System Alert Guidelines
    st.markdown("---")
    st.markdown("### 🔔 Same-Day Due Alerts & 💬 WhatsApp Nudges")
    st.markdown(
        """
        To maintain high operational efficiency, the system provides real-time highlights for same-day deadlines:
        - **Same-Day Due Alarms:** If any active tasks are due on the current day, a large animated bell is displayed at the top of the **Workflows & Tasks Workspace** for users who are responsible for the pending action.
        - **WhatsApp Nudges:** Operators can send nudge notifications to the responsible team members by inputting their phone number in the task details view. This action is securely logged in the task's timeline history and system audit logs, and redirects the user to WhatsApp Web to deliver the message.
        """
    )
