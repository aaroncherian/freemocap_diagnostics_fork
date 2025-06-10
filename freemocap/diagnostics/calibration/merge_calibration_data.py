from pathlib import Path
import pandas as pd
import subprocess
import sys

# repo root = three levels up from this script
repo_root = Path(__file__).resolve().parents[3]
print("🧭 repo_root =", repo_root)

summary_csv = repo_root / "freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv"
collected = Path("collected")  # where download-artifact puts the CSVs

# 1) load existing summary
if summary_csv.exists():
    full_df = pd.read_csv(summary_csv)
    print(f"Loaded existing summary with {len(full_df)} rows")
else:
    # Create empty dataframe with expected columns if file doesn't exist
    full_df = pd.DataFrame(columns=["os", "version", "mean_distance", "median_distance", "std_distance", "mean_error"])
    print("Created new summary dataframe")

# 2) ingest rows
csv_files = list(collected.glob("**/*.csv"))
print(f"Found {len(csv_files)} CSV files to merge:")
for f in csv_files:
    print(f"  - {f}")

if not csv_files:
    sys.exit("❌ No calibration rows found in ./collected")

rows = []
for f in csv_files:
    try:
        df = pd.read_csv(f)
        print(f"  Read {len(df)} rows from {f.name}")
        rows.append(df)
    except Exception as e:
        print(f"  Error reading {f}: {e}")

new_df = pd.concat(rows, ignore_index=True)
print(f"Combined into {len(new_df)} new rows")

# Standardize OS names
new_df["os"] = new_df["os"].str.strip()

# 3) replace old 'current' rows and save
full_df = full_df[full_df["version"] != "current"]
full_df = pd.concat([full_df, new_df], ignore_index=True)

# Ensure OS names are standardized
full_df["os"] = full_df["os"].str.strip()

print(f"Final dataframe has {len(full_df)} rows")
print(f"OS values: {full_df['os'].unique()}")
print(f"Version values: {full_df['version'].unique()}")

summary_csv.parent.mkdir(parents=True, exist_ok=True)
full_df.to_csv(summary_csv, index=False)
print(f"✅ Summary updated: {summary_csv}")

# 4) regenerate HTML
report_script = repo_root / "freemocap/diagnostics/generate_calibration_report.py"
if report_script.exists():
    print(f"Running report generation script: {report_script}")
    result = subprocess.run([sys.executable, str(report_script)], capture_output=True, text=True)
    print("STDOUT:", result.stdout)
    if result.stderr:
        print("STDERR:", result.stderr)
    if result.returncode != 0:
        sys.exit(f"Report generation failed with code {result.returncode}")
else:
    print(f"⚠️ Report script not found at {report_script}")
    
print("🎉 Process complete!")