"""
PARAKH Plotly Visualization Engine
Tailored, theme-aware financial data visualizations with zero visual clutter.
"""
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from utils.styling import get_theme_colors

def _get_chart_layout_base(theme: str = "dark") -> dict:
    """Returns baseline transparent layout parameters matching the active theme."""
    c = get_theme_colors(theme)
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {
            "family": "Plus Jakarta Sans, sans-serif",
            "color": c["text_secondary"],
            "size": 11
        },
        "margin": {"l": 20, "r": 20, "t": 30, "b": 20},
        "hoverlabel": {
            "bgcolor": c["surface_elevated"],
            "font_family": "Plus Jakarta Sans, sans-serif",
            "font_color": c["text_primary"],
            "bordercolor": c["border"]
        }
    }


def create_gauge_chart(score: int, min_val: int = 300, max_val: int = 850, theme: str = "dark") -> go.Figure:
    """Creates a sleek, modern semicircular gauge for the credit score."""
    c = get_theme_colors(theme)
    
    # Needle color based on score
    if score >= 720:
        bar_color = "#10B981"
    elif score >= 640:
        bar_color = "#F59E0B"
    else:
        bar_color = "#EF4444"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        number={
            'font': {'size': 44, 'family': 'JetBrains Mono, monospace', 'color': c["text_primary"]},
            'suffix': " / 850"
        },
        gauge={
            'axis': {'range': [min_val, max_val], 'tickwidth': 1, 'tickcolor': c["border"], 'tickfont': {'color': c["text_muted"], 'size': 9}},
            'bar': {'color': bar_color, 'thickness': 0.28},
            'bgcolor': c["surface_hover"],
            'borderwidth': 0,
            'steps': [
                {'range': [300, 620], 'color': "rgba(239, 68, 68, 0.18)"},
                {'range': [620, 719], 'color': "rgba(245, 158, 11, 0.18)"},
                {'range': [719, 850], 'color': "rgba(16, 185, 129, 0.18)"},
            ],
            'threshold': {
                'line': {'color': bar_color, 'width': 3},
                'thickness': 0.8,
                'value': score
            }
        }
    ))

    layout = _get_chart_layout_base(theme)
    layout["height"] = 240
    layout["margin"] = {"l": 10, "r": 10, "t": 20, "b": 10}
    fig.update_layout(**layout)
    return fig


def create_factor_impact_chart(factors: list, theme: str = "dark") -> go.Figure:
    """Creates a horizontal diverging impact bar chart (SHAP explanation)."""
    c = get_theme_colors(theme)
    
    features = [f["feature"] for f in reversed(factors)]
    impacts = [f["impact"] * 100 for f in reversed(factors)]  # scaled to points
    colors = ["#10B981" if imp >= 0 else "#EF4444" for imp in impacts]

    fig = go.Figure(go.Bar(
        x=impacts,
        y=features,
        orientation='h',
        marker=dict(
            color=colors,
            line=dict(width=0)
        ),
        text=[f"{'+' if i>0 else ''}{i:.1f} pts" for i in impacts],
        textposition="outside",
        textfont=dict(color=c["text_primary"], family="JetBrains Mono, monospace", size=10)
    ))

    layout = _get_chart_layout_base(theme)
    layout["height"] = max(240, len(factors) * 48)
    layout["margin"] = {"l": 180, "r": 50, "t": 20, "b": 20}
    layout["xaxis"] = dict(
        showgrid=True,
        gridcolor=c["border"],
        zeroline=True,
        zerolinecolor=c["text_muted"],
        zerolinewidth=1,
        title=dict(text="Impact on Credit Trust Score (Points)", font=dict(size=10, color=c["text_muted"]))
    )
    layout["yaxis"] = dict(
        showgrid=False,
        tickfont=dict(size=10, color=c["text_primary"])
    )
    fig.update_layout(**layout)
    return fig


def create_portfolio_trend_chart(df: pd.DataFrame, theme: str = "dark") -> go.Figure:
    """Creates a smooth area chart for application volumes and approvals."""
    c = get_theme_colors(theme)
    
    fig = go.Figure()

    # Total Applications area
    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Total Applications"],
        mode='lines',
        name='Total Volume',
        line=dict(width=2.5, color="#64748B"),
        stackgroup='one',
        fillcolor="rgba(100, 116, 139, 0.1)"
    ))

    # Approved applications line
    fig.add_trace(go.Scatter(
        x=df["Month"],
        y=df["Approved"],
        mode='lines+markers',
        name='Approved',
        line=dict(width=3, color=c["accent"]),
        marker=dict(size=6, color=c["accent"])
    ))

    layout = _get_chart_layout_base(theme)
    layout["height"] = 280
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    layout["xaxis"] = dict(showgrid=False, color=c["text_muted"])
    layout["yaxis"] = dict(showgrid=True, gridcolor=c["border"], color=c["text_muted"])
    fig.update_layout(**layout)
    return fig


def create_risk_distribution_donut(dist_dict: dict, theme: str = "dark") -> go.Figure:
    """Creates a modern donut chart for portfolio risk tiers."""
    c = get_theme_colors(theme)
    
    labels = list(dist_dict.keys())
    values = list(dist_dict.values())
    colors = ["#10B981", "#F59E0B", "#EF4444"]

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.68,
        marker=dict(colors=colors, line=dict(color=c["surface"], width=2)),
        textinfo='percent',
        textfont=dict(color="#FFFFFF", size=11, family="JetBrains Mono"),
        hoverinfo='label+percent+value'
    )])

    layout = _get_chart_layout_base(theme)
    layout["height"] = 260
    layout["showlegend"] = True
    layout["legend"] = dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5)
    layout["annotations"] = [{
        "text": "Risk Tiers",
        "font": {"size": 13, "family": "Plus Jakarta Sans", "color": c["text_primary"], "weight": "bold"},
        "showarrow": False,
        "x": 0.5,
        "y": 0.5
    }]
    fig.update_layout(**layout)
    return fig


def create_feature_importance_chart(features: list, theme: str = "dark") -> go.Figure:
    """Creates a horizontal ranking bar chart for global model explainability."""
    c = get_theme_colors(theme)
    
    names = [f["feature"] for f in reversed(features)]
    vals = [f["importance"] * 100 for f in reversed(features)]

    fig = go.Figure(go.Bar(
        x=vals,
        y=names,
        orientation='h',
        marker=dict(
            color=c["accent"],
            line=dict(width=0)
        ),
        text=[f"{v:.1f}%" for v in vals],
        textposition="outside",
        textfont=dict(color=c["text_primary"], family="JetBrains Mono", size=10)
    ))

    layout = _get_chart_layout_base(theme)
    layout["height"] = max(260, len(features) * 38)
    layout["margin"] = {"l": 220, "r": 40, "t": 10, "b": 30}
    layout["xaxis"] = dict(
        showgrid=True,
        gridcolor=c["border"],
        title=dict(text="Relative SHAP Weight (%)", font=dict(size=10, color=c["text_muted"]))
    )
    layout["yaxis"] = dict(showgrid=False, tickfont=dict(size=10, color=c["text_primary"]))
    fig.update_layout(**layout)
    return fig


def create_roc_curve_chart(fpr, tpr, auc: float, theme: str = "dark") -> go.Figure:
    """Creates an institutional ROC curve with AUC highlight."""
    c = get_theme_colors(theme)
    
    fig = go.Figure()
    
    # Baseline diagonal
    fig.add_trace(go.Scatter(
        x=[0, 1], y=[0, 1],
        mode='lines',
        name='Random Classifier (0.50)',
        line=dict(dash='dash', color=c["border"], width=1.5)
    ))

    # PARAKH Model curve
    fig.add_trace(go.Scatter(
        x=fpr, y=tpr,
        mode='lines',
        name=f'PARAKH Model (AUC = {auc:.3f})',
        line=dict(color=c["accent"], width=3),
        fill='tonexty',
        fillcolor=c["accent_glow"]
    ))

    layout = _get_chart_layout_base(theme)
    layout["height"] = 280
    layout["xaxis"] = dict(title="False Positive Rate (1 - Specificity)", showgrid=True, gridcolor=c["border"])
    layout["yaxis"] = dict(title="True Positive Rate (Sensitivity)", showgrid=True, gridcolor=c["border"])
    layout["legend"] = dict(yanchor="bottom", y=0.05, xanchor="right", x=0.95)
    fig.update_layout(**layout)
    return fig
