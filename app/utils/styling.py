"""
PARAKH Design System & Styling Engine
Institutional Sovereign fintech design direction inspired by high-density trading consoles and Noiz.ai.
Features floating glassmorphism navbar and precision theme slider toggle.
"""
import textwrap
import streamlit as st

def get_theme_colors(theme: str = "dark") -> dict:
    """Returns the color tokens for the specified theme."""
    if theme == "light":
        return {
            "theme": "light",
            "bg": "#F7F8FA",
            "bg_subtle": "#EDF0F5",
            "surface": "#FFFFFF",
            "surface_hover": "#F8FAFC",
            "surface_elevated": "#FFFFFF",
            "border": "#E2E8F0",
            "border_focus": "#2563EB",
            "text_primary": "#0F172A",
            "text_secondary": "#475569",
            "text_muted": "#94A3B8",
            "accent": "#2563EB",
            "accent_hover": "#1D4ED8",
            "accent_subtle": "#EFF6FF",
            "accent_glow": "rgba(37, 99, 235, 0.15)",
            "success": "#059669",
            "success_subtle": "#ECFDF5",
            "success_border": "#A7F3D0",
            "warning": "#D97706",
            "warning_subtle": "#FFFBEB",
            "warning_border": "#FDE68A",
            "danger": "#DC2626",
            "danger_subtle": "#FEF2F2",
            "danger_border": "#FECACA",
            "card_shadow": "0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.03)",
            "card_shadow_hover": "0 10px 25px -5px rgba(0, 0, 0, 0.08)",
            # Floating Glass Navbar Tokens (Light)
            "navbar_glass_bg": "rgba(255, 255, 255, 0.72)",
            "navbar_glass_border": "rgba(17, 24, 39, 0.08)",
            "navbar_glass_shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.06), 0 1px 2px 0 rgba(0, 0, 0, 0.04)",
            "nav_active_bg": "rgba(37, 99, 235, 0.08)",
            "nav_active_border": "rgba(37, 99, 235, 0.16)",
            "nav_hover_bg": "rgba(0, 0, 0, 0.04)",
            # Tactile Hardware Toggle Tokens (Light)
            "toggle_track_bg": "#E2E8F0",
            "toggle_track_border": "#CBD5E1",
            "toggle_track_shadow": "inset 0 2px 4px rgba(0, 0, 0, 0.08), 0 1px 2px rgba(255, 255, 255, 0.6)",
            "toggle_thumb_bg": "#FFFFFF",
            "toggle_thumb_border": "rgba(0, 0, 0, 0.08)",
            "toggle_thumb_shadow": "0 4px 10px rgba(0, 0, 0, 0.14), 0 1px 3px rgba(0, 0, 0, 0.08), inset 0 1px 1px rgba(255, 255, 255, 0.95)",
            "toggle_thumb_left": "-4px",
            "toggle_icon_svg": "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23F59E0B' stroke-width='2.2' stroke-linecap='round' stroke-linejoin='round'%3E%3Ccircle cx='12' cy='12' r='4'/%3E%3Cpath d='M12 2v2'/%3E%3Cpath d='M12 20v2'/%3E%3Cpath d='M4.93 4.93l1.41 1.41'/%3E%3Cpath d='M17.66 17.66l1.41 1.41'/%3E%3Cpath d='M2 12h2'/%3E%3Cpath d='M20 12h2'/%3E%3Cpath d='M6.34 17.66l-1.41 1.41'/%3E%3Cpath d='M19.07 4.93l-1.41 1.41'/%3E%3C/svg%3E\")",
            "sun_color": "#D97706",
            "moon_color": "#94A3B8",
        }
    else:  # Dark mode (default Institutional Sovereign)
        return {
            "theme": "dark",
            "bg": "#0B0F14",
            "bg_subtle": "#0E141B",
            "surface": "#111820",
            "surface_hover": "#16202C",
            "surface_elevated": "#182230",
            "border": "#1A2332",
            "border_focus": "#3B82F6",
            "text_primary": "#F1F5F9",
            "text_secondary": "#94A3B8",
            "text_muted": "#475569",
            "accent": "#3B82F6",
            "accent_hover": "#60A5FA",
            "accent_subtle": "rgba(59, 130, 246, 0.12)",
            "accent_glow": "rgba(59, 130, 246, 0.25)",
            "success": "#10B981",
            "success_subtle": "rgba(16, 185, 129, 0.12)",
            "success_border": "rgba(16, 185, 129, 0.28)",
            "warning": "#F59E0B",
            "warning_subtle": "rgba(245, 158, 11, 0.12)",
            "warning_border": "rgba(245, 158, 11, 0.28)",
            "danger": "#EF4444",
            "danger_subtle": "rgba(239, 68, 68, 0.12)",
            "danger_border": "rgba(239, 68, 68, 0.28)",
            "card_shadow": "0 2px 8px rgba(0, 0, 0, 0.35)",
            "card_shadow_hover": "0 12px 28px rgba(0, 0, 0, 0.55), 0 0 20px rgba(59, 130, 246, 0.12)",
            # Floating Glass Navbar Tokens (Dark)
            "navbar_glass_bg": "rgba(11, 15, 20, 0.72)",
            "navbar_glass_border": "rgba(255, 255, 255, 0.08)",
            "navbar_glass_shadow": "0 8px 32px 0 rgba(0, 0, 0, 0.37), 0 1px 2px 0 rgba(0, 0, 0, 0.2)",
            "nav_active_bg": "rgba(59, 130, 246, 0.15)",
            "nav_active_border": "rgba(59, 130, 246, 0.28)",
            "nav_hover_bg": "rgba(255, 255, 255, 0.05)",
            # Tactile Hardware Toggle Tokens (Dark)
            "toggle_track_bg": "#0E1520",
            "toggle_track_border": "#1E293B",
            "toggle_track_shadow": "inset 0 2px 5px rgba(0, 0, 0, 0.45), 0 1px 1px rgba(255, 255, 255, 0.05)",
            "toggle_thumb_bg": "#182230",
            "toggle_thumb_border": "rgba(255, 255, 255, 0.14)",
            "toggle_thumb_shadow": "0 4px 12px rgba(0, 0, 0, 0.5), 0 1px 3px rgba(0, 0, 0, 0.35), inset 0 1px 1px rgba(255, 255, 255, 0.2), 0 0 12px rgba(59, 130, 246, 0.28)",
            "toggle_thumb_left": "24px",
            "toggle_icon_svg": "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='15' height='15' viewBox='0 0 24 24' fill='%2360A5FA' stroke='%2360A5FA' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z'/%3E%3C/svg%3E\")",
            "sun_color": "#64748B",
            "moon_color": "#60A5FA",
        }


def render_html(html_str: str):
    """
    Safely renders custom HTML in Streamlit.
    Automatically dedents and strips the string to guarantee Markdown never parses
    indented lines as raw <pre><code> blocks.
    """
    cleaned = textwrap.dedent(html_str).strip()
    st.markdown(cleaned, unsafe_allow_html=True)


def render_section_gap():
    """Renders a standardized 32px vertical section spacer."""
    render_html('<div class="section-gap"></div>')


def render_module_gap():
    """Renders a standardized 20px vertical module spacer."""
    render_html('<div class="module-gap"></div>')


def get_global_css(theme: str = "dark") -> str:
    """Generates the full CSS stylesheet applied across the Streamlit application."""
    c = get_theme_colors(theme)
    
    return f"""
<style>
/* ==========================================================================
   Google Fonts: Plus Jakarta Sans (Headings), Inter (Body), JetBrains Mono (Financials)
   ========================================================================== */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

/* ==========================================================================
   Global Theme Variables
   ========================================================================== */
:root {{
    --font-sans: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --font-heading: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
    
    --bg: {c['bg']};
    --bg-subtle: {c['bg_subtle']};
    --surface: {c['surface']};
    --surface-hover: {c['surface_hover']};
    --surface-elevated: {c['surface_elevated']};
    --border: {c['border']};
    --border-focus: {c['border_focus']};
    
    --text-primary: {c['text_primary']};
    --text-secondary: {c['text_secondary']};
    --text-muted: {c['text_muted']};
    
    --accent: {c['accent']};
    --accent-hover: {c['accent_hover']};
    --accent-subtle: {c['accent_subtle']};
    --accent-glow: {c['accent_glow']};
    
    --success: {c['success']};
    --success-subtle: {c['success_subtle']};
    --success-border: {c['success_border']};
    
    --warning: {c['warning']};
    --warning-subtle: {c['warning_subtle']};
    --warning-border: {c['warning_border']};
    
    --danger: {c['danger']};
    --danger-subtle: {c['danger_subtle']};
    --danger-border: {c['danger_border']};
    
    --card-shadow: {c['card_shadow']};
    --card-shadow-hover: {c['card_shadow_hover']};

    /* Floating Glass Navbar Tokens */
    --navbar-glass-bg: {c['navbar_glass_bg']};
    --navbar-glass-border: {c['navbar_glass_border']};
    --navbar-glass-shadow: {c['navbar_glass_shadow']};
    --nav-active-bg: {c['nav_active_bg']};
    --nav-active-border: {c['nav_active_border']};
    --nav-hover-bg: {c['nav_hover_bg']};
    --toggle-track-bg: {c['toggle_track_bg']};
    --toggle-track-border: {c['toggle_track_border']};
    --toggle-thumb-bg: {c['toggle_thumb_bg']};
    --toggle-thumb-shadow: {c['toggle_thumb_shadow']};
}}

/* ==========================================================================
   Streamlit Default Overrides
   ========================================================================== */
html, body, [class*="css"], .stApp {{
    font-family: var(--font-sans) !important;
    background-color: var(--bg) !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.01em;
    -webkit-font-smoothing: antialiased;
}}

/* Hide Default Streamlit Header, Footer, and Sidebar Decoration */
header[data-testid="stHeader"] {{
    display: none !important;
}}
footer {{
    display: none !important;
}}
#MainMenu, [data-testid="stDecoration"] {{
    display: none !important;
}}

/* Hide Sidebar Completely */
[data-testid="stSidebar"] {{
    display: none !important;
}}

/* Layout Container Spacing (Standardized 1320px Global Content Grid) */
.block-container {{
    padding-top: 0.75rem !important;
    padding-bottom: 3.5rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 1320px !important;
    margin: 0 auto !important;
}}

@media (max-width: 768px) {{
    .block-container {{
        padding-left: 0.85rem !important;
        padding-right: 0.85rem !important;
        padding-top: 0.5rem !important;
    }}
}}

/* Standard Section & Module Spacing Utility Classes (Replaces manual div spacers) */
.section-gap {{
    margin-bottom: 2rem !important;
}}

.module-gap {{
    margin-bottom: 1.25rem !important;
}}

.submodule-gap {{
    margin-bottom: 0.75rem !important;
}}

/* ==========================================================================
   Keyframe Animations
   ========================================================================== */
@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(6px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

@keyframes pulseGlow {{
    0%, 100% {{ transform: scale(1); opacity: 1; }}
    50% {{ transform: scale(1.15); opacity: 0.75; }}
}}

.animate-fade-in {{
    animation: fadeIn 0.24s cubic-bezier(0.16, 1, 0.3, 1) forwards;
}}

/* ==========================================================================
   FLOATING GLASS NAVBAR ARCHITECTURE (Inspired by shadcn NavigationMenu)
   ========================================================================== */
.st-key-parakh_navbar,
div[class*="st-key-parakh_navbar"] {{
    background: var(--navbar-glass-bg) !important;
    backdrop-filter: blur(18px) !important;
    -webkit-backdrop-filter: blur(18px) !important;
    border: 1px solid var(--navbar-glass-border) !important;
    border-radius: 16px !important;
    box-shadow: var(--navbar-glass-shadow) !important;
    max-width: 1320px !important;
    width: 100% !important;
    margin: 0.5rem auto 1.75rem auto !important;
    padding: 0 1.25rem !important;
    height: 66px !important;
    min-height: 66px !important;
    max-height: 66px !important;
    display: flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: space-between !important;
    position: sticky !important;
    top: 0.75rem !important;
    z-index: 9999 !important;
    box-sizing: border-box !important;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
}}

/* Ensure direct children of navbar align properly without extra margins */
.st-key-parakh_navbar > [data-testid="stElementContainer"],
.st-key-parakh_navbar > div {{
    margin: 0 !important;
    padding: 0 !important;
}}

/* Brand Wordmark & Emblem */
.nav-brand-container {{
    display: inline-flex;
    align-items: center;
    gap: 0.75rem;
    height: 40px;
    user-select: none;
}}

.nav-brand-icon {{
    width: 32px;
    height: 32px;
    border-radius: 8px;
    background: #3B82F6;
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
    font-weight: 800;
    font-family: var(--font-heading);
    box-shadow: 0 0 14px rgba(59, 130, 246, 0.4);
    letter-spacing: -0.02em;
}}

.nav-brand-text {{
    display: flex;
    flex-direction: column;
    justify-content: center;
}}

.nav-brand-title {{
    font-family: var(--font-heading) !important;
    font-size: 1.12rem;
    font-weight: 800;
    letter-spacing: -0.03em;
    color: var(--text-primary);
    line-height: 1.1;
    margin: 0;
}}

.nav-brand-subtitle {{
    font-family: var(--font-mono) !important;
    font-size: 0.58rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    margin: 0;
    line-height: 1.2;
}}

/* Center Navigation Group (Text-first SaaS Navigation Pills) */
.st-key-parakh_nav_links,
div[class*="st-key-parakh_nav_links"],
div[class*="parakh_nav_links"] {{
    display: inline-flex !important;
    flex-direction: row !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.35rem !important;
    height: 40px !important;
    margin: 0 auto !important;
}}

.st-key-parakh_nav_links [data-testid="stElementContainer"],
div[class*="parakh_nav_links"] [data-testid="stElementContainer"] {{
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    display: inline-flex !important;
}}

div[class*="parakh_nav_links"] button,
.st-key-parakh_nav_links button {{
    border-radius: 9999px !important;
    font-family: var(--font-sans) !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    height: 32px !important;
    min-height: 32px !important;
    max-height: 32px !important;
    padding: 0 14px !important;
    margin: 0 !important;
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    color: var(--text-secondary) !important;
    box-shadow: none !important;
    white-space: nowrap !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    width: auto !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    cursor: pointer !important;
}}

div[class*="parakh_nav_links"] button:hover,
.st-key-parakh_nav_links button:hover {{
    background: var(--nav-hover-bg) !important;
    background-color: var(--nav-hover-bg) !important;
    color: var(--text-primary) !important;
    border-color: transparent !important;
}}

/* Active Nav Pill: Soft Blue Tint Pill, ZERO RED, ZERO SOLID BLUE */
div[class*="parakh_nav_"] button[kind="primary"],
div[class*="parakh_nav_"] button[data-testid="stBaseButton-primary"],
div[class*="parakh_nav_links"] button[kind="primary"],
div[class*="parakh_nav_links"] button[data-testid="stBaseButton-primary"],
.st-key-parakh_nav_links button[kind="primary"],
.st-key-parakh_nav_links button[data-testid="stBaseButton-primary"],
button[data-testid="stBaseButton-primary"][key*="parakh_nav_"] {{
    background: rgba(59, 130, 246, 0.12) !important;
    background-color: rgba(59, 130, 246, 0.12) !important;
    color: #3B82F6 !important;
    border: 1px solid rgba(59, 130, 246, 0.22) !important;
    border-color: rgba(59, 130, 246, 0.22) !important;
    font-weight: 600 !important;
    border-radius: 9999px !important;
    box-shadow: none !important;
}}

div[class*="parakh_nav_"] button[kind="primary"] *,
div[class*="parakh_nav_"] button[data-testid="stBaseButton-primary"] *,
div[class*="parakh_nav_links"] button[kind="primary"] *,
div[class*="parakh_nav_links"] button[data-testid="stBaseButton-primary"] *,
.st-key-parakh_nav_links button[kind="primary"] *,
.st-key-parakh_nav_links button[data-testid="stBaseButton-primary"] * {{
    color: #3B82F6 !important;
    background: transparent !important;
    background-color: transparent !important;
}}

div[class*="parakh_nav_"] button[kind="primary"]:hover,
div[class*="parakh_nav_"] button[data-testid="stBaseButton-primary"]:hover,
div[class*="parakh_nav_links"] button[kind="primary"]:hover,
div[class*="parakh_nav_links"] button[data-testid="stBaseButton-primary"]:hover,
div[class*="parakh_nav_links"] button[kind="primary"]:focus,
div[class*="parakh_nav_links"] button[data-testid="stBaseButton-primary"]:focus,
div[class*="parakh_nav_links"] button[kind="primary"]:active,
div[class*="parakh_nav_links"] button[data-testid="stBaseButton-primary"]:active {{
    background: rgba(59, 130, 246, 0.18) !important;
    background-color: rgba(59, 130, 246, 0.18) !important;
    color: #3B82F6 !important;
    border: 1px solid rgba(59, 130, 246, 0.3) !important;
    border-color: rgba(59, 130, 246, 0.3) !important;
    box-shadow: none !important;
}}

/* Right Navigation Group (Zones 3 & 4 - Strictly No Wrapping) */
.st-key-parakh_nav_right,
div[class*="st-key-parakh_nav_right"],
div[class*="parakh_nav_right"],
.st-key-parakh_nav_right [data-testid="stHorizontalBlock"],
div[class*="parakh_nav_right"] [data-testid="stHorizontalBlock"] {{
    display: inline-flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important;
    white-space: nowrap !important;
    align-items: center !important;
    justify-content: flex-end !important;
    gap: 0.75rem !important;
    height: 40px !important;
    flex-shrink: 0 !important;
    width: auto !important;
}}

.st-key-parakh_nav_right [data-testid="stElementContainer"],
div[class*="parakh_nav_right"] [data-testid="stElementContainer"] {{
    width: auto !important;
    margin: 0 !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    flex-shrink: 0 !important;
    flex-wrap: nowrap !important;
}}

/* Zone 3: Combined Status and Context Group */
.nav-status-context-group {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.5rem !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
}}

/* System Status Badge (Credit Engine Live) */
.nav-status-badge {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.45rem !important;
    height: 28px !important;
    padding: 0 0.65rem !important;
    border-radius: 9999px !important;
    background: rgba(16, 185, 129, 0.08) !important;
    border: 1px solid rgba(16, 185, 129, 0.25) !important;
    user-select: none !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
    flex-shrink: 0 !important;
}}

.nav-status-dot {{
    width: 6px !important;
    height: 6px !important;
    border-radius: 50% !important;
    background: #10B981 !important;
    box-shadow: 0 0 8px #10B981 !important;
    animation: pulseGlow 2s infinite ease-in-out !important;
    display: inline-block !important;
}}

.nav-status-label {{
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: #10B981 !important;
    letter-spacing: 0.02em !important;
    display: inline !important;
}}

/* Context Indicator Pill (Current Portfolio / All Applications) */
.nav-context-pill {{
    display: inline-flex !important;
    align-items: center !important;
    height: 28px !important;
    padding: 0 0.65rem !important;
    border-radius: 9999px !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    font-family: var(--font-mono) !important;
    font-size: 0.72rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    user-select: none !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
    flex-shrink: 0 !important;
}}

/* ==========================================================================
   ZONE 4: PREMIUM TACTILE THEME TOGGLE (56px x 28px Track, 36px 3D Thumb, SVG Icons)
   ========================================================================== */
div[class*="parakh_theme_toggle"],
div[class*="theme_toggle"],
.st-key-parakh_theme_toggle_user,
.st-key-parakh_theme_toggle_admin {{
    overflow: visible !important;
    width: 56px !important;
    min-width: 56px !important;
    max-width: 56px !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
    margin: 0 4px !important;
    flex-shrink: 0 !important;
}}

div[class*="parakh_theme_toggle"] [data-testid="stElementContainer"],
div[class*="theme_toggle"] [data-testid="stElementContainer"],
div[class*="parakh_theme_toggle"] .stButton,
div[class*="theme_toggle"] .stButton {{
    overflow: visible !important;
    width: 56px !important;
    min-width: 56px !important;
    max-width: 56px !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    margin: 0 !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    position: relative !important;
}}

/* The Pill Track */
div[class*="parakh_theme_toggle"] button,
div[class*="theme_toggle"] button,
div[class*="parakh_theme_toggle"] .stButton button,
div[class*="theme_toggle"] .stButton button {{
    width: 56px !important;
    min-width: 56px !important;
    max-width: 56px !important;
    height: 28px !important;
    min-height: 28px !important;
    max-height: 28px !important;
    border-radius: 9999px !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 1px solid {c['toggle_track_border']} !important;
    background: {c['toggle_track_bg']} !important;
    box-shadow: {c['toggle_track_shadow']} !important;
    position: relative !important;
    cursor: pointer !important;
    transition: all 0.26s cubic-bezier(0.16, 1, 0.3, 1) !important;
    overflow: visible !important;
    display: block !important;
    outline: none !important;
}}

div[class*="parakh_theme_toggle"] button:hover,
div[class*="theme_toggle"] button:hover {{
    border-color: var(--accent) !important;
}}

/* Hide all text/p/div inside the toggle button */
div[class*="parakh_theme_toggle"] button *,
div[class*="theme_toggle"] button * {{
    display: none !important;
    visibility: hidden !important;
}}

/* Large Overlapping 3D Tactile Circular Thumb (36px, extends 4px above and below 28px track) */
div[class*="parakh_theme_toggle"] button::after,
div[class*="theme_toggle"] button::after {{
    content: '' !important;
    position: absolute !important;
    top: -4px !important;
    left: {c['toggle_thumb_left']} !important;
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    background-color: {c['toggle_thumb_bg']} !important;
    background-image: {c['toggle_icon_svg']} !important;
    background-repeat: no-repeat !important;
    background-position: center center !important;
    border: 1px solid {c['toggle_thumb_border']} !important;
    box-shadow: {c['toggle_thumb_shadow']} !important;
    transition: left 0.26s cubic-bezier(0.16, 1, 0.3, 1), background-color 0.26s ease, box-shadow 0.26s ease !important;
    pointer-events: none !important;
    box-sizing: border-box !important;
    z-index: 10 !important;
    display: block !important;
}}

div[class*="parakh_theme_toggle"] button::before,
div[class*="theme_toggle"] button::before {{
    display: none !important;
    content: none !important;
}}

/* Fintech Profile Pill Control */
.nav-profile-pill {{
    display: inline-flex !important;
    align-items: center !important;
    gap: 0.55rem !important;
    height: 34px !important;
    padding: 0 0.75rem 0 0.35rem !important;
    border-radius: 9999px !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    user-select: none !important;
    white-space: nowrap !important;
    flex-shrink: 0 !important;
    box-sizing: border-box !important;
}}
    white-space: nowrap;
}}

.nav-profile-pill.admin {{
    border-color: rgba(16, 185, 129, 0.25);
}}

.nav-profile-avatar {{
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: var(--accent);
    color: #FFFFFF;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.68rem;
    font-weight: 800;
    font-family: var(--font-heading);
}}

.nav-profile-avatar.admin {{
    background: #10B981;
}}

.nav-profile-info {{
    display: flex;
    flex-direction: column;
    justify-content: center;
    line-height: 1.15;
}}

.nav-profile-name {{
    font-size: 0.78rem;
    font-weight: 700;
    color: var(--text-primary);
}}

.nav-profile-role {{
    font-size: 0.62rem;
    font-weight: 600;
    color: var(--text-muted);
    font-family: var(--font-mono);
}}

.nav-profile-role.admin {{
    color: #10B981;
}}

/* ==========================================================================
   Cards & Surface Modules
   ========================================================================== */
.p-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem 1.4rem;
    box-shadow: var(--card-shadow);
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
}}

.p-card:hover {{
    border-color: var(--border-focus);
    box-shadow: var(--card-shadow-hover);
    transform: translateY(-1px);
}}

.p-card-static {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.25rem 1.4rem;
    box-shadow: var(--card-shadow);
}}

.p-card-accent {{
    background: linear-gradient(145deg, var(--surface) 0%, var(--surface-hover) 100%);
    border: 1px solid var(--border);
    border-top: 2px solid var(--accent);
    border-radius: 8px;
    padding: 1.25rem 1.4rem;
    box-shadow: var(--card-shadow);
    transition: all 0.2s ease;
}}

.p-card-accent:hover {{
    box-shadow: var(--card-shadow-hover);
}}

/* ==========================================================================
   Hero Section Styling
   ========================================================================== */
.hero-wrapper {{
    background: linear-gradient(135deg, var(--surface) 0%, var(--bg-subtle) 100%);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2.25rem 2rem;
    position: relative;
    overflow: hidden;
    box-shadow: var(--card-shadow);
}}

.hero-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--accent);
    background: var(--accent-subtle);
    border: 1px solid rgba(59, 130, 246, 0.25);
    padding: 0.3rem 0.75rem;
    border-radius: 9999px;
    margin-bottom: 1rem;
}}

.hero-title {{
    font-family: var(--font-heading);
    font-size: 2.4rem;
    font-weight: 800;
    line-height: 1.15;
    letter-spacing: -0.04em;
    color: var(--text-primary);
    margin-bottom: 0.85rem;
}}

.hero-subtitle {{
    font-size: 0.96rem;
    font-weight: 400;
    line-height: 1.6;
    color: var(--text-secondary);
    max-width: 580px;
    margin-bottom: 1.5rem;
}}

/* ==========================================================================
   Risk Badges & Indicators
   ========================================================================== */
.risk-badge {{
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.25rem 0.65rem;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    line-height: 1;
    white-space: nowrap;
}}

.risk-badge.low {{
    background: var(--success-subtle);
    color: var(--success);
    border: 1px solid var(--success-border);
}}

.risk-badge.medium {{
    background: var(--warning-subtle);
    color: var(--warning);
    border: 1px solid var(--warning-border);
}}

.risk-badge.high {{
    background: var(--danger-subtle);
    color: var(--danger);
    border: 1px solid var(--danger-border);
}}

.risk-badge.neutral {{
    background: var(--bg-subtle);
    color: var(--text-secondary);
    border: 1px solid var(--border);
}}

.risk-dot {{
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
}}

.risk-dot.low {{
    background-color: var(--success);
    box-shadow: 0 0 6px var(--success);
}}

.risk-dot.medium {{
    background-color: var(--warning);
    box-shadow: 0 0 6px var(--warning);
}}

.risk-dot.high {{
    background-color: var(--danger);
    box-shadow: 0 0 6px var(--danger);
    animation: pulseGlow 1.8s infinite ease-in-out;
}}

/* ==========================================================================
   KPI Cards
   ========================================================================== */
.kpi-card {{
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.15rem 1.3rem;
    box-shadow: var(--card-shadow);
    transition: all 0.2s ease;
    height: 100%;
    min-height: 124px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}}

.kpi-card:hover {{
    border-color: var(--border-focus);
    transform: translateY(-1px);
}}

.kpi-label {{
    font-size: 0.74rem;
    font-weight: 600;
    color: var(--text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 0.35rem;
}}

.kpi-value {{
    font-size: 1.75rem;
    font-weight: 700;
    font-family: var(--font-mono);
    color: var(--text-primary);
    letter-spacing: -0.03em;
    line-height: 1.1;
}}

.kpi-delta {{
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 600;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    margin-top: 0.4rem;
}}

.kpi-delta.positive {{
    color: var(--success);
}}

.kpi-delta.neutral {{
    color: var(--text-muted);
}}

.kpi-delta.negative {{
    color: var(--danger);
}}

/* ==========================================================================
   Standard Streamlit Component Resets (outside navbar - 42px standardized height)
   ========================================================================== */
div:not([class*="parakh"]):not([class*="theme_toggle"]):not([class*="nav_"]) > .stButton > button,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button {{
    border-radius: 8px !important;
    font-family: var(--font-heading) !important;
    font-weight: 600 !important;
    font-size: 0.88rem !important;
    padding: 0 1.25rem !important;
    height: 42px !important;
    min-height: 42px !important;
    max-height: 42px !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1) !important;
    border: 1px solid var(--border) !important;
    background-color: var(--surface) !important;
    color: var(--text-primary) !important;
    box-shadow: var(--card-shadow) !important;
    white-space: nowrap !important;
    box-sizing: border-box !important;
}}

div:not([class*="parakh"]):not([class*="theme_toggle"]):not([class*="nav_"]) > .stButton > button:hover,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button:hover,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button:hover {{
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background-color: var(--surface-hover) !important;
    transform: translateY(-1px) !important;
}}

div:not([class*="parakh"]):not([class*="theme_toggle"]):not([class*="nav_"]) > .stButton > button[kind="primary"],
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"],
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"],
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"],
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"] {{
    background: var(--accent) !important;
    background-color: var(--accent) !important;
    color: #FFFFFF !important;
    border: 1px solid rgba(255, 255, 255, 0.15) !important;
    box-shadow: 0 2px 10px var(--accent-glow) !important;
}}

div:not([class*="parakh"]):not([class*="theme_toggle"]):not([class*="nav_"]) > .stButton > button[kind="primary"] *,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"] *,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"] *,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"] *,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"] * {{
    color: #FFFFFF !important;
}}

div:not([class*="parakh"]):not([class*="theme_toggle"]):not([class*="nav_"]) > .stButton > button[kind="primary"]:hover,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"]:hover,
.stApp .block-container > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"]:hover,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[kind="primary"]:hover,
.stApp div[data-testid="stVerticalBlock"] > div:not([class*="parakh_navbar"]) .stButton > button[data-testid="stBaseButton-primary"]:hover {{
    background: var(--accent-hover) !important;
    background-color: var(--accent-hover) !important;
    color: #FFFFFF !important;
    box-shadow: 0 4px 14px var(--accent-glow) !important;
}}

/* Inputs & Form Fields */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stSelectbox > div > div,
.stTextArea > div > div > textarea {{
    background-color: var(--surface) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    font-family: var(--font-sans) !important;
    font-size: 0.88rem !important;
}}

.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus,
.stSelectbox > div > div:focus-within,
.stTextArea > div > div > textarea:focus {{
    border-color: var(--border-focus) !important;
    box-shadow: 0 0 0 1px var(--border-focus) !important;
}}

label[data-testid="stWidgetLabel"] p {{
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    margin-bottom: 0.25rem !important;
}}

/* Monospace font utility */
.font-mono {{
    font-family: var(--font-mono) !important;
}}

/* Headings font utility */
.font-heading {{
    font-family: var(--font-heading) !important;
}}

/* Mock data badge */
.mock-badge {{
    display: inline-flex;
    align-items: center;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    font-family: var(--font-mono);
    font-size: 0.68rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    background: rgba(148, 163, 184, 0.12);
    color: var(--text-muted);
    border: 1px solid var(--border);
}}

/* Layout Spacing Utilities */
.section-gap {{
    height: 32px;
    width: 100%;
}}

.module-gap {{
    height: 20px;
    width: 100%;
}}

.divider-line {{
    height: 1px;
    width: 100%;
    background: var(--border);
    margin: 1.5rem 0;
}}

.table-divider {{
    height: 1px;
    width: 100%;
    background: var(--border);
    margin: 0.35rem 0 0.75rem 0;
}}

.table-row-divider {{
    height: 1px;
    width: 100%;
    background: var(--border);
    margin: 0.4rem 0 0.5rem 0;
    opacity: 0.6;
}}

/* ==========================================================================
   ULTRA-SPECIFIC NAVBAR LINK & ACTIVE PILL OVERRIDES
   Guarantees subtle translucent blue pill with ZERO RED and ZERO SOLID BLUE
   ========================================================================== */
.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button,
.st-key-parakh_nav_links .stButton > button,
div[class*="st-key-parakh_nav_u_"] .stButton > button,
div[class*="st-key-parakh_nav_a_"] .stButton > button {{
    height: 32px !important;
    min-height: 32px !important;
    max-height: 32px !important;
    border-radius: 9999px !important;
    padding: 0 14px !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    background: transparent !important;
    background-color: transparent !important;
    border: 1px solid transparent !important;
    color: var(--text-secondary) !important;
    box-shadow: none !important;
    width: auto !important;
}}

.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button *,
.st-key-parakh_nav_links .stButton > button *,
div[class*="st-key-parakh_nav_u_"] .stButton > button *,
div[class*="st-key-parakh_nav_a_"] .stButton > button * {{
    color: var(--text-secondary) !important;
    background: transparent !important;
    background-color: transparent !important;
    font-weight: 500 !important;
}}

.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button:hover,
.st-key-parakh_nav_links .stButton > button:hover,
div[class*="st-key-parakh_nav_u_"] .stButton > button:hover,
div[class*="st-key-parakh_nav_a_"] .stButton > button:hover {{
    background: var(--nav-hover-bg) !important;
    background-color: var(--nav-hover-bg) !important;
    border-color: transparent !important;
    color: var(--text-primary) !important;
    box-shadow: none !important;
    transform: none !important;
}}

.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button:hover *,
.st-key-parakh_nav_links .stButton > button:hover *,
div[class*="st-key-parakh_nav_u_"] .stButton > button:hover *,
div[class*="st-key-parakh_nav_a_"] .stButton > button:hover * {{
    color: var(--text-primary) !important;
}}

/* Active Nav Pill: Soft Blue Tint Pill */
.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button[kind="primary"],
.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button[data-testid="stBaseButton-primary"],
.st-key-parakh_nav_links .stButton > button[kind="primary"],
.st-key-parakh_nav_links .stButton > button[data-testid="stBaseButton-primary"],
div[class*="st-key-parakh_nav_u_"] .stButton > button[kind="primary"],
div[class*="st-key-parakh_nav_u_"] .stButton > button[data-testid="stBaseButton-primary"],
div[class*="st-key-parakh_nav_a_"] .stButton > button[kind="primary"],
div[class*="st-key-parakh_nav_a_"] .stButton > button[data-testid="stBaseButton-primary"] {{
    background: var(--nav-active-bg) !important;
    background-color: var(--nav-active-bg) !important;
    color: var(--accent) !important;
    border: 1px solid var(--nav-active-border) !important;
    border-color: var(--nav-active-border) !important;
    border-radius: 9999px !important;
    height: 32px !important;
    min-height: 32px !important;
    max-height: 32px !important;
    padding: 0 14px !important;
    box-shadow: none !important;
    font-weight: 600 !important;
    transform: none !important;
}}

.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button[kind="primary"] *,
.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button[data-testid="stBaseButton-primary"] *,
.st-key-parakh_nav_links .stButton > button[kind="primary"] *,
.st-key-parakh_nav_links .stButton > button[data-testid="stBaseButton-primary"] *,
div[class*="st-key-parakh_nav_u_"] .stButton > button[kind="primary"] *,
div[class*="st-key-parakh_nav_u_"] .stButton > button[data-testid="stBaseButton-primary"] *,
div[class*="st-key-parakh_nav_a_"] .stButton > button[kind="primary"] *,
div[class*="st-key-parakh_nav_a_"] .stButton > button[data-testid="stBaseButton-primary"] * {{
    color: var(--accent) !important;
    background: transparent !important;
    background-color: transparent !important;
    font-weight: 600 !important;
}}

.st-key-parakh_navbar .st-key-parakh_nav_links .stButton > button[kind="primary"]:hover,
.st-key-parakh_nav_links .stButton > button[kind="primary"]:hover,
div[class*="st-key-parakh_nav_u_"] .stButton > button[kind="primary"]:hover,
div[class*="st-key-parakh_nav_a_"] .stButton > button[kind="primary"]:hover {{
    background: var(--nav-active-bg) !important;
    background-color: var(--nav-active-bg) !important;
    border-color: var(--accent) !important;
    box-shadow: none !important;
    transform: none !important;
}}
</style>
"""
