# Shared Memory Automation

## Purpose
Keep shared intelligence memory self-feeding across Quandalf, Frodex, and Logron.

## Recurring Promotion Paths
### Quandalf
- `scripts/backfill_quandalf_lessons.py`
- promotes reusable strategy lessons from curated cycle summaries and journals

### Frodex + Logron
- `scripts/backfill_agent_memory.py --agent all`
- promotes agent decisions into shared decision memory
- promotes Logron self-healing policy into known-fixes memory

## Automation Hook
These scripts are now part of `pipelines/daily-maintenance.lobster`.
That means shared memory promotion runs automatically during recurring maintenance.

## Why This Matters
- the system does not rely on manual curation forever
- useful old memory gets surfaced over time
- new memory is promoted into the correct shared layer
- shared intelligence compounds across agents instead of staying siloed

## Guardrails
- bulk factual data stays in SQLite/state, not shared memory prose
- canonical rules are never overwritten by promoted memory
- compaction runs separately to keep shared memory lean
- evidence remains traceable via completion records and source files
