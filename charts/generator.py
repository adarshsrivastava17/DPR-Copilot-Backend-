"""Chart generator using Plotly for DPR visualizations."""
import os
import plotly.graph_objects as go
from config import get_settings

settings = get_settings()

# Colors
NAVY = "#003366"
TEAL = "#006699"
GOLD = "#CC9900"
COLORS = ["#003366", "#006699", "#CC9900", "#339966", "#CC3333", "#9933CC", "#FF6600"]


def generate_revenue_chart(projections: list, report_id: str) -> str:
    """Generate a revenue growth bar chart."""
    years = [f"Year {p['year']}" for p in projections]
    revenues = [p["revenue"] for p in projections]
    profits = [p["net_profit"] for p in projections]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="Revenue", x=years, y=revenues, marker_color=NAVY))
    fig.add_trace(go.Bar(name="Net Profit", x=years, y=profits, marker_color=GOLD))

    fig.update_layout(
        title="Revenue & Profit Projections",
        xaxis_title="Year",
        yaxis_title="Amount (₹)",
        barmode="group",
        template="plotly_white",
        font=dict(family="Helvetica", size=12),
        plot_bgcolor="white",
    )

    path = os.path.join(settings.CHARTS_DIR, f"{report_id}_revenue.png")
    os.makedirs(settings.CHARTS_DIR, exist_ok=True)
    fig.write_image(path, width=800, height=450)
    return path


def generate_cost_breakdown_chart(project_cost: dict, report_id: str) -> str:
    """Generate a project cost breakdown pie chart."""
    labels = []
    values = []
    label_map = {
        "land_and_site": "Land & Site",
        "building_civil": "Building",
        "plant_machinery": "Plant & Machinery",
        "misc_fixed_assets": "Misc Assets",
        "preoperative_expenses": "Pre-operative",
        "contingency": "Contingency",
        "working_capital_margin": "Working Capital",
    }

    for key, label in label_map.items():
        if key in project_cost and project_cost[key] > 0:
            labels.append(label)
            values.append(project_cost[key])

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=COLORS[:len(labels)],
        textinfo="percent+label",
    )])

    fig.update_layout(
        title="Project Cost Breakdown",
        template="plotly_white",
        font=dict(family="Helvetica", size=12),
    )

    path = os.path.join(settings.CHARTS_DIR, f"{report_id}_cost.png")
    os.makedirs(settings.CHARTS_DIR, exist_ok=True)
    fig.write_image(path, width=800, height=450)
    return path


def generate_profitability_chart(projections: list, report_id: str) -> str:
    """Generate a profitability trend line chart."""
    years = [f"Year {p['year']}" for p in projections]
    margins = [float(p["net_profit_margin"].replace("%", "")) for p in projections]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=years, y=margins, mode="lines+markers",
        name="Net Profit Margin %",
        line=dict(color=TEAL, width=3),
        marker=dict(size=10),
    ))

    fig.update_layout(
        title="Profitability Trend",
        xaxis_title="Year",
        yaxis_title="Net Profit Margin (%)",
        template="plotly_white",
        font=dict(family="Helvetica", size=12),
    )

    path = os.path.join(settings.CHARTS_DIR, f"{report_id}_profitability.png")
    os.makedirs(settings.CHARTS_DIR, exist_ok=True)
    fig.write_image(path, width=800, height=450)
    return path
