# Memory Governance V2

## Purpose
Memory V2 gives AutoQuant a durable, low-drift, self-managing knowledge system.

It is designed to:
- keep always-loaded context small
- preserve reusable intelligence
- avoid personality drift across agents
- separate facts from prose
- keep long builds moving with a persistent task spine

## Architecture

### 1. Canonical layer
Files and config that define identity, role, rules, and non-negotiable contracts.

Examples:
- `SOUL.md`
- `AGENTS.md`
- `USER.md`
- `MEMORY.md`
- `config/*.json`

### 2. Shared intelligence layer
Curated, promoted memory that any relevant agent may consume.

Buckets:
- lessons
- decisions
- known fixes
- regimes
- strategy families
- postmortems
- handoffs

### 3. Agent-private layer
Role-specific working memory for drafts, local reflections, and narrow heuristics.

### 4. Deterministic layer
SQLite, state JSON, and schema-backed artifacts.

### 5. Cold archive
Raw evidence retained for retrieval and audit, not default loading.

## Governance Rules
- Canonical rules beat all other memory.
- Shared intelligence beats private notes.
- DB/state facts beat prose when they conflict.
- Raw artifacts never become live context without a summary or query reason.
- Completion records are required for meaningful progress tracking.

## Task Spine
The persistent execution spine is:
- `ROADMAP.md` for strategic direction
- `data/state/task_board.json` for operational truth
- `artifacts/completions/` for proof

## Automation
- `scripts/task_governor.py` manages task state and roadmap sync.
- `scripts/memory_governor.py` manages shared memory bootstrap and promotion.
- Logron should audit stale tasks, blocked tasks, and missing completion records.

## Migration Strategy
- Build beside the current system first
- Keep the DB unchanged
- Backfill old journals and artifacts into shared intelligence gradually
- Cut over retrieval rules only after validation
- Archive old structures only after safe adoption
