"""
PARAKH User Portal - Multi-Step Application Onboarding Flow
Progressive disclosure form with calm fintech aesthetics, 6 distinct stages, and real-time AI credit simulation.
"""
import streamlit as st
from utils.mock_data import calculate_dynamic_assessment
from utils.navigation import navigate_user
from utils.styling import render_html, render_module_gap

STEPS = [
    {"num": 1, "label": "Identity & KYC"},
    {"num": 2, "label": "Employment"},
    {"num": 3, "label": "Obligations"},
    {"num": 4, "label": "Loan Terms"},
    {"num": 5, "label": "Review"},
    {"num": 6, "label": "Decision"}
]

def render_stepper(current_step: int):
    """Renders the horizontal progress stepper bar."""
    step_items_html = ""
    for s in STEPS:
        is_active = (s["num"] == current_step)
        is_done = (s["num"] < current_step)
        
        status_class = "active" if is_active else ("completed" if is_done else "")
        label_class = "active" if is_active else ""
        icon = "✓" if is_done else str(s["num"])

        step_items_html += f"""
<div class="stepper-step">
<div class="step-circle {status_class}">{icon}</div>
<span class="step-label {label_class}">{s['label']}</span>
</div>
"""

    render_html(f"""
<div class="stepper-container" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem; position: relative; padding: 0 0.5rem;">
<div style="position: absolute; top: 18px; left: 8%; right: 8%; height: 1px; background: var(--border); z-index: 1;"></div>
{step_items_html}
</div>
""")


def render_user_application():
    """Renders the multi-step credit application workflow."""
    if "app_form_step" not in st.session_state:
        st.session_state.app_form_step = 1

    # Form state store
    if "form_store" not in st.session_state:
        st.session_state.form_store = {
            "full_name": "Aarav Mehta",
            "email": "aarav.mehta@techcorp.in",
            "phone": "+91 98450 12890",
            "pan": "ABCDE1234F",
            "city": "Bangalore",
            "employment_type": "Salaried - Corporate",
            "employer": "Infosys Technologies Ltd",
            "experience_years": 8,
            "monthly_income": 285000,
            "existing_debt": 350000,
            "bank_balance": 920000,
            "credit_cards_count": 2,
            "late_payments": 0,
            "loan_amount": 2000000,
            "tenure_months": 36,
            "loan_purpose": "Home Improvement & Solar",
            "collateral": "None (Unsecured Facility)"
        }

    current_step = st.session_state.app_form_step

    # Page Header
    render_html("""
<div style="margin-bottom: 1.5rem; text-align: center;">
<div style="font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 0.3rem; font-family: var(--font-mono);">Digital Credit Onboarding</div>
<h2 style="font-size: 1.85rem; font-weight: 800; color: var(--text-primary); margin: 0; letter-spacing: -0.03em; font-family: var(--font-heading);">New Credit Facility Application</h2>
<p style="font-size: 0.9rem; color: var(--text-secondary); margin-top: 0.35rem;">Transparent evaluation driven by the PARAKH Neural Underwriting Engine.</p>
</div>
""")

    # Render Progress Stepper
    render_stepper(current_step)

    # Form Container
    f_cols = st.columns([1, 2.6, 1])
    with f_cols[1]:
        # STEP 1: Personal Information & KYC
        if current_step == 1:
            render_html("""
<div class="p-card-static" style="padding: 1.75rem;">
<h4 style="margin: 0 0 0.35rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Step 1: Identity & KYC Verification</h4>
<p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1.25rem;">Provide legal identity information matching your tax and PAN records.</p>
</div>
""")
            st.session_state.form_store["full_name"] = st.text_input(
                "Full Legal Name",
                value=st.session_state.form_store["full_name"]
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.form_store["email"] = st.text_input(
                    "Work / Primary Email",
                    value=st.session_state.form_store["email"]
                )
            with col2:
                st.session_state.form_store["phone"] = st.text_input(
                    "Mobile Contact",
                    value=st.session_state.form_store["phone"]
                )

            col3, col4 = st.columns(2)
            with col3:
                st.session_state.form_store["pan"] = st.text_input(
                    "Permanent Account Number (PAN)",
                    value=st.session_state.form_store["pan"]
                )
            with col4:
                st.session_state.form_store["city"] = st.selectbox(
                    "Current Residential City",
                    options=["Bangalore", "Mumbai", "Delhi NCR", "Hyderabad", "Pune", "Chennai", "Kolkata"],
                    index=0
                )

            render_html("""
<div style="padding: 0.65rem 0.85rem; background: var(--bg-subtle); border-radius: 6px; font-size: 0.74rem; color: var(--text-secondary); margin-top: 1rem; border: 1px solid var(--border);">
Identity credentials are transmitted over encrypted TLS 1.3 channels and matched with institutional bureau records.
</div>
""")

            render_module_gap()
            btn_cols = st.columns([1, 1])
            with btn_cols[1]:
                if st.button("Continue to Employment →", key="step1_next", type="primary", use_container_width=True):
                    st.session_state.app_form_step = 2
                    st.rerun()

        # STEP 2: Employment & Income
        elif current_step == 2:
            render_html("""
<div class="p-card-static" style="padding: 1.75rem;">
<h4 style="margin: 0 0 0.35rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Step 2: Employment & Verified Income</h4>
<p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1.25rem;">Declare your primary source of recurring cash flow and enterprise affiliation.</p>
</div>
""")
            st.session_state.form_store["employment_type"] = st.selectbox(
                "Employment Classification",
                options=["Salaried - Corporate", "Salaried - Public Sector", "Self-Employed - Business Owner", "Independent Consultant / Freelancer"],
                index=0
            )

            st.session_state.form_store["employer"] = st.text_input(
                "Employer / Registered Business Entity",
                value=st.session_state.form_store["employer"]
            )

            col1, col2 = st.columns(2)
            with col1:
                st.session_state.form_store["experience_years"] = st.number_input(
                    "Total Work Experience (Years)",
                    min_value=1,
                    max_value=40,
                    value=st.session_state.form_store["experience_years"]
                )
            with col2:
                st.session_state.form_store["monthly_income"] = st.number_input(
                    "Net Monthly Inflow (₹)",
                    min_value=15000,
                    max_value=2000000,
                    step=10000,
                    value=st.session_state.form_store["monthly_income"]
                )

            render_module_gap()
            btn_cols = st.columns([1, 1])
            with btn_cols[0]:
                if st.button("← Back to Identity", key="step2_back", use_container_width=True):
                    st.session_state.app_form_step = 1
                    st.rerun()
            with btn_cols[1]:
                if st.button("Continue to Liabilities →", key="step2_next", type="primary", use_container_width=True):
                    st.session_state.app_form_step = 3
                    st.rerun()

        # STEP 3: Financial Liabilities & History
        elif current_step == 3:
            render_html("""
<div class="p-card-static" style="padding: 1.75rem;">
<h4 style="margin: 0 0 0.35rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Step 3: Financial Liabilities & Liquidity</h4>
<p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1.25rem;">PARAKH calculates your debt serviceability index from active obligations.</p>
</div>
""")
            col1, col2 = st.columns(2)
            with col1:
                st.session_state.form_store["existing_debt"] = st.number_input(
                    "Total Outstanding Principal Debt (₹)",
                    min_value=0,
                    max_value=10000000,
                    step=25000,
                    value=st.session_state.form_store["existing_debt"]
                )
            with col2:
                st.session_state.form_store["bank_balance"] = st.number_input(
                    "Average Liquid Savings Balance (₹)",
                    min_value=5000,
                    max_value=10000000,
                    step=50000,
                    value=st.session_state.form_store["bank_balance"]
                )

            col3, col4 = st.columns(2)
            with col3:
                st.session_state.form_store["late_payments"] = st.selectbox(
                    "Late Payments (30+ DPD) in Last 36 Months",
                    options=[0, 1, 2, 3, 4],
                    index=0
                )
            with col4:
                st.session_state.form_store["credit_cards_count"] = st.number_input(
                    "Active Credit Cards",
                    min_value=0,
                    max_value=12,
                    value=st.session_state.form_store["credit_cards_count"]
                )

            render_module_gap()
            btn_cols = st.columns([1, 1])
            with btn_cols[0]:
                if st.button("← Back to Income", key="step3_back", use_container_width=True):
                    st.session_state.app_form_step = 2
                    st.rerun()
            with btn_cols[1]:
                if st.button("Continue to Loan Terms →", key="step3_next", type="primary", use_container_width=True):
                    st.session_state.app_form_step = 4
                    st.rerun()

        # STEP 4: Loan Details & Facility
        elif current_step == 4:
            render_html("""
<div class="p-card-static" style="padding: 1.75rem;">
<h4 style="margin: 0 0 0.35rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Step 4: Requested Facility & Tenor</h4>
<p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1.25rem;">Specify your target capital requirements and preferred repayment tenure.</p>
</div>
""")
            st.session_state.form_store["loan_amount"] = st.number_input(
                "Requested Facility Amount (₹)",
                min_value=100000,
                max_value=10000000,
                step=100000,
                value=st.session_state.form_store["loan_amount"]
            )

            col1, col2 = st.columns(2)
            with col1:
                st.session_state.form_store["tenure_months"] = st.selectbox(
                    "Requested Tenure",
                    options=[12, 24, 36, 48, 60, 84],
                    index=2,
                    format_func=lambda x: f"{x} Months ({x//12} yrs)" if x>=12 else f"{x} Months"
                )
            with col2:
                st.session_state.form_store["loan_purpose"] = st.selectbox(
                    "Primary Facility Purpose",
                    options=["Home Improvement & Solar", "Working Capital Expansion", "Executive Higher Education", "Medical & Emergency", "Debt Consolidation", "Equipment Purchase"],
                    index=0
                )

            # Simulated EMI calculation preview
            p = st.session_state.form_store["loan_amount"]
            t = st.session_state.form_store["tenure_months"]
            r = 0.105 / 12
            est_emi = (p * r * ((1 + r) ** t)) / (((1 + r) ** t) - 1)

            render_html(f"""
<div style="margin-top: 1rem; padding: 0.85rem; background: var(--bg-subtle); border-radius: 6px; display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border);">
<div>
<div style="font-size: 0.7rem; text-transform: uppercase; color: var(--text-muted); font-weight: 700; font-family: var(--font-mono);">Indicative Monthly Installment (EMI)</div>
<div class="font-mono" style="font-size: 1.15rem; font-weight: 800; color: var(--accent);">₹{est_emi:,.0f} / mo</div>
</div>
<div style="text-align: right;">
<div style="font-size: 0.7rem; color: var(--text-muted); font-family: var(--font-mono);">Benchmark Rate</div>
<div class="font-mono" style="font-size: 0.9rem; font-weight: 700; color: var(--text-primary);">10.5% p.a.</div>
</div>
</div>
""")

            render_module_gap()
            btn_cols = st.columns([1, 1])
            with btn_cols[0]:
                if st.button("← Back to Liabilities", key="step4_back", use_container_width=True):
                    st.session_state.app_form_step = 3
                    st.rerun()
            with btn_cols[1]:
                if st.button("Review Application →", key="step4_next", type="primary", use_container_width=True):
                    st.session_state.app_form_step = 5
                    st.rerun()

        # STEP 5: Final Review & Submission Confirmation
        elif current_step == 5:
            render_html("""
<div class="p-card-static" style="padding: 1.75rem;">
<h4 style="margin: 0 0 0.35rem 0; font-weight: 800; color: var(--text-primary); font-family: var(--font-heading);">Step 5: Review Submission & Authorization</h4>
<p style="font-size: 0.82rem; color: var(--text-secondary); margin-bottom: 1.25rem;">Verify all details before initiating the real-time neural credit assessment.</p>
</div>
""")
            data = st.session_state.form_store

            render_html(f"""
<div style="display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1.25rem; background: var(--surface); padding: 1.25rem; border-radius: 8px; border: 1px solid var(--border);">
<div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Applicant Name</span>
<span style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">{data['full_name']}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Employer & Inflow</span>
<span style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">{data['employer']} (₹{data['monthly_income']:,.0f}/mo)</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Facility Requested</span>
<span class="font-mono" style="font-weight: 800; color: var(--accent); font-size: 0.95rem;">₹{data['loan_amount']:,.0f} ({data['tenure_months']} mos)</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 0.5rem 0; border-bottom: 1px solid var(--border);">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Purpose</span>
<span style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">{data['loan_purpose']}</span>
</div>
<div style="display: flex; justify-content: space-between; padding: 0.5rem 0;">
<span style="color: var(--text-secondary); font-size: 0.85rem;">Existing Debt Obligation</span>
<span class="font-mono" style="font-weight: 700; color: var(--text-primary); font-size: 0.85rem;">₹{data['existing_debt']:,.0f}</span>
</div>
</div>
""")

            consent = st.checkbox("I consent to PARAKH pulling simulated bureau data and executing an automated neural risk evaluation.", value=True)

            render_module_gap()
            btn_cols = st.columns([1, 1.2])
            with btn_cols[0]:
                if st.button("← Edit Details", key="step5_back", use_container_width=True):
                    st.session_state.app_form_step = 4
                    st.rerun()
            with btn_cols[1]:
                if st.button("Run Instant Assessment", key="step5_submit", type="primary", disabled=not consent, use_container_width=True):
                    st.session_state.app_form_step = 6
                    st.rerun()

        # STEP 6: Decision & Real-Time Assessment Complete
        elif current_step == 6:
            if "submitted_assessment" not in st.session_state or st.session_state.submitted_assessment is None:
                assessment = calculate_dynamic_assessment(st.session_state.form_store)
                st.session_state.submitted_assessment = assessment
            else:
                assessment = st.session_state.submitted_assessment

            render_html(f"""
<div class="p-card-static" style="text-align: center; padding: 2rem 1.5rem;">
<div style="width: 48px; height: 48px; background: rgba(16, 185, 129, 0.12); border: 1px solid #10B981; border-radius: 50%; display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem auto; color: #10B981; font-size: 1.4rem; font-weight: 800;">
✓
</div>
<span class="font-mono" style="font-size: 0.76rem; font-weight: 700; color: var(--accent); letter-spacing: 0.05em;">{assessment['id']}</span>
<h3 style="font-size: 1.5rem; font-weight: 800; color: var(--text-primary); margin: 0.35rem 0; font-family: var(--font-heading);">Assessment Successfully Synthesized</h3>
<p style="font-size: 0.88rem; color: var(--text-secondary); max-width: 480px; margin: 0 auto 1.5rem auto;">
PARAKH Neural Ensemble has processed your telemetry with 99.4% confidence calibration.
</p>

<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; padding: 1.25rem; background: var(--bg-subtle); border-radius: 8px; margin-bottom: 1.5rem; border: 1px solid var(--border);">
<div style="text-align: center; border-right: 1px solid var(--border);">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Credit Trust Score</div>
<div class="font-mono" style="font-size: 2.2rem; font-weight: 800; color: var(--text-primary); line-height: 1.2;">{assessment['credit_score']}</div>
<div style="font-size: 0.74rem; font-weight: 700; color: #10B981; font-family: var(--font-mono);">{assessment['risk_category']}</div>
</div>
<div style="text-align: center;">
<div style="font-size: 0.72rem; color: var(--text-muted); text-transform: uppercase; font-family: var(--font-mono);">Default Probability</div>
<div class="font-mono" style="font-size: 2.2rem; font-weight: 800; color: var(--text-primary); line-height: 1.2;">{assessment['default_probability']*100:.1f}%</div>
<div style="font-size: 0.74rem; font-weight: 700; color: var(--accent); font-family: var(--font-mono);">{assessment['status']}</div>
</div>
</div>
</div>
""")

            render_module_gap()
            btn_cols = st.columns([1, 1.2])
            with btn_cols[0]:
                if st.button("New Application", key="step6_reset", use_container_width=True):
                    st.session_state.app_form_step = 1
                    st.session_state.submitted_assessment = None
                    st.rerun()
            with btn_cols[1]:
                if st.button("Inspect Decision Memo →", key="step6_view_memo", type="primary", use_container_width=True):
                    navigate_user("result", app_id=assessment['id'])
