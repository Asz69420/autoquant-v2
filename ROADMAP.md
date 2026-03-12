# AutoQuant Roadmap

## Prime Objective
Build a long-term autonomous quant research and execution system that compounds market intelligence, preserves lessons, avoids drift, and gets more reliable over time.

## Current Strategic Direction
- Keep a **small core cast** of durable agents
- Be **tool/skill heavy**, not agent-sprawl heavy
- Keep **hard facts in SQLite**
- Build **shared intelligence memory** above the DB
- Keep **agent-private working memory** role-shaped and bounded
- Add a **governance spine** for roadmap, tasks, completions, promotion, and compaction

## Phase Ladder
1. Governance spine
2. Shared intelligence memory
3. Pipeline and agent integration
4. Journal/lesson backfill
5. External market intelligence ingestion
6. Execution/risk layer maturation

## Canonical Rules
- Deterministic facts belong in DB/state JSON
- Canonical rules outrank journals
- Shared intelligence outranks private notes
- Raw artifacts are evidence, not default context
- Every significant change should leave a completion record

## Live Status
<!-- TASK_SUMMARY_START -->
_Last synced: 2026-03-12T08:23:25.633604+00:00_

- Queued: **2**
- Active: **2**
- Blocked: **0**
- Done: **20**

### Active
- `TASK-0017` **Add agent feedback loop and Oragorn synthesis** — owner: oragorn
- `TASK-0023` **Clean misleading zero-trade history, inspect gateway errors, and audit Quandalf strategy loop** — owner: oragorn

### Blocked
- None

### Next Up
- `TASK-0016` **Implement concrete HyperLiquid and macro feed fetchers when endpoint/provider decisions are finalized** — owner: oragorn
- `TASK-0024` **Trace and neutralize duplicate watchdog launcher instances if gateway-noise still persists after the patched watchdog is the active instance** — owner: oragorn

### Recently Done
- `TASK-0001` **Bootstrap memory governance spine**
- `TASK-0002` **Bootstrap shared intelligence memory buckets**
- `TASK-0003` **Backfill Quandalf lessons into shared intelligence**
- `TASK-0004` **Integrate completion records into recurring pipelines**
- `TASK-0018` **Fix delegation reliability and align souls with actual execution model**
<!-- TASK_SUMMARY_END -->

## Notes
- `data/state/task_board.json` is the operational source of truth for task state.
- `artifacts/completions/` is the proof trail for completed work.
- Future live-feed work is already scaffolded; HyperLiquid integration should plug into the external-intel registry/scoring path documented in `docs/HYPERLIQUID_INTEGRATION_TODO.md`.
- This file is strategic and should stay concise.
