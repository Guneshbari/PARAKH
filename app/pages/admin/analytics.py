"""
PARAKH Admin Portal - Portfolio Analytics & Underwriting Telemetry
In-depth institutional analysis of portfolio origination volume, risk migration, and approval efficiencies.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.styling import get_theme_colors, render_html, render_section_gap
from components.cards import render_kpi_card
from utils.mock_data import ADMIN_PORTFOLIO_METRICS

def render_admin_analytics():
    """Renders the comprehensive portfolio analytics dashboard."""
    theme = st.session_state.get("theme", "dark")
    c = get_theme_colors(theme)
    kpis = ADMIN_PORTFOLIO_METRICS

    render_html("""
<div style="margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;">
<span style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-family: var(--font-mono);">Macro Portfolio Telemetry</span>
<span class="mock-badge">Demo / Mock Data</span>
</div>
<h1 style="font-size: 2.1rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">Portfolio Analytics</h1>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">Real-time originations distribution, exposure concentration, and simulated risk migration dynamics.</p>
</div>
""")

    # Macro KPI Row
    m1, m2, m3, m4 = st.columns(4, gap="small")
    with m1:
        render_html(render_kpi_card("Capital Deployed", kpis["portfolio_capital_deployed"], delta="+₹6.2 Cr QoQ", delta_type="positive"))
    with m2:
        render_html(render_kpi_card("Default Rate (90+ DPD)", kpis["portfolio_default_rate"], delta="-0.4% vs Industry", delta_type="positive"))
    with m3:
        render_html(render_kpi_card("Avg Underwrite Latency", kpis["avg_decision_latency"], delta="vs 48 hrs Manual", delta_type="positive"))
    with m4:
        render_html(render_kpi_card("Mean Bureau Score", str(kpis["avg_credit_score"]), delta="+6 pts MoM", delta_type="positive"))

    render_section_gap()

    # First Chart Row: Approval Rate by Income Tier + Loan Purpose Exposure
    col_a1, col_a2 = st.columns(2, gap="large")

    with col_a1:
        render_html('<h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.5rem; font-family: var(--font-heading);">Approval Rate by Monthly Income Bracket (Simulated)</h4>')
        
        income_df = pd.DataFrame({
            "Bracket": ["< ₹50k", "₹50k - ₹1.2L", "₹1.2L - ₹2.5L", "₹2.5L - ₹5L", "> ₹5L"],
            "Approval Rate (%)": [38.2, 64.5, 82.1, 91.4, 96.8]
        })

        fig_inc = go.Figure(go.Bar(
            x=income_df["Bracket"],
            y=income_df["Approval Rate (%)"],
            marker=dict(color=c["accent"], line=dict(width=0)),
            text=[f"{v}%" for v in income_df["Approval Rate (%)"]],
            textposition="outside",
            textfont=dict(color=c["text_primary"], family="JetBrains Mono", size=10)
        ))
        fig_inc.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=260,
            margin=dict(l=20, r=20, t=20, b=20),
            yaxis=dict(range=[0, 110], showgrid=True, gridcolor=c["border"], color=c["text_muted"]),
            xaxis=dict(showgrid=False, color=c["text_muted"])
        )
        st.plotly_chart(fig_inc, use_container_width=True, config={"displayModeBar": False})

    with col_a2:
        render_html('<h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin-bottom: 0.5rem; font-family: var(--font-heading);">Loan Exposure by Capital Purpose (Simulated)</h4>')
        
        purpose_df = pd.DataFrame({
            "Purpose": ["Home & Solar", "Working Capital", "Education", "Equipment", "Emergency"],
            "Volume (₹ Cr)": [18.4, 12.6, 5.2, 4.8, 1.8]
        })

        fig_pur = go.Figure(go.Pie(
            labels=purpose_df["Purpose"],
            values=purpose_df["Volume (₹ Cr)"],
            hole=0.6,
            marker=dict(colors=["#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#CBD5E1"], line=dict(color=c["surface"], width=2)),
            textinfo="label+percent",
            textfont=dict(color="#FFFFFF", size=10)
        ))
        fig_pur.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            height=260,
            showlegend=False,
            margin=dict(l=20, r=20, t=20, b=20)
        )
        st.plotly_chart(fig_pur, use_container_width=True, config={"displayModeBar": False})

    render_section_gap()

    # Second Section: Geographic & Segment Concentration
    render_html("""
<div class="p-card-static" style="padding: 1.5rem;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
<h4 style="margin: 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Regional Concentration & Risk Migration</h4>
<span class="mock-badge">Demo / Mock Data</span>
</div>
<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem;">
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Bengaluru Hub</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin: 0.25rem 0;">₹16.4 Cr</div>
<span style="font-size: 0.72rem; color: #10B981; font-weight: 700; font-family: var(--font-mono);">Default: 1.4% (Prime)</span>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Mumbai MMR</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin: 0.25rem 0;">₹13.8 Cr</div>
<span style="font-size: 0.72rem; color: #10B981; font-weight: 700; font-family: var(--font-mono);">Default: 1.8% (Prime)</span>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Delhi NCR</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin: 0.25rem 0;">₹8.2 Cr</div>
<span style="font-size: 0.72rem; color: #F59E0B; font-weight: 700; font-family: var(--font-mono);">Default: 2.7% (Moderate)</span>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Hyderabad & Pune</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); margin: 0.25rem 0;">₹4.4 Cr</div>
<span style="font-size: 0.72rem; color: #10B981; font-weight: 700; font-family: var(--font-mono);">Default: 1.9% (Prime)</span>
</div>
</div>
</div>
""")
