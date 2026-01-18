"""QA validation checks for the earnings reversal pipeline.

Run with:
    python -m src.qa.run_qa --mode local
    python -m src.qa.run_qa --mode ci

Checks:
1. Required project files exist
2. Phase 1 CSV exports exist and are valid
3. Data quality constraints (date ordering, OHLC consistency)
4. Signal rule correctness (per spec: LONG=R1>0 & Gap2<0, SHORT=R1<0 & Gap2>0)
5. Trade validation (target=t1_close, return math correctness)
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

        required_cols = ["signal", "target_price", "entry_price", "t1_close"]
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"Missing column in signals: {col}")

    # Check trades
    trades_path = csv_dir / "phase_1__trades.csv"
    if trades_path.exists():
        df = pd.read_csv(trades_path)

        required_cols = ["signal", "entry_price", "target_price", "exit_price",
                         "hit_target", "gross_return", "cost_bps", "net_return", "t1_close"]
        for col in required_cols:
            if col not in df.columns:
                issues.append(f"Missing column in trades: {col}")

    return issues


def check_signal_rule_correctness() -> list[str]:
    """Check that signal rules match spec: LONG=R1>0 & Gap2<0, SHORT=R1<0 & Gap2>0."""
    issues = []
    csv_dir = Path("data/exports/csv")

    signals_path = csv_dir / "phase_1__signals.csv"
    if not signals_path.exists():
        return ["signals.csv not found for signal rule check"]

    df = pd.read_csv(signals_path)

    # Filter to tradeable signals
    longs = df[df["signal"] == "LONG"]
    shorts = df[df["signal"] == "SHORT"]

    # Check LONG signals: R1 > 0 AND Gap2 < 0
    if len(longs) > 0:
        invalid_longs = longs[(longs["R1"] <= 0) | (longs["Gap2"] >= 0)]
        if len(invalid_longs) > 0:
            issues.append(
                f"LONG signal rule violation: {len(invalid_longs)} signals with R1<=0 or Gap2>=0. "
                f"Spec requires LONG when R1>0 AND Gap2<0"
            )

    # Check SHORT signals: R1 < 0 AND Gap2 > 0
    if len(shorts) > 0:
        invalid_shorts = shorts[(shorts["R1"] >= 0) | (shorts["Gap2"] <= 0)]
        if len(invalid_shorts) > 0:
            issues.append(
                f"SHORT signal rule violation: {len(invalid_shorts)} signals with R1>=0 or Gap2<=0. "
                f"Spec requires SHORT when R1<0 AND Gap2>0"
            )

    return issues


def check_trade_validation() -> list[str]:
    """Check trade validation: target=t1_close and return math correctness."""
    issues = []
    csv_dir = Path("data/exports/csv")

    trades_path = csv_dir / "phase_1__trades.csv"
    if not trades_path.exists():
        return []  # No trades is not an error

    df = pd.read_csv(trades_path)
    if len(df) == 0:
        return []  # No trades is not an error

    # Check 1: target_price == t1_close
    if "t1_close" in df.columns:
        target_mismatch = (abs(df["target_price"] - df["t1_close"]) > 0.0001).sum()
        if target_mismatch > 0:
            issues.append(f"Target price != t1_close in {target_mismatch} trade(s)")

    # Check 2: For hit trades, return math should be correct
    hits = df[df["hit_target"] == True]
    for _, trade in hits.iterrows():
        entry = trade["entry_price"]
        target = trade["target_price"]
        exit_price = trade["exit_price"]
        gross = trade["gross_return"]

        # Exit should equal target for hit trades
        if abs(exit_price - target) > 0.0001:
            issues.append(
                f"Hit trade exit != target: {trade['symbol']} {trade['earnings_date']} "
                f"exit={exit_price}, target={target}"
            )

        # Check return calculation
        if trade["signal"] == "LONG":
            expected = (target - entry) / entry
        else:  # SHORT
            expected = (entry - target) / entry

        if abs(gross - expected) > 0.0001:
            issues.append(
                f"Return math error: {trade['symbol']} {trade['earnings_date']} "
                f"gross={gross:.6f}, expected={expected:.6f}"
            )

    # Check 3: Cost model consistency
    cost_bps = df["cost_bps"].unique()
    if len(cost_bps) > 1:
        issues.append(f"Inconsistent cost_bps across trades: {cost_bps}")

    # Verify net = gross - cost
    for _, trade in df.iterrows():
        expected_net = trade["gross_return"] - (trade["cost_bps"] / 10000)
        if abs(trade["net_return"] - expected_net) > 0.0001:
            issues.append(
                f"Net return calculation error: {trade['symbol']} {trade['earnings_date']} "
                f"net={trade['net_return']:.6f}, expected={expected_net:.6f}"
            )

    return issues


def check_coverage_reporting() -> list[str]:
    """Check coverage and missingness reporting."""
    warnings = []
    csv_dir = Path("data/exports/csv")

    # Check signals for exclusion reasons
    signals_path = csv_dir / "phase_1__signals.csv"
    if signals_path.exists():
        df = pd.read_csv(signals_path)

        # Report exclusion breakdown
        if "signal" in df.columns:
            signal_counts = df["signal"].value_counts()
            excluded_count = signal_counts.get("EXCLUDED_UNKNOWN_SESSION", 0)
            if excluded_count > 0:
                warnings.append(
                    f"Events excluded due to unknown session: {excluded_count} "
                    f"(cannot determine BMO/AMC from FMP data)"
                )

    return warnings


def main():
    ap = argparse.ArgumentParser(description="Run QA checks for earnings reversal pipeline")
    ap.add_argument("--mode", choices=["ci", "local"], default="local")
    args = ap.parse_args()

    print("=" * 60)
    print("QA Validation Checks")
    print("=" * 60)

    all_issues = []
    all_warnings = []

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
            all_warnings.append(issue)
    else:
        print("  PASS: Data quality checks passed")

    # Check 4: Signal rule correctness (per spec)
    print("\n[Check 4] Signal rule correctness (per spec)...")
    signal_issues = check_signal_rule_correctness()
    if signal_issues:
        for issue in signal_issues:
            print(f"  FAIL: {issue}")
            all_issues.append(issue)
    else:
        print("  PASS: Signal rules match spec (LONG: R1>0 & Gap2<0, SHORT: R1<0 & Gap2>0)")

    # Check 5: Trade validation
    print("\n[Check 5] Trade validation (target=t1_close, return math)...")
    trade_issues = check_trade_validation()
    if trade_issues:
        for issue in trade_issues:
            print(f"  FAIL: {issue}")
            all_issues.append(issue)
    else:
        print("  PASS: All trade validations passed")

    # Check 6: Coverage reporting
    print("\n[Check 6] Coverage and exclusion reporting...")
    coverage_warnings = check_coverage_reporting()
    if coverage_warnings:
        for w in coverage_warnings:
            print(f"  INFO: {w}")
            all_warnings.append(w)
    else:
        print("  PASS: No coverage issues")

    # Summary
    print("\n" + "=" * 60)
    if all_issues:
        print(f"QA FAIL: {len(all_issues)} issue(s) found")
        for issue in all_issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("QA PASS: All checks passed")
        if all_warnings:
            print(f"  (with {len(all_warnings)} warning(s)/info)")
        sys.exit(0)


if __name__ == "__main__":
    main()
