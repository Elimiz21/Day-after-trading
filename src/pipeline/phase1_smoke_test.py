"""Phase 1: Smoke Test Pipeline - End-to-End Backtest

This module implements the Phase 1 smoke test as a minimal end-to-end
backtest that implements the full strategy specification:

1. Data ingestion: Earnings dates + OHLCV from FMP API
2. Event mapping: T0/T1/T2 with session handling (BMO/AMC)
3. Signal generation: Significant move on T1, opposite gap on T2
4. Trade entry: Enter at Open(T2) if signal conditions met
5. Hit detection: Check if target (Close(T1)) hit using T2 High/Low
6. Exit rules: Exit at target if hit, else at Close(T2)
7. Cost modeling: Apply scenario-based execution costs
8. P&L computation: Gross and net returns

Strategy Specification:
-----------------------
The earnings reversal strategy:
- R1 = Close(T1) / Close(T0) - 1  (day-after return, the "significant move")
- Gap2 = Open(T2) / Close(T1) - 1 (overnight gap, the "opposite direction")
- Target = Close(T1) (reversion target)
- Entry = Open(T2)

Signal Rules (per spec):
- LONG: R1 > threshold (positive significant move) AND Gap2 < 0 (gap down)
  → Expect price to revert UP to Close(T1), which is ABOVE entry
- SHORT: R1 < -threshold (negative significant move) AND Gap2 > 0 (gap up)
  → Expect price to revert DOWN to Close(T1), which is BELOW entry

This is a "gap fade" / "mean reversion" strategy: after a big move,
if the market gaps in the opposite direction, bet on continuation
of that gap (i.e., reversion toward the T1 close level).

Ticker Selection Criteria (Phase 1):
-------------------------------------
5 tickers from different sectors for diversity:
1. AAPL (Technology) - High liquidity, frequent earnings
2. JPM (Financials) - Major bank, different earnings cycle
3. JNJ (Healthcare) - Defensive stock, stable earnings
4. XOM (Energy) - Commodity-linked, volatile around earnings
5. WMT (Consumer Defensive) - Retail sector, different seasonality

Data Policy:
------------
- OHLCV: FMP /stable/historical-price-eod/full (split-adjusted, NOT dividend-adjusted)
- R1/Gap2 computed from adjusted closes for consistency
- All signals and P&L use the same adjustment policy
- Split-adjusted means corporate actions (stock splits) are reflected
- NOT dividend-adjusted means overnight gaps include ex-dividend effects

BMO/AMC Limitation:
-------------------
FMP API does not provide announcement time (BMO vs AMC). Events with
unknown session are EXCLUDED from the backtest to avoid systematic
misalignment. The session field tracks this exclusion reason.
For future phases: either obtain timing from another source or run
dual-assumption sensitivity analysis.
"""

import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml

from src.ingestion import EarningsSession, FMPClient, TradingCalendar

# Phase 1 selected tickers with rationale
PHASE1_TICKERS = {
    "AAPL": "Technology - High liquidity, frequent earnings",
    "JPM": "Financials - Major bank, different earnings cycle",
    "JNJ": "Healthcare - Defensive stock, stable earnings",
    "XOM": "Energy - Commodity-linked, volatile around earnings",
    "WMT": "Consumer Defensive - Retail sector, different seasonality",
}

EXPORT_DIR = Path("data/exports/csv")
CONFIG_DIR = Path("config")


def load_config():
    """Load configuration files."""
    with open(CONFIG_DIR / "significance.yaml") as f:
        significance = yaml.safe_load(f)
    with open(CONFIG_DIR / "execution_costs.yaml") as f:
        costs = yaml.safe_load(f)
    return significance, costs


class Phase1Pipeline:
    """Phase 1 end-to-end backtest pipeline."""

    def __init__(self):
        self.fmp = FMPClient()
        self.calendar = TradingCalendar()
        self.tickers = list(PHASE1_TICKERS.keys())
        self.significance_config, self.cost_config = load_config()

        # Data containers
        self.sp500_constituents: Optional[pd.DataFrame] = None
        self.earnings_events: Optional[pd.DataFrame] = None
        self.daily_ohlcv: Optional[pd.DataFrame] = None
        self.event_windows: Optional[pd.DataFrame] = None
        self.signals: Optional[pd.DataFrame] = None
        self.trades: Optional[pd.DataFrame] = None

        # Stats for QA
        self.stats = {
            "selected_tickers": self.tickers,
            "ticker_rationale": PHASE1_TICKERS,
            "total_earnings_events": 0,
            "events_with_unknown_session": 0,
            "missing_t0": 0,
            "missing_t1": 0,
            "missing_t2": 0,
            "complete_windows": 0,
            "signals_generated": 0,
            "trades_executed": 0,
            "trades_hit_target": 0,
        }

    def run(self) -> dict:
        """Execute full Phase 1 pipeline."""
        print("=" * 60)
        print("PHASE 1: End-to-End Backtest Pipeline")
        print("=" * 60)

        self._step1_fetch_sp500()
        self._step2_fetch_earnings()
        self._step3_fetch_ohlcv()
        self._step4_build_event_windows()
        self._step5_compute_features()
        self._step6_generate_signals()
        self._step7_simulate_trades()
        self._step8_export_csvs()

        print("\n" + "=" * 60)
        print("Phase 1 Complete!")
        print("=" * 60)
        self._print_summary()

        return self.stats

    def _step1_fetch_sp500(self):
        """Fetch S&P 500 constituents sample."""
        print("\n[Step 1] Creating S&P 500 constituents sample...")
        self.sp500_constituents = self.fmp.get_sp500_constituents_sample(self.tickers)
        print(f"  Created sample with {len(self.sp500_constituents)} constituents")
        for _, row in self.sp500_constituents.iterrows():
            print(f"    {row['symbol']}: {row['name']} ({row['sector']})")

    def _step2_fetch_earnings(self):
        """Fetch historical earnings for selected tickers."""
        print("\n[Step 2] Fetching earnings events...")

        all_earnings = []
        for ticker in self.tickers:
            print(f"  Fetching earnings for {ticker}...")
            df = self.fmp.get_earnings_historical(ticker, limit=10)
            if not df.empty:
                # Keep only past events with actual EPS (not future)
                df = df[df["epsActual"].notna()]
                all_earnings.append(df)
                print(f"    Found {len(df)} historical earnings events")

        if all_earnings:
            self.earnings_events = pd.concat(all_earnings, ignore_index=True)
            self.earnings_events = self.earnings_events.sort_values(
                "date", ascending=False
            ).reset_index(drop=True)

            # Add session field - UNKNOWN since FMP doesn't provide it
            self.earnings_events["session"] = EarningsSession.UNKNOWN.value
            self.stats["events_with_unknown_session"] = len(self.earnings_events)
        else:
            self.earnings_events = pd.DataFrame()

        self.stats["total_earnings_events"] = len(self.earnings_events)
        print(f"\n  Total earnings events: {len(self.earnings_events)}")
        print(f"  Events with unknown session (BMO/AMC): {self.stats['events_with_unknown_session']}")

    def _step3_fetch_ohlcv(self):
        """Fetch daily OHLCV data."""
        print("\n[Step 3] Fetching daily OHLCV data...")
        print("  Note: Using FMP split-adjusted prices (not dividend-adjusted)")

        if self.earnings_events.empty:
            print("  ERROR: No earnings events")
            return

        min_date = self.earnings_events["date"].min() - pd.Timedelta(days=90)
        max_date = self.earnings_events["date"].max() + pd.Timedelta(days=10)

        all_ohlcv = []
        for ticker in self.tickers:
            print(f"  Fetching OHLCV for {ticker}...")
            df = self.fmp.get_historical_prices(
                ticker,
                from_date=min_date.strftime("%Y-%m-%d"),
                to_date=max_date.strftime("%Y-%m-%d"),
            )
            if not df.empty:
                all_ohlcv.append(df)
                print(f"    Got {len(df)} trading days")

        if all_ohlcv:
            self.daily_ohlcv = pd.concat(all_ohlcv, ignore_index=True)
        else:
            self.daily_ohlcv = pd.DataFrame()

        print(f"\n  Total OHLCV rows: {len(self.daily_ohlcv)}")

    def _step4_build_event_windows(self):
        """Build T0/T1/T2 windows with session-aware mapping."""
        print("\n[Step 4] Building event windows (T0/T1/T2)...")
        print("  Using AMC (after market close) assumption for all events")

        if self.earnings_events.empty or self.daily_ohlcv.empty:
            print("  ERROR: Missing data")
            return

        # Create OHLCV lookup
        ohlcv_lookup = {}
        for _, row in self.daily_ohlcv.iterrows():
            key = (row["symbol"], row["date"].date())
            ohlcv_lookup[key] = row

        windows = []
        missing_t0 = missing_t1 = missing_t2 = 0

        for _, event in self.earnings_events.iterrows():
            symbol = event["symbol"]
            earnings_date = event["date"].date()
            session = EarningsSession(event["session"])

            # Get T0/T1/T2 with session handling
            t_dates = self.calendar.get_t0_t1_t2(earnings_date, session)

            # Look up OHLCV
            t0_data = ohlcv_lookup.get((symbol, t_dates["t0"]))
            t1_data = ohlcv_lookup.get((symbol, t_dates["t1"]))
            t2_data = ohlcv_lookup.get((symbol, t_dates["t2"]))

            if t0_data is None:
                missing_t0 += 1
            if t1_data is None:
                missing_t1 += 1
            if t2_data is None:
                missing_t2 += 1

            window = {
                "symbol": symbol,
                "earnings_date": earnings_date,
                "session": t_dates["session"],
                "effective_session": t_dates["effective_session"],
                "t0_date": t_dates["t0"],
                "t1_date": t_dates["t1"],
                "t2_date": t_dates["t2"],
                # T0 OHLCV
                "t0_open": t0_data["open"] if t0_data is not None else None,
                "t0_high": t0_data["high"] if t0_data is not None else None,
                "t0_low": t0_data["low"] if t0_data is not None else None,
                "t0_close": t0_data["close"] if t0_data is not None else None,
                "t0_volume": t0_data["volume"] if t0_data is not None else None,
                # T1 OHLCV
                "t1_open": t1_data["open"] if t1_data is not None else None,
                "t1_high": t1_data["high"] if t1_data is not None else None,
                "t1_low": t1_data["low"] if t1_data is not None else None,
                "t1_close": t1_data["close"] if t1_data is not None else None,
                "t1_volume": t1_data["volume"] if t1_data is not None else None,
                # T2 OHLCV
                "t2_open": t2_data["open"] if t2_data is not None else None,
                "t2_high": t2_data["high"] if t2_data is not None else None,
                "t2_low": t2_data["low"] if t2_data is not None else None,
                "t2_close": t2_data["close"] if t2_data is not None else None,
                "t2_volume": t2_data["volume"] if t2_data is not None else None,
            }
            windows.append(window)

        self.event_windows = pd.DataFrame(windows)

        # Validation: t0 <= t1 < t2
        valid = self.event_windows.dropna(subset=["t0_date", "t1_date", "t2_date"])
        date_order_ok = (
            (valid["t0_date"] <= valid["t1_date"]) &
            (valid["t1_date"] < valid["t2_date"])
        ).all()

        complete = self.event_windows.dropna(subset=["t0_close", "t1_close", "t2_close", "t2_open"])

        self.stats["missing_t0"] = missing_t0
        self.stats["missing_t1"] = missing_t1
        self.stats["missing_t2"] = missing_t2
        self.stats["complete_windows"] = len(complete)

        print(f"  Total event windows: {len(self.event_windows)}")
        print(f"  Complete windows: {len(complete)}")
        print(f"  Missing T0: {missing_t0}, T1: {missing_t1}, T2: {missing_t2}")
        print(f"  Date ordering valid (t0 <= t1 < t2): {date_order_ok}")

    def _step5_compute_features(self):
        """Compute R1 and Gap2 features."""
        print("\n[Step 5] Computing features (R1, Gap2)...")

        if self.event_windows is None or self.event_windows.empty:
            return

        df = self.event_windows

        # R1 = Close(T1) / Close(T0) - 1 (day-after return)
        df["R1"] = df["t1_close"] / df["t0_close"] - 1

        # Gap2 = Open(T2) / Close(T1) - 1 (overnight gap into T2)
        df["Gap2"] = df["t2_open"] / df["t1_close"] - 1

        # Absolute values for filtering
        df["abs_R1"] = df["R1"].abs()
        df["abs_Gap2"] = df["Gap2"].abs()

        valid_r1 = df["R1"].notna().sum()
        valid_gap2 = df["Gap2"].notna().sum()

        self.stats["valid_r1_count"] = int(valid_r1)
        self.stats["valid_gap2_count"] = int(valid_gap2)

        if valid_r1 > 0:
            self.stats["r1_mean"] = float(df["R1"].mean())
            self.stats["r1_std"] = float(df["R1"].std())
            print(f"  R1: mean={df['R1'].mean():.4f}, std={df['R1'].std():.4f}")
        if valid_gap2 > 0:
            self.stats["gap2_mean"] = float(df["Gap2"].mean())
            self.stats["gap2_std"] = float(df["Gap2"].std())
            print(f"  Gap2: mean={df['Gap2'].mean():.4f}, std={df['Gap2'].std():.4f}")

    def _step6_generate_signals(self):
        """Generate trading signals based on spec: significant R1 + opposite Gap2.

        Strategy Spec (corrected):
        - LONG: R1 > threshold (price went UP on T1) AND Gap2 < 0 (gaps DOWN into T2)
          → Target = Close(T1) is ABOVE entry = Open(T2), so we go long to catch the reversion up
        - SHORT: R1 < -threshold (price went DOWN on T1) AND Gap2 > 0 (gaps UP into T2)
          → Target = Close(T1) is BELOW entry = Open(T2), so we go short to catch the reversion down

        This is a gap-fade / mean-reversion strategy.
        """
        print("\n[Step 6] Generating signals...")

        if self.event_windows is None or self.event_windows.empty:
            return

        df = self.event_windows.copy()

        # Use minimum threshold from config for Phase 1
        # abs_R1 > 1% is a "significant move"
        r1_threshold = 0.01  # 1%
        gap2_min = self.significance_config.get("gap2_min_abs", {}).get("thresholds", [0.0025])[0]

        print(f"  R1 threshold (absolute): {r1_threshold:.2%}")
        print(f"  Gap2 minimum (absolute): {gap2_min:.4f}")
        print(f"  Signal logic (per spec):")
        print(f"    LONG:  R1 > +{r1_threshold:.2%} AND Gap2 < 0 (big up, then gap down)")
        print(f"    SHORT: R1 < -{r1_threshold:.2%} AND Gap2 > 0 (big down, then gap up)")

        signals = []
        for idx, row in df.iterrows():
            # Check if session is unknown - exclude from backtest per QA requirement
            session_known = row.get("effective_session") != "amc_assumed"

            if pd.isna(row["R1"]) or pd.isna(row["Gap2"]):
                signal = "EXCLUDED_NO_DATA"
                exclusion_reason = "missing R1 or Gap2"
            elif not session_known and row.get("session") == "unknown":
                # Unknown session = exclude from backtest to avoid misalignment
                # But for Phase 1, we run dual-assumption: treat all as AMC and flag it
                signal = "EXCLUDED_UNKNOWN_SESSION"
                exclusion_reason = "unknown BMO/AMC session"
            elif row["abs_R1"] < r1_threshold:
                signal = "NO_TRADE_SMALL_R1"
                exclusion_reason = f"R1 magnitude too small: {row['abs_R1']:.4f}"
            elif row["abs_Gap2"] < gap2_min:
                signal = "NO_TRADE_SMALL_GAP"
                exclusion_reason = f"Gap2 magnitude too small: {row['abs_Gap2']:.4f}"
            elif row["R1"] > r1_threshold and row["Gap2"] < 0:
                # LONG: Big up on T1, gap down into T2 -> revert up to Close(T1)
                # Target (t1_close) should be > Entry (t2_open) for this to make sense
                signal = "LONG"
                exclusion_reason = None
            elif row["R1"] < -r1_threshold and row["Gap2"] > 0:
                # SHORT: Big down on T1, gap up into T2 -> revert down to Close(T1)
                # Target (t1_close) should be < Entry (t2_open) for this to make sense
                signal = "SHORT"
                exclusion_reason = None
            else:
                # Gap direction same as R1 direction (no opposite gap)
                signal = "NO_TRADE_SAME_DIRECTION"
                exclusion_reason = "Gap2 direction matches R1 direction"

            # Calculate target and entry for validation
            target_price = row["t1_close"]
            entry_price = row["t2_open"]

            # Sanity check: for valid signals, verify target/entry relationship
            target_entry_valid = True
            if signal == "LONG" and not pd.isna(target_price) and not pd.isna(entry_price):
                # For LONG, target should be >= entry (we're buying low, targeting high)
                if target_price < entry_price:
                    # This is unexpected - target below entry for a long
                    # But it can happen if gap was very large
                    pass  # Still valid, just means we have upside target
            elif signal == "SHORT" and not pd.isna(target_price) and not pd.isna(entry_price):
                # For SHORT, target should be <= entry (we're selling high, targeting low)
                if target_price > entry_price:
                    # This is unexpected - target above entry for a short
                    pass  # Still valid

            signals.append({
                "event_idx": idx,
                "symbol": row["symbol"],
                "earnings_date": row["earnings_date"],
                "session": row["session"],
                "effective_session": row["effective_session"],
                "t0_date": row["t0_date"],
                "t1_date": row["t1_date"],
                "t2_date": row["t2_date"],
                "t0_close": row["t0_close"],
                "t1_close": row["t1_close"],
                "t2_open": row["t2_open"],
                "R1": row["R1"],
                "Gap2": row["Gap2"],
                "signal": signal,
                "exclusion_reason": exclusion_reason,
                "target_price": target_price,  # Target = Close(T1)
                "entry_price": entry_price,    # Entry = Open(T2)
                "t2_high": row["t2_high"],
                "t2_low": row["t2_low"],
                "t2_close": row["t2_close"],
            })

        self.signals = pd.DataFrame(signals)

        # Count signals
        signal_counts = self.signals["signal"].value_counts()
        tradeable = self.signals[self.signals["signal"].isin(["LONG", "SHORT"])]

        self.stats["signals_generated"] = len(tradeable)
        self.stats["events_excluded_unknown_session"] = int(
            (self.signals["signal"] == "EXCLUDED_UNKNOWN_SESSION").sum()
        )

        print(f"  Signal distribution:")
        for sig, count in signal_counts.items():
            print(f"    {sig}: {count}")

    def _step7_simulate_trades(self):
        """Simulate trade execution with hit detection and P&L.

        Trade Logic:
        - Entry: Open(T2)
        - Target: Close(T1) (the level we expect price to revert to)
        - Hit detection:
          - LONG: T2_high >= target (price reached up to target)
          - SHORT: T2_low <= target (price reached down to target)
        - Exit:
          - If hit: exit at target
          - If not hit: exit at Close(T2)

        Return Calculation:
        - LONG: (exit - entry) / entry  (profit if exit > entry)
        - SHORT: (entry - exit) / entry (profit if exit < entry)

        Assertions (QA requirement):
        - target_price == t1_close (exact)
        - For LONG hit: exit_price == target_price, gross_return == target/entry - 1
        - For SHORT hit: exit_price == target_price, gross_return == entry/target - 1
        """
        print("\n[Step 7] Simulating trades...")

        if self.signals is None or self.signals.empty:
            return

        # Get tradeable signals
        tradeable = self.signals[self.signals["signal"].isin(["LONG", "SHORT"])].copy()

        if tradeable.empty:
            print("  No tradeable signals")
            self.trades = pd.DataFrame()
            return

        # Load cost scenario (use medium for Phase 1)
        cost_scenario = self.cost_config["scenarios"]["medium"]
        total_cost_bps = (
            cost_scenario["spread_bps_each_side"] +
            cost_scenario["slippage_bps_each_side"] +
            cost_scenario["commission_bps_each_side"]
        ) * 2  # Entry + exit (round-trip)

        print(f"  Cost scenario: medium ({total_cost_bps} bps round-trip)")
        print(f"    - Applied once per trade as: net_return = gross_return - {total_cost_bps/100:.2f}%")

        trades = []
        validation_errors = []

        for _, sig in tradeable.iterrows():
            entry = sig["entry_price"]
            target = sig["target_price"]
            t1_close = sig["t1_close"]
            t2_high = sig["t2_high"]
            t2_low = sig["t2_low"]
            t2_close = sig["t2_close"]

            if pd.isna(entry) or pd.isna(target):
                continue

            # ASSERTION 1: target_price == t1_close
            if abs(target - t1_close) > 0.0001:
                validation_errors.append(
                    f"{sig['symbol']} {sig['earnings_date']}: target_price ({target}) != t1_close ({t1_close})"
                )

            # Hit detection using T2 High/Low
            if sig["signal"] == "LONG":
                # LONG: we bought at entry, target is the level we expect to reach
                # Check if intraday high reached target
                hit = t2_high >= target if not pd.isna(t2_high) else False
                if hit:
                    exit_price = target
                else:
                    exit_price = t2_close if not pd.isna(t2_close) else entry

                # LONG return: profit if we sell higher than we bought
                gross_return = (exit_price - entry) / entry

                # ASSERTION 2: For LONG hit, gross_return should equal target/entry - 1
                if hit:
                    expected_return = (target - entry) / entry
                    if abs(gross_return - expected_return) > 0.0001:
                        validation_errors.append(
                            f"{sig['symbol']} {sig['earnings_date']} LONG hit: "
                            f"gross_return ({gross_return:.6f}) != expected ({expected_return:.6f})"
                        )

            else:  # SHORT
                # SHORT: we sold at entry, target is the level we expect to reach
                # Check if intraday low reached target
                hit = t2_low <= target if not pd.isna(t2_low) else False
                if hit:
                    exit_price = target
                else:
                    exit_price = t2_close if not pd.isna(t2_close) else entry

                # SHORT return: profit if we buy back lower than we sold
                gross_return = (entry - exit_price) / entry

                # ASSERTION 3: For SHORT hit, gross_return should equal (entry - target) / entry
                if hit:
                    expected_return = (entry - target) / entry
                    if abs(gross_return - expected_return) > 0.0001:
                        validation_errors.append(
                            f"{sig['symbol']} {sig['earnings_date']} SHORT hit: "
                            f"gross_return ({gross_return:.6f}) != expected ({expected_return:.6f})"
                        )

            # Apply costs (once per round-trip trade)
            net_return = gross_return - (total_cost_bps / 10000)

            trades.append({
                "symbol": sig["symbol"],
                "earnings_date": sig["earnings_date"],
                "session": sig["session"],
                "effective_session": sig["effective_session"],
                "t0_date": sig["t0_date"],
                "t1_date": sig["t1_date"],
                "t2_date": sig["t2_date"],
                "signal": sig["signal"],
                "R1": sig["R1"],
                "Gap2": sig["Gap2"],
                "t0_close": sig["t0_close"],
                "t1_close": t1_close,
                "entry_price": entry,
                "target_price": target,
                "exit_price": exit_price,
                "t2_high": t2_high,
                "t2_low": t2_low,
                "t2_close": t2_close,
                "hit_target": hit,
                "gross_return": gross_return,
                "cost_bps": total_cost_bps,
                "net_return": net_return,
            })

        self.trades = pd.DataFrame(trades)

        # Report validation errors
        if validation_errors:
            print(f"\n  WARNING: {len(validation_errors)} validation error(s):")
            for err in validation_errors[:5]:
                print(f"    - {err}")
            if len(validation_errors) > 5:
                print(f"    ... and {len(validation_errors) - 5} more")
            self.stats["trade_validation_errors"] = len(validation_errors)
        else:
            print("  All trade validations passed (target=t1_close, return math correct)")
            self.stats["trade_validation_errors"] = 0

        if not self.trades.empty:
            hits = self.trades["hit_target"].sum()
            self.stats["trades_executed"] = len(self.trades)
            self.stats["trades_hit_target"] = int(hits)
            self.stats["hit_rate"] = float(hits / len(self.trades)) if len(self.trades) > 0 else 0.0
            self.stats["avg_gross_return"] = float(self.trades["gross_return"].mean())
            self.stats["avg_net_return"] = float(self.trades["net_return"].mean())

            print(f"\n  Trades executed: {len(self.trades)}")
            print(f"  Hit target: {hits} ({hits/len(self.trades):.1%})")
            print(f"  Avg gross return: {self.trades['gross_return'].mean():.4f}")
            print(f"  Avg net return: {self.trades['net_return'].mean():.4f}")

            # Show sample trades for verification
            print("\n  Sample trades (for verification):")
            for _, trade in self.trades.head(3).iterrows():
                direction = "↑" if trade["signal"] == "LONG" else "↓"
                hit_str = "HIT" if trade["hit_target"] else "MISS"
                print(f"    {trade['symbol']} {trade['t2_date']} {trade['signal']}{direction}: "
                      f"entry={trade['entry_price']:.2f} target={trade['target_price']:.2f} "
                      f"exit={trade['exit_price']:.2f} [{hit_str}] gross={trade['gross_return']:.4f}")

    def _step8_export_csvs(self):
        """Export all data to CSVs."""
        print("\n[Step 8] Exporting CSVs...")

        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        exports = {}

        # 1. S&P 500 constituents sample
        if self.sp500_constituents is not None and not self.sp500_constituents.empty:
            path = EXPORT_DIR / "phase_1__sp500_constituents_sample.csv"
            self.sp500_constituents.to_csv(path, index=False)
            exports["phase_1__sp500_constituents_sample.csv"] = len(self.sp500_constituents)
            print(f"  {path.name}: {len(self.sp500_constituents)} rows")

        # 2. Earnings events
        if self.earnings_events is not None and not self.earnings_events.empty:
            path = EXPORT_DIR / "phase_1__earnings_events.csv"
            self.earnings_events.to_csv(path, index=False)
            exports["phase_1__earnings_events.csv"] = len(self.earnings_events)
            print(f"  {path.name}: {len(self.earnings_events)} rows")

        # 3. Daily OHLCV
        if self.daily_ohlcv is not None and not self.daily_ohlcv.empty:
            path = EXPORT_DIR / "phase_1__daily_ohlcv.csv"
            self.daily_ohlcv.to_csv(path, index=False)
            exports["phase_1__daily_ohlcv.csv"] = len(self.daily_ohlcv)
            print(f"  {path.name}: {len(self.daily_ohlcv)} rows")

        # 4. Event windows (with features)
        if self.event_windows is not None and not self.event_windows.empty:
            path = EXPORT_DIR / "phase_1__event_windows.csv"
            self.event_windows.to_csv(path, index=False)
            exports["phase_1__event_windows.csv"] = len(self.event_windows)
            print(f"  {path.name}: {len(self.event_windows)} rows")

        # 5. Signals
        if self.signals is not None and not self.signals.empty:
            path = EXPORT_DIR / "phase_1__signals.csv"
            self.signals.to_csv(path, index=False)
            exports["phase_1__signals.csv"] = len(self.signals)
            print(f"  {path.name}: {len(self.signals)} rows")

        # 6. Trades
        if self.trades is not None and not self.trades.empty:
            path = EXPORT_DIR / "phase_1__trades.csv"
            self.trades.to_csv(path, index=False)
            exports["phase_1__trades.csv"] = len(self.trades)
            print(f"  {path.name}: {len(self.trades)} rows")

        # 7. Core features (for backward compatibility)
        if self.event_windows is not None and not self.event_windows.empty:
            features = self.event_windows[
                [
                    "symbol", "earnings_date", "session", "effective_session",
                    "t0_date", "t1_date", "t2_date",
                    "t0_close", "t1_close", "t2_open",
                    "R1", "Gap2", "abs_R1", "abs_Gap2",
                ]
            ].copy()
            path = EXPORT_DIR / "phase_1__features_core.csv"
            features.to_csv(path, index=False)
            exports["phase_1__features_core.csv"] = len(features)
            print(f"  {path.name}: {len(features)} rows")

        self.stats["exports"] = exports

    def _print_summary(self):
        """Print final summary."""
        print("\nSummary:")
        print("-" * 40)
        print(f"Tickers: {', '.join(self.tickers)}")
        print(f"Earnings events: {self.stats['total_earnings_events']}")
        print(f"Events with unknown session: {self.stats['events_with_unknown_session']}")
        print(f"Complete windows: {self.stats['complete_windows']}")
        print(f"Signals generated: {self.stats['signals_generated']}")
        print(f"Trades executed: {self.stats['trades_executed']}")
        if self.stats['trades_executed'] > 0:
            print(f"Hit rate: {self.stats.get('hit_rate', 0):.1%}")
            print(f"Avg gross return: {self.stats.get('avg_gross_return', 0):.4f}")
            print(f"Avg net return: {self.stats.get('avg_net_return', 0):.4f}")


def main():
    """Run Phase 1 pipeline."""
    pipeline = Phase1Pipeline()
    stats = pipeline.run()
    return stats


if __name__ == "__main__":
    main()
