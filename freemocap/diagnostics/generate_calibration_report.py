from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from jinja2 import Template
from packaging.version import parse as vparse, Version
import sys

CURRENT_SENTINEL = Version("9999.0.0")   # big so it always sorts "latest"

EXPECTED = 58.0
OS_ORDER = ["Windows", "macOS", "Linux"]

def safe_parse(ver: str) -> Version:
    """
    Parse semantic versions; return a giant sentinel for the tag 'current'
    so it always sorts last (most recent) and passes numeric comparisons.
    """
    return CURRENT_SENTINEL if ver == "current" else vparse(ver)

def load_summary_data():
    # Try to find the CSV in multiple locations
    possible_paths = [
        Path("freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv"),
        Path("calibration_diagnostics_summary.csv"),
        Path.cwd() / "freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv",
    ]
    
    summary_csv = None
    for path in possible_paths:
        if path.exists():
            summary_csv = path
            break
    
    if summary_csv is None:
        print(f"Could not find calibration_diagnostics_summary.csv in any of these locations:")
        for path in possible_paths:
            print(f"  - {path.absolute()}")
        sys.exit(1)
    
    print(f"Loading data from: {summary_csv}")
    df = pd.read_csv(summary_csv)
    
    # Standardize OS names
    df["os"] = df["os"].str.strip()
    
    # Add version_key for sorting
    df["version_key"] = df["version"].apply(safe_parse)
    
    # Calculate mean_error if not present
    if "mean_error" not in df.columns:
        df["mean_error"] = df["mean_distance"] - EXPECTED
    
    # Sort by OS and version (ascending OS, ascending version)
    df = df.sort_values(["os", "version_key"], ascending=[True, True])
    
    print(f"Loaded {len(df)} rows")
    print(f"OS values: {df['os'].unique()}")
    print(f"Version values: {df['version'].unique()}")
    
    return df

def generate_figures(df):
    # Figure 1 – All OS mean distance over all versions
    fig1 = go.Figure()
    
    for os_name in OS_ORDER:
        # Filter and sort data for this OS
        os_df = df[df["os"] == os_name].sort_values("version_key")
        
        if len(os_df) > 0:
            fig1.add_scatter(
                x=os_df["version"], 
                y=os_df["mean_distance"],
                mode="lines+markers", 
                name=os_name,
                line=dict(width=2),
                marker=dict(size=8)
            )
    
    fig1.add_hline(y=EXPECTED, line_dash="dash", line_color="black", 
                   annotation_text="Expected size", annotation_position="top right")
    
    fig1.update_layout(
        title="Mean Charuco Square Size (mm) – all operating systems",
        yaxis_title="Square Size Estimate (mm)",
        xaxis_title="FreeMoCap Version",
        title_font=dict(size=20),
        xaxis_title_font=dict(size=22),
        yaxis_title_font=dict(size=20),
        xaxis_tickfont=dict(size=16),
        yaxis_tickfont=dict(size=18),
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, xanchor="left", yanchor="top")
    )

    # Figure 2 – Per OS, post-1.6.0
    # Filter for versions >= 1.6.0 (including "current")
    post = df[(df["version_key"] >= vparse("1.6.0")) | (df["version"] == "current")]
    
    fig2 = make_subplots(rows=1, cols=3, shared_yaxes=True, 
                         subplot_titles=OS_ORDER,
                         horizontal_spacing=0.1)
    
    for col, os_name in enumerate(OS_ORDER, start=1):
        # Get data for this OS and sort by version
        os_data = post[post["os"] == os_name].sort_values("version_key")
        
        if len(os_data) > 0:
            # Add scatter plot with error bars
            fig2.add_scatter(
                x=os_data["version"], 
                y=os_data["mean_distance"],
                error_y=dict(
                    type='data', 
                    array=os_data["std_distance"], 
                    visible=True,
                    width=4,
                    thickness=2
                ),
                mode="markers", 
                marker=dict(size=10, color=f"rgb({col*70}, {100+col*30}, {200-col*50})"),
                showlegend=False, 
                row=1, 
                col=col
            )
            
            # Add value annotations
            for _, row in os_data.iterrows():
                fig2.add_annotation(
                    x=row["version"], 
                    y=row["mean_distance"] + row["std_distance"] + 0.3,
                    text=f"{row['mean_distance']:.2f}±{row['std_distance']:.2f}", 
                    showarrow=False,
                    yanchor="bottom", 
                    row=1, 
                    col=col,
                    font=dict(size=10)
                )
        
        # Add expected line
        fig2.add_hline(y=EXPECTED, line_dash="dash", line_color="black", 
                       row=1, col=col)
        
        # Update x-axis
        fig2.update_xaxes(
            tickfont=dict(size=14),
            title_font=dict(size=16),
            title_text="Version",
            row=1, col=col
        )
    
    # Update y-axis (only for first subplot)
    fig2.update_yaxes(
        tickfont=dict(size=14),
        title_font=dict(size=16),
        title_text="Square-size estimate (mm)",
        range=[EXPECTED - 3, EXPECTED + 3],
        row=1, col=1
    )
    
    fig2.update_layout(
        title="Charuco Square Size Estimate – versions ≥ 1.6.0",
        title_font=dict(size=20),
        height=400
    )

    # Figure 3 – Mean error plot
    fig3 = go.Figure()
    
    for os_name in OS_ORDER:
        os_data = post[post["os"] == os_name].sort_values("version_key")
        
        if len(os_data) > 0:
            fig3.add_trace(go.Scatter(
                x=os_data["version"], 
                y=os_data["mean_error"],
                mode="lines+markers", 
                name=os_name,
                line=dict(width=2),
                marker=dict(size=8)
            ))
    
    fig3.add_hline(y=0, line_dash="dot", line_color="gray", 
                   annotation_text="No error", annotation_position="top right")
    
    fig3.update_layout(
        title="Mean Error in Square Size Estimate (Post v1.6.0)",
        yaxis_title="Mean error (mm)", 
        xaxis_title="FreeMoCap version",
        height=400,
        xaxis_title_font=dict(size=22),
        yaxis_title_font=dict(size=20),
        xaxis_tickfont=dict(size=16),
        yaxis_tickfont=dict(size=18),
        showlegend=True,
        legend=dict(x=0.02, y=0.98, xanchor="left", yanchor="top")
    )

    return fig1, fig2, fig3

def generate_summary_table(df):
    # Get the latest data for each OS (highest version_key)
    latest = df.sort_values("version_key", ascending=False).groupby("os").first().reset_index()
    
    # Ensure OS order
    latest = latest.set_index('os').reindex(OS_ORDER).reset_index()
    
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
            fill_color='#f8f9fa'
        )
    )])
    
    table.update_layout(
        title="Latest Calibration Summary (per OS)",
        margin=dict(t=60, l=0, r=0),
        height=250
    )
    
    return table

def generate_html_report(df, output_path="freemocap/diagnostics/calibration_diagnostics.html"):
    fig1, fig2, fig3 = generate_figures(df)
    table = generate_summary_table(df)

    template = Template("""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset='utf-8'>
        <title>Calibration Diagnostics Report</title>
        <script src='https://cdn.plot.ly/plotly-latest.min.js'></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; }
            h1 { color: #333; }
            .plot-container { margin: 20px 0; }
        </style>
    </head>
    <body>
        <h1>Calibration Diagnostics Report</h1>

        <hr><h2>Latest Calibration Summary (per OS)</h2>
        <p>Expected square size: <strong>{{ expected }} mm</strong></p>
        <div style='max-width:1200px; margin:auto;'>{{ table|safe }}</div>

        <hr><h2>Mean Charuco Square Size Per OS</h2>
        <div class="plot-container">{{ fig1|safe }}</div>
        <p style='font-size:0.9em;'>Dashed line = expected size.</p>

        <hr><h2>Mean Charuco Square Size – versions ≥ 1.6.0</h2>
        <div class="plot-container">{{ fig2|safe }}</div>
        <p style='font-size:0.9em;'>Error bars show ±1 SD; numerical values annotated.</p>

        <hr><h2>Mean Square Size Error – versions ≥ 1.6.0</h2>
        <div class="plot-container">{{ fig3|safe }}</div>
    </body>
    </html>
    """)

    rendered = template.render(
        fig1=pio.to_html(fig1, include_plotlyjs=False, full_html=False),
        fig2=pio.to_html(fig2, include_plotlyjs=False, full_html=False),
        fig3=pio.to_html(fig3, include_plotlyjs=False, full_html=False),
        table=pio.to_html(table, include_plotlyjs=False, full_html=False),
        expected=EXPECTED
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(rendered, encoding="utf-8")
    print(f"✅ Calibration report written to: {output_file.absolute()}")

if __name__ == "__main__":
    df = load_summary_data()
    generate_html_report(df)