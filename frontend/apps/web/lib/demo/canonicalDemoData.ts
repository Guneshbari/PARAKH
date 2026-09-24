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
      status: "PASS — AUDIT VALIDATED",
      demographicParityRatio: 0.93,
      equalOpportunityDifference: 0.024,
      targetCriteria: "0.80 – 1.25 DPR",
      ruleFramework: "Four-Fifths Rule (80% Rule)",
      evaluationStandard: "Fairlearn Protocol 0.97",
      guidance: "RBI Fair Lending Practices & DPDP Act Data Minimization",
      lastEvaluated: "2026-09-24T00:00:00.000Z",
      sampleEvaluatedCount: 1673,
      overallAssessment: "No algorithmic disparate impact detected across gig worker cohorts, geographies, or inclusion proxies.",
      benchmarkRange: {
        min: 0.80,
        max: 1.25,
        parity: 1.00,
        current: 0.93
      },
      categories: [
        {
          id: "gig_sectors",
          name: "Gig Work Sectors",
          icon: "Building2",
          description: "Audited across informal platform occupations to verify income volatility normalization does not systematically penalize specific worker segments.",
          dpr: 0.93,
          eod: 0.021,
          subgroups: [
            {
              name: "Delivery",
              sampleCount: 628,
              favorableRate: 88.7,
              selectionRate: 11.3,
              parityRatio: 0.93,
              truePositiveRate: 74.4,
              falsePositiveRate: 1.8,
              status: "Compliant"
            },
            {
              name: "Ride Hailing",
              sampleCount: 614,
              favorableRate: 91.2,
              selectionRate: 8.8,
              parityRatio: 0.96,
              truePositiveRate: 69.4,
              falsePositiveRate: 0.7,
              status: "Compliant"
            },
            {
              name: "Logistics",
              sampleCount: 215,
              favorableRate: 86.5,
              selectionRate: 13.5,
              parityRatio: 0.91,
              truePositiveRate: 89.7,
              falsePositiveRate: 1.6,
              status: "Compliant"
            },
            {
              name: "Home Services",
              sampleCount: 144,
              favorableRate: 89.6,
              selectionRate: 10.4,
              parityRatio: 0.94,
              truePositiveRate: 60.9,
              falsePositiveRate: 0.8,
              status: "Compliant"
            },
            {
              name: "Freelance & Micro",
              sampleCount: 72,
              favorableRate: 93.1,
              selectionRate: 6.9,
              parityRatio: 0.98,
              truePositiveRate: 66.7,
              falsePositiveRate: 1.5,
              status: "Compliant"
            }
          ]
        },
        {
          id: "geography",
          name: "Regional Geographies",
          icon: "MapPin",
          description: "Zonal distribution across metro and non-metro corridors ensuring workers outside Tier-1 hubs receive non-discriminatory alternative credit access.",
          dpr: 0.94,
          eod: 0.019,
          subgroups: [
            {
              name: "Tier 1 Metro (Mumbai, Delhi, BLR)",
              sampleCount: 740,
              favorableRate: 91.1,
              selectionRate: 8.9,
              parityRatio: 0.96,
              truePositiveRate: 75.1,
              falsePositiveRate: 1.2,
              status: "Compliant"
            },
            {
              name: "Tier 2 Urban (Pune, Jaipur, Kochi)",
              sampleCount: 580,
              favorableRate: 89.4,
              selectionRate: 10.6,
              parityRatio: 0.94,
              truePositiveRate: 72.8,
              falsePositiveRate: 1.4,
              status: "Compliant"
            },
            {
              name: "Tier 3 Semi-Urban / Rural Corridors",
              sampleCount: 353,
              favorableRate: 87.8,
              selectionRate: 12.2,
              parityRatio: 0.92,
              truePositiveRate: 71.0,
              falsePositiveRate: 1.7,
              status: "Compliant"
            }
          ]
        },
        {
          id: "inclusion",
          name: "Inclusion & Tenacity Cohorts",
          icon: "Users",
          description: "Synthetic proxy groups for under-banked earners, assessing whether thin credit histories are treated equitably through platform longevity metrics.",
          dpr: 0.95,
          eod: 0.018,
          subgroups: [
            {
              name: "Women Gig Earners",
              sampleCount: 312,
              favorableRate: 90.7,
              selectionRate: 9.3,
              parityRatio: 0.95,
              truePositiveRate: 73.2,
              falsePositiveRate: 1.1,
              status: "Compliant"
            },
            {
              name: "Men Gig Earners",
              sampleCount: 1361,
              favorableRate: 89.7,
              selectionRate: 10.3,
              parityRatio: 0.94,
              truePositiveRate: 73.8,
              falsePositiveRate: 1.3,
              status: "Compliant"
            },
            {
              name: "New-to-Credit (<6 Mo Experience)",
              sampleCount: 428,
              favorableRate: 88.5,
              selectionRate: 11.5,
              parityRatio: 0.93,
              truePositiveRate: 70.4,
              falsePositiveRate: 1.9,
              status: "Compliant"
            }
          ]
        }
      ]
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
