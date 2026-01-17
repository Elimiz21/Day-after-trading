# Phase 1 Summaries

## Data Counts

| Metric | Value |
|--------|-------|
| Selected tickers | 5 |
| Total earnings events | 38 |
| Complete windows | 38 |
| Missing T0 | 0 |
| Missing T1 | 0 |
| Missing T2 | 0 |

## CSV Row Counts

| File | Rows |
|------|------|
| phase_1__daily_ohlcv.csv | 2520 |
| phase_1__earnings_events.csv | 38 |
| phase_1__event_windows.csv | 38 |
| phase_1__features_core.csv | 38 |
| phase_1__sp500_constituents_sample.csv | 5 |

## Sample: Core Features (first 5 rows)

```
symbol earnings_date    t0_date    t1_date    t2_date  t0_close  t1_close  t2_open        R1      Gap2
   JPM    2026-01-13 2026-01-13 2026-01-14 2026-01-15    310.90    307.87   308.47 -0.009746  0.001949
   WMT    2025-11-20 2025-11-20 2025-11-21 2025-11-24    107.11    105.32   105.36 -0.016712  0.000380
   XOM    2025-10-31 2025-10-31 2025-11-03 2025-11-04    114.36    113.76   113.38 -0.005247 -0.003340
  AAPL    2025-10-30 2025-10-30 2025-10-31 2025-11-03    271.40    270.37   270.42 -0.003795  0.000185
   JPM    2025-10-14 2025-10-14 2025-10-15 2025-10-16    302.08    305.69   305.35  0.011950 -0.001112
```

## Sample: Earnings Events (first 5 rows)

```
symbol       date  epsActual  epsEstimated
   JPM 2026-01-13       5.23         4.850
   WMT 2025-11-20       0.62         0.601
   XOM 2025-10-31       1.88         1.820
  AAPL 2025-10-30       1.85         1.780
   JPM 2025-10-14       5.07         4.850
```
