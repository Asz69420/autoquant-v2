# Council Debate — Memory Model for AutoQuant / Quandalf

## Topic
Which memory model should AutoQuant prefer for Quandalf research: the current 3-layer memory architecture, or a simpler local autoresearch-style memory model?

## Round 1 — Positions

### Frodex
- Keep the 3-layer architecture as system memory.
- Simplify Quandalf's active research loop so it behaves more like a local autoresearch model.
- Main claim: current pain is retrieval/selection failure, not lack of storage.
- Recommended shape:
  - active local working memory
  - distilled lesson memory
  - archive/audit memory

### Logron
- Prefer the current 3-layer memory architecture.
- Main claim: AutoQuant is cumulative and multi-agent, so memory types must stay separated.
- Strongest reason: research notes, experiment records, and promoted lessons should not have equal authority.
- Recommended hybrid:
  - keep 3-layer as system of record
  - add a lightweight local scratchpad in front of it

## Round 2 — Critiques

### Shared agreement
- Do not replace the 3-layer model with a flat local notebook.
- The active research loop should feel simpler and faster than it does now.
- Archive should not be the default retrieval surface.
- Promotion rules must stay strict so the system does not bloat or drift.

### Main tension
- Frodex leans harder toward simplifying default retrieval.
- Logron leans harder toward preserving strict separation and auditability.

## Round 3 — Synthesis (Oragorn)
The council outcome is:

**Keep the 3-layer memory model, but make Quandalf operate through a much simpler front-end research memory.**

That means:
1. **Do not replace system memory.**
   - keep layered memory for governance, durability, and cross-cycle learning
2. **Add a local research scratchpad / active experiment buffer** for Quandalf
   - fast, messy, cycle-local
   - hypothesis notes, comparisons, candidate mechanisms
3. **Promote only proven findings upward**
   - experiment cards -> distilled lessons -> promoted priors
4. **Make archive write-heavy, read-light**
   - default retrieval should hit active + distilled, not raw archive
5. **Add decay / review rules**
   - lessons must expire or be revalidated by regime age/evidence

## Final Outcome
Our memory model is better **if kept disciplined**.
The autoresearch-style model is better only as a **front-end working style**, not as the system of record.

Best move:
- keep 3-layer memory
- add a thin local scratchpad / experiment-object layer for Quandalf
- tighten promotion, retrieval, and decay so memory stays useful instead of bloating
