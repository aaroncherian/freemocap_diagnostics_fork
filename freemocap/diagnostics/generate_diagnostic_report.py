from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
from jinja2 import Template
from packaging.version import parse as vparse, Version
import sys

CURRENT_SENTINEL = Version("9999.0.0")
EXPECTED = 58.0
OS_ORDER = ["Windows", "macOS", "Linux"]

def safe_parse(ver: str) -> Version:
    """Parse semantic versions; return a giant sentinel for 'current'"""
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
        print(f"Could not find calibration_diagnostics_summary.csv")
        sys.exit(1)
    
    df = pd.read_csv(summary_csv)
    
    # Remove any duplicates
    df = df.drop_duplicates(subset=['os', 'version'], keep='last')
    
    # Standardize OS names
    df["os"] = df["os"].str.strip()
    
    # Add version_key for sorting
    df["version_key"] = df["version"].apply(safe_parse)
    
    # Calculate mean_error if not present
    if "mean_error" not in df.columns:
        df["mean_error"] = df["mean_distance"] - EXPECTED
    
    return df

def generate_figures(df):
    # Get all versions in sorted order
    all_versions = df['version'].unique().tolist()
    
    # Separate 'current' from version numbers
    current_version = 'current' if 'current' in all_versions else None
    numeric_versions = [v for v in all_versions if v != 'current']
    
    # Sort using packaging.version.Version
    sorted_versions = sorted(numeric_versions, key=vparse)
    
    # Add 'current' at the end if it exists
    if current_version:
        sorted_versions.append(current_version)
    
    # Create a custom mapping for sorting
    version_to_index = {v: i for i, v in enumerate(sorted_versions)}
    
    # Add a sort key to the dataframe
    df['sort_key'] = df['version'].map(version_to_index)
    
    # Figure 1 – All OS mean distance over all versions
    fig1 = go.Figure()
    
    # Process each OS separately and add traces
    for os_name in OS_ORDER:
        os_data = df[df['os'] == os_name].copy()
        # Sort by our custom sort key
        os_data = os_data.sort_values('sort_key')
        
        if len(os_data) > 0:
            fig1.add_trace(go.Scatter(
                x=os_data['version'],
                y=os_data['mean_distance'],
                mode='lines+markers',
                name=os_name,
                connectgaps=True,
                line=dict(width=2),
                marker=dict(size=8)
            ))
    
    # Add expected line
    fig1.add_hline(y=EXPECTED, line_dash="dash", line_color="black", 
                   annotation_text="Expected size", annotation_position="top right")
    
    # Update layout with proper category ordering
    fig1.update_layout(
        title="Mean Charuco Square Size (mm) – all operating systems",
        xaxis=dict(
            title="FreeMoCap Version",
            type='category',
            categoryorder='array',
            categoryarray=sorted_versions,
            tickfont=dict(size=16),
            title_font=dict(size=22)
        ),
        yaxis=dict(
            title="Square Size Estimate (mm)",
            tickfont=dict(size=18),
            title_font=dict(size=20)
        ),
        title_font=dict(size=20),
        height=500,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, xanchor="left", yanchor="top")
    )

    # Figure 2 – Per OS, post-1.6.0
    # Filter for versions >= 1.6.0 
    post_versions = [v for v in sorted_versions if v == 'current' or (v != 'current' and vparse(v) >= vparse("1.6.0"))]
    post = df[df['version'].isin(post_versions)]
    
    fig2 = make_subplots(rows=1, cols=3, shared_yaxes=True, 
                         subplot_titles=OS_ORDER,
                         horizontal_spacing=0.1)
    
    for col, os_name in enumerate(OS_ORDER, start=1):
        os_data = post[post["os"] == os_name].copy()
        os_data = os_data.sort_values('sort_key')
        
        if len(os_data) > 0:
            # Add scatter plot with error bars
            fig2.add_trace(go.Scatter(
                x=os_data['version'],
                y=os_data['mean_distance'],
                error_y=dict(
                    type='data',
                    array=os_data['std_distance'],
                    visible=True,
                    width=4,
                    thickness=2
                ),
                mode='markers',
                marker=dict(size=10, color=f"rgb({col*70}, {100+col*30}, {200-col*50})"),
                showlegend=False
            ), row=1, col=col)
            
            # Add value annotations
            for _, row in os_data.iterrows():
                fig2.add_annotation(
                    x=row['version'],
                    y=row['mean_distance'] + row['std_distance'] + 0.3,
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
        
        # Update x-axis with category ordering
        fig2.update_xaxes(
            tickfont=dict(size=14),
            title_font=dict(size=16),
            title_text="Version",
            type='category',
            categoryorder='array',
            categoryarray=post_versions,
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
        os_data = post[post["os"] == os_name].copy()
        os_data = os_data.sort_values('sort_key')
        
        if len(os_data) > 0:
            fig3.add_trace(go.Scatter(
                x=os_data['version'],
                y=os_data['mean_error'],
                mode='lines+markers',
                name=os_name,
                connectgaps=True,
                line=dict(width=2),
                marker=dict(size=8)
            ))
    
    fig3.add_hline(y=0, line_dash="dot", line_color="gray", 
                   annotation_text="No error", annotation_position="top right")
    
    fig3.update_layout(
        title="Mean Error in Square Size Estimate (Post v1.6.0)",
        xaxis=dict(
            title="FreeMoCap version",
            type='category',
            categoryorder='array',
            categoryarray=post_versions,
            tickfont=dict(size=16),
            title_font=dict(size=22)
        ),
        yaxis=dict(
            title="Mean error (mm)",
            tickfont=dict(size=18),
            title_font=dict(size=20)
        ),
        height=400,
        showlegend=True,
        legend=dict(x=0.02, y=0.98, xanchor="left", yanchor="top")
    )

    return fig1, fig2, fig3

def generate_summary_table(df):
    # Get the latest data for each OS
    latest_rows = []
    for os_name in OS_ORDER:
        os_df = df[df["os"] == os_name]
        if len(os_df) > 0:
            # Get the row with the highest version_key
            latest = os_df.loc[os_df['version_key'].idxmax()]
            latest_rows.append(latest)
    
    if not latest_rows:
        # Fallback if no data
        latest_df = pd.DataFrame({
            "os": OS_ORDER,
            "mean_distance": [0, 0, 0],
            "std_distance": [0, 0, 0],
            "mean_error": [0, 0, 0]
        })
    else:
        latest_df = pd.DataFrame(latest_rows)
    
    table = go.Figure(data=[go.Table(
        header=dict(
            values=["OS", "Mean Square Size ± SD (mm)", "Mean Error (mm)"],
            fill_color='lightgray',
            align='center',
            font=dict(size=18)
        ),
        cells=dict(
            values=[
                latest_df["os"].tolist(),
                [f"{m:.2f} ± {s:.2f}" for m, s in zip(
                    latest_df["mean_distance"], 
                    latest_df["std_distance"]
                )],
                [f"{e:.2f}" for e in latest_df["mean_error"]]
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
        fig1=fig1.to_html(full_html=False, include_plotlyjs=False),
        fig2=fig2.to_html(full_html=False, include_plotlyjs=False),
        fig3=fig3.to_html(full_html=False, include_plotlyjs=False),
        table=table.to_html(full_html=False, include_plotlyjs=False),
        expected=EXPECTED
    )

    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text(rendered, encoding="utf-8")
    print(f"✅ Calibration report written to: {output_file.absolute()}")

if __name__ == "__main__":
    df = load_summary_data()
    generate_html_report(df)