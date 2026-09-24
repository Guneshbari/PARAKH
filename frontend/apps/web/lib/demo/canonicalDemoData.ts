export const canonicalDemoData = {
  mlInsights: {
    globalFeatures: [
      {
        id: "feat-1",
        name: "Cashflow Volatility & Buffer",
        description: "Weighted coefficient of variation across rolling 90-day UPI and AA banking inflow cycles.",
        importance: 0.45
      },
      {
        id: "feat-2",
        name: "Platform Continuity & Rating",
        description: "Tenure, active payout frequency, and partner performance metrics across verified gig platforms.",
        importance: 0.25
      },
      {
        id: "feat-3",
        name: "Multi-Gig Income Resilience",
        description: "Diversification index across delivery, mobility, and home services streams mitigating sector shocks.",
        importance: 0.15
      },
      {
        id: "feat-4",
        name: "BBPS Utility Payment Cadence",
        description: "Consistency of recurring electricity, telecom, and municipal utility payments via NPCI BBPS.",
        importance: 0.15
      }
    ],
    fairness: {
      status: "PASS",
      demographicParityRatio: 0.92,
      protectedGroups: ["Female", "Rural", "New to Credit"],
      lastEvaluated: new Date().toISOString()
    }
  },
  alerts: {
    operational: [
      {
        id: "alert-1",
        title: "Priority Review Queue Inflow Alerts",
        description: "Receive immediate desktop alerts when an application is flagged with INSUFFICIENT EVIDENCE / MANUAL REVIEW.",
        active: true
      },
      {
        id: "alert-2",
        title: "Monsoon & Seasonal Extreme Variance Warnings",
        description: "Notifies when regional rain dips exceed 30% to prevent misattribution of weather shocks to applicant distress.",
        active: false
      },
      {
        id: "alert-3",
        title: "Algorithmic Demographic Parity Drift Alerts",
        description: "Automatic escalation if Fairlearn demographic parity ratio falls below 0.85 across any gig cohort.",
        active: true
      }
    ]
  }
};
