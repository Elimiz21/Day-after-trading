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
    ]

    for csv_name in required_csvs:
        csv_path = csv_dir / csv_name
        if not csv_path.exists():
            issues.append(f"Missing CSV: {csv_path}")
        else:
            try:
                df = pd.read_csv(csv_path)
                if len(df) == 0:
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

    # Check event windows completeness
    windows_path = csv_dir / "phase_1__event_windows.csv"
    if windows_path.exists():
        df = pd.read_csv(windows_path)
        missing_t0 = df["t0_close"].isna().sum()
        missing_t1 = df["t1_close"].isna().sum()
        missing_t2 = df["t2_close"].isna().sum()

        # Warn if more than 20% missing (not a hard fail for Phase 1)
        total = len(df)
        if total > 0:
            if missing_t0 / total > 0.2:
                issues.append(f"High T0 missing rate: {missing_t0}/{total}")
            if missing_t1 / total > 0.2:
                issues.append(f"High T1 missing rate: {missing_t1}/{total}")
            if missing_t2 / total > 0.2:
                issues.append(f"High T2 missing rate: {missing_t2}/{total}")

    # Check features
    features_path = csv_dir / "phase_1__features_core.csv"
    if features_path.exists():
        df = pd.read_csv(features_path)
        if "R1" not in df.columns:
            issues.append("Missing R1 column in features")
        if "Gap2" not in df.columns:
            issues.append("Missing Gap2 column in features")

        # Check for NaN in computed features (should be minimal)
        if "R1" in df.columns:
            r1_na = df["R1"].isna().sum()
            if r1_na > len(df) * 0.1:
                issues.append(f"High R1 NaN rate: {r1_na}/{len(df)}")

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
            # Quality issues are warnings, not hard failures for Phase 1
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
