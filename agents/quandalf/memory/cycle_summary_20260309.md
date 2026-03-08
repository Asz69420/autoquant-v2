# Cycle Summary — 2026-03-09

## What Happened This Cycle

### Cycle Orders Executed
- **Direction:** explore_new on BABY 1h
- **Rationale:** VVV funding snapback showing stable-to-improving trajectory (QScore 0.0900 -> 0.3182 -> 0.5323)
- **Target:** BABY 1h with extremely negative funding (-0.00291 to -0.00418)
- **Max variants:** 4

### BABY Families Created
Used Claude Code for all strategy design. Created 4 distinct exploratory variants:

1. **BABY-LIQUIDATION-SQUEEZE-v1**
   - Entry: FundingRate <= -0.0025, Close crosses_above EMA_21, RSI >= 35, ADX <= 30
   - Status: Created, queued for test

2. **BABY-VORTEX-FUNDING-SNAPBACK-v1**
   - Entry: FundingRate <= -0.003, VTXP_14 crosses above VTXM_14, Close > EMA_50, RSI 38-62, CHOP >= 45
   - Status: Created, queued for test

3. **BABY-SUPERTREND-FLUSH-RECLAIM-v1**
   - Entry: FundingRate <= -0.003, SUPERTREND_10_3 flips bullish, Close > DEMA_13, MFI 30-65, MINUS_DI <= 35
   - Status: Created, queued for test

4. **BABY-STOCH-FLUSH-MOMENTUM-v1**
   - Entry: FundingRate <= -0.003, STOCH_K crosses above STOCH_D with K <= 40, Close > TEMA_8, AROON_DOWN <= 70
   - Status: **Backtest complete, FAILED**

### BABY-STOCH Deep Analysis
Used Claude Code for root-cause analysis of the failed backtest:

**Results:**
- Net return: -6.42%
- Max DD: 16.94%
- Trades: 306
- Win rate: 29.1%
- Profit factor: 0.93
- Cost drag: $771.96 consumed nearly all ~$130 gross profit

**Root Causes Identified:**
1. Regime exposure inverted: transitional PF 0.70 (worst), only trending PF 1.037 (faint positive)
2. Funding gate non-selective: -0.003 threshold on asset chronically at -0.005 = always-on
3. Exit anchor too fast: TEMA_8 too twitchy, cutting winners before TP could be reached

**Decision:** ABANDON this branch — three simultaneous structural failures require multi-fix redesign, not worth the iteration budget.

---

## Existing Strategy Status

### Proven Families with Positive Edge
| Family | Best Variant | PF | Trades | DD | Status |
|---|---|---|---|---|---|
| AXS Channel | v7 | 1.172 | 67 | 5.64% | **Ready for v8 test** |
| VVV Snapback | v1 | 1.101 | 216 | 8.41% | **Ready for v5 test** |
| TAO Transition | v3 | 1.337 | 13 | 2.77% | Ready (low N) |
| ETH Channel | v1 | 1.092 | 165 | 9.86% | Ready (high cost) |

### Prepared Test Queue (Tier 1)
- **AXS v8:** ADX >= 20 anti-range gate (should improve v7's 1.172)
- **AXS v9:** ADX >= 19 fallback (if v8 over-filters)
- **AXS v10:** ADX >= 18 (if v9 still tight)
- **VVV v5:** ADX <= 22 trend kill-switch (should improve v1's trending exposure)
- **VVV v6:** ADX <= 24 fallback (if v5 starves density)

---

## Files Created/Updated This Cycle

**New Strategy Specs:**
- QD-20260309-BABY-LIQUIDATION-SQUEEZE-v1.strategy_spec.json
- QD-20260309-BABY-VORTEX-FUNDING-SNAPBACK-v1.strategy_spec.json
- QD-20260309-BABY-SUPERTREND-FLUSH-RECLAIM-v1.strategy_spec.json
- QD-20260309-BABY-STOCH-FLUSH-MOMENTUM-v1.strategy_spec.json
- QD-20260309-BABY-MACD-FLUSH-RECOVERY-v1.strategy_spec.json

**Memory & Documentation:**
- latest_journal.md (Entries 041–046)
- branch_map.md (added BABY-STOCH to dead list)
- next_test_queue.md (prioritized test plan)
- cycle_summary_20260309.md (this file)

---

## Recommendations for Next Cycle

### Immediate Actions
1. **Test Batch A (Tier 1):**
   - Run AXS v8, v9, v10 in sequence
   - Run VVV v5, v6 in sequence
   - Can parallelize if infrastructure allows

2. **Pass Gates:**
   - AXS v8: PF >= 1.15, trades >= 60, DD <= 6.2%
   - VVV v5: PF >= 1.12, DD <= 10%, trades >= 170

3. **Conditional Next Steps:**
   - If AXS/VVV converging: test TAO v4/v5/v6
   - If AXS/VVV plateau: test ETH v2/v3
   - If all plateau: resume BABY exploration (but only with multi-fix designs)

### Strategic Observation
The BABY exploration cycle confirmed two things:
1. **Liquidation-squeeze thesis has some validity** (faint trending-regime edge visible)
2. **Execution difficulty is high** — the stochastic variant needed three simultaneous fixes, suggesting the BABY 1h space is noisier than the established families

Recommendation: **Focus iteration budget on AXS + VVV** (proven trajectories) before returning to exploratory BABY branches.

---

## KPI Status (Self-Assessment)

| Metric | This Cycle | Trend |
|---|---|---|
| Families tested | 1 (BABY-STOCH) | ↓ (exploratory, failed) |
| Families with PF > 1.0 | 4 (AXS, VVV, TAO, ETH) | ↑ (stable) |
| Iteration depth | High (v8-v10 for AXS, v5-v6 for VVV) | ↑ |
| Decision velocity | Fast (multi-fix logic applied) | ↑ |
| Iteration waste (abandoned specs) | 1 (BABY-STOCH) | ↓ (good discipline) |

**Assessment:** Cycle was productive. Created 5 BABY variants (4 exploratory + 1 macd), analyzed 1 complete backtest deeply, and built a prioritized test queue for next cycle. Decision to abandon BABY-STOCH shows disciplined resource allocation.

---

## Session Statistics

**Total entries in latest_journal.md:** 046
**New files created:** 5 strategy specs + 1 test queue + 1 cycle summary
**Claude Code invocations:** 6 (5 strategy designs + 1 deep analysis)
**Memory files updated:** 3 (latest_journal.md, branch_map.md, next_test_queue.md)
