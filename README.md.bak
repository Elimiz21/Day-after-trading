# Day-after Trading (Earnings Reversal Research)

This repo is for researching and testing a post-earnings, day-after reversal strategy.

## Governance (Option B)
We use:
- **Claude Code** to build/run the project in this repo
- **GitHub Actions** to run QA + build a QA bundle
- **OpenAI API (Responses API)** to review the QA bundle and post a **GO/NO-GO** PR comment automatically

### Secrets required (GitHub → Settings → Secrets and variables → Actions)
- `FMP_API_KEY`
- `OPENAI_API_KEY`

Optional variable:
- `OPENAI_MODEL` (default: `gpt-5.2`)

## What exists now
This is scaffolding only:
- CI workflow that runs a basic QA gate
- QA bundle builder
- OpenAI PR reviewer script (Responses API)
- A master prompt for Claude Code in `docs/claude_master_prompt.md`

The full pipeline/backtester/dashboard will be implemented next by Claude Code.
