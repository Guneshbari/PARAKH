"""
PARAKH Floating Glass Navbar Component
Unified floating rounded glass navigation container with 4-zone fintech hierarchy:
Zone 1 (Brand) | Zone 2 (Primary Navigation) | Zone 3 (System Status & Context) | Zone 4 (Tactile Toggle & Profile)
"""
import streamlit as st
from utils.navigation import navigate_user, navigate_admin, toggle_theme
from utils.styling import render_html

def render_navbar():
    """
    Renders the unified 4-zone floating rounded glass navigation bar for PARAKH.
    Strictly separates User and Admin portals with zero leaked controls.
    """
    portal = st.session_state.get("portal", "user")
    theme = st.session_state.get("theme", "dark")

    # Single Unified Floating Glass Container (Snaps to 1320px Global Content Grid)
    with st.container(key="parakh_navbar", horizontal=True):
        
        # ZONE 1: Brand Logo & Institutional Fintech Wordmark (Left)
        subtitle = "AI Credit Intelligence" if portal == "user" else "Underwriter Console"
        subtitle_color = "var(--accent)" if portal == "user" else "#10B981"
        
        render_html(f"""
<div class="nav-brand-container">
    <div class="nav-brand-icon">P</div>
    <div class="nav-brand-text">
        <span class="nav-brand-title">PARAKH</span>
        <span class="nav-brand-subtitle" style="color: {subtitle_color};">{subtitle}</span>
    </div>
</div>
""")

        # ZONE 2: Primary Navigation Links (Center)
        with st.container(key="parakh_nav_links", horizontal=True):
            if portal == "user":
                active_page = st.session_state.get("user_page", "dashboard")
                
                if st.button("Dashboard", key="parakh_nav_u_dash", type="primary" if active_page == "dashboard" else "secondary"):
                    navigate_user("dashboard")
                if st.button("Applications", key="parakh_nav_u_apps", type="primary" if active_page == "applications" else "secondary"):
                    navigate_user("applications")
                if st.button("Results", key="parakh_nav_u_res", type="primary" if active_page == "result" else "secondary"):
                    navigate_user("result")
                if st.button("Profile", key="parakh_nav_u_prof", type="primary" if active_page == "profile" else "secondary"):
                    navigate_user("profile")
            else:
                active_page = st.session_state.get("admin_page", "dashboard")
                
                if st.button("Dashboard", key="parakh_nav_a_dash", type="primary" if active_page == "dashboard" else "secondary"):
                    navigate_admin("dashboard")
                if st.button("Applications", key="parakh_nav_a_apps", type="primary" if active_page in ["applications", "application_detail"] else "secondary"):
                    navigate_admin("applications")
                if st.button("Analytics", key="parakh_nav_a_anl", type="primary" if active_page == "analytics" else "secondary"):
                    navigate_admin("analytics")
                if st.button("Model Insights", key="parakh_nav_a_mod", type="primary" if active_page == "model_insights" else "secondary"):
                    navigate_admin("model_insights")

        # ZONE 3 & 4: System Status, Context, Tactile Theme Toggle, and Profile (Right)
        with st.container(key="parakh_nav_right", horizontal=True):
            # Zone 3: Live Status Badge + Context Indicator Pill
            status_text = "Credit Engine Live" if portal == "user" else "Underwriting Live"
            context_text = "Current Portfolio" if portal == "user" else "All Applications"
            render_html(f"""
<div class="nav-status-context-group">
    <div class="nav-status-badge">
        <span class="nav-status-dot"></span>
        <span class="nav-status-label">{status_text}</span>
    </div>
    <div class="nav-context-pill">
        <span>{context_text}</span>
    </div>
</div>
""")

            # Zone 4: Tactile Hardware Theme Toggle
            toggle_key = f"parakh_theme_toggle_{portal}"
            if st.button("", key=toggle_key):
                toggle_theme()

            # Zone 4: User Profile Control
            if portal == "user":
                render_html("""
<div class="nav-profile-pill">
    <div class="nav-profile-avatar">AM</div>
    <div class="nav-profile-info">
        <span class="nav-profile-name">Aarav M.</span>
        <span class="nav-profile-role">Risk Analyst</span>
    </div>
</div>
""")
            else:
                render_html("""
<div class="nav-profile-pill admin">
    <div class="nav-profile-avatar admin">SJ</div>
    <div class="nav-profile-info">
        <span class="nav-profile-name">S. Jenkins</span>
        <span class="nav-profile-role admin">Underwriter Desk</span>
    </div>
</div>
""")
