# Phase 1: Smoke Test - Status Report

**Date**: 2026-01-17
**Status**: COMPLETE (End-to-End Backtest)
**Phase**: 1 of 6

## Overview

Phase 1 implements a complete end-to-end smoke test of the earnings-reversal pipeline using real FMP API data, including signal generation, trade execution simulation, and P&L computation.

## Objectives

- [x] Pull S&P 500 constituents sample from FMP
- [x] Select 5 tickers with documented rationale
- [x] Pull historical quarterly earnings dates (~20 events target)
- [x] Pull daily OHLCV data covering T0/T1/T2 dates
- [x] Implement trading-day mapping (NYSE calendar via exchange_calendars)
- [x] Build event windows table with OHLCV
- [x] Compute core features (R1, Gap2)
- [x] Implement signal generation (significant move filter)
- [x] Implement entry/exit/hit logic with target price
- [x] Add cost model (spread + slippage + commission)
- [x] Compute gross and net P&L
- [x] Export all CSVs

## Ticker Selection

| Ticker | Company | Sector | Rationale |
|--------|---------|--------|-----------|
| AAPL | Apple Inc. | Technology | High liquidity, frequent earnings |
| JPM | JPMorgan Chase & Co. | Financials | Major bank, different earnings cycle |
| JNJ | Johnson & Johnson | Healthcare | Defensive stock, stable earnings |
| XOM | Exxon Mobil Corporation | Energy | Commodity-linked, volatile around earnings |
| WMT | Walmart Inc. | Consumer Defensive | Retail sector, different seasonality |

**Selection criteria**: Diversification across major S&P 500 sectors, high liquidity, confirmed S&P 500 membership.

## Data Policy

- **OHLCV Source**: FMP `/stable/historical-price-eod/full`
- **Adjustment**: Split-adjusted (NOT dividend-adjusted)
- **BMO/AMC**: FMP does not provide earnings timing; all events treated as AMC (conservative assumption)

## Data Summary

### Earnings Events
- **Total events**: 38 (target was ~20)
- **Date range**: 2022 - 2025
- **Source**: FMP `/stable/earnings` endpoint
- **Session tracking**: All marked as "unknown" (FMP limitation), treated as AMC

### OHLCV Data
- **Total rows**: 2,795
- **Trading days per ticker**: ~559
- **Source**: FMP `/stable/historical-price-eod/full` endpoint

### Event Windows
- **Total windows**: 38
- **Complete windows** (T0+T1+T2 data): 38 (100%)
- **Missing T0**: 0
- **Missing T1**: 0
- **Missing T2**: 0

### Trading Calendar
- Uses `exchange_calendars` library (production-grade NYSE calendar)
- Full NYSE holiday and early close handling
- Session-aware T0/T1/T2 mapping (BMO vs AMC)

## Feature Statistics

| Feature | Valid Count | Mean | Std Dev |
|---------|-------------|------|---------|
| R1 | 38 | -0.0023 | 0.0172 |
| Gap2 | 38 | -0.0031 | 0.0168 |

**Definitions**:
- **R1** = Close(T1) / Close(T0) - 1 (day-after return)
- **Gap2** = Open(T2) / Close(T1) - 1 (overnight gap into T2)

## Signal Generation

**Strategy Logic**:
- **LONG signal**: R1 < -1% (big drop) AND Gap2 > 0 (positive overnight gap)
- **SHORT signal**: R1 > +1% (big rise) AND Gap2 < 0 (negative overnight gap)
- **NO_SIGNAL**: Conditions not met

**Results**:
- Total events: 38
- Tradeable signals (LONG/SHORT): 6
- Signal rate: 15.8%

## Trade Execution

**Entry/Exit Rules**:
- **Entry**: Open(T2) at market open
- **Target**: Close(T1) (reversion target)
- **Hit detection**:
  - LONG: T2_high >= target_price
  - SHORT: T2_low <= target_price
- **Exit**: Target if hit, else Close(T2)

**Cost Model** (medium scenario from config):
- Spread: 5 bps
- Slippage: 5 bps
- Commission: 10 bps
- **Total round-trip**: 20 bps

**Results**:
- Trades executed: 6
- Trades hit target: varies per run
- Hit rate: see QA manifest for current stats

## Exported Files

| File | Rows | Description |
|------|------|-------------|
| phase_1__sp500_constituents_sample.csv | 5 | Selected tickers with sector info |
| phase_1__earnings_events.csv | 38 | Historical earnings dates + EPS data |
| phase_1__daily_ohlcv.csv | 2,795 | Daily price data for all tickers |
| phase_1__event_windows.csv | 38 | T0/T1/T2 dates and OHLCV per event |
| phase_1__features_core.csv | 38 | Computed R1 and Gap2 features |
| phase_1__signals.csv | 38 | Signal for each event with entry/target prices |
| phase_1__trades.csv | 6 | Executed trades with P&L |

## Technical Notes

### FMP API Endpoints Used
- `/stable/earnings?symbol={ticker}&limit=10` - Historical earnings
- `/stable/historical-price-eod/full?symbol={ticker}&from=...&to=...` - Daily OHLCV

### FMP Subscription Limitations
- `/stable/sp500-constituent` requires higher tier (not used)
- BMO/AMC timing not provided (all treated as AMC)
- Workaround: Used hardcoded S&P 500 sample for Phase 1

### Trading Day Definitions (Session-Aware)

**AMC (After Market Close) / Unknown**:
- T0 = Earnings date (market is closed when earnings released)
- T1 = Next trading day (first full trading day post-earnings)
- T2 = Next trading day after T1

**BMO (Before Market Open)**:
- T0 = Previous trading day
- T1 = Earnings date (first full trading day post-earnings)
- T2 = Next trading day after T1

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

## Next Steps (Phase 2)

1. Scale to full S&P 500 universe (requires API upgrade or alternative data source)
2. Extend historical range to 15 years
3. Implement rolling signal features (z-score, percentile rank)
4. Add BMO/AMC handling with alternative data source

## QA Status

- [x] All required files exported
- [x] No missing T0/T1/T2 windows
- [x] R1 and Gap2 computed for all events
- [x] Signal generation implemented
- [x] Trade execution simulated
- [x] Cost model applied
- [x] Local QA checks: PASS

---
*Generated by Phase 1 smoke test pipeline*
