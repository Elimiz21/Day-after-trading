"""QA validation checks for the earnings reversal pipeline.

Run with:
    python -m src.qa.run_qa --mode local
    python -m src.qa.run_qa --mode ci
"""

import argparse
import sys
from pathlib import Path

import pandas as pd


def check_required_files() -> list[str]:
    """Check that required project files exist."""
    required = [
        Path("config/significance.yaml"),
        Path("config/execution_costs.yaml"),
        Path("config/openai_qa_prompt.md"),
        Path("docs/status_reports/latest.md"),
    ]
    return [str(p) for p in required if not p.exists()]


def check_phase1_exports() -> list[str]:
    """Check that Phase 1 CSV exports exist and are valid."""
    issues = []
    csv_dir = Path("data/exports/csv")

    required_csvs = [
        "phase_1__sp500_constituents_sample.csv",
        "phase_1__earnings_events.csv",
        "phase_1__daily_ohlcv.csv",
        "phase_1__event_windows.csv",
        "phase_1__features_core.csv",
        "phase_1__signals.csv",
        "phase_1__trades.csv",
    ]

    for csv_name in required_csvs:
        csv_path = csv_dir / csv_name
        if not csv_path.exists():
            issues.append(f"Missing CSV: {csv_path}")
        else:
            try:
                df = pd.read_csv(csv_path)
                if len(df) == 0 and csv_name != "phase_1__trades.csv":
                    issues.append(f"Empty CSV: {csv_path}")
            except Exception as e:
                issues.append(f"Invalid CSV {csv_path}: {e}")

    return issues


def check_phase1_data_quality() -> list[str]:
    """Check Phase 1 data quality constraints."""
    issues = []
    csv_dir = Path("data/exports/csv")

    # Check constituents
    constituents_path = csv_dir / "phase_1__sp500_constituents_sample.csv"
    if constituents_path.exists():
        df = pd.read_csv(constituents_path)
        if len(df) < 5:
            issues.append(f"Insufficient tickers: {len(df)} (expected at least 5)")

    # Check event windows
    windows_path = csv_dir / "phase_1__event_windows.csv"
    if windows_path.exists():
        df = pd.read_csv(windows_path)

        # Check for session field (BMO/AMC tracking)
        if "session" not in df.columns:
            issues.append("Missing 'session' column in event_windows (BMO/AMC tracking)")

        # Check date ordering: t0 <= t1 < t2
        df["t0_date"] = pd.to_datetime(df["t0_date"])
        df["t1_date"] = pd.to_datetime(df["t1_date"])
        df["t2_date"] = pd.to_datetime(df["t2_date"])

        date_violations = (
            (df["t0_date"] > df["t1_date"]) |
            (df["t1_date"] >= df["t2_date"])
        ).sum()
        if date_violations > 0:
            issues.append(f"Date ordering violations (t0 <= t1 < t2): {date_violations}")

        # Check OHLC consistency: Low <= Open,Close <= High
        for prefix in ["t0", "t1", "t2"]:
            ohlc_cols = [f"{prefix}_open", f"{prefix}_high", f"{prefix}_low", f"{prefix}_close"]
            if all(c in df.columns for c in ohlc_cols):
                valid_rows = df.dropna(subset=ohlc_cols)
                ohlc_violations = (
                    (valid_rows[f"{prefix}_low"] > valid_rows[f"{prefix}_open"]) |
                    (valid_rows[f"{prefix}_low"] > valid_rows[f"{prefix}_close"]) |
                    (valid_rows[f"{prefix}_high"] < valid_rows[f"{prefix}_open"]) |
                    (valid_rows[f"{prefix}_high"] < valid_rows[f"{prefix}_close"])
                ).sum()
                if ohlc_violations > 0:
                    issues.append(f"OHLC consistency violations in {prefix}: {ohlc_violations}")

    # Check features
    features_path = csv_dir / "phase_1__features_core.csv"
    if features_path.exists():
        df = pd.read_csv(features_path)

        required_cols = ["R1", "Gap2", "session", "effective_session"]
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"Missing column in features: {col}")

    # Check signals
    signals_path = csv_dir / "phase_1__signals.csv"
    if signals_path.exists():
        df = pd.read_csv(signals_path)

        required_cols = ["signal", "target_price", "entry_price"]
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"Missing column in signals: {col}")

    # Check trades
    trades_path = csv_dir / "phase_1__trades.csv"
    if trades_path.exists():
        df = pd.read_csv(trades_path)

        required_cols = ["signal", "entry_price", "target_price", "exit_price",
                         "hit_target", "gross_return", "cost_bps", "net_return"]
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"Missing column in trades: {col}")

    return issues


def main():
    ap = argparse.ArgumentParser(description="Run QA checks for earnings reversal pipeline")
    ap.add_argument("--mode", choices=["ci", "local"], default="local")
    args = ap.parse_args()

    print("=" * 60)
    print("QA Validation Checks")
    print("=" * 60)

    all_issues = []

    # Check 1: Required project files
    print("\n[Check 1] Required project files...")
    missing = check_required_files()
    if missing:
        for m in missing:
            print(f"  FAIL: Missing {m}")
            all_issues.append(f"Missing file: {m}")
    else:
        print("  PASS: All required files present")

    # Check 2: Phase 1 CSV exports
    print("\n[Check 2] Phase 1 CSV exports...")
    csv_issues = check_phase1_exports()
    if csv_issues:
        for issue in csv_issues:
            print(f"  FAIL: {issue}")
            all_issues.append(issue)
    else:
        print("  PASS: All Phase 1 CSVs present and valid")

    # Check 3: Data quality
    print("\n[Check 3] Phase 1 data quality...")
    quality_issues = check_phase1_data_quality()
    if quality_issues:
        for issue in quality_issues:
            print(f"  WARN: {issue}")
    else:
        print("  PASS: Data quality checks passed")

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(f"QA FAIL: {len(all_issues)} issue(s) found")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("QA PASS: All checks passed")
        if quality_issues:
            print(f"  (with {len(quality_issues)} warning(s))")
        sys.exit(0)


if __name__ == "__main__":
    main()
