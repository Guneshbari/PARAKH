"""
PARAKH User Portal - Flagship Dashboard
Institutional credit intelligence dashboard with hero, live telemetry widget, financial KPIs, and active facility tracking.
"""
import streamlit as st
import plotly.graph_objects as go
from utils.mock_data import MOCK_APPLICATIONS
from utils.navigation import navigate_user
from utils.styling import render_html, get_theme_colors, render_section_gap, render_module_gap
from components.score_card import render_score_card
from components.risk_badge import render_risk_badge, render_status_pill
from components.cards import render_kpi_card, render_factor_row

def _create_mini_sparkline(theme: str = "dark") -> go.Figure:
    """Creates a tiny, elegant sparkline for the hero credit score trend."""
    c = get_theme_colors(theme)
    months = ["Jun", "Jul", "Aug", "Sep"]
    scores = [718, 725, 734, 742]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=months,
        y=scores,
        mode='lines+markers',
        line=dict(color="#3B82F6", width=2.5),
        marker=dict(size=5, color="#10B981"),
        fill='tozeroy',
        fillcolor='rgba(59, 130, 246, 0.08)'
    ))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=65,
        margin=dict(l=10, r=10, t=5, b=5),
        xaxis=dict(showgrid=False, showticklabels=False, zeroline=False),
        yaxis=dict(showgrid=False, showticklabels=False, range=[700, 755], zeroline=False),
        hovermode=False
    )
    return fig


def render_user_dashboard():
    """Renders the comprehensive User Portal Dashboard."""
    theme = st.session_state.get("theme", "dark")
    active_app = MOCK_APPLICATIONS[0]  # Aarav Mehta default profile

    # 1. Flagship Hero Section
    hero_cols = st.columns([1.35, 1.15], gap="large")
    
    with hero_cols[0]:
        render_html("""
<div class="hero-wrapper animate-fade-in" style="margin-bottom: 1rem;">
<div class="hero-eyebrow">
<span style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 6px var(--accent);"></span>
AI-POWERED CREDIT INTELLIGENCE
</div>
<h1 class="hero-title">
Understand credit risk.<br>Make better decisions.
</h1>
<p class="hero-subtitle">
PARAKH transforms opaque underwriting into real-time, explainable credit decisions.
Monitor your institutional score, uncover positive financial drivers, and access fast liquidity with zero hidden friction.
</p>
</div>
""")

        # Primary & Secondary CTA row
        btn_c1, btn_c2 = st.columns([1.2, 1.0], gap="small")
        with btn_c1:
            if st.button("Start New Application →", key="hero_start_app", type="primary", use_container_width=True):
                st.session_state.app_form_step = 1
                navigate_user("application")
        with btn_c2:
            if st.button("View Applications", key="hero_view_apps", use_container_width=True):
                navigate_user("applications")

    with hero_cols[1]:
        # Live Credit Intelligence Hero Card (No raw HTML, meticulously structured)
        risk_pill = render_risk_badge("Low Risk")
        
        render_html(f"""
<div class="p-card-accent" style="padding: 1.4rem;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.85rem;">
<div>
<span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: var(--accent); letter-spacing: 0.08em; font-family: var(--font-mono);">Real-Time Underwriting Telemetry</span>
<div style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary); margin-top: 0.15rem; font-family: var(--font-heading);">Credit Health Matrix</div>
</div>
{risk_pill}
</div>

<div style="display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.65rem;">
<span style="font-size: 3rem; font-weight: 800; font-family: var(--font-mono); color: var(--text-primary); line-height: 1;">742</span>
<span style="font-size: 0.95rem; font-weight: 600; color: var(--text-muted); font-family: var(--font-mono);">/ 850</span>
<span style="margin-left: auto; font-size: 0.75rem; font-weight: 700; color: #10B981; background: rgba(16,185,129,0.12); padding: 0.25rem 0.6rem; border-radius: 4px; font-family: var(--font-mono);">Top 8% Tier-1</span>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; padding: 0.75rem 0; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); margin-bottom: 0.85rem;">
<div>
<span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Default Probability</span>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: #10B981;">12.0%</div>
</div>
<div>
<span style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Debt Service Margin</span>
<div class="font-mono" style="font-size: 1.1rem; font-weight: 800; color: var(--text-primary);">82.0% Available</div>
</div>
</div>
""")
        
        # Sparkline visualization for score trend
        st.plotly_chart(_create_mini_sparkline(theme=theme), use_container_width=True, config={"displayModeBar": False})

        render_html("""
<div style="padding: 0.7rem 0.85rem; background: var(--bg-subtle); border-radius: 6px; font-size: 0.78rem; line-height: 1.5; color: var(--text-secondary); border: 1px solid var(--border);">
<strong style="color: var(--text-primary);">AI Insight:</strong> Verified income of ₹2.85L/mo combined with disciplined 9.5-year repayment history qualifies this profile for prime tier liquidity.
</div>
</div>
""")

    render_section_gap()

    # 2. Financial Snapshot KPIs
    render_html('<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin-bottom: 1rem; letter-spacing: -0.02em; font-family: var(--font-heading);">Financial Health Snapshot</h3>')
    
    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4, gap="small")
    with kpi_col1:
        render_html(render_kpi_card("Active Applications", "3", delta="+1 this month", delta_type="positive"))
    with kpi_col2:
        render_html(render_kpi_card("Under Active Review", "0", delta="All resolved", delta_type="neutral"))
    with kpi_col3:
        render_html(render_kpi_card("Approved Facilities", "₹37,00,000", delta="100% Approval Rate", delta_type="positive"))
    with kpi_col4:
        render_html(render_kpi_card("Credit Trust Index", "742 / 850", delta="+17 pts vs baseline", delta_type="positive"))

    render_section_gap()

    # 3. Two Column Split: Current Active Application vs Credit Intelligence Breakdown
    col_left, col_right = st.columns([1.2, 1], gap="large")

    with col_left:
        render_html('<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin-bottom: 1rem; letter-spacing: -0.02em; font-family: var(--font-heading);">Active Credit Facility</h3>')
        
        status_pill = render_status_pill(active_app['status'])
        risk_pill = render_risk_badge(active_app['risk_category'])
        
        render_html(f"""
<div class="p-card" style="margin-bottom: 1.25rem;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
<div>
<span class="font-mono" style="font-size: 0.74rem; font-weight: 700; color: var(--accent); letter-spacing: 0.05em;">{active_app['id']}</span>
<h4 style="margin: 0.2rem 0; font-size: 1.2rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">{active_app['loan_purpose']}</h4>
<span style="font-size: 0.82rem; color: var(--text-secondary);">{active_app['employer']} • {active_app['tenure_months']} Months Tenure</span>
</div>
<div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.4rem;">
{status_pill}
{risk_pill}
</div>
</div>

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.85rem; padding: 0.9rem; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 1.25rem; border: 1px solid var(--border);">
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Sanctioned Amount</div>
<div class="font-mono" style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary);">₹{active_app['loan_amount']:,.0f}</div>
</div>
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Computed EMI</div>
<div class="font-mono" style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary);">₹64,580/mo</div>
</div>
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase; font-weight: 600;">Sanction Date</div>
<div class="font-mono" style="font-size: 0.95rem; font-weight: 600; color: var(--text-secondary);">{active_app['submission_date']}</div>
</div>
</div>

<div style="display: flex; justify-content: space-between; align-items: center;">
<span style="font-size: 0.78rem; color: var(--text-secondary);">Automated disbursement protocol completed</span>
</div>
</div>
""")

        if st.button("View Detailed Assessment Memo →", key="btn_view_full_result", use_container_width=True):
            navigate_user("result", app_id=active_app['id'])

        render_section_gap()
        render_html('<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin-bottom: 1rem; letter-spacing: -0.02em; font-family: var(--font-heading);">Recent Milestones & Activity</h3>')
        
        timeline_html = '<div style="display: flex; flex-direction: column; gap: 0.65rem;">'
        for event in active_app.get("timeline", []):
            timeline_html += f"""
<div style="display: flex; align-items: center; justify-content: space-between; padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 6px;">
<div style="display: flex; align-items: center; gap: 0.75rem;">
<span class="risk-dot low"></span>
<span style="font-size: 0.84rem; font-weight: 600; color: var(--text-primary);">{event['title']}</span>
</div>
<span class="font-mono" style="font-size: 0.72rem; color: var(--text-muted);">{event['time']}</span>
</div>
"""
        timeline_html += '</div>'
        render_html(timeline_html)

    with col_right:
        render_html('<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin-bottom: 1rem; letter-spacing: -0.02em; font-family: var(--font-heading);">Credit Factor Breakdown</h3>')
        
        # Render score card
        render_html(render_score_card(
            score=742,
            risk_category="Low Risk",
            default_prob=0.12,
            compact=True
        ))

        render_module_gap()
        render_html('<div style="font-size: 0.74rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); letter-spacing: 0.06em; margin-bottom: 0.6rem; font-family: var(--font-mono);">Key Contributing Drivers</div>')

        for factor in active_app.get("risk_factors", [])[:4]:
            render_html(render_factor_row(factor))
