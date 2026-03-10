# Automation Maintenance Loop

## Purpose
Turn memory and evidence governance into recurring unattended maintenance.

## Daily Maintenance Pipeline
`pipelines/daily-maintenance.lobster` now runs:
1. health check
2. shared-memory compaction
3. queue housekeeping
4. old strategy spec archiving
5. git sync

## Why This Matters
- shared memory dedupes itself
- stale evidence gets trimmed safely
- queue state stays honest
- old non-promoted specs get archived
- the workspace keeps converging instead of bloating

## Retrieval Enforcement
Quandalf briefing now prefers:
- shared memory summaries
- DB/state facts when exactness matters
- asset-relevant external intel before generic media

And avoids:
- whole historical journals by default
- raw transcripts by default
- unrelated agent-private memory

## Outcome
The system is closer to self-managing:
- compaction becomes recurring
- retention becomes recurring
- retrieval is more bounded and relevant
- memory stays useful as it scales
