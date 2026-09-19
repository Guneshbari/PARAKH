"""
PARAKH Admin Portal - Institutional Applications Registry
Full-featured portfolio management with search, multi-factor filtering, risk tier sorting, and case inspection.
"""
import streamlit as st
from utils.mock_data import MOCK_APPLICATIONS, get_applications
from utils.styling import render_html
from components.tables import render_applications_table

def render_admin_applications():
    """Renders the comprehensive administrative application registry."""
    render_html("""
<div style="margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;">
<span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-family: var(--font-mono);">Credit Underwriting Registry</span>
<span class="mock-badge">Simulated Book · Demo</span>
</div>
<h1 style="font-size: 2.1rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">Applications Management</h1>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">Inspect applicant dossiers, verify bureau telemetry, and perform committee overrides.</p>
</div>
""")

    # Search & Filter Toolbar
    f_cols = st.columns([2.5, 1.2, 1.2, 1.2], gap="small")
    with f_cols[0]:
        search_query = st.text_input("Search Registry", placeholder="Search by name, ID, employer, or purpose...", label_visibility="collapsed")
    with f_cols[1]:
        status_filter = st.selectbox("Status", ["All", "Approved", "Under Review", "High Risk", "Rejected"], index=0, label_visibility="collapsed")
    with f_cols[2]:
        risk_filter = st.selectbox("Risk Tier", ["All", "Low Risk", "Medium Risk", "High Risk"], index=0, label_visibility="collapsed")
    with f_cols[3]:
        sort_by = st.selectbox("Sort Order", ["Score (High to Low)", "Score (Low to High)", "Amount (High to Low)", "Date (Newest First)"], index=0, label_visibility="collapsed")

    # Fetch and filter applications
    apps = get_applications(search=search_query, status_filter=status_filter, risk_filter=risk_filter)

    # Apply Sorting
    if sort_by == "Score (High to Low)":
        apps = sorted(apps, key=lambda x: x["credit_score"], reverse=True)
    elif sort_by == "Score (Low to High)":
        apps = sorted(apps, key=lambda x: x["credit_score"])
    elif sort_by == "Amount (High to Low)":
        apps = sorted(apps, key=lambda x: x["loan_amount"], reverse=True)
    elif sort_by == "Date (Newest First)":
        apps = sorted(apps, key=lambda x: x["submission_date"], reverse=True)

    render_html(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin: 1.25rem 0 0.75rem 0;">
<span style="font-size: 0.82rem; font-weight: 700; color: var(--text-secondary);">Showing <strong>{len(apps)}</strong> matched applications</span>
<span style="font-size: 0.74rem; color: var(--text-muted); font-family: var(--font-mono);">Portfolio Registry Live</span>
</div>
""")

    # Render Table
    render_applications_table(apps, is_admin=True)
