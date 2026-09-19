"""
PARAKH User Portal - AI Credit Assessment Result Page
Flagship demo screen: credit score gauge, default probability, SHAP factor impact breakdown, and AI executive memo.
"""
import streamlit as st
from utils.mock_data import MOCK_APPLICATIONS, get_application_by_id
from utils.navigation import navigate_user
from utils.styling import render_html, render_section_gap
from components.score_card import render_score_card
from components.risk_badge import render_risk_badge, render_status_pill
from components.cards import render_factor_row, render_ai_memo_card
from components.charts import create_factor_impact_chart

def render_user_result():
    """Renders the comprehensive AI Credit Assessment Result Screen."""
    theme = st.session_state.get("theme", "dark")
    
    # Check if there's a freshly submitted assessment from the onboarding flow
    if st.session_state.get("submitted_assessment"):
        app_data = st.session_state.submitted_assessment
    else:
        selected_id = st.session_state.get("selected_app_id", "PRK-2026-8941")
        app_data = get_application_by_id(selected_id)

    status_pill = render_status_pill(app_data['status'])
    risk_pill = render_risk_badge(app_data['risk_category'])

    # Page Header
    header_cols = st.columns([2.5, 1.5])
    with header_cols[0]:
        render_html(f"""
<div style="margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.35rem;">
<span class="font-mono" style="font-size: 0.78rem; font-weight: 700; color: var(--accent);">{app_data['id']}</span>
<span style="color: var(--text-muted);">•</span>
<span style="font-size: 0.78rem; color: var(--text-secondary);">{app_data['submission_date']}</span>
</div>
<h2 style="font-size: 2rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">
AI Credit Assessment Memo
</h2>
<p style="font-size: 0.92rem; color: var(--text-secondary); margin-top: 0.25rem;">
Applicant: <strong>{app_data['applicant_name']}</strong> • Facility: <strong>₹{app_data['loan_amount']:,.0f}</strong> ({app_data['loan_purpose']})
</p>
</div>
""")

    with header_cols[1]:
        render_html(f"""
<div style="display: flex; justify-content: flex-end; align-items: center; gap: 0.75rem; height: 100%;">
{status_pill}
{risk_pill}
</div>
""")

    # Main Grid: Left side score card, Right side key financial metrics
    top_cols = st.columns([1.2, 1], gap="large")
    
    with top_cols[0]:
        render_html(render_score_card(
            score=app_data['credit_score'],
            risk_category=app_data['risk_category'],
            default_prob=app_data['default_probability']
        ))

    with top_cols[1]:
        dti_color = "#10B981" if app_data.get('debt_to_income', 0) < 0.35 else "#EF4444"
        render_html(f"""
<div class="p-card-static" style="height: 100%; display: flex; flex-direction: column; justify-content: space-between;">
<div>
<span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.08em; font-family: var(--font-mono);">Financial Telemetry Verified</span>
<h4 style="margin: 0.2rem 0 1rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Obligation & Liquidity Profile</h4>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.85rem;">
<div style="padding: 0.75rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Verified Inflow</div>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary);">₹{app_data.get('monthly_income', 0):,.0f}</div>
</div>
<div style="padding: 0.75rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Debt-to-Income (DTI)</div>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: {dti_color};">
{app_data.get('debt_to_income', 0)*100:.1f}%
</div>
</div>
<div style="padding: 0.75rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Liquid Bank Balance</div>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary);">₹{app_data.get('bank_balance', 0):,.0f}</div>
</div>
<div style="padding: 0.75rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Bureau History</div>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary);">{app_data.get('bureau_history_years', 5)} Years</div>
</div>
</div>
</div>

<div style="margin-top: 1rem; padding: 0.7rem 0.85rem; background: var(--bg-subtle); border: 1px solid var(--border); border-radius: 6px; font-size: 0.76rem; color: var(--text-secondary);">
<strong style="color: var(--text-primary);">Policy Guideline:</strong> Portfolio DTI tolerance ceiling is 45.0%. Current obligation buffer is sufficient.
</div>
</div>
""")

    render_section_gap()

    # AI Synthesis Memo Card (with Demo / Mock content indication)
    render_html(render_ai_memo_card(app_data.get("ai_memo", "")))

    # Explainability: "Why this assessment?"
    render_html("""
<div style="margin-bottom: 1.25rem;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-family: var(--font-mono);">Explainable AI (XAI) Attribution</div>
<h3 style="font-size: 1.4rem; font-weight: 800; color: var(--text-primary); margin: 0.15rem 0 0.35rem 0; font-family: var(--font-heading);">Why this assessment?</h3>
<p style="font-size: 0.88rem; color: var(--text-secondary); margin: 0;">
The PARAKH neural attribution framework breaks down how individual financial telemetry factors positively or negatively affected your score.
</p>
</div>
""")

    factors = app_data.get("risk_factors", [])
    
    fac_col1, fac_col2 = st.columns([1.1, 1.2], gap="large")
    
    with fac_col1:
        render_html('<h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.75rem; font-family: var(--font-heading);">Factor Attribution List</h4>')
        for f in factors:
            render_html(render_factor_row(f))
            
    with fac_col2:
        render_html('<h4 style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary); margin-bottom: 0.75rem; font-family: var(--font-heading);">SHAP Impact Distribution</h4>')
        fig_impact = create_factor_impact_chart(factors, theme=theme)
        st.plotly_chart(fig_impact, use_container_width=True, config={"displayModeBar": False})

    # Bottom Action Bar
    render_section_gap()
    b_cols = st.columns([1.5, 1, 1, 1.5])
    with b_cols[1]:
        if st.button("← Back to Dashboard", key="res_back_dash", use_container_width=True):
            navigate_user("dashboard")
    with b_cols[2]:
        if st.button("+ Start New Application", key="res_new_app", type="primary", use_container_width=True):
            st.session_state.app_form_step = 1
            st.session_state.submitted_assessment = None
            navigate_user("application")
