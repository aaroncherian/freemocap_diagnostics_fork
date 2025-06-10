from pathlib import Path
import pandas as pd, subprocess, sys

# repo root = three levels up from this script
repo_root = Path(__file__).resolve().parents[3]
print("🧭 repo_root =", repo_root)

summary_csv = repo_root / "freemocap/diagnostics/calibration/calibration_diagnostics_summary.csv"
collected   = Path("collected")          # where download-artifact puts the CSVs

# 1) load existing summary
if summary_csv.exists():
    full_df = pd.read_csv(summary_csv)
else:
    raise FileNotFoundError(
        f"Expected summary CSV not found: {summary_csv}\n"
        "Run build_calibration_dataset.py once to create it."
    )

# 2) ingest rows
rows = [pd.read_csv(f) for f in collected.glob("**/*.csv")]
if not rows:
    sys.exit("❌ No calibration rows found in ./collected")

new_df = pd.concat(rows, ignore_index=True)

# 3) replace old 'current' rows and save
full_df = full_df[full_df["version"] != "current"]
full_df = pd.concat([full_df, new_df], ignore_index=True)

summary_csv.parent.mkdir(parents=True, exist_ok=True)
full_df.to_csv(summary_csv, index=False)
print("✅ summary updated:", summary_csv)

# 4) regenerate HTML
report_script = repo_root / "freemocap/diagnostics/calibration/generate_calibration_report.py"
subprocess.run([sys.executable, str(report_script)], check=True)
print("🎉 HTML report regenerated")