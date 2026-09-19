"""
PARAKH Mock Data Engine
Provides high-fidelity, institutional-grade credit intelligence mock data
for retail, SME, and commercial lending scenarios.
"""
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Sample realistic applications registry
MOCK_APPLICATIONS = [
    {
        "id": "PRK-2026-8941",
        "applicant_name": "Aarav Mehta",
        "applicant_email": "aarav.mehta@techcorp.in",
        "avatar_initials": "AM",
        "employment_type": "Salaried - Senior Architect",
        "employer": "Infosys Technologies",
        "monthly_income": 285000,
        "loan_amount": 2500000,
        "loan_purpose": "Home Improvement & Solar",
        "tenure_months": 48,
        "credit_score": 785,
        "risk_category": "Low Risk",
        "risk_level": "low",
        "default_probability": 0.038,
        "status": "Approved",
        "submission_date": "2026-09-15",
        "debt_to_income": 0.18,
        "credit_utilization": 0.14,
        "existing_debt": 420000,
        "bank_balance": 980000,
        "bureau_history_years": 9.5,
        "late_payments_36m": 0,
        "recent_inquiries_6m": 1,
        "ai_memo": (
            "Applicant exhibits an exemplary credit profile characterized by a disciplined 9.5-year repayment history "
            "with zero 30+ DPD delinquencies. Debt-to-Income (DTI) of 18% is well below the portfolio conservative ceiling (35%). "
            "Liquid reserves cover 3.9x proposed EMI requirements. Instant unconditional approval recommended at prime risk tier."
        ),
        "risk_factors": [
            {"feature": "Historical Repayment Track Record", "impact": 0.32, "type": "positive", "detail": "100% on-time payments across 42 historical cycles"},
            {"feature": "Conservative Debt-to-Income (18%)", "impact": 0.26, "type": "positive", "detail": "Monthly obligation well within disposable liquidity"},
            {"feature": "Strong Liquid Cash Cushion", "impact": 0.19, "type": "positive", "detail": "Liquid balance of ₹9.8L covers 4+ months of total expenses"},
            {"feature": "High Credit Line Utilization (<15%)", "impact": 0.12, "type": "positive", "detail": "Revolving credit line utilization strictly contained"},
            {"feature": "Recent Hard Inquiries", "impact": -0.04, "type": "negative", "detail": "1 inquiry logged in the last 6 months"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-15 09:30 AM", "status": "done"},
            {"title": "Automated KYC & Bureau Pulled", "time": "2026-09-15 09:31 AM", "status": "done"},
            {"title": "PARAKH Neural Assessment Run", "time": "2026-09-15 09:32 AM", "status": "done"},
            {"title": "System Approved (Tier-1 Auto)", "time": "2026-09-15 09:33 AM", "status": "done"}
        ]
    },
    {
        "id": "PRK-2026-8942",
        "applicant_name": "Priya Nair",
        "applicant_email": "priya.nair@meridian.io",
        "avatar_initials": "PN",
        "employment_type": "Salaried - VP Marketing",
        "employer": "Meridian Media",
        "monthly_income": 190000,
        "loan_amount": 1200000,
        "loan_purpose": "Executive Education",
        "tenure_months": 36,
        "credit_score": 742,
        "risk_category": "Low Risk",
        "risk_level": "low",
        "default_probability": 0.12,
        "status": "Approved",
        "submission_date": "2026-09-16",
        "debt_to_income": 0.24,
        "credit_utilization": 0.22,
        "existing_debt": 310000,
        "bank_balance": 520000,
        "bureau_history_years": 7.0,
        "late_payments_36m": 0,
        "recent_inquiries_6m": 2,
        "ai_memo": (
            "Strong applicant with consistent salary credits and low revolving exposure. Employment stability is notable (4.2 years with current employer). "
            "Moderate educational funding request is commensurate with verified compensation level. Low default likelihood of 12% aligns with prime guidelines."
        ),
        "risk_factors": [
            {"feature": "Stable Career Tenure & Income", "impact": 0.24, "type": "positive", "detail": "Verified income with continuous employment tier"},
            {"feature": "Manageable Debt-to-Income (24%)", "impact": 0.18, "type": "positive", "detail": "Adequate disposable buffer post obligations"},
            {"feature": "Clean Bureau Track Record", "impact": 0.15, "type": "positive", "detail": "Zero defaults across all past personal loans"},
            {"feature": "Recent Credit Inquiries (2)", "impact": -0.07, "type": "negative", "detail": "2 inquiries in past 180 days on retail credit cards"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-16 11:15 AM", "status": "done"},
            {"title": "Automated Income Verification", "time": "2026-09-16 11:17 AM", "status": "done"},
            {"title": "PARAKH Neural Assessment Run", "time": "2026-09-16 11:18 AM", "status": "done"},
            {"title": "Approved by Automated Policy", "time": "2026-09-16 11:20 AM", "status": "done"}
        ]
    },
    {
        "id": "PRK-2026-8943",
        "applicant_name": "Vikram Malhotra",
        "applicant_email": "vikram@malhotralogistics.com",
        "avatar_initials": "VM",
        "employment_type": "Self-Employed - Fleet Operator",
        "employer": "Malhotra Logistics Pvt Ltd",
        "monthly_income": 340000,
        "loan_amount": 4500000,
        "loan_purpose": "Working Capital & Vehicle Fleet",
        "tenure_months": 60,
        "credit_score": 668,
        "risk_category": "Medium Risk",
        "risk_level": "medium",
        "default_probability": 0.28,
        "status": "Under Review",
        "submission_date": "2026-09-17",
        "debt_to_income": 0.42,
        "credit_utilization": 0.58,
        "existing_debt": 1850000,
        "bank_balance": 640000,
        "bureau_history_years": 8.2,
        "late_payments_36m": 1,
        "recent_inquiries_6m": 3,
        "ai_memo": (
            "Self-employed logistics operator displaying strong top-line business velocity but elevated leverage. Current DTI stands at 42% with credit card utilization at 58%. "
            "A single 30-day delinquency occurred 14 months ago during regional supply chain disruption. Recommended conditional approval subject to GST return verification and secondary collateral pledge."
        ),
        "risk_factors": [
            {"feature": "Substantial Business Turnover", "impact": 0.22, "type": "positive", "detail": "Average monthly bank inflow exceeds ₹3.4L"},
            {"feature": "Established Commercial Bureau", "impact": 0.14, "type": "positive", "detail": "Over 8 years in commercial credit ecosystem"},
            {"feature": "Elevated DTI Ratio (42%)", "impact": -0.21, "type": "negative", "detail": "Approaching portfolio tolerance threshold of 45%"},
            {"feature": "Credit Utilization at 58%", "impact": -0.16, "type": "negative", "detail": "Working capital limits actively drawn above 50%"},
            {"feature": "Single 30-day Delinquency (14m ago)", "impact": -0.11, "type": "negative", "detail": "Brief technical late payment recorded"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-17 02:45 PM", "status": "done"},
            {"title": "Automated GST & Bank Statement Extracted", "time": "2026-09-17 02:47 PM", "status": "done"},
            {"title": "Flagged for Secondary Analyst Inspection", "time": "2026-09-17 02:50 PM", "status": "active"},
            {"title": "Final Credit Committee Sign-off", "time": "Pending Review", "status": "pending"}
        ]
    },
    {
        "id": "PRK-2026-8944",
        "applicant_name": "Rohit Verma",
        "applicant_email": "rohit.ux@freelance.net",
        "avatar_initials": "RV",
        "employment_type": "Freelancer - UI/UX Designer",
        "employer": "Self-Employed",
        "monthly_income": 95000,
        "loan_amount": 800000,
        "loan_purpose": "Hardware Studio Upgrade",
        "tenure_months": 24,
        "credit_score": 582,
        "risk_category": "High Risk",
        "risk_level": "high",
        "default_probability": 0.54,
        "status": "High Risk",
        "submission_date": "2026-09-18",
        "debt_to_income": 0.56,
        "credit_utilization": 0.84,
        "existing_debt": 640000,
        "bank_balance": 45000,
        "bureau_history_years": 3.1,
        "late_payments_36m": 4,
        "recent_inquiries_6m": 6,
        "ai_memo": (
            "High default probability flagged (54%). High debt-to-income ratio (56%), revolving balance utilization at 84%, "
            "and 4 missed payments across the preceding 24 months. Recent inquiry spike (6 inquiries in 90 days) signals credit hunger. "
            "Automated system recommends decline or mandatory co-signer with collateral backstop."
        ),
        "risk_factors": [
            {"feature": "Revolving Line Utilization (84%)", "impact": -0.34, "type": "negative", "detail": "Revolving balances close to statutory limit"},
            {"feature": "Multiple Delinquencies (4 in 24m)", "impact": -0.28, "type": "negative", "detail": "Unresolved late payments in active bureau records"},
            {"feature": "Elevated DTI (56%)", "impact": -0.24, "type": "negative", "detail": "Over half of monthly earnings committed to servicing existing debt"},
            {"feature": "Inquiry Velocity Spike", "impact": -0.15, "type": "negative", "detail": "6 hard credit searches within trailing quarter"},
            {"feature": "Verified Freelance Contracts", "impact": 0.08, "type": "positive", "detail": "Demonstrated client contracts over past 12 months"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-18 10:10 AM", "status": "done"},
            {"title": "Automated Rule Engine Triggered", "time": "2026-09-18 10:11 AM", "status": "done"},
            {"title": "High Risk Classification Assigned", "time": "2026-09-18 10:12 AM", "status": "done"},
            {"title": "Referred to Fraud & Risk Desk", "time": "2026-09-18 10:15 AM", "status": "active"}
        ]
    },
    {
        "id": "PRK-2026-8945",
        "applicant_name": "Ananya Desai",
        "applicant_email": "ananya.desai@globalhealth.org",
        "avatar_initials": "AD",
        "employment_type": "Salaried - Clinical Director",
        "employer": "Apollo Global Health",
        "monthly_income": 220000,
        "loan_amount": 1800000,
        "loan_purpose": "Medical Practice Expansion",
        "tenure_months": 48,
        "credit_score": 710,
        "risk_category": "Low Risk",
        "risk_level": "low",
        "default_probability": 0.16,
        "status": "Approved",
        "submission_date": "2026-09-18",
        "debt_to_income": 0.28,
        "credit_utilization": 0.25,
        "existing_debt": 580000,
        "bank_balance": 820000,
        "bureau_history_years": 6.4,
        "late_payments_36m": 0,
        "recent_inquiries_6m": 1,
        "ai_memo": (
            "Healthcare sector specialist with consistent earnings trajectory and well-buffered liquidity. "
            "Debt service ratio is stable at 28%. No derogatory bureau events detected in 6+ years. Recommended approval."
        ),
        "risk_factors": [
            {"feature": "Healthcare Sector Recurrency", "impact": 0.21, "type": "positive", "detail": "High career security and resilient sector track"},
            {"feature": "Healthy Liquid Savings", "impact": 0.17, "type": "positive", "detail": "Substantial deposits in prime scheduled bank"},
            {"feature": "Balanced DTI Profile", "impact": 0.14, "type": "positive", "detail": "Sufficient net cash surplus post installment commitments"},
            {"feature": "Unsecured Exposure", "impact": -0.06, "type": "negative", "detail": "Existing balance includes personal loan tranche"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-18 04:20 PM", "status": "done"},
            {"title": "Medical License & KYC Validated", "time": "2026-09-18 04:22 PM", "status": "done"},
            {"title": "PARAKH Neural Assessment Run", "time": "2026-09-18 04:23 PM", "status": "done"},
            {"title": "Approved with Standard Pricing", "time": "2026-09-18 04:25 PM", "status": "done"}
        ]
    },
    {
        "id": "PRK-2026-8946",
        "applicant_name": "Karan Singhania",
        "applicant_email": "karan.s@singhaniatraders.in",
        "avatar_initials": "KS",
        "employment_type": "Self-Employed - Retail Trader",
        "employer": "Singhania Commodity Traders",
        "monthly_income": 140000,
        "loan_amount": 3200000,
        "loan_purpose": "Inventory Financing",
        "tenure_months": 36,
        "credit_score": 540,
        "risk_category": "High Risk",
        "risk_level": "high",
        "default_probability": 0.62,
        "status": "Rejected",
        "submission_date": "2026-09-19",
        "debt_to_income": 0.68,
        "credit_utilization": 0.91,
        "existing_debt": 2400000,
        "bank_balance": 35000,
        "bureau_history_years": 4.5,
        "late_payments_36m": 5,
        "recent_inquiries_6m": 7,
        "ai_memo": (
            "Severe over-leverage observed: Debt-to-income exceeds 68% with 91% credit utilization and multiple 60+ DPD delinquencies. "
            "Volatile cash flows and 7 recent bureau inquiries suggest acute liquidity stress. Decline policy mandatory."
        ),
        "risk_factors": [
            {"feature": "Excessive Debt Leverage (DTI 68%)", "impact": -0.38, "type": "negative", "detail": "Existing obligations exceed safe repayment threshold"},
            {"feature": "Credit Line Saturation (91%)", "impact": -0.32, "type": "negative", "detail": "Active credit lines nearly exhausted"},
            {"feature": "Repetitive Delinquencies", "impact": -0.27, "type": "negative", "detail": "5 late payment occurrences logged in past 36 months"},
            {"feature": "Credit Inquiries Density", "impact": -0.14, "type": "negative", "detail": "Aggressive borrowing activity over past 90 days"}
        ],
        "timeline": [
            {"title": "Application Initialized", "time": "2026-09-19 09:10 AM", "status": "done"},
            {"title": "High Default Warning Triggered", "time": "2026-09-19 09:12 AM", "status": "done"},
            {"title": "Automated Decline Executed", "time": "2026-09-19 09:15 AM", "status": "done"}
        ]
    }
]

# Admin Global Portfolio KPIs
ADMIN_PORTFOLIO_METRICS = {
    "total_applications": 1482,
    "total_applications_growth": "+14.8%",
    "under_review_count": 48,
    "approved_count": 1087,
    "approval_rate": "73.4%",
    "high_risk_flagged": 84,
    "high_risk_rate": "5.7%",
    "avg_credit_score": 714,
    "avg_decision_latency": "1.8 hrs",
    "traditional_latency": "48 hrs",
    "portfolio_default_rate": "2.1%",
    "portfolio_capital_deployed": "₹42.8 Cr",
}

# Model Governance & Explainability Metrics
MODEL_INSIGHTS_DATA = {
    "model_name": "PARAKH Neural Ensemble v3.4 (XGBoost + TabNet Hybrid)",
    "last_trained": "2026-09-10",
    "auc_roc": 0.942,
    "f1_score": 0.887,
    "ks_statistic": 48.6,
    "gini_coefficient": 0.884,
    "psi_stability": 0.038,  # Population Stability Index (<0.1 indicates perfect stability)
    "feature_importances": [
        {"feature": "Debt-to-Income (DTI) Ratio", "importance": 0.28, "category": "Obligations"},
        {"feature": "Historical Bureau Repayment Track (36m)", "importance": 0.22, "category": "Behavior"},
        {"feature": "Revolving Credit Line Utilization", "importance": 0.16, "category": "Liquidity"},
        {"feature": "Liquid Bank Balance to EMI Ratio", "importance": 0.13, "category": "Cash Flow"},
        {"feature": "Recent Bureau Inquiries (Trailing 6m)", "importance": 0.09, "category": "Velocity"},
        {"feature": "Verified Income & Career Stability", "importance": 0.07, "category": "Employment"},
        {"feature": "Collateral & Loan-to-Value (LTV)", "importance": 0.05, "category": "Collateral"}
    ],
    "risk_distribution": {
        "Low Risk (700-850)": 58,
        "Moderate Risk (620-699)": 28,
        "High Risk (<620)": 14
    }
}

# User Profile Mock
USER_PROFILE = {
    "name": "Aarav Mehta",
    "email": "aarav.mehta@techcorp.in",
    "phone": "+91 98450 12890",
    "pan_card": "ABCDE1234F",
    "aadhaar_masked": "XXXX-XXXX-8921",
    "kyc_status": "Verified (Tier 1 Digital)",
    "occupation": "Senior Staff Architect",
    "company": "Infosys Technologies",
    "work_location": "Bangalore, India",
    "active_application_id": "PRK-2026-8941",
    "total_credit_limit": "₹15,00,000",
    "linked_accounts": ["HDFC Bank (Salary)", "ICICI Bank (Investments)"]
}

# Admin Profile Mock
ADMIN_PROFILE = {
    "name": "Sarah Jenkins",
    "title": "Principal Credit Risk Officer",
    "department": "Institutional & Retail Underwriting",
    "badge_id": "PRK-CR-008",
    "role": "Super Admin",
    "clearance": "Level 4 (Full Discretionary Authority)",
    "email": "sarah.jenkins@parakh.fintech.ai"
}

def get_applications(search: str = "", status_filter: str = "All", risk_filter: str = "All") -> list:
    """Filter and search through the applications registry."""
    filtered = MOCK_APPLICATIONS.copy()
    
    if status_filter and status_filter != "All":
        filtered = [a for a in filtered if a["status"].lower() == status_filter.lower()]
        
    if risk_filter and risk_filter != "All":
        filtered = [a for a in filtered if a["risk_category"].lower() == risk_filter.lower()]
        
    if search:
        s = search.lower().strip()
        filtered = [
            a for a in filtered
            if s in a["applicant_name"].lower()
            or s in a["id"].lower()
            or s in a["employer"].lower()
            or s in a["loan_purpose"].lower()
        ]
        
    return filtered


def get_application_by_id(app_id: str) -> dict:
    """Retrieve an application by ID, or return default."""
    for a in MOCK_APPLICATIONS:
        if a["id"] == app_id:
            return a
    return MOCK_APPLICATIONS[0]


def calculate_dynamic_assessment(form_data: dict) -> dict:
    """
    Computes a realistic AI credit assessment simulation based on user input.
    Keeps everything strictly frontend-only with realistic heuristic scoring.
    """
    income = float(form_data.get("monthly_income", 150000))
    loan_amount = float(form_data.get("loan_amount", 1000000))
    existing_debt = float(form_data.get("existing_debt", 200000))
    tenure = int(form_data.get("tenure_months", 36))
    delinquencies = int(form_data.get("late_payments", 0))
    inquiries = int(form_data.get("recent_inquiries", 1))
    
    # Calculate simulated monthly EMI assuming 11% p.a.
    r = (0.11) / 12
    emi = (loan_amount * r * ((1 + r) ** tenure)) / (((1 + r) ** tenure) - 1)
    
    # DTI calculation
    monthly_existing_servicing = existing_debt * 0.03
    dti = (monthly_existing_servicing + emi) / max(income, 1)
    
    # Heuristic scoring engine (300 to 850 scale)
    base_score = 720
    
    # Income adjustments
    if income > 200000:
        base_score += 35
    elif income < 60000:
        base_score -= 50
        
    # DTI adjustments
    if dti < 0.25:
        base_score += 45
    elif dti > 0.50:
        base_score -= 85
    elif dti > 0.40:
        base_score -= 35
        
    # Delinquency penalty
    base_score -= (delinquencies * 45)
    
    # Inquiry penalty
    if inquiries > 4:
        base_score -= 30
    elif inquiries > 2:
        base_score -= 15
        
    # Clamp score
    credit_score = int(np.clip(base_score, 320, 845))
    
    # Default probability mapping
    if credit_score >= 740:
        risk_cat = "Low Risk"
        risk_level = "low"
        default_prob = round(0.02 + (850 - credit_score) * 0.0008, 3)
        status = "Approved"
    elif credit_score >= 640:
        risk_cat = "Medium Risk"
        risk_level = "medium"
        default_prob = round(0.18 + (740 - credit_score) * 0.002, 3)
        status = "Under Review"
    else:
        risk_cat = "High Risk"
        risk_level = "high"
        default_prob = round(0.45 + (640 - credit_score) * 0.0025, 3)
        default_prob = min(default_prob, 0.88)
        status = "High Risk"

    factors = []
    if dti <= 0.30:
        factors.append({"feature": f"Healthy Debt-to-Income Ratio ({dti*100:.1f}%)", "impact": 0.25, "type": "positive", "detail": "Commitments comfortably serviced by verified income"})
    else:
        factors.append({"feature": f"Elevated Debt-to-Income Ratio ({dti*100:.1f}%)", "impact": -0.24, "type": "negative", "detail": "Existing obligations create cash flow sensitivity"})
        
    if delinquencies == 0:
        factors.append({"feature": "Flawless Repayment Track Record", "impact": 0.28, "type": "positive", "detail": "Zero 30+ DPD bureau delinquencies across history"})
    else:
        factors.append({"feature": f"Recorded Delinquencies ({delinquencies} incident/s)", "impact": -0.32, "type": "negative", "detail": "Past missed payments penalize credit trust score"})
        
    if income >= 120000:
        factors.append({"feature": "Strong Monthly Income Capacity", "impact": 0.18, "type": "positive", "detail": f"Monthly inflow of ₹{income:,.0f} provides solid buffer"})
        
    if inquiries <= 2:
        factors.append({"feature": "Controlled Bureau Inquiries", "impact": 0.09, "type": "positive", "detail": "Low search velocity demonstrates disciplined credit appetite"})
    else:
        factors.append({"feature": "Elevated Bureau Inquiries", "impact": -0.14, "type": "negative", "detail": f"{inquiries} inquiries in recent months indicate credit appetite"})

    memo = (
        f"PARAKH Neural Ensemble evaluated the credit submission for ₹{loan_amount:,.0f}. "
        f"Simulated DTI of {dti*100:.1f}% combined with a computed credit score of {credit_score} points "
        f"categorizes this applicant into the {risk_cat} tier with a default probability of {default_prob*100:.1f}%. "
        f"{'Automatic pre-approval granted at standard tier pricing.' if risk_level == 'low' else 'Manual review or collateral verification recommended.'}"
    )

    new_id = f"PRK-2026-{np.random.randint(9000, 9999)}"
    
    return {
        "id": new_id,
        "applicant_name": form_data.get("full_name", "Demo Applicant"),
        "applicant_email": form_data.get("email", "demo@applicant.ai"),
        "avatar_initials": "".join([part[0].upper() for part in form_data.get("full_name", "Demo Applicant").split()][:2]),
        "employment_type": form_data.get("employment_type", "Salaried - Professional"),
        "employer": form_data.get("employer", "Global Enterprise Ltd"),
        "monthly_income": income,
        "loan_amount": loan_amount,
        "loan_purpose": form_data.get("loan_purpose", "Personal Capital"),
        "tenure_months": tenure,
        "credit_score": credit_score,
        "risk_category": risk_cat,
        "risk_level": risk_level,
        "default_probability": default_prob,
        "status": status,
        "submission_date": datetime.now().strftime("%Y-%m-%d"),
        "debt_to_income": round(dti, 2),
        "credit_utilization": 0.28,
        "existing_debt": existing_debt,
        "bank_balance": float(form_data.get("bank_balance", 450000)),
        "bureau_history_years": float(form_data.get("credit_history_years", 5)),
        "late_payments_36m": delinquencies,
        "recent_inquiries_6m": inquiries,
        "ai_memo": memo,
        "risk_factors": factors,
        "timeline": [
            {"title": "Application Initialized", "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "status": "done"},
            {"title": "Digital KYC & Income Verification", "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "status": "done"},
            {"title": "PARAKH Neural Ensemble Assessment", "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "status": "done"},
            {"title": f"Outcome: {status}", "time": datetime.now().strftime("%Y-%m-%d %I:%M %p"), "status": "done"}
        ]
    }


def get_portfolio_trends() -> pd.DataFrame:
    """Returns monthly application trends data."""
    months = ["Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026"]
    return pd.DataFrame({
        "Month": months,
        "Total Applications": [180, 215, 240, 275, 310, 362],
        "Approved": [132, 160, 178, 204, 230, 268],
        "High Risk Flagged": [14, 18, 16, 21, 22, 23],
        "Avg Score": [706, 710, 712, 715, 714, 718]
    })


def get_roc_curve_data() -> tuple:
    """Returns sample FPR and TPR arrays for the ROC curve."""
    fpr = np.linspace(0, 1, 100)
    tpr = 1 - (1 - fpr) ** 3.5  # Creates a sharp, high-AUC curve (~0.942)
    return fpr, tpr
