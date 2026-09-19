"""
PARAKH Reusable Cards & Container Components
Clean fintech cards with micro-interactions, responsive typography, and subtle boundaries.
"""
import textwrap
from components.risk_badge import render_risk_badge, render_status_pill

def render_kpi_card(title: str, value: str, delta: str = None, delta_type: str = "positive", note: str = "") -> str:
    """Renders a modern fintech KPI card with clean typography."""
    delta_class = "positive" if delta_type == "positive" else ("negative" if delta_type == "negative" else "neutral")
    delta_arrow = "↑" if delta_type == "positive" else ("↓" if delta_type == "negative" else "•")
    
    delta_html = ""
    if delta:
        delta_html = f'<div class="kpi-delta {delta_class}"><span>{delta_arrow}</span><span>{delta}</span></div>'
        
    note_html = f'<div style="font-size: 0.72rem; color: var(--text-muted); margin-top: 0.25rem;">{note}</div>' if note else ""

    html = f"""
<div class="kpi-card">
<div class="kpi-label">{title}</div>
<div class="kpi-value">{value}</div>
<div style="display: flex; align-items: center; justify-content: space-between; min-height: 24px;">
{delta_html}
{note_html}
</div>
</div>
"""
    return textwrap.dedent(html).strip()


def render_application_summary_card(app_data: dict) -> str:
    """Renders a rich preview card for an active or highlighted application."""
    app_id = app_data.get("id", "PRK-2026-XXXX")
    name = app_data.get("applicant_name", "Applicant")
    amount = app_data.get("loan_amount", 0)
    purpose = app_data.get("loan_purpose", "Credit Facility")
    status = app_data.get("status", "Pending")
    risk_cat = app_data.get("risk_category", "Low Risk")
    date = app_data.get("submission_date", "2026-09-18")
    score = app_data.get("credit_score", 700)

    status_html = render_status_pill(status)
    risk_html = render_risk_badge(risk_cat)

    html = f"""
<div class="p-card">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1rem;">
<div>
<span class="font-mono" style="font-size: 0.74rem; font-weight: 700; color: var(--accent); letter-spacing: 0.04em;">{app_id}</span>
<h3 style="margin: 0.2rem 0 0 0; font-size: 1.15rem; font-weight: 700; color: var(--text-primary);">{name}</h3>
<span style="font-size: 0.8rem; color: var(--text-secondary);">{purpose}</span>
</div>
<div style="display: flex; flex-direction: column; align-items: flex-end; gap: 0.4rem;">
{status_html}
{risk_html}
</div>
</div>

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 0.75rem; padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; margin-bottom: 0.5rem; border: 1px solid var(--border);">
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Facility Request</div>
<div class="font-mono" style="font-size: 0.95rem; font-weight: 700; color: var(--text-primary);">₹{amount:,.0f}</div>
</div>
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Credit Score</div>
<div class="font-mono" style="font-size: 0.95rem; font-weight: 700; color: var(--accent);">{score}</div>
</div>
<div>
<div style="font-size: 0.7rem; color: var(--text-muted); text-transform: uppercase;">Submitted</div>
<div class="font-mono" style="font-size: 0.85rem; font-weight: 600; color: var(--text-secondary);">{date}</div>
</div>
</div>
</div>
"""
    return textwrap.dedent(html).strip()


def render_factor_row(factor: dict) -> str:
    """Renders a single SHAP factor with visual bar and delta."""
    feature = factor.get("feature", "")
    impact = factor.get("impact", 0.0)
    detail = factor.get("detail", "")
    is_positive = impact >= 0
    
    color = "#10B981" if is_positive else "#EF4444"
    bg_subtle = "rgba(16, 185, 129, 0.1)" if is_positive else "rgba(239, 68, 68, 0.1)"
    sign = "+" if is_positive else ""
    impact_str = f"{sign}{impact*100:.1f} pts"
    bar_width = int(min(100, abs(impact) * 220))

    html = f"""
<div style="padding: 0.75rem 1rem; background: var(--surface); border: 1px solid var(--border); border-radius: 6px; margin-bottom: 0.6rem; transition: all 0.2s ease;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
<span style="font-size: 0.85rem; font-weight: 600; color: var(--text-primary);">{feature}</span>
<span class="font-mono" style="font-size: 0.78rem; font-weight: 700; color: {color}; background: {bg_subtle}; padding: 0.2rem 0.5rem; border-radius: 4px;">{impact_str}</span>
</div>
<div style="display: flex; align-items: center; gap: 0.75rem;">
<div style="flex-grow: 1; background: var(--bg-subtle); height: 4px; border-radius: 9999px; overflow: hidden;">
<div style="width: {bar_width}%; height: 100%; background: {color}; border-radius: 9999px;"></div>
</div>
<span style="font-size: 0.74rem; color: var(--text-secondary); white-space: nowrap;">{detail}</span>
</div>
</div>
"""
    return textwrap.dedent(html).strip()


def render_ai_memo_card(memo_text: str, title: str = "PARAKH Neural Credit Assessment Memo") -> str:
    """Renders the AI generated credit memo with institutional formatting."""
    html = f"""
<div style="background: var(--surface); border: 1px solid var(--border); border-left: 3px solid var(--accent); border-radius: 8px; padding: 1.25rem 1.4rem; margin-bottom: 1.5rem; box-shadow: var(--card-shadow);">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.75rem;">
<span style="background: var(--accent-subtle); color: var(--accent); font-weight: 700; font-size: 0.72rem; padding: 0.2rem 0.55rem; border-radius: 4px; letter-spacing: 0.05em; text-transform: uppercase; font-family: var(--font-mono);">AI Synthesis</span>
<span style="font-size: 0.86rem; font-weight: 700; color: var(--text-primary); font-family: var(--font-heading);">{title}</span>
<span class="mock-badge" style="margin-left: auto;">Demo / Mock Data</span>
</div>
<p style="margin: 0; font-size: 0.9rem; line-height: 1.65; color: var(--text-secondary);">
"{memo_text}"
</p>
<div style="display: flex; align-items: center; justify-content: space-between; margin-top: 0.9rem; padding-top: 0.65rem; border-top: 1px dashed var(--border); font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono);">
<span>Model: XGB-TabNet Ensemble v3.4</span>
<span>Fairness & Determinism Validated</span>
</div>
</div>
"""
    return textwrap.dedent(html).strip()
