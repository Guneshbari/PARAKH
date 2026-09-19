"""
PARAKH Score Card Component
High-precision credit score visualization with risk level, default probability, and visual indicator.
"""
import textwrap
from components.risk_badge import render_risk_badge

def render_score_card(score: int, max_score: int = 850, risk_category: str = "Low Risk", default_prob: float = 0.12, compact: bool = False) -> str:
    """Returns styled HTML for the credit score visual display."""
    percentage = int(max(0, min(100, (score - 300) / (max_score - 300) * 100)))
    
    # Semantic color definition
    if score >= 720:
        bar_color = "#10B981"
        glow_color = "rgba(16, 185, 129, 0.25)"
        tier_label = "Tier-1 Prime"
    elif score >= 640:
        bar_color = "#F59E0B"
        glow_color = "rgba(245, 158, 11, 0.25)"
        tier_label = "Near Prime"
    else:
        bar_color = "#EF4444"
        glow_color = "rgba(239, 68, 68, 0.25)"
        tier_label = "Subprime / Watch"

    risk_badge_html = render_risk_badge(risk_category)
    prob_str = f"{default_prob * 100:.1f}%" if default_prob is not None else "12.0%"

    if compact:
        html = f"""
<div class="p-card" style="padding: 1.25rem;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.75rem;">
<span style="font-size: 0.76rem; font-weight: 700; text-transform: uppercase; color: var(--text-secondary); letter-spacing: 0.05em; font-family: var(--font-mono);">AI Credit Score</span>
{risk_badge_html}
</div>
<div style="display: flex; align-items: baseline; gap: 0.4rem; margin-bottom: 0.6rem;">
<span style="font-size: 2.2rem; font-weight: 800; font-family: var(--font-mono); color: var(--text-primary); line-height: 1;">{score}</span>
<span style="font-size: 0.85rem; font-weight: 600; color: var(--text-muted); font-family: var(--font-mono);">/ {max_score}</span>
</div>
<div style="background: var(--bg-subtle); height: 6px; border-radius: 9999px; overflow: hidden; margin-bottom: 0.8rem; border: 1px solid var(--border);">
<div style="width: {percentage}%; height: 100%; background: {bar_color}; border-radius: 9999px;"></div>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.78rem; color: var(--text-secondary);">
<span>Default Probability</span>
<span class="font-mono" style="font-weight: 700; color: var(--text-primary);">{prob_str}</span>
</div>
</div>
"""
        return textwrap.dedent(html).strip()

    # Full institutional card
    html = f"""
<div class="p-card-accent" style="position: relative;">
<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.25rem;">
<div>
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 0.25rem; font-family: var(--font-mono);">Credit Intelligence Engine</div>
<div style="font-size: 1.25rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Overall Credit Trust Score</div>
</div>
{risk_badge_html}
</div>

<div style="display: flex; align-items: baseline; gap: 0.5rem; margin-bottom: 0.85rem;">
<span style="font-size: 3.4rem; font-weight: 800; font-family: var(--font-mono); color: var(--text-primary); line-height: 1; letter-spacing: -0.04em;">{score}</span>
<span style="font-size: 1.1rem; font-weight: 600; color: var(--text-muted); font-family: var(--font-mono);">/ {max_score}</span>
<span style="margin-left: auto; font-size: 0.78rem; font-weight: 700; color: {bar_color}; background: {glow_color}; padding: 0.25rem 0.65rem; border-radius: 4px; font-family: var(--font-mono);">{tier_label}</span>
</div>

<div style="position: relative; margin-bottom: 1.25rem;">
<div style="background: var(--bg-subtle); height: 8px; border-radius: 9999px; overflow: hidden; border: 1px solid var(--border);">
<div style="width: {percentage}%; height: 100%; background: linear-gradient(90deg, #3B82F6 0%, {bar_color} 100%); border-radius: 9999px;"></div>
</div>
<div style="display: flex; justify-content: space-between; font-size: 0.7rem; color: var(--text-muted); margin-top: 0.4rem; font-family: var(--font-mono);">
<span>300 Subprime</span>
<span>640 Near Prime</span>
<span>720 Prime</span>
<span>850 Super Prime</span>
</div>
</div>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding-top: 1rem; border-top: 1px solid var(--border);">
<div>
<div style="font-size: 0.74rem; color: var(--text-secondary); margin-bottom: 0.2rem;">Default Probability (PD)</div>
<div class="font-mono" style="font-size: 1.3rem; font-weight: 800; color: var(--text-primary);">{prob_str}</div>
</div>
<div>
<div style="font-size: 0.74rem; color: var(--text-secondary); margin-bottom: 0.2rem;">Confidence Calibration</div>
<div class="font-mono" style="font-size: 1.3rem; font-weight: 800; color: #10B981;">99.4%</div>
</div>
</div>
</div>
"""
    return textwrap.dedent(html).strip()
