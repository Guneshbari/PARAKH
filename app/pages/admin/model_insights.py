"""
PARAKH Admin Portal - Model Governance & Neural Explainability (XAI)
Model audit workstation: simulated validation metrics, ROC curves, global SHAP weights, and bias monitoring.
"""
import streamlit as st
from utils.mock_data import MODEL_INSIGHTS_DATA, get_roc_curve_data
from utils.styling import get_theme_colors, render_html, render_section_gap
from components.cards import render_kpi_card
from components.charts import create_feature_importance_chart, create_roc_curve_chart

def render_admin_model_insights():
    """Renders the comprehensive model governance and explainability workspace."""
    theme = st.session_state.get("theme", "dark")
    c = get_theme_colors(theme)
    m = MODEL_INSIGHTS_DATA

    render_html(f"""
<div style="margin-bottom: 1.5rem;">
<div style="display: flex; align-items: center; gap: 0.6rem; margin-bottom: 0.3rem;">
<span style="display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.2rem 0.55rem; background: rgba(16,185,129,0.12); color: #10B981; border-radius: 4px; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; font-family: var(--font-mono);">
<span style="width: 6px; height: 6px; border-radius: 50%; background: #10B981;"></span>
Model Registry: Simulated Production Book
</span>
<span class="mock-badge">DEMO / MOCK DATA ONLY</span>
</div>
<h1 style="font-size: 2.1rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">
Neural Model Governance & Explainability
</h1>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">
Simulated validation benchmarks for {m['model_name']}. All metrics represent synthetic evaluation telemetry.
</p>
</div>
""")

    # 1. Statistical Validation KPIs (Clearly labeled as DEMO / MOCK DATA)
    m1, m2, m3, m4 = st.columns(4, gap="small")
    with m1:
        render_html(render_kpi_card("AUC-ROC (Demo)", f"{m['auc_roc']:.3f}", delta="Demonstration Metric", delta_type="positive"))
    with m2:
        render_html(render_kpi_card("F1-Score (Demo)", f"{m['f1_score']:.3f}", delta="Demonstration Metric", delta_type="positive"))
    with m3:
        render_html(render_kpi_card("KS Statistic (Demo)", f"{m['ks_statistic']}", delta="Demonstration Metric", delta_type="positive"))
    with m4:
        render_html(render_kpi_card("Stability PSI (Demo)", f"{m['psi_stability']}", delta="Demonstration Metric", delta_type="positive", note="PSI < 0.10 is stable"))

    render_section_gap()

    # 2. Charts Row: Global Feature Importance vs ROC Curve
    col_c1, col_c2 = st.columns([1.2, 1], gap="large")

    with col_c1:
        render_html("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
<h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin: 0; font-family: var(--font-heading);">Global Feature Attribution (Mean |SHAP| - Demo)</h4>
<span style="font-size: 0.72rem; color: var(--text-muted); font-family: var(--font-mono);">Simulated N=120k</span>
</div>
""")
        fig_feat = create_feature_importance_chart(m["feature_importances"], theme=theme)
        st.plotly_chart(fig_feat, use_container_width=True, config={"displayModeBar": False})

    with col_c2:
        render_html("""
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
<h4 style="font-size: 1.05rem; font-weight: 800; color: var(--text-primary); margin: 0; font-family: var(--font-heading);">Receiver Operating Characteristic (ROC - Demo)</h4>
<span class="font-mono" style="font-size: 0.72rem; color: #10B981; font-weight: 700;">Simulated AUC = 0.942</span>
</div>
""")
        fpr, tpr = get_roc_curve_data()
        fig_roc = create_roc_curve_chart(fpr, tpr, m["auc_roc"], theme=theme)
        st.plotly_chart(fig_roc, use_container_width=True, config={"displayModeBar": False})

    render_section_gap()

    # 3. Model Governance, Fairness, & Regulatory Audit (Clearly labeled as DEMO / MOCK DATA)
    render_html("""
<div class="p-card-static" style="padding: 1.5rem;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
<div>
<div style="display: flex; align-items: center; gap: 0.5rem;">
<h4 style="margin: 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Fairness, Ethics & Regulatory Audit</h4>
<span class="mock-badge">DEMO / MOCK DATA</span>
</div>
<span style="font-size: 0.8rem; color: var(--text-secondary);">Simulated compliance with Digital Lending Guidelines & Fair Lending Mandates</span>
</div>
<span style="background: rgba(16,185,129,0.12); color: #10B981; font-weight: 700; font-size: 0.74rem; padding: 0.25rem 0.65rem; border-radius: 4px; border: 1px solid rgba(16,185,129,0.28); font-family: var(--font-mono);">
✓ AUDIT DEMO PASSED
</span>
</div>

<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem;">
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Demographic Parity (Mock)</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: #10B981;">0.982</div>
<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.2rem;">Permissible: 0.80 - 1.25</div>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Equal Opportunity (Mock)</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: #10B981;">0.014</div>
<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.2rem;">Permissible: &lt; 0.05</div>
</div>
<div style="padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Expected Calibration (Mock)</div>
<div class="font-mono" style="font-size: 1.25rem; font-weight: 800; color: #10B981;">0.018</div>
<div style="font-size: 0.72rem; color: var(--text-secondary); margin-top: 0.2rem;">Synthetic ECE test</div>
</div>
</div>
</div>
""")
