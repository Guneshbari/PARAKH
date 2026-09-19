"""
PARAKH Navigation & State Controller
Manages active portal (User vs Admin), pages, theme switching, and application selection.
"""
import streamlit as st

def init_session_state():
    """Initializes Streamlit session state keys with robust defaults."""
    if "theme" not in st.session_state:
        st.session_state.theme = "dark"
        
    if "portal" not in st.session_state:
        st.session_state.portal = "user"  # 'user' or 'admin'
        
    if "user_page" not in st.session_state:
        st.session_state.user_page = "dashboard"  # 'dashboard', 'application', 'applications', 'result', 'profile'
        
    if "admin_page" not in st.session_state:
        st.session_state.admin_page = "dashboard"  # 'dashboard', 'applications', 'application_detail', 'analytics', 'model_insights'
        
    if "selected_app_id" not in st.session_state:
        st.session_state.selected_app_id = "PRK-2026-8941"
        
    if "app_form_step" not in st.session_state:
        st.session_state.app_form_step = 1
        
    if "submitted_assessment" not in st.session_state:
        st.session_state.submitted_assessment = None


def toggle_theme():
    """Toggles between Dark and Light mode and triggers rerun."""
    if st.session_state.theme == "dark":
        st.session_state.theme = "light"
    else:
        st.session_state.theme = "dark"
    st.rerun()


def set_portal(portal: str):
    """Switches active portal between 'user' and 'admin'."""
    st.session_state.portal = portal
    st.rerun()


def navigate_user(page: str, app_id: str = None):
    """Navigates to a specific page inside the User Portal."""
    st.session_state.portal = "user"
    st.session_state.user_page = page
    if app_id:
        st.session_state.selected_app_id = app_id
    st.rerun()


def navigate_admin(page: str, app_id: str = None):
    """Navigates to a specific page inside the Admin Portal."""
    st.session_state.portal = "admin"
    st.session_state.admin_page = page
    if app_id:
        st.session_state.selected_app_id = app_id
    st.rerun()
