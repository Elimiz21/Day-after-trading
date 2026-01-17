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
        "events_unknown_session": 0,
        "missing_t0": 0,
        "missing_t1": 0,
        "missing_t2": 0,
        "complete_windows": 0,
        "signals_generated": 0,
        "trades_executed": 0,
        "trades_hit_target": 0,
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
        stats["missing_t0"] = int(df["t0_close"].isna().sum())
        stats["missing_t1"] = int(df["t1_close"].isna().sum())
        stats["missing_t2"] = int(df["t2_close"].isna().sum())
        stats["complete_windows"] = len(df.dropna(subset=["t0_close", "t1_close", "t2_close"]))

        # Count unknown sessions
        if "session" in df.columns:
            stats["events_unknown_session"] = int((df["session"] == "unknown").sum())

    # Read features for R1/Gap2 stats
    features_file = csv_dir / "phase_1__features_core.csv"
    if features_file.exists():
        df = pd.read_csv(features_file)
        stats["r1_mean"] = float(df["R1"].mean())
        stats["r1_std"] = float(df["R1"].std())
        stats["gap2_mean"] = float(df["Gap2"].mean())
        stats["gap2_std"] = float(df["Gap2"].std())

    # Read signals
    signals_file = csv_dir / "phase_1__signals.csv"
    if signals_file.exists():
        df = pd.read_csv(signals_file)
        tradeable = df[df["signal"].isin(["LONG", "SHORT"])]
        stats["signals_generated"] = len(tradeable)

    # Read trades
    trades_file = csv_dir / "phase_1__trades.csv"
    if trades_file.exists():
        df = pd.read_csv(trades_file)
        stats["trades_executed"] = len(df)
        if "hit_target" in df.columns:
            stats["trades_hit_target"] = int(df["hit_target"].sum())
        if len(df) > 0:
            stats["hit_rate"] = float(df["hit_target"].sum() / len(df))
            stats["avg_gross_return"] = float(df["gross_return"].mean())
            stats["avg_net_return"] = float(df["net_return"].mean())

    return stats


def get_sample_data(csv_dir: Path) -> dict:
    """Get small samples from each CSV for summaries."""
    samples = {}

    features_file = csv_dir / "phase_1__features_core.csv"
    if features_file.exists():
        df = pd.read_csv(features_file)
        cols = ["symbol", "earnings_date", "session", "t0_date", "t1_date", "t2_date", "R1", "Gap2"]
        cols = [c for c in cols if c in df.columns]
        samples["features"] = df[cols].head(5).to_string(index=False)

    signals_file = csv_dir / "phase_1__signals.csv"
    if signals_file.exists():
        df = pd.read_csv(signals_file)
        cols = ["symbol", "earnings_date", "signal", "R1", "Gap2", "entry_price", "target_price"]
        cols = [c for c in cols if c in df.columns]
        samples["signals"] = df[cols].head(10).to_string(index=False)

    trades_file = csv_dir / "phase_1__trades.csv"
    if trades_file.exists():
        df = pd.read_csv(trades_file)
        if len(df) > 0:
            cols = ["symbol", "signal", "entry_price", "target_price", "exit_price",
                    "hit_target", "gross_return", "net_return"]
            cols = [c for c in cols if c in df.columns]
            samples["trades"] = df[cols].to_string(index=False)

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

    manifest = f"""# QA Manifest (Phase 1 - End-to-End Backtest)

- **timestamp_utc**: {now}
- **git_commit**: {commit}
- **phase**: 1 (Smoke Test)

## Selected Tickers
{tickers_str}

## Data Policy
- **OHLCV Source**: FMP /stable/historical-price-eod/full
- **Adjustment**: Split-adjusted (NOT dividend-adjusted)
- **BMO/AMC**: All events treated as AMC (FMP does not provide timing)

## Coverage Statistics
- **Total earnings events**: {phase1_stats['earnings_count']}
- **Events with unknown session (BMO/AMC)**: {phase1_stats['events_unknown_session']}
- **Complete event windows** (T0+T1+T2): {phase1_stats['complete_windows']}
- **Missing T0 data**: {phase1_stats['missing_t0']}
- **Missing T1 data**: {phase1_stats['missing_t1']}
- **Missing T2 data**: {phase1_stats['missing_t2']}

## Signal & Trade Statistics
- **Tradeable signals generated**: {phase1_stats['signals_generated']}
- **Trades executed**: {phase1_stats['trades_executed']}
- **Trades hit target**: {phase1_stats['trades_hit_target']}
"""
    if phase1_stats['trades_executed'] > 0:
        manifest += f"- **Hit rate**: {phase1_stats.get('hit_rate', 0):.1%}\n"
        manifest += f"- **Avg gross return**: {phase1_stats.get('avg_gross_return', 0):.4f}\n"
        manifest += f"- **Avg net return**: {phase1_stats.get('avg_net_return', 0):.4f}\n"

    manifest += """
## Exported CSVs

| File | Row Count |
|------|-----------|
"""
    for fname, count in csv_stats.items():
        manifest += f"| {fname} | {count} |\n"

    manifest += """
## Reproduction Commands
```bash
python -m src.pipeline.phase1_smoke_test
python -m src.qa.run_qa --mode local
python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest
```

## Feature Statistics
"""
    if "r1_mean" in phase1_stats:
        manifest += f"- **R1**: mean={phase1_stats['r1_mean']:.4f}, std={phase1_stats['r1_std']:.4f}\n"
        manifest += f"- **Gap2**: mean={phase1_stats['gap2_mean']:.4f}, std={phase1_stats['gap2_std']:.4f}\n"

    manifest += """
## Strategy Implementation Status
- [x] T0/T1/T2 mapping with session handling (BMO/AMC)
- [x] Signal generation (significant R1 + opposite Gap2)
- [x] Entry at Open(T2)
- [x] Target = Close(T1)
- [x] Hit detection using T2 High/Low
- [x] Exit at target if hit, else Close(T2)
- [x] Cost model (medium scenario: 20 bps round-trip)
- [x] Gross and net P&L

## Known Limitations
- BMO/AMC timing not available from FMP (all treated as AMC)
- Exchange calendar uses exchange_calendars library (production-grade)
- Phase 1 uses 5 tickers only (not full S&P 500)
"""

    (out / "qa_manifest.md").write_text(manifest, encoding="utf-8")

    # Build summaries
    samples = get_sample_data(csv_dir)

    summaries = f"""# Phase 1 Summaries

## Data Counts

| Metric | Value |
|--------|-------|
| Selected tickers | {len(phase1_stats['tickers'])} |
| Total earnings events | {phase1_stats['earnings_count']} |
| Events with unknown session | {phase1_stats['events_unknown_session']} |
| Complete windows | {phase1_stats['complete_windows']} |
| Missing T0 | {phase1_stats['missing_t0']} |
| Missing T1 | {phase1_stats['missing_t1']} |
| Missing T2 | {phase1_stats['missing_t2']} |
| Signals generated | {phase1_stats['signals_generated']} |
| Trades executed | {phase1_stats['trades_executed']} |
| Trades hit target | {phase1_stats['trades_hit_target']} |

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

    summaries += "\n## Sample: Signals (first 10 rows)\n\n```\n"
    if "signals" in samples:
        summaries += samples["signals"]
    else:
        summaries += "(no signals data)"
    summaries += "\n```\n"

    summaries += "\n## Sample: Trades (all)\n\n```\n"
    if "trades" in samples:
        summaries += samples["trades"]
    else:
        summaries += "(no trades)"
    summaries += "\n```\n"

    (out / "summaries.md").write_text(summaries, encoding="utf-8")

    print(f"Wrote QA bundle to {out}")
    print(f"  - qa_manifest.md")
    print(f"  - status_report.md")
    print(f"  - summaries.md")


if __name__ == "__main__":
    main()
