"""Phase 1: Smoke Test Pipeline

This module implements the Phase 1 smoke test:
- Pull S&P 500 constituents sample (5 tickers)
- Pull ~20 earnings events from FMP
- Pull daily OHLCV for T0/T1/T2
- Compute R1 and Gap2 features
- Export all CSVs

Ticker Selection Criteria (Phase 1):
-------------------------------------
We select 5 tickers from different sectors to ensure diversity:
1. AAPL (Technology) - High liquidity, frequent earnings
2. JPM (Financials) - Major bank, different earnings cycle
3. JNJ (Healthcare) - Defensive stock, stable earnings
4. XOM (Energy) - Commodity-linked, volatile around earnings
5. WMT (Consumer Defensive) - Retail sector, different seasonality

These represent major sectors and have sufficient liquidity.
All are confirmed S&P 500 members.
"""

from datetime import date, timedelta
from pathlib import Path
from typing import Optional

import pandas as pd

from src.ingestion import FMPClient, TradingCalendar

# Phase 1 selected tickers with rationale
PHASE1_TICKERS = {
    "AAPL": "Technology - High liquidity, frequent earnings",
    "JPM": "Financials - Major bank, different earnings cycle",
    "JNJ": "Healthcare - Defensive stock, stable earnings",
    "XOM": "Energy - Commodity-linked, volatile around earnings",
    "WMT": "Consumer Defensive - Retail sector, different seasonality",
}

EXPORT_DIR = Path("data/exports/csv")


class Phase1Pipeline:
    """Phase 1 smoke test pipeline."""

    def __init__(self):
        self.fmp = FMPClient()
        self.calendar = TradingCalendar()
        self.tickers = list(PHASE1_TICKERS.keys())

        # Data containers
        self.sp500_constituents: Optional[pd.DataFrame] = None
        self.earnings_events: Optional[pd.DataFrame] = None
        self.daily_ohlcv: Optional[pd.DataFrame] = None
        self.event_windows: Optional[pd.DataFrame] = None
        self.features: Optional[pd.DataFrame] = None

        # Stats for QA
        self.stats = {
            "selected_tickers": self.tickers,
            "ticker_rationale": PHASE1_TICKERS,
            "total_earnings_events": 0,
            "missing_t0": 0,
            "missing_t1": 0,
            "missing_t2": 0,
            "complete_windows": 0,
        }

    def run(self) -> dict:
        """Execute full Phase 1 pipeline."""
        print("=" * 60)
        print("PHASE 1: Smoke Test Pipeline")
        print("=" * 60)

        self._step1_fetch_sp500()
        self._step2_fetch_earnings()
        self._step3_fetch_ohlcv()
        self._step4_build_event_windows()
        self._step5_compute_features()
        self._step6_export_csvs()

        print("\n" + "=" * 60)
        print("Phase 1 Complete!")
        print("=" * 60)
        self._print_summary()

        return self.stats

    def _step1_fetch_sp500(self):
        """Fetch S&P 500 constituents sample."""
        print("\n[Step 1] Creating S&P 500 constituents sample...")
        # Note: /stable/sp500-constituent requires higher tier subscription
        # For Phase 1, we use hardcoded sample of our selected tickers
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
            else:
                print(f"    WARNING: No earnings data for {ticker}")

        if all_earnings:
            self.earnings_events = pd.concat(all_earnings, ignore_index=True)
            # Sort by date descending to get most recent
            self.earnings_events = self.earnings_events.sort_values(
                "date", ascending=False
            ).reset_index(drop=True)
        else:
            self.earnings_events = pd.DataFrame()

        self.stats["total_earnings_events"] = len(self.earnings_events)
        print(f"\n  Total earnings events: {len(self.earnings_events)}")

    def _step3_fetch_ohlcv(self):
        """Fetch daily OHLCV data for all dates needed."""
        print("\n[Step 3] Fetching daily OHLCV data...")

        if self.earnings_events.empty:
            print("  ERROR: No earnings events to fetch OHLCV for")
            return

        # Determine date range needed (with buffer for T0/T1/T2)
        min_date = self.earnings_events["date"].min() - timedelta(days=10)
        max_date = self.earnings_events["date"].max() + timedelta(days=10)

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
            else:
                print(f"    WARNING: No OHLCV data for {ticker}")

        if all_ohlcv:
            self.daily_ohlcv = pd.concat(all_ohlcv, ignore_index=True)
        else:
            self.daily_ohlcv = pd.DataFrame()

        print(f"\n  Total OHLCV rows: {len(self.daily_ohlcv)}")

    def _step4_build_event_windows(self):
        """Build T0/T1/T2 windows for each earnings event."""
        print("\n[Step 4] Building event windows (T0/T1/T2)...")

        if self.earnings_events.empty or self.daily_ohlcv.empty:
            print("  ERROR: Missing earnings or OHLCV data")
            return

        # Create lookup for OHLCV by (symbol, date)
        ohlcv_lookup = {}
        for _, row in self.daily_ohlcv.iterrows():
            key = (row["symbol"], row["date"].date())
            ohlcv_lookup[key] = row

        windows = []
        missing_t0 = 0
        missing_t1 = 0
        missing_t2 = 0

        for _, event in self.earnings_events.iterrows():
            symbol = event["symbol"]
            earnings_date = event["date"].date()

            # Get T0/T1/T2 dates
            t_dates = self.calendar.get_t0_t1_t2(earnings_date)

            # Look up OHLCV for each date
            t0_data = ohlcv_lookup.get((symbol, t_dates["t0"]))
            t1_data = ohlcv_lookup.get((symbol, t_dates["t1"]))
            t2_data = ohlcv_lookup.get((symbol, t_dates["t2"]))

            # Track missing data
            if t0_data is None:
                missing_t0 += 1
            if t1_data is None:
                missing_t1 += 1
            if t2_data is None:
                missing_t2 += 1

            window = {
                "symbol": symbol,
                "earnings_date": earnings_date,
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

        # Count complete windows (all T0/T1/T2 have data)
        complete = self.event_windows.dropna(
            subset=["t0_close", "t1_close", "t2_close"]
        )

        self.stats["missing_t0"] = missing_t0
        self.stats["missing_t1"] = missing_t1
        self.stats["missing_t2"] = missing_t2
        self.stats["complete_windows"] = len(complete)

        print(f"  Total event windows: {len(self.event_windows)}")
        print(f"  Complete windows (T0+T1+T2): {len(complete)}")
        print(f"  Missing T0: {missing_t0}, T1: {missing_t1}, T2: {missing_t2}")

    def _step5_compute_features(self):
        """Compute R1 and Gap2 features."""
        print("\n[Step 5] Computing core features (R1, Gap2)...")

        if self.event_windows is None or self.event_windows.empty:
            print("  ERROR: No event windows to compute features")
            return

        df = self.event_windows.copy()

        # R1 = Close(T1) / Close(T0) - 1
        df["R1"] = df["t1_close"] / df["t0_close"] - 1

        # Gap2 = Open(T2) / Close(T1) - 1
        df["Gap2"] = df["t2_open"] / df["t1_close"] - 1

        self.features = df[
            [
                "symbol",
                "earnings_date",
                "t0_date",
                "t1_date",
                "t2_date",
                "t0_close",
                "t1_close",
                "t2_open",
                "R1",
                "Gap2",
            ]
        ].copy()

        # Stats on computed features
        valid_r1 = df["R1"].notna().sum()
        valid_gap2 = df["Gap2"].notna().sum()

        self.stats["valid_r1_count"] = int(valid_r1)
        self.stats["valid_gap2_count"] = int(valid_gap2)

        print(f"  Valid R1 values: {valid_r1}")
        print(f"  Valid Gap2 values: {valid_gap2}")

        if valid_r1 > 0:
            r1_mean = df["R1"].mean()
            r1_std = df["R1"].std()
            self.stats["r1_mean"] = float(r1_mean)
            self.stats["r1_std"] = float(r1_std)
            print(f"  R1 mean: {r1_mean:.4f}, std: {r1_std:.4f}")
        if valid_gap2 > 0:
            gap2_mean = df["Gap2"].mean()
            gap2_std = df["Gap2"].std()
            self.stats["gap2_mean"] = float(gap2_mean)
            self.stats["gap2_std"] = float(gap2_std)
            print(f"  Gap2 mean: {gap2_mean:.4f}, std: {gap2_std:.4f}")

    def _step6_export_csvs(self):
        """Export all data to CSVs."""
        print("\n[Step 6] Exporting CSVs...")

        # Ensure export directory exists
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)

        exports = {}

        # 1. S&P 500 constituents (sample for Phase 1)
        if self.sp500_constituents is not None and not self.sp500_constituents.empty:
            path = EXPORT_DIR / "phase_1__sp500_constituents_sample.csv"
            self.sp500_constituents.to_csv(path, index=False)
            exports["phase_1__sp500_constituents_sample.csv"] = len(self.sp500_constituents)
            print(f"  Exported {path.name}: {len(self.sp500_constituents)} rows")

        # 2. Earnings events
        if self.earnings_events is not None and not self.earnings_events.empty:
            path = EXPORT_DIR / "phase_1__earnings_events.csv"
            self.earnings_events.to_csv(path, index=False)
            exports["phase_1__earnings_events.csv"] = len(self.earnings_events)
            print(f"  Exported {path.name}: {len(self.earnings_events)} rows")

        # 3. Daily OHLCV (only needed rows)
        if self.daily_ohlcv is not None and not self.daily_ohlcv.empty:
            path = EXPORT_DIR / "phase_1__daily_ohlcv.csv"
            self.daily_ohlcv.to_csv(path, index=False)
            exports["phase_1__daily_ohlcv.csv"] = len(self.daily_ohlcv)
            print(f"  Exported {path.name}: {len(self.daily_ohlcv)} rows")

        # 4. Event windows
        if self.event_windows is not None and not self.event_windows.empty:
            path = EXPORT_DIR / "phase_1__event_windows.csv"
            self.event_windows.to_csv(path, index=False)
            exports["phase_1__event_windows.csv"] = len(self.event_windows)
            print(f"  Exported {path.name}: {len(self.event_windows)} rows")

        # 5. Features
        if self.features is not None and not self.features.empty:
            path = EXPORT_DIR / "phase_1__features_core.csv"
            self.features.to_csv(path, index=False)
            exports["phase_1__features_core.csv"] = len(self.features)
            print(f"  Exported {path.name}: {len(self.features)} rows")

        self.stats["exports"] = exports

    def _print_summary(self):
        """Print final summary."""
        print("\nSummary:")
        print("-" * 40)
        print(f"Selected tickers: {', '.join(self.tickers)}")
        print(f"Total earnings events: {self.stats['total_earnings_events']}")
        print(f"Complete windows: {self.stats['complete_windows']}")
        print(f"Missing T0: {self.stats['missing_t0']}")
        print(f"Missing T1: {self.stats['missing_t1']}")
        print(f"Missing T2: {self.stats['missing_t2']}")
        print("\nExported files:")
        for fname, rows in self.stats.get("exports", {}).items():
            print(f"  {fname}: {rows} rows")


def main():
    """Run Phase 1 pipeline."""
    pipeline = Phase1Pipeline()
    stats = pipeline.run()
    return stats


if __name__ == "__main__":
    main()
