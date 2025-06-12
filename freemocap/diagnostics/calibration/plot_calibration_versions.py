# generate_calibration_report_plotly.py
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from packaging.version import parse as vparse
import plotly.io as pio

# -------------------------------------------------------------------
# CONFIGURE THESE PATHS
summary_csv   = Path(r"D:\diagnostics\calibration_diagnostics\summary.csv")
report_html   = Path(r"D:\diagnostics\calibration_diagnostics\calibration_report.html")
# -------------------------------------------------------------------

# 1) Load & prep ----------------------------------------------------
df = pd.read_csv(summary_csv)
EXPECTED = 58.0
OS_ORDER = ["Windows", "macOS", "Linux"]

df["version_key"] = df["version"].apply(vparse)
df = df.sort_values(["os", "version_key"])
df["mean_error"] = df["mean_distance"] - EXPECTED

# 2) FIGURE 1 – mean distance (no error bars) -----------------------
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
    title="Mean Charuco Square Size (mm) – all operating systems",
    yaxis_title="Square Size Estimate (mm)",
    xaxis_title="FreeMoCap Version",
    title_font=dict(size=20),
    xaxis_title_font=dict(size=22),
    yaxis_title_font=dict(size=20),
    xaxis_tickfont=dict(size=20),
    yaxis_tickfont=dict(size=18),
)

# 3) FIGURE 2 – per OS post-1.6.0, with error bars ------------------
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
        showlegend=False,
        row=1, col=col
    )
    # annotate values
    for xv, m, s in zip(g["version"], g["mean_distance"], g["std_distance"]):
        fig2.add_annotation(
            x=xv, y=m + 0.05,
            text=f"{m:.2f}±{s:.2f}",
            showarrow=False, yanchor="bottom",
            row=1, col=col, font=dict(size=10)
        )
    # dashed ref line
    fig2.add_hline(y=EXPECTED, line_dash="dash", line_color="black",
                   row=1, col=col)

# apply font sizes to each subplot axis
for i in range(1, 4):
    fig2.update_xaxes(
        tickfont=dict(size=20),
        title_font=dict(size=22),
        title_text="Version",
        row=1, col=i
    )

fig2.update_yaxes(
    tickfont=dict(size=18),
    title_font=dict(size=20),
    range=[EXPECTED-3, EXPECTED+3],
    title_text="Square-size estimate (mm)",
    row=1, col=1
)

fig2.update_layout(
    title="Charuco Square Size Estimate – versions ≥ 1.6.0",
    title_font=dict(size=20)
)

# 4) FIGURE 3 – mean error plot ------------------------------------
fig3 = go.Figure()
for os_name, group in post.groupby("os"):
    fig3.add_trace(go.Scatter(
        x=group["version"],
        y=group["mean_error"],
        mode="lines+markers",
        name=os_name
    ))
fig3.update_layout(
    title="Mean Error in Square Size Estimate (Post v1.6.0)",
    yaxis_title="Mean error (mm)",
    xaxis_title="FreeMoCap version",
    height=400,
    xaxis_title_font=dict(size=22),
    yaxis_title_font=dict(size=20),
    xaxis_tickfont=dict(size=20),
    yaxis_tickfont=dict(size=18),
)

# 5) TABLE – latest calibration summary ----------------------------
latest = df.sort_values("version_key").groupby("os").tail(1)
table = go.Figure(data=[go.Table(
    header=dict(
        values=["OS", "Mean Square Size ± SD (mm)", "Mean Error (mm)"],
        fill_color='lightgray',
        align='center',
        font=dict(size=18)
    ),
    cells=dict(
        values=[
            latest["os"],
            [f"{m:.2f} ± {s:.2f}" for m, s in zip(latest["mean_distance"], latest["std_distance"])],
            [f"{e:.2f}" for e in latest["mean_error"]]
        ],
        align="center",
        font=dict(size=16),
        height=30,
        fill_color='#f8f9fa'  # subtle light fill
    )
)])
table.update_layout(
    title="Latest Calibration Summary (per OS)",
    margin=dict(t=60, l=0, r=0),
    height=250
)

# 6) Assemble HTML --------------------------------------------------
html_parts = [
    "<!DOCTYPE html><html><head><meta charset='utf-8'>",
    "<title>Calibration Diagnostics</title>",
    "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>",
    "<style>body{font-family:Arial,sans-serif;margin:40px;}h1{color:#333}</style>",
    "</head><body>",
    "<h1>Calibration Diagnostics Report</h1>",

    "<hr><h2>Latest Calibration Summary (per OS)</h2>",
    "<p>Expected square size: <strong> {square_size}mm </strong> </p>".format(square_size=EXPECTED),
    "<div style='max-width:1200px; margin:auto;'>"
    + pio.to_html(table, include_plotlyjs=False, full_html=False)
    + "</div>"


    "<h2>Mean Charuco Square Size Per OS </h2>",
    pio.to_html(fig1, include_plotlyjs=False, full_html=False),
    "<p style='font-size:0.9em;'> Dashed line = expected size. "
    "Error bars show ±1 SD; </p>",

    "<hr><h2>Mean Charuco Square Size – versions ≥ 1.6.0 </h2>",
    pio.to_html(fig2, include_plotlyjs=False, full_html=False),
    "<p style='font-size:0.9em;'>Dashed line = expected size. "
    "Error bars show ±1 SD; numerical values annotated.</p>",

    "<hr><h2>Mean Square Size Error – versions ≥ 1.6.0</h2>",
    pio.to_html(fig3, include_plotlyjs=False, full_html=False),



    "</body></html>"
]

report_html.write_text("\n".join(html_parts), encoding="utf-8")
print(f"✅ Report written → {report_html}")
