# generate_calibration_report_plotly.py
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from packaging.version import parse as vparse

# -------------------------------------------------------------------
# CONFIGURE THESE PATHS
summary_csv   = Path(r"D:\diagnostics\calibration_diagnostics\summary.csv")
report_html   = Path(r"D:\diagnostics\calibration_diagnostics\calibration_report.html")
# -------------------------------------------------------------------

# 1) load & prep ----------------------------------------------------
df = pd.read_csv(summary_csv)

df["version_key"] = df["version"].apply(vparse)
df = df.sort_values(["os", "version_key"])

EXPECTED = 58.0
OS_ORDER = ["Windows", "macOS", "Linux"]  # force visual order

# 2) FIGURE 1 – all OS, no error bars ------------------------------
fig1 = go.Figure()
for os_name in OS_ORDER:
    sub = df[df["os"].str.lower() == os_name.lower()]
    fig1.add_scatter(
        x=sub["version"],
        y=sub["mean_distance"],
        mode="lines+markers",
        name=os_name
    )
fig1.add_hline(y=EXPECTED, line_dash="dash", line_color="black")
fig1.update_layout(
    title="Mean Charuco Square Size – all operating systems",
    yaxis_title="Square-size estimate (mm)",
    xaxis_title="FreeMoCap version"
)

# 3) FIGURE 2 – post-1.6 in 3 sub-plots ----------------------------
post = df[df["version_key"] >= vparse("1.6.0")]

fig2 = make_subplots(rows=1, cols=3, shared_yaxes=True,
                     subplot_titles=OS_ORDER)

for col, os_name in enumerate(OS_ORDER, start=1):
    g = post[post["os"].str.lower() == os_name.lower()].sort_values("version_key")
    fig2.add_scatter(
        x=g["version"], y=g["mean_distance"],
        error_y=dict(type='data', array=g["std_distance"], visible=True),
        mode="markers",
        marker=dict(size=8),
        name=os_name,
        showlegend=False,
        row=1, col=col
    )
    # add annotations
    for xv, m, s in zip(g["version"], g["mean_distance"], g["std_distance"]):
        fig2.add_annotation(
            x=xv, y=m + 0.05,
            text=f"{m:.2f}±{s:.2f}",
            showarrow=False,
            yanchor="bottom",
            row=1, col=col,
            font=dict(size=10)
        )
    # 58-mm reference
    fig2.add_hline(y=EXPECTED, line_dash="dash", line_color="black",
                   row=1, col=col)

fig2.update_yaxes(range=[EXPECTED-3, EXPECTED+3],
                  title_text="Square-size estimate (mm)", row=1, col=1)
fig2.update_xaxes(title_text="Version", tickangle=45)
fig2.update_layout(title="Charuco Square Size Estimate – versions ≥ 1.6.0")

# 4) EXPORT single HTML -------------------------------------------
import plotly.io as pio, json, html

html_parts = [
    "<!DOCTYPE html><html><head><meta charset='utf-8'>",
    '<title>Calibration Diagnostics</title>',
    # include Plotly once via CDN
    '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>',
    '<style>body{font-family:Arial, sans-serif;margin:40px;}h1{color:#333}</style>',
    "</head><body>",
    "<h1>Calibration Diagnostics Report</h1>",
    "<h2>Mean Charuco Square Size (all OS)</h2>",
    pio.to_html(fig1, include_plotlyjs=False, full_html=False),
    "<hr>",
    "<h2>Square-size estimate – versions ≥ 1.6.0</h2>",
    pio.to_html(fig2, include_plotlyjs=False, full_html=False),
    "<p style='font-size:0.9em;'>Dashed line = expected size (58 mm). "
    "Error bars show ±1 SD; numerical values annotated.</p>",
    "</body></html>"
]
report_html.write_text("\n".join(html_parts), encoding="utf-8")
print(f"✅ Report written → {report_html}")
