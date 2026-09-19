"""
PARAKH Risk Badge Component
Renders semantic risk indicators (Low, Medium, High Risk) with micro-dots and accessible contrast.
"""
import textwrap

def render_risk_badge(risk_category: str, show_dot: bool = True) -> str:
    """Returns clean HTML for a risk badge based on category string."""
    cat_lower = (risk_category or "").lower()
    
    if "low" in cat_lower:
        badge_class = "low"
        dot_class = "low"
        label = "Low Risk"
    elif "medium" in cat_lower or "moderate" in cat_lower:
        badge_class = "medium"
        dot_class = "medium"
        label = "Medium Risk"
    elif "high" in cat_lower:
        badge_class = "high"
        dot_class = "high"
        label = "High Risk"
    else:
        badge_class = "neutral"
        dot_class = "neutral"
        label = risk_category or "Neutral"
        
    dot_html = f'<span class="risk-dot {dot_class}"></span>' if show_dot else ""
    html = f'<div class="risk-badge {badge_class}">{dot_html}<span>{label}</span></div>'
    return textwrap.dedent(html).strip()


def render_status_pill(status: str) -> str:
    """Returns clean HTML for an application status pill."""
    status_lower = (status or "").lower()
    
    if "approved" in status_lower:
        style = "background: rgba(16, 185, 129, 0.12); color: #10B981; border: 1px solid rgba(16, 185, 129, 0.28);"
    elif "review" in status_lower or "pending" in status_lower:
        style = "background: rgba(245, 158, 11, 0.12); color: #F59E0B; border: 1px solid rgba(245, 158, 11, 0.28);"
    elif "high" in status_lower or "reject" in status_lower or "flag" in status_lower:
        style = "background: rgba(239, 68, 68, 0.12); color: #EF4444; border: 1px solid rgba(239, 68, 68, 0.28);"
    else:
        style = "background: rgba(148, 163, 184, 0.12); color: #94A3B8; border: 1px solid var(--border);"
        
    html = f'<span style="display:inline-flex; align-items:center; padding: 0.25rem 0.6rem; border-radius: 4px; font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; {style}">{status}</span>'
    return textwrap.dedent(html).strip()
