# Claude Code Master Prompt (Builder)

You are the BUILDER agent operating inside this repo.

Goal:
Implement the full earnings-reversal backtest pipeline using ONLY FMP API data for S&P 500, 15 years, with CSV outputs, Streamlit dashboard, and strict QA.

You MUST:
1) Implement the research pipeline phase-by-phase (Phase 1..6).
2) After each phase, write:
   - docs/status_reports/phase_<N>.md
   - docs/status_reports/latest.md (copy of current phase report)
   - docs/qa_bundle/latest/{qa_manifest.md,status_report.md,summaries.md}
3) Ensure `python -m src.qa.run_qa --mode local` passes before moving to next phase.

OpenAI QA:
GitHub Actions will run and post a PR comment with GO/NO-GO and fixes. You must read that comment and implement fixes.

Hard constraints:
- Data: ONLY FMP API
- Universe: S&P 500 only
- Real data only; log exclusions
- No lookahead: rolling features only pre-event
- Costs are scenario assumptions (explicit), not empirical spreads
- Daily OHLC target-hit rules are used (unless intraday is added legally/available)

Start with Phase 1 smoke test (5 tickers, ~20 events).
