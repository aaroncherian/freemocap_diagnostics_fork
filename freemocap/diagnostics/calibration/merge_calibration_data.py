"""
 1.  collect every 1-row CSV in ./collected/**
 2.  append them to freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv
 3.  re-run generate_calibration_report.py
"""
from pathlib import Path
import pandas as pd
import subprocess, sys

repo_root   = Path(__file__).resolve().parents[1]          # repo root
summary_csv = Path("freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv")
collected   = Path("collected")

print(f"Collecting calibration rows from {collected} → {summary_csv}")

# 1) read existing summary (or fail loudly)
if summary_csv.exists():
    full_df = pd.read_csv(summary_csv)
else:
    raise FileNotFoundError(
        f"Expected summary CSV not found: {summary_csv}\n"
        "Run build_calibration_dataset.py once to create it."
    )

# 2) ingest each per-OS row
rows = [pd.read_csv(csv_file) for csv_file in collected.glob("**/*.csv")]
if not rows:
    sys.exit("❌ No calibration rows found!")

new_df = pd.concat(rows, ignore_index=True)

# 3) drop previous “current” rows, append fresh ones, save
full_df = full_df[full_df["version"] != "current"]
full_df = pd.concat([full_df, new_df], ignore_index=True)

summary_csv.parent.mkdir(parents=True, exist_ok=True)      # ensure dir exists
full_df.to_csv(summary_csv, index=False)
print(f"✅ summary updated → {summary_csv}")

# 4) regenerate HTML report
subprocess.run(
    [sys.executable, "freemocap/diagnostics/calibration/generate_calibration_report.py"],
    check=True
)