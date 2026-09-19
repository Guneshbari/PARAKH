"""
PARAKH User Portal - Profile & Account Settings
Clean, institutional user profile page with verified KYC badge, linked financial entities, and security preferences.
"""
import streamlit as st
from utils.mock_data import USER_PROFILE
from utils.navigation import toggle_theme
from utils.styling import render_html

def render_user_profile():
    """Renders the User Profile and Account Management view."""
    p = USER_PROFILE
    theme = st.session_state.get("theme", "dark")

    render_html("""
<div style="margin-bottom: 1.5rem;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); font-family: var(--font-mono);">Account & Compliance</div>
<h2 style="font-size: 1.85rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">Borrower Profile & Credentials</h2>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.25rem;">Manage verified identity credentials, banking linkages, and telemetry security.</p>
</div>
""")

    p_cols = st.columns([1.1, 1.4], gap="large")

    with p_cols[0]:
        render_html(f"""
<div class="p-card-static" style="text-align: center; padding: 1.75rem 1.5rem;">
<div style="width: 64px; height: 64px; border-radius: 50%; background: #3B82F6; color: #FFFFFF; display: flex; align-items: center; justify-content: center; font-size: 1.6rem; font-weight: 800; margin: 0 auto 1rem auto; box-shadow: 0 0 15px rgba(59,130,246,0.3); font-family: var(--font-heading);">
AM
</div>
<h3 style="margin: 0; font-size: 1.3rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">{p['name']}</h3>
<span style="font-size: 0.85rem; color: var(--text-secondary);">{p['occupation']}</span>

<div style="margin-top: 0.85rem; display: inline-flex; align-items: center; gap: 0.4rem; padding: 0.25rem 0.65rem; background: rgba(16,185,129,0.12); color: #10B981; border: 1px solid rgba(16,185,129,0.28); border-radius: 4px; font-size: 0.72rem; font-weight: 700; font-family: var(--font-mono);">
<span>✓</span> {p['kyc_status']}
</div>

<div class="divider-line"></div>

<div style="text-align: left; display: flex; flex-direction: column; gap: 0.75rem; font-size: 0.84rem;">
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">Email</span>
<span style="font-weight: 600; color: var(--text-primary);">{p['email']}</span>
</div>
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">Mobile Contact</span>
<span class="font-mono" style="font-weight: 600; color: var(--text-primary);">{p['phone']}</span>
</div>
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">PAN Identifier</span>
<span class="font-mono" style="font-weight: 700; color: var(--accent);">{p['pan_card']}</span>
</div>
<div style="display: flex; justify-content: space-between;">
<span style="color: var(--text-secondary);">Masked Aadhaar</span>
<span class="font-mono" style="font-weight: 600; color: var(--text-primary);">{p['aadhaar_masked']}</span>
</div>
</div>
</div>
""")

    with p_cols[1]:
        render_html("""
<div class="p-card-static" style="padding: 1.5rem; margin-bottom: 1.25rem;">
<h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Financial Telemetry Linkages</h4>
<div style="display: flex; flex-direction: column; gap: 0.75rem;">
<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div>
<div style="font-weight: 700; font-size: 0.86rem; color: var(--text-primary);">HDFC Bank (Salary Account)</div>
<div style="font-size: 0.72rem; color: var(--text-secondary);">Account ending in **9012 • Auto-Consent Active</div>
</div>
<span style="font-size: 0.72rem; font-weight: 700; color: #10B981; font-family: var(--font-mono);">CONNECTED</span>
</div>
<div style="display: flex; justify-content: space-between; align-items: center; padding: 0.75rem 0.85rem; background: var(--bg-subtle); border-radius: 6px; border: 1px solid var(--border);">
<div>
<div style="font-weight: 700; font-size: 0.86rem; color: var(--text-primary);">ICICI Direct (Portfolio & Demat)</div>
<div style="font-size: 0.72rem; color: var(--text-secondary);">Collateral Pool Evaluated • Real-time Valuation</div>
</div>
<span style="font-size: 0.72rem; font-weight: 700; color: #10B981; font-family: var(--font-mono);">CONNECTED</span>
</div>
</div>
</div>
""")

        render_html("""
<div class="p-card-static" style="padding: 1.5rem;">
<h4 style="margin: 0 0 1rem 0; font-size: 1.1rem; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Preferences & UI Customization</h4>
</div>
""")

        col_pref1, col_pref2 = st.columns(2)
        with col_pref1:
            st.markdown(f"**Current Theme:** `{theme.capitalize()} Mode`")
            if st.button("Toggle Theme", key="prof_toggle_theme", use_container_width=True):
                toggle_theme()
        with col_pref2:
            st.checkbox("Real-time SMS Risk Alerts", value=True)
            st.checkbox("Automated Bureau Refresh Sync", value=True)
