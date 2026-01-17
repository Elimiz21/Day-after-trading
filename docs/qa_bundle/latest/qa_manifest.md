# QA Manifest (Phase 1 - End-to-End Backtest)

- **timestamp_utc**: 2026-01-17T21:12:09.914495Z
- **git_commit**: cf1570061015761793959cb929ae08a072749e8c
- **phase**: 1 (Smoke Test)

## Selected Tickers
AAPL, JPM, JNJ, XOM, WMT

## Data Policy
- **OHLCV Source**: FMP /stable/historical-price-eod/full
- **Adjustment**: Split-adjusted (NOT dividend-adjusted)
- **BMO/AMC**: All events treated as AMC (FMP does not provide timing)

## Coverage Statistics
- **Total earnings events**: 38
- **Events with unknown session (BMO/AMC)**: 38
- **Complete event windows** (T0+T1+T2): 38
- **Missing T0 data**: 0
- **Missing T1 data**: 0
- **Missing T2 data**: 0

## Signal & Trade Statistics
- **Tradeable signals generated**: 6
- **Trades executed**: 6
- **Trades hit target**: 6
- **Hit rate**: 100.0%
- **Avg gross return**: -0.0081
- **Avg net return**: -0.0101

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
