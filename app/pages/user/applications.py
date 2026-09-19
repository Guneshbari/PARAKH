"""
PARAKH User Portal - My Applications Registry
View historical and active credit applications with detailed status tracking and memo links.
"""
import streamlit as st
from utils.mock_data import MOCK_APPLICATIONS
from utils.navigation import navigate_user
from utils.styling import render_html, render_module_gap
from components.tables import render_applications_table

def render_user_applications():
    """Renders the user's applications portfolio."""
    render_html("""
<div style="margin-bottom: 1.5rem;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-family: var(--font-mono);">Credit Portfolio</div>
<h2 style="font-size: 1.85rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">My Credit Applications</h2>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">Review all past and current credit evaluations submitted under your profile.</p>
</div>
""")

    # Filter Bar
    filter_cols = st.columns([2.5, 1.2, 1.2])
    with filter_cols[0]:
        search_query = st.text_input("Search applications by ID or purpose", placeholder="e.g. Home Improvement, PRK-2026", label_visibility="collapsed")
    with filter_cols[1]:
        status_filter = st.selectbox("Status", ["All", "Approved", "Under Review", "High Risk", "Rejected"], label_visibility="collapsed")
    with filter_cols[2]:
        if st.button("+ New Facility", type="primary", use_container_width=True):
            st.session_state.app_form_step = 1
            navigate_user("application")

    # Filter data
    apps = MOCK_APPLICATIONS.copy()
    if search_query:
        apps = [a for a in apps if search_query.lower() in a['loan_purpose'].lower() or search_query.lower() in a['id'].lower()]
    if status_filter != "All":
        apps = [a for a in apps if a['status'].lower() == status_filter.lower()]

    render_module_gap()
    
    # Render table (is_admin=False)
    render_applications_table(apps, is_admin=False)
