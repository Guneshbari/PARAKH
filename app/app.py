"""
PARAKH - AI-Powered Credit Assessment Platform
Main Streamlit Application Entrypoint (v2.1)
"""
import sys
import os

# Ensure the app directory is on sys.path for direct imports
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="PARAKH | AI Credit Intelligence Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Core utilities & styling
from utils.styling import get_global_css, render_html
from utils.navigation import init_session_state
from components.navbar import render_navbar

# User Portal Pages
from pages.user.dashboard import render_user_dashboard
from pages.user.application import render_user_application
from pages.user.applications import render_user_applications
from pages.user.result import render_user_result
from pages.user.profile import render_user_profile

# Admin Portal Pages
from pages.admin.dashboard import render_admin_dashboard
from pages.admin.applications import render_admin_applications
from pages.admin.application_detail import render_admin_application_detail
from pages.admin.analytics import render_admin_analytics
from pages.admin.model_insights import render_admin_model_insights

def main():
    """Main application lifecycle and routing orchestrator."""
    # 1. Initialize State
    init_session_state()
    
    # Query parameter sync for demo evaluation (e.g. ?portal=admin)
    query_portal = st.query_params.get("portal")
    if query_portal in ["admin", "user"] and query_portal != st.session_state.portal:
        st.session_state.portal = query_portal

    theme = st.session_state.get("theme", "dark")

    # 2. Inject Institutional CSS Design System
    st.markdown(get_global_css(theme), unsafe_allow_html=True)

    # 3. Render SaaS Top Navigation Bar (Strictly Role Separated)
    render_navbar()

    # 4. Route to Active Page
    portal = st.session_state.get("portal", "user")

    if portal == "user":
        page = st.session_state.get("user_page", "dashboard")
        if page == "dashboard":
            render_user_dashboard()
        elif page == "application":
            render_user_application()
        elif page == "applications":
            render_user_applications()
        elif page == "result":
            render_user_result()
        elif page == "profile":
            render_user_profile()
        else:
            render_user_dashboard()

    elif portal == "admin":
        page = st.session_state.get("admin_page", "dashboard")
        if page == "dashboard":
            render_admin_dashboard()
        elif page == "applications":
            render_admin_applications()
        elif page == "application_detail":
            render_admin_application_detail()
        elif page == "analytics":
            render_admin_analytics()
        elif page == "model_insights":
            render_admin_model_insights()
        else:
            render_admin_dashboard()

    # 5. Global Discreet Footer with Demo Evaluation Role Switcher
    render_html('<div style="margin-top: 3.5rem; padding-top: 1.25rem; border-top: 1px solid var(--border);"></div>')
    
    foot_c1, foot_c2 = st.columns([3, 1])
    with foot_c1:
        render_html("""
<div style="font-size: 0.74rem; color: var(--text-muted); line-height: 1.5;">
<strong>PARAKH</strong> • Autonomous Credit Assessment & Explainability Platform<br>
<span style="font-family: var(--font-mono); font-size: 0.7rem;">v2.4 Institutional Build · Simulated Hackathon Demo Environment</span>
</div>
""")
    with foot_c2:
        demo_btn_label = "Demo: Switch to Admin View ↗" if portal == "user" else "Demo: Switch to User View ↗"
        if st.button(demo_btn_label, key="footer_demo_role_toggle", use_container_width=True):
            st.session_state.portal = "admin" if portal == "user" else "user"
            st.rerun()

if __name__ == "__main__":
    main()
