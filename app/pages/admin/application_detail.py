"""
PARAKH Admin Portal - Institutional Case Inspection & Decision Workstation
Detailed credit analyst terminal with AI explainability, financial telemetry, SHAP attribution, and sign-off actions.
"""
import streamlit as st
from utils.mock_data import get_application_by_id, MOCK_APPLICATIONS
from utils.navigation import navigate_admin
from utils.styling import render_html, render_section_gap, render_module_gap
from components.score_card import render_score_card
from components.risk_badge import render_risk_badge, render_status_pill
from components.cards import render_ai_memo_card
from components.charts import create_factor_impact_chart

def render_admin_application_detail():
    """Renders the comprehensive credit case inspection workstation."""
    theme = st.session_state.get("theme", "dark")
    selected_id = st.session_state.get("selected_app_id", "PRK-2026-8943")
    app = get_application_by_id(selected_id)

    status_pill = render_status_pill(app['status'])
    risk_pill = render_risk_badge(app['risk_category'])

    # Top Case Navigation Bar
    render_html(f"""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border);">
<div>
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.25rem;">
<span class="font-mono" style="font-size: 0.78rem; font-weight: 700; color: var(--accent);">{app['id']}</span>
<span style="color: var(--text-muted);">•</span>
<span style="font-size: 0.78rem; color: var(--text-secondary);">{app['submission_date']}</span>
<span style="color: var(--text-muted);">•</span>
<span style="font-size: 0.78rem; color: var(--text-muted);">Underwriting Desk</span>
<span class="mock-badge">Demo Case</span>
</div>
<h2 style="font-size: 2rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">
Case File: {app['applicant_name']}
</h2>
<span style="font-size: 0.9rem; color: var(--text-secondary);">{app['employer']} • {app['employment_type']}</span>
</div>
<div style="display: flex; align-items: center; gap: 0.75rem;">
{status_pill}
{risk_pill}
</div>
</div>
""")

    # Quick Case Switcher Pill
    app_ids = [a["id"] for a in MOCK_APPLICATIONS]
    current_idx = app_ids.index(selected_id) if selected_id in app_ids else 0
    
    col_nav1, col_nav2 = st.columns([1.2, 4], gap="small")
    with col_nav1:
        if st.button("← Back to Registry", key="detail_back_btn", use_container_width=True):
            navigate_admin("applications")
    with col_nav2:
        new_sel = st.selectbox(
            "Switch dossier directly:",
            options=app_ids,
            index=current_idx,
            format_func=lambda x: f"{x} - {get_application_by_id(x)['applicant_name']} ({get_application_by_id(x)['risk_category']})",
            label_visibility="collapsed"
        )
        if new_sel != selected_id:
            st.session_state.selected_app_id = new_sel
            st.rerun()

    render_module_gap()

    # Main Dossier: Two-Column Split
    c_left, c_right = st.columns([1.2, 1], gap="large")

    with c_left:
        # 1. AI Score Card
        render_html(render_score_card(
            score=app['credit_score'],
            risk_category=app['risk_category'],
            default_prob=app['default_probability']
        ))

        render_section_gap()

        # 2. Institutional AI Credit Memo
        render_html(render_ai_memo_card(app['ai_memo'], title="PARAKH Underwriting Recommendation"))

        # 3. Factor Attribution Breakdown
        render_html('<h4 style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.85rem; font-family: var(--font-heading);">Neural Attribution (SHAP Waterfall)</h4>')
        fig_impact = create_factor_impact_chart(app.get("risk_factors", []), theme=theme)
        st.plotly_chart(fig_impact, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        # 1. Financial Profile Telemetry Card
        dti_color = "#10B981" if app['debt_to_income'] < 0.35 else "#EF4444"
        delinq_color = "#10B981" if app.get('late_payments_36m', 0) == 0 else "#EF4444"

        render_html(f"""
<div class="p-card-static" style="margin-bottom: 1.5rem;">
<h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Financial & Liquidity Telemetry</h4>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem; margin-bottom: 1.25rem;">
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Verified Monthly Income</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary);">₹{app['monthly_income']:,.0f}</div>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Debt-to-Income (DTI)</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: {dti_color};">
{app['debt_to_income']*100:.1f}%
</div>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Active Debt Principal</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary);">₹{app.get('existing_debt', 0):,.0f}</div>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Average Bank Reserves</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary);">₹{app.get('bank_balance', 0):,.0f}</div>
</div>
</div>

<div style="display: flex; flex-direction: column; gap: 0.6rem; font-size: 0.82rem; border-top: 1px solid var(--border); padding-top: 1rem;">
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">Bureau Credit History Length</span>
<span class="font-mono" style="font-weight: 700; color: var(--text-primary);">{app.get('bureau_history_years', 5)} Years</span>
</div>
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">30+ DPD Delinquencies (36m)</span>
<span class="font-mono" style="font-weight: 700; color: {delinq_color};">
{app.get('late_payments_36m', 0)} Recorded
</span>
</div>
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">Hard Bureau Searches (Trailing 6m)</span>
<span class="font-mono" style="font-weight: 700; color: var(--text-primary);">{app.get('recent_inquiries_6m', 1)} Inquiries</span>
</div>
</div>
</div>
""")

        # 2. Facility Details & Structure
        render_html(f"""
<div class="p-card-static" style="margin-bottom: 1.5rem;">
<h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Loan Terms & Exposure Structure</h4>

<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Requested Principal</span>
<span class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: var(--accent);">₹{app['loan_amount']:,.0f}</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Facility Purpose</span>
<span style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">{app['loan_purpose']}</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.65rem 0;">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Amortization Tenor</span>
<span class="font-mono" style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">{app['tenure_months']} Months</span>
</div>
</div>
""")

        # 3. Interactive Underwriting Decision Desk
        render_html("""
<div class="p-card-accent" style="padding: 1.4rem;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--accent); letter-spacing: 0.08em; margin-bottom: 0.3rem; font-family: var(--font-mono);">Underwriting Committee Station</div>
<h4 style="margin: 0 0 1rem 0; font-size: 1.15rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Credit Analyst Sign-off</h4>
</div>
""")

        analyst_note = st.text_area(
            "Committee Remarks / Conditionality Notes",
            placeholder="e.g. Approved subject to primary salary credit lien verification...",
            height=75
        )

        act_col1, act_col2 = st.columns(2)
        with act_col1:
            if st.button("✓ Sanction Facility", key="btn_sanction", type="primary", use_container_width=True):
                st.success(f"Facility for {app['applicant_name']} sanctioned under Level 4 authority.")
        with act_col2:
            if st.button("✕ Reject / Decline", key="btn_decline", use_container_width=True):
                st.error(f"Application {app['id']} marked as Declined.")

        if st.button("Request Secondary Collateral", key="btn_collateral", use_container_width=True):
            st.warning("Secondary collateral request issued to applicant.")
