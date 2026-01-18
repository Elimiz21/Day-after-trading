# Phase 1 Summaries

## Data Counts

| Metric | Value |
|--------|-------|
| Selected tickers | 5 |
| Total earnings events | 38 |
| Events with unknown session | 38 |
| Complete windows | 38 |
| Missing T0 | 0 |
| Missing T1 | 0 |
| Missing T2 | 0 |
| LONG signals | 3 |
| SHORT signals | 3 |
| Trades executed | 6 |
| Trades hit target | 4 |

## CSV Row Counts

| File | Rows |
|------|------|
| phase_1__daily_ohlcv.csv | 2795 |
| phase_1__earnings_events.csv | 38 |
| phase_1__event_windows.csv | 38 |
| phase_1__features_core.csv | 38 |
| phase_1__signals.csv | 38 |
| phase_1__sp500_constituents_sample.csv | 5 |
| phase_1__trades.csv | 6 |

## Sample: Core Features (first 5 rows)

```
symbol earnings_date session    t0_date    t1_date    t2_date        R1      Gap2
   JPM    2026-01-13 unknown 2026-01-13 2026-01-14 2026-01-15 -0.009746  0.001949
   WMT    2025-11-20 unknown 2025-11-20 2025-11-21 2025-11-24 -0.016712  0.000380
   XOM    2025-10-31 unknown 2025-10-31 2025-11-03 2025-11-04 -0.005247 -0.003340
  AAPL    2025-10-30 unknown 2025-10-30 2025-10-31 2025-11-03 -0.003795  0.000185
   JPM    2025-10-14 unknown 2025-10-14 2025-10-15 2025-10-16  0.011950 -0.001112
```

## Sample: Tradeable Signals (all LONG/SHORT)

```
symbol earnings_date signal        R1      Gap2  entry_price  target_price  t1_close
  AAPL    2025-07-31  SHORT -0.025004  0.010525       204.51        202.38    202.38
   JNJ    2025-07-16  SHORT -0.010924  0.005829       163.93        162.98    162.98
   WMT    2025-05-15   LONG  0.019616 -0.016185        96.65         98.24     98.24
   XOM    2025-05-02  SHORT -0.027681  0.006004       103.89        103.27    103.27
  AAPL    2024-05-02   LONG  0.059816 -0.005617       182.35        183.38    183.38
   XOM    2024-04-26   LONG  0.014242 -0.004430       119.11        119.64    119.64
```

## Sample: Trades (all)

```
symbol    t2_date signal        R1      Gap2  entry_price  target_price  t1_close  exit_price  hit_target  gross_return  net_return
  AAPL 2025-08-04  SHORT -0.025004  0.010525       204.51        202.38    202.38      202.38        True      0.010415    0.008415
   JNJ 2025-07-18  SHORT -0.010924  0.005829       163.93        162.98    162.98      163.70       False      0.001403   -0.000597
   WMT 2025-05-19   LONG  0.019616 -0.016185        96.65         98.24     98.24       98.24        True      0.016451    0.014451
   XOM 2025-05-06  SHORT -0.027681  0.006004       103.89        103.27    103.27      104.71       False     -0.007893   -0.009893
  AAPL 2024-05-06   LONG  0.059816 -0.005617       182.35        183.38    183.38      183.38        True      0.005648    0.003648
   XOM 2024-04-30   LONG  0.014242 -0.004430       119.11        119.64    119.64      119.64        True      0.004450    0.002450
```
