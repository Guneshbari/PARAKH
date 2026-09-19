"""
PARAKH Admin Portal - Credit Analyst Workspace & Intelligence Dashboard
Executive portfolio oversight with neural risk monitoring, interactive volume trends, risk distribution, and critical alerts.
"""
import streamlit as st
from utils.mock_data import ADMIN_PORTFOLIO_METRICS, MOCK_APPLICATIONS, get_portfolio_trends, MODEL_INSIGHTS_DATA
from utils.navigation import navigate_admin
from utils.styling import render_html, render_section_gap, render_module_gap
from components.cards import render_kpi_card
from components.charts import create_portfolio_trend_chart, create_risk_distribution_donut
from components.tables import render_applications_table

def render_admin_dashboard():
    """Renders the institutional credit risk workspace."""
    theme = st.session_state.get("theme", "dark")
    kpis = ADMIN_PORTFOLIO_METRICS

    # Top Header
    h_col1, h_col2 = st.columns([2.5, 1.2])
    with h_col1:
        render_html("""
<div style="margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;">
<span style="display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.2rem 0.55rem; background: rgba(59,130,246,0.12); color: var(--accent); border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; font-family: var(--font-mono);">
<span style="width: 6px; height: 6px; border-radius: 50%; background: var(--accent);"></span>
Underwriting Command Center
</span>
<span class="mock-badge">Simulated Book · Demo</span>
</div>
<h1 style="font-size: 2.1rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">
Credit Intelligence Workspace
</h1>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
Supervising institutional originations, risk migrations, and autonomous decision policies.
</p>
</div>
""")

    with h_col2:
        render_html("""
<div style="background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 0.85rem 1rem; text-align: right; box-shadow: var(--card-shadow);">
<div style="font-size: 0.7rem; font-weight: 700; text-transform: uppercase; color: var(--text-muted); font-family: var(--font-mono);">Active Underwriter</div>
<div style="font-size: 0.95rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Sarah Jenkins</div>
<div style="font-size: 0.74rem; color: #10B981; font-weight: 600; font-family: var(--font-mono);">Discretionary Authority L4</div>
</div>
""")

    # 1. Executive Metric Row
    m1, m2, m3, m4 = st.columns(4, gap="small")
    with m1:
        render_html(render_kpi_card("Total Originations", f"{kpis['total_applications']:,}", delta=kpis["total_applications_growth"], delta_type="positive"))
    with m2:
        render_html(render_kpi_card("Queue Under Review", str(kpis["under_review_count"]), delta="4 Critical", delta_type="neutral"))
    with m3:
        render_html(render_kpi_card("Approval Rate", kpis["approval_rate"], delta="Benchmark: 70%", delta_type="positive"))
    with m4:
        render_html(render_kpi_card("High Risk Flagged", f"{kpis['high_risk_flagged']} ({kpis['high_risk_rate']})", delta="-1.2% MoM", delta_type="positive"))

    render_section_gap()

    # 2. Charts Row: Origination Trends + Risk Distribution Donut
    c_left, c_right = st.columns([1.6, 1], gap="large")
    
    with c_left:
        render_html("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin: 0; font-family: var(--font-heading);">Portfolio Inflow & Decision Velocity</h3>
<span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">Trailing 6 Months</span>
</div>
""")
        trends_df = get_portfolio_trends()
        fig_trend = create_portfolio_trend_chart(trends_df, theme=theme)
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    with c_right:
        render_html("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin: 0; font-family: var(--font-heading);">Risk Tier Segmentation</h3>
<span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">Active Book</span>
</div>
""")
        fig_donut = create_risk_distribution_donut(MODEL_INSIGHTS_DATA["risk_distribution"], theme=theme)
        st.plotly_chart(fig_donut, use_container_width=True, config={"displayModeBar": False})

    render_section_gap()

    # 3. Critical Risk Alerts Section
    render_html("""
<div class="p-card" style="border-left: 3px solid #EF4444; margin-bottom: 1.75rem;">
<div style="display: flex; align-items: center; justify-content: space-between;">
<div style="display: flex; align-items: center; gap: 0.75rem;">
<span class="risk-dot high"></span>
<div>
<span style="font-size: 0.88rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">High Risk Alert: Unusual Delinquency Spike in Retail Commodities Sector</span>
<div style="font-size: 0.78rem; color: var(--text-secondary); margin-top: 0.15rem;">Application PRK-2026-8946 flagged with 91% revolving credit utilization and 7 hard inquiries in 90 days.</div>
</div>
</div>
<span class="font-mono" style="font-size: 0.72rem; font-weight: 700; color: #EF4444; background: rgba(239,68,68,0.1); padding: 0.25rem 0.6rem; border-radius: 4px;">HIGH PRIORITY</span>
</div>
</div>
""")

    # 4. Applications Registry Preview & Quick Review Queue
    render_html("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
<div>
<h3 style="font-size: 1.15rem; font-weight: 800; color: var(--text-primary); margin: 0; font-family: var(--font-heading);">Underwriting Review Queue</h3>
<span style="font-size: 0.8rem; color: var(--text-secondary);">Direct pipeline requiring analyst sign-off or policy override</span>
</div>
</div>
""")

    # Show top applications
    render_applications_table(MOCK_APPLICATIONS[:4], is_admin=True)

    render_module_gap()
    if st.button("Open Full Applications Registry (1,482) →", key="btn_admin_full_reg", use_container_width=True):
        navigate_admin("applications")
