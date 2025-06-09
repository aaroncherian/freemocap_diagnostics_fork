"""
 1.  collect every 1-row CSV in ./collected/**
 2.  append them to freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv
 3.  re-run generate_calibration_report.py
"""
from pathlib import Path
import pandas as pd
import subprocess, sys

root = Path(__file__).resolve().parents[2]  # repo root
summary_csv = root / "freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv"
collected   = Path("collected")

# 1) read existing summary (or create fresh)
if summary_csv.exists():
    full_df = pd.read_csv(summary_csv)
else:
    full_df = pd.DataFrame(columns=["os","version","mean_distance","std_distance"])

# 2) ingest each per-OS row
rows = []
for csv_file in collected.glob("**/*.csv"):
    rows.append(pd.read_csv(csv_file))

if not rows:
    sys.exit("❌ No calibration rows found!")

new_df = pd.concat(rows, ignore_index=True)

# drop any old rows tagged "current"
full_df = full_df[full_df["version"] != "current"]

# append & save
full_df = pd.concat([full_df, new_df], ignore_index=True)
full_df.to_csv(summary_csv, index=False)
print(f"✅ summary updated → {summary_csv}")

# 3) regenerate HTML report
subprocess.run(
    [sys.executable, "freemocap/diagnostics/calibration/generate_calibration_report.py"],
    check=True
)
