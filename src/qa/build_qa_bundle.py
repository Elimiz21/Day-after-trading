"""Build QA bundle with Phase 1 manifest and summaries."""

import argparse
import datetime
import subprocess
from pathlib import Path

import pandas as pd


def run(cmd):
    """Run shell command and return output."""
    return subprocess.check_output(cmd, text=True).strip()


def get_csv_stats(csv_dir: Path) -> dict:
    """Get row counts for all CSVs in directory."""
    stats = {}
    if csv_dir.exists():
        for csv_file in sorted(csv_dir.glob("phase_1__*.csv")):
            try:
                df = pd.read_csv(csv_file)
                stats[csv_file.name] = len(df)
            except Exception as e:
                stats[csv_file.name] = f"ERROR: {e}"
    return stats


def get_phase1_stats(csv_dir: Path) -> dict:
    """Extract Phase 1 statistics from exported CSVs."""
    stats = {
        "tickers": [],
        "earnings_count": 0,
        "missing_t0": 0,
        "missing_t1": 0,
        "missing_t2": 0,
        "complete_windows": 0,
    }

    # Read constituents for tickers
    constituents_file = csv_dir / "phase_1__sp500_constituents_sample.csv"
    if constituents_file.exists():
        df = pd.read_csv(constituents_file)
        stats["tickers"] = df["symbol"].tolist()

    # Read event windows for completeness stats
    windows_file = csv_dir / "phase_1__event_windows.csv"
    if windows_file.exists():
        df = pd.read_csv(windows_file)
        stats["earnings_count"] = len(df)
        stats["missing_t0"] = df["t0_close"].isna().sum()
        stats["missing_t1"] = df["t1_close"].isna().sum()
        stats["missing_t2"] = df["t2_close"].isna().sum()
        stats["complete_windows"] = len(df.dropna(subset=["t0_close", "t1_close", "t2_close"]))

    # Read features for R1/Gap2 stats
    features_file = csv_dir / "phase_1__features_core.csv"
    if features_file.exists():
        df = pd.read_csv(features_file)
        stats["r1_mean"] = df["R1"].mean()
        stats["r1_std"] = df["R1"].std()
        stats["gap2_mean"] = df["Gap2"].mean()
        stats["gap2_std"] = df["Gap2"].std()

    return stats


def get_sample_data(csv_dir: Path) -> dict:
    """Get small samples from each CSV for summaries."""
    samples = {}

    features_file = csv_dir / "phase_1__features_core.csv"
    if features_file.exists():
        df = pd.read_csv(features_file)
        samples["features"] = df.head(5).to_string(index=False)

    earnings_file = csv_dir / "phase_1__earnings_events.csv"
    if earnings_file.exists():
        df = pd.read_csv(earnings_file)
        samples["earnings"] = df[["symbol", "date", "epsActual", "epsEstimated"]].head(5).to_string(index=False)

    return samples


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, help="Output directory for QA bundle")
    args = ap.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    csv_dir = Path("data/exports/csv")

    # Get git info
    commit = run(["git", "rev-parse", "HEAD"])
    now = datetime.datetime.utcnow().isoformat() + "Z"

    # Copy status report
    status_report_src = Path("docs/status_reports/latest.md")
    if status_report_src.exists():
        (out / "status_report.md").write_text(
            status_report_src.read_text(encoding="utf-8"), encoding="utf-8"
        )
    else:
        (out / "status_report.md").write_text(
            "(missing docs/status_reports/latest.md)\n", encoding="utf-8"
        )

    # Get Phase 1 stats
    csv_stats = get_csv_stats(csv_dir)
    phase1_stats = get_phase1_stats(csv_dir)

    # Build manifest
    tickers_str = ", ".join(phase1_stats["tickers"]) if phase1_stats["tickers"] else "(none)"

    manifest = f"""# QA Manifest (Phase 1)

- **timestamp_utc**: {now}
- **git_commit**: {commit}
- **phase**: 1 (Smoke Test)

## Selected Tickers
{tickers_str}

## Coverage Statistics
- **Total earnings events**: {phase1_stats['earnings_count']}
- **Complete event windows** (T0+T1+T2): {phase1_stats['complete_windows']}
- **Missing T0 data**: {phase1_stats['missing_t0']}
- **Missing T1 data**: {phase1_stats['missing_t1']}
- **Missing T2 data**: {phase1_stats['missing_t2']}

## Exported CSVs

| File | Row Count |
|------|-----------|
"""
    for fname, count in csv_stats.items():
        manifest += f"| {fname} | {count} |\n"

    manifest += """
## Reproduction Commands
```bash
python -m src.qa.run_qa --mode local
python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest
```

## Feature Statistics
"""
    if "r1_mean" in phase1_stats:
        manifest += f"- **R1**: mean={phase1_stats['r1_mean']:.4f}, std={phase1_stats['r1_std']:.4f}\n"
        manifest += f"- **Gap2**: mean={phase1_stats['gap2_mean']:.4f}, std={phase1_stats['gap2_std']:.4f}\n"

    (out / "qa_manifest.md").write_text(manifest, encoding="utf-8")

    # Build summaries
    samples = get_sample_data(csv_dir)

    summaries = f"""# Phase 1 Summaries

## Data Counts

| Metric | Value |
|--------|-------|
| Selected tickers | {len(phase1_stats['tickers'])} |
| Total earnings events | {phase1_stats['earnings_count']} |
| Complete windows | {phase1_stats['complete_windows']} |
| Missing T0 | {phase1_stats['missing_t0']} |
| Missing T1 | {phase1_stats['missing_t1']} |
| Missing T2 | {phase1_stats['missing_t2']} |

## CSV Row Counts

| File | Rows |
|------|------|
"""
    for fname, count in csv_stats.items():
        summaries += f"| {fname} | {count} |\n"

    summaries += "\n## Sample: Core Features (first 5 rows)\n\n```\n"
    if "features" in samples:
        summaries += samples["features"]
    else:
        summaries += "(no features data)"
    summaries += "\n```\n"

    summaries += "\n## Sample: Earnings Events (first 5 rows)\n\n```\n"
    if "earnings" in samples:
        summaries += samples["earnings"]
    else:
        summaries += "(no earnings data)"
    summaries += "\n```\n"

    (out / "summaries.md").write_text(summaries, encoding="utf-8")

    print(f"Wrote QA bundle to {out}")
    print(f"  - qa_manifest.md")
    print(f"  - status_report.md")
    print(f"  - summaries.md")


if __name__ == "__main__":
    main()
