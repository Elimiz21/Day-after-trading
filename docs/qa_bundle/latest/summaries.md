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
| Signals generated | 6 |
| Trades executed | 6 |
| Trades hit target | 6 |

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

## Sample: Signals (first 10 rows)

```
symbol earnings_date             signal        R1      Gap2  entry_price  target_price
   JPM    2026-01-13  NO_TRADE_SMALL_R1 -0.009746  0.001949       308.47        307.87
   WMT    2025-11-20 NO_TRADE_SMALL_GAP -0.016712  0.000380       105.36        105.32
   XOM    2025-10-31  NO_TRADE_SMALL_R1 -0.005247 -0.003340       113.38        113.76
  AAPL    2025-10-30  NO_TRADE_SMALL_R1 -0.003795  0.000185       270.42        270.37
   JPM    2025-10-14 NO_TRADE_SMALL_GAP  0.011950 -0.001112       305.35        305.69
   JNJ    2025-10-14  NO_TRADE_SMALL_R1  0.001677  0.000889       191.34        191.17
   WMT    2025-08-21 NO_TRADE_SMALL_GAP -0.011535  0.001756        97.00         96.83
   XOM    2025-08-01 NO_TRADE_SMALL_GAP -0.020704 -0.001397       107.22        107.37
  AAPL    2025-07-31               LONG -0.025004  0.010525       204.51        202.38
   JNJ    2025-07-16               LONG -0.010924  0.005829       163.93        162.98
```

## Sample: Trades (all)

```
symbol signal  entry_price  target_price  exit_price  hit_target  gross_return  net_return
  AAPL   LONG       204.51        202.38      202.38        True     -0.010415   -0.012415
   JNJ   LONG       163.93        162.98      162.98        True     -0.005795   -0.007795
   WMT  SHORT        96.65         98.24       98.24        True     -0.016451   -0.018451
   XOM   LONG       103.89        103.27      103.27        True     -0.005968   -0.007968
  AAPL  SHORT       182.35        183.38      183.38        True     -0.005648   -0.007648
   XOM  SHORT       119.11        119.64      119.64        True     -0.004450   -0.006450
```
