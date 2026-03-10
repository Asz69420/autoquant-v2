# Memory Governance Audit

## Purpose
Validate that the memory-governance system stays healthy under recurring automation.

## Checks
- shared memory index exists and is non-empty
- active/blocked tasks are visible
- stale active tasks are detected
- compaction state exists and is fresh
- enabled external-intel sources are visible
- external-intel ingest history is checked when sources are enabled

## Recurring Hook
`pipelines/daily-maintenance.lobster` now runs `scripts/audit_memory_governance.py`.

## Output
The audit writes:
- `data/state/memory_governance_audit.json`

Status values:
- `ok` = no warnings
- `warn` = one or more governance health warnings

## Goal
Catch drift, stale maintenance, and governance decay before memory quality silently degrades.
