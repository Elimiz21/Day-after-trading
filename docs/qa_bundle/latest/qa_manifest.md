# QA Manifest (Phase 1 - End-to-End Backtest)

- **timestamp_utc**: 2026-01-17T21:24:11.557787Z
- **git_commit**: 331c0c57f487f3e40ea397cdf3c6bc5c381e8224
- **phase**: 1 (Smoke Test)

## Selected Tickers
AAPL, JPM, JNJ, XOM, WMT

## Data Policy
- **OHLCV Source**: FMP /stable/historical-price-eod/full
- **Adjustment**: Split-adjusted (NOT dividend-adjusted)
  - Split-adjusted: stock splits are reflected in historical prices
  - NOT dividend-adjusted: overnight gaps include ex-dividend effects
- **BMO/AMC Handling**: FMP does not provide earnings announcement timing
  - Events with unknown session: tracked and reported
  - For correctness: unknown-session events should be excluded or run with dual-assumption sensitivity

## Coverage Statistics
- **Total earnings events**: 38
- **Events with unknown session (BMO/AMC)**: 38
- **Complete event windows** (T0+T1+T2): 38
- **Missing T0 data**: 0
- **Missing T1 data**: 0
- **Missing T2 data**: 0

## Signal Generation Statistics
- **Signal rule**: LONG when R1 > 1% AND Gap2 < 0; SHORT when R1 < -1% AND Gap2 > 0
- **LONG signals**: 3
- **SHORT signals**: 3
- **Total tradeable signals**: 6

### Non-Signal Breakdown
- Events excluded (unknown session): 0
- No trade (R1 too small): 22
- No trade (Gap2 too small): 5
- No trade (same direction): 5

## Trade Execution Statistics
- **Trades executed**: 6
- **Trades hit target**: 4
- **Hit rate**: 66.7%
- **Avg gross return**: 0.0051
- **Avg net return**: 0.0031
- **LONG avg gross**: 0.0088 (hit rate: 100.0%)
- **SHORT avg gross**: 0.0013 (hit rate: 33.3%)

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
| phase_1__daily_ohlcv.csv | 2795 |
| phase_1__earnings_events.csv | 38 |
| phase_1__event_windows.csv | 38 |
| phase_1__features_core.csv | 38 |
| phase_1__signals.csv | 38 |
| phase_1__sp500_constituents_sample.csv | 5 |
| phase_1__trades.csv | 6 |

## Reproduction Commands
```bash
python -m src.pipeline.phase1_smoke_test
python -m src.qa.run_qa --mode local
python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest
```

## Feature Statistics
- **R1**: mean=-0.0023, std=0.0172
- **Gap2**: mean=-0.0031, std=0.0168

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
