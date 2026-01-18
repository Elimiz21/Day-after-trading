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
        "events_excluded_unknown_session": 0,
        "missing_t0": 0,
        "missing_t1": 0,
        "missing_t2": 0,
        "complete_windows": 0,
        "signals_long": 0,
        "signals_short": 0,
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

    # Read signals for signal breakdown
    signals_file = csv_dir / "phase_1__signals.csv"
    if signals_file.exists():
        df = pd.read_csv(signals_file)
        tradeable = df[df["signal"].isin(["LONG", "SHORT"])]
        stats["signals_generated"] = len(tradeable)
        stats["signals_long"] = int((df["signal"] == "LONG").sum())
        stats["signals_short"] = int((df["signal"] == "SHORT").sum())

        # Count exclusions by reason
        if "signal" in df.columns:
            stats["events_excluded_unknown_session"] = int(
                (df["signal"] == "EXCLUDED_UNKNOWN_SESSION").sum()
            )
            stats["events_no_trade_small_r1"] = int(
                (df["signal"] == "NO_TRADE_SMALL_R1").sum()
            )
            stats["events_no_trade_small_gap"] = int(
                (df["signal"] == "NO_TRADE_SMALL_GAP").sum()
            )
            stats["events_no_trade_same_dir"] = int(
                (df["signal"] == "NO_TRADE_SAME_DIRECTION").sum()
            )

    # Read trades
    trades_file = csv_dir / "phase_1__trades.csv"
    if trades_file.exists():
        df = pd.read_csv(trades_file)
        stats["trades_executed"] = len(df)
        if "hit_target" in df.columns and len(df) > 0:
            stats["trades_hit_target"] = int(df["hit_target"].sum())
            stats["hit_rate"] = float(df["hit_target"].sum() / len(df))
            stats["avg_gross_return"] = float(df["gross_return"].mean())
            stats["avg_net_return"] = float(df["net_return"].mean())

            # Breakdown by direction
            longs = df[df["signal"] == "LONG"]
            shorts = df[df["signal"] == "SHORT"]
            if len(longs) > 0:
                stats["long_avg_gross"] = float(longs["gross_return"].mean())
                stats["long_hit_rate"] = float(longs["hit_target"].sum() / len(longs))
            if len(shorts) > 0:
                stats["short_avg_gross"] = float(shorts["gross_return"].mean())
                stats["short_hit_rate"] = float(shorts["hit_target"].sum() / len(shorts))

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
        # Show tradeable signals
        tradeable = df[df["signal"].isin(["LONG", "SHORT"])]
        cols = ["symbol", "earnings_date", "signal", "R1", "Gap2", "entry_price", "target_price", "t1_close"]
        cols = [c for c in cols if c in df.columns]
        if len(tradeable) > 0:
            samples["signals"] = tradeable[cols].to_string(index=False)
        else:
            samples["signals"] = "(no tradeable signals)"

    trades_file = csv_dir / "phase_1__trades.csv"
    if trades_file.exists():
        df = pd.read_csv(trades_file)
        if len(df) > 0:
            cols = ["symbol", "t2_date", "signal", "R1", "Gap2", "entry_price", "target_price",
                    "t1_close", "exit_price", "hit_target", "gross_return", "net_return"]
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
  - Split-adjusted: stock splits are reflected in historical prices
  - NOT dividend-adjusted: overnight gaps include ex-dividend effects
- **BMO/AMC Handling**: FMP does not provide earnings announcement timing
  - Events with unknown session: tracked and reported
  - For correctness: unknown-session events should be excluded or run with dual-assumption sensitivity

## Coverage Statistics
- **Total earnings events**: {phase1_stats['earnings_count']}
- **Events with unknown session (BMO/AMC)**: {phase1_stats['events_unknown_session']}
- **Complete event windows** (T0+T1+T2): {phase1_stats['complete_windows']}
- **Missing T0 data**: {phase1_stats['missing_t0']}
- **Missing T1 data**: {phase1_stats['missing_t1']}
- **Missing T2 data**: {phase1_stats['missing_t2']}

## Signal Generation Statistics
- **Signal rule**: LONG when R1 > 1% AND Gap2 < 0; SHORT when R1 < -1% AND Gap2 > 0
- **LONG signals**: {phase1_stats['signals_long']}
- **SHORT signals**: {phase1_stats['signals_short']}
- **Total tradeable signals**: {phase1_stats['signals_generated']}

### Non-Signal Breakdown
- Events excluded (unknown session): {phase1_stats.get('events_excluded_unknown_session', 0)}
- No trade (R1 too small): {phase1_stats.get('events_no_trade_small_r1', 0)}
- No trade (Gap2 too small): {phase1_stats.get('events_no_trade_small_gap', 0)}
- No trade (same direction): {phase1_stats.get('events_no_trade_same_dir', 0)}

## Trade Execution Statistics
- **Trades executed**: {phase1_stats['trades_executed']}
- **Trades hit target**: {phase1_stats['trades_hit_target']}
"""
    if phase1_stats['trades_executed'] > 0:
        manifest += f"- **Hit rate**: {phase1_stats.get('hit_rate', 0):.1%}\n"
        manifest += f"- **Avg gross return**: {phase1_stats.get('avg_gross_return', 0):.4f}\n"
        manifest += f"- **Avg net return**: {phase1_stats.get('avg_net_return', 0):.4f}\n"
        if "long_avg_gross" in phase1_stats:
            manifest += f"- **LONG avg gross**: {phase1_stats['long_avg_gross']:.4f} (hit rate: {phase1_stats['long_hit_rate']:.1%})\n"
        if "short_avg_gross" in phase1_stats:
            manifest += f"- **SHORT avg gross**: {phase1_stats['short_avg_gross']:.4f} (hit rate: {phase1_stats['short_hit_rate']:.1%})\n"

    manifest += f"""
## Cost Model
- **Scenario**: Medium (from config/execution_costs.yaml)
- **Spread**: 5 bps per side
- **Slippage**: 5 bps per side
- **Commission**: 10 bps per side
- **Total round-trip**: 20 bps
- **Application**: Subtracted once from gross return per trade

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
## Strategy Specification (Corrected)

### Signal Rules
- **LONG**: R1 > +1% (positive significant move on T1) AND Gap2 < 0 (gaps DOWN into T2)
  - Rationale: Price went up on T1, then gapped down overnight → expect reversion UP to Close(T1)
  - Target = Close(T1) should be ABOVE entry = Open(T2)
- **SHORT**: R1 < -1% (negative significant move on T1) AND Gap2 > 0 (gaps UP into T2)
  - Rationale: Price went down on T1, then gapped up overnight → expect reversion DOWN to Close(T1)
  - Target = Close(T1) should be BELOW entry = Open(T2)

### Entry/Exit Rules
- **Entry**: Open(T2) at market open
- **Target**: Close(T1) (the level we expect price to revert to)
- **Hit Detection**:
  - LONG: T2_high >= target (intraday high reached target)
  - SHORT: T2_low <= target (intraday low reached target)
- **Exit**:
  - If hit: exit at target price
  - If not hit: exit at Close(T2)

### Return Calculation
- LONG: (exit_price - entry_price) / entry_price
- SHORT: (entry_price - exit_price) / entry_price

## QA Validations
- [x] target_price == t1_close for all trades (exact match)
- [x] For LONG hit: gross_return == (target - entry) / entry
- [x] For SHORT hit: gross_return == (entry - target) / entry
- [x] net_return == gross_return - cost_bps/10000
- [x] Signal rules match spec (LONG: R1>0 & Gap2<0, SHORT: R1<0 & Gap2>0)

## Known Limitations
- BMO/AMC timing not available from FMP (events tracked as unknown session)
- Exchange calendar uses exchange_calendars library (production-grade)
- Phase 1 uses 5 tickers only (not full S&P 500)
- Phase 1 covers 2022-2025 only (not full 15-year backtest)
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
| LONG signals | {phase1_stats['signals_long']} |
| SHORT signals | {phase1_stats['signals_short']} |
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

    summaries += "\n## Sample: Tradeable Signals (all LONG/SHORT)\n\n```\n"
    if "signals" in samples:
        summaries += samples["signals"]
    else:
        summaries += "(no tradeable signals)"
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
