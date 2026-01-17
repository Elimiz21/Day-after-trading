# QA Manifest (Phase 1)

- **timestamp_utc**: 2026-01-17T20:52:28.179227Z
- **git_commit**: 1f9696e070fad0046431b847d73165d63a95803b
- **phase**: 1 (Smoke Test)

## Selected Tickers
AAPL, JPM, JNJ, XOM, WMT

## Coverage Statistics
- **Total earnings events**: 38
- **Complete event windows** (T0+T1+T2): 38
- **Missing T0 data**: 0
- **Missing T1 data**: 0
- **Missing T2 data**: 0

## Exported CSVs

| File | Row Count |
|------|-----------|
| phase_1__daily_ohlcv.csv | 2520 |
| phase_1__earnings_events.csv | 38 |
| phase_1__event_windows.csv | 38 |
| phase_1__features_core.csv | 38 |
| phase_1__sp500_constituents_sample.csv | 5 |

## Reproduction Commands
```bash
python -m src.qa.run_qa --mode local
python -m src.qa.build_qa_bundle --out docs/qa_bundle/latest
```

## Feature Statistics
- **R1**: mean=-0.0023, std=0.0172
- **Gap2**: mean=-0.0031, std=0.0168
