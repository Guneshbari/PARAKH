"""
PARAKH Tables Component
Financial data tables with risk badges, status indicators, and inspection triggers.
"""
import streamlit as st
from components.risk_badge import render_risk_badge, render_status_pill
from utils.navigation import navigate_admin, navigate_user
from utils.styling import render_html

def render_applications_table(apps: list, is_admin: bool = True):
    """
    Renders a high-end application registry table with interactive selection buttons.
    """
    if not apps:
        render_html("""
<div class="p-card-static" style="text-align: center; padding: 2.5rem 1.5rem;">
<h4 style="margin: 0 0 0.4rem 0; color: var(--text-primary); font-family: var(--font-heading);">No applications found</h4>
<p style="margin: 0; font-size: 0.85rem; color: var(--text-secondary);">Try adjusting your search terms or filter criteria.</p>
</div>
""")
        return

    # Table Header
    header_col_widths = [1.8, 1.8, 1.2, 1.3, 1.2, 1.1, 1.4]
    h1, h2, h3, h4, h5, h6, h7 = st.columns(header_col_widths)
    with h1:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Applicant / ID</span>')
    with h2:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Employer / Purpose</span>')
    with h3:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Facility</span>')
    with h4:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Status</span>')
    with h5:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Risk Tier</span>')
    with h6:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; font-family: var(--font-mono);">Score</span>')
    with h7:
        render_html('<span style="font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; text-align: right; display: block; font-family: var(--font-mono);">Action</span>')

    render_html('<div class="table-divider"></div>')

    # Render Rows
    for idx, app in enumerate(apps):
        row_container = st.container()
        with row_container:
            c1, c2, c3, c4, c5, c6, c7 = st.columns(header_col_widths)
            
            with c1:
                render_html(f"""
<div style="display: flex; flex-direction: column;">
<span style="font-size: 0.88rem; font-weight: 700; color: var(--text-primary);">{app['applicant_name']}</span>
<span class="font-mono" style="font-size: 0.72rem; color: var(--accent);">{app['id']}</span>
</div>
""")
                
            with c2:
                render_html(f"""
<div style="display: flex; flex-direction: column;">
<span style="font-size: 0.84rem; color: var(--text-primary); font-weight: 500;">{app['employer']}</span>
<span style="font-size: 0.72rem; color: var(--text-secondary);">{app['loan_purpose']}</span>
</div>
""")
                
            with c3:
                render_html(f"""
<div style="font-size: 0.88rem; font-weight: 700; font-family: var(--font-mono); color: var(--text-primary);">
₹{app['loan_amount']:,.0f}
</div>
""")
                
            with c4:
                render_html(render_status_pill(app['status']))
                
            with c5:
                render_html(render_risk_badge(app['risk_category']))
                
            with c6:
                score_color = "#10B981" if app['credit_score'] >= 720 else ("#F59E0B" if app['credit_score'] >= 640 else "#EF4444")
                render_html(f"""
<span class="font-mono" style="font-size: 0.95rem; font-weight: 800; color: {score_color};">
{app['credit_score']}
</span>
""")
                
            with c7:
                btn_label = "Inspect Case →" if is_admin else "View Memo →"
                if st.button(btn_label, key=f"tbl_btn_{app['id']}_{idx}", use_container_width=True):
                    if is_admin:
                        navigate_admin("application_detail", app_id=app['id'])
                    else:
                        navigate_user("result", app_id=app['id'])

            render_html('<div class="table-row-divider"></div>')
