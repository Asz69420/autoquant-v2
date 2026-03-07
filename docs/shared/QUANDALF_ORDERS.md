# QUANDALF ORDERS

## ORDER QO-2026-03-04-KICKSTART-01 (ACTIVE)
**Issued:** 2026-03-04 18:31 AEST  
**Owner:** Frodex execution loop  
**Window:** Next 2 cycles only (`N` and `N+1`), then auto-revert

### Objective
Execute a controlled 2-cycle kickstart to increase near-term adaptability while keeping risk bounded.

### Action 1 — Temporarily soften directive filters (2 cycles)
Apply temporary filter softening for cycles `N` and `N+1` only:

- Reduce directive acceptance threshold by **15%** from current configured value.
- Absolute lower bound: threshold may not go below **0.55**.
- Maximum softened approvals: **2 per cycle**.
- Never soften safety/compliance/risk hard-block directives.
- If any cycle starts with risk state `>= MEDIUM`, skip softening for that cycle.

### Action 2 — Force a freshness slice each cycle
Reserve mandatory freshness evaluation each cycle:

- Reserve **20%** of candidate evaluation budget for fresh candidates.
- Fresh candidate definition: signal/event age `<= 1 cycle`.
- Evaluate at least **1 fresh candidate per cycle**.
- Execute only if baseline risk checks pass; otherwise log `FRESHNESS_NO_SAFE_EXECUTION`.
- Freshness slice cannot bypass hard risk limits.

### Action 3 — Low-risk exploration micro-batch each cycle
Run controlled exploration in each cycle:

- Attempt micro-batch size: **3 exploratory candidates per cycle**.
- Position size per exploratory execution: **0.10x normal size**.
- Exploration risk cap: **<= 0.25R per cycle**, **<= 0.40R total across N..N+1**.
- Mandatory protections per exploratory execution: hard stop + time stop (max hold = 1 cycle).
- Exclude candidates failing normal liquidity/spread safeguards.

### Risk Controls (non-optional)
- Hard risk limits remain unchanged and take precedence over this order.
- No leverage increase authorized.
- If any hard-risk breach occurs, immediately disable all three actions and mark order `HALTED`.

### Success Checks
For each cycle (`N`, `N+1`), produce explicit check results:

1. `softening_applied` (true/false) and `softened_approvals <= 2`
2. `freshness_slice_reserved = 20%` and `fresh_candidates_evaluated >= 1`
3. `exploration_attempted = 3` (or documented shortfall) and risk caps respected
4. `hard_risk_breaches = 0`

### Completion / Revert
- After cycle `N+1`, automatically restore all temporary parameters to baseline.
- Emit final status: `COMPLETED` if all risk controls held, else `COMPLETED_WITH_EXCEPTIONS` with breach details.
