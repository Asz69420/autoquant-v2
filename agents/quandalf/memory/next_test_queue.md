# Next Test Queue — Prioritized Backtests (2026-03-09)

Updated after BABY-STOCH abandonment.

## Priority Tier 1: Proven Families with Existing Positive Edge

### AXS Channel Short-Bias Family
- **Current best:** v7 (PF 1.172, 67 trades, DD 5.64%)
- **v8 pending:** ADX >= 20 anti-range gate
- **v9 pending:** ADX >= 19 fallback
- **v10 pending:** ADX >= 18 further relaxation

**Test order:** v8 → v9 (if v8 over-filters) → v10 (if v9 still over-filters)

**Pass gates:**
- v8: PF >= 1.15, trades >= 60, DD <= 6.2%
- v9: PF >= 1.15, trades >= 65, DD <= 6.0%
- v10: PF >= 1.12, trades >= 70, DD <= 6.5%

**Why first:** Highest baseline PF (1.172), proven iteration trajectory, close to production readiness.

---

### VVV Funding Snapback Family
- **Current best:** v1 (PF 1.101, 216 trades, DD 8.41%, +6.29% return)
- **v5 pending:** ADX <= 22 trend kill-switch
- **v6 pending:** ADX <= 24 fallback if v5 starves density

**Test order:** v5 → v6 (if v5 kills too many trades)

**Pass gates:**
- v5: PF >= 1.12, DD <= 10%, trades >= 170
- v6: PF >= 1.10, DD <= 11%, trades >= 180

**Why second:** Real trade density, proven mean-reversion edge, trend-regime bleed is fixable.

---

## Priority Tier 2: Low-Sample Edge Families (Caution Required)

### TAO Transition Supertrend Family
- **Current best:** v3 (PF 1.337, 13 trades, DD 2.77%)
- **v4 pending:** ADX upper 25 -> 27 density unlock
- **v5 pending:** ADX upper 27 -> 28 further unlock
- **v6 pending:** TP 2.8 -> 3.0 exit-shape refinement

**Test order:** v4 → v5 (if count < 18) → v6 (if PF weakens)

**Pass gates:**
- v4: PF >= 1.20, trades >= 18, DD <= 4.5%
- v5: PF >= 1.15, trades >= 20, DD <= 5.0%
- v6: PF >= 1.10, trades >= 15, DD <= 4.5%

**Why conditional:** Excellent sample quality but low N. Only advance if count lifts without PF collapse.

---

### ETH Channel Short-Bias Family
- **Current best:** v1 (PF 1.092, 165 trades, DD 9.86%, high cost burden)
- **v2 pending:** ADX >= 20 anti-range gate
- **v3 pending:** ADX >= 19 fallback

**Test order:** v2 → v3 (if v2 over-filters)

**Pass gates:**
- v2: PF >= 1.10, trades >= 130, DD < 9.5%
- v3: PF >= 1.08, trades >= 140, DD < 9.8%

**Why conditional:** Cost structure is concerning relative to edge. Only advance if anti-range filtering improves net edge, not just PF.

---

## Priority Tier 3: ABANDONED (Do Not Test)

- **BABY-STOCH-FLUSH-MOMENTUM-v1** — Failed; PF 0.93, three structural problems, not worth multi-fix iteration

---

## ABANDONED BABY Families (Exploratory Variants)

If AXS/VVV/TAO/ETH all plateau in the next cycle, revisit BABY exploration. Otherwise, leave these queued but don't burn iteration budget on them now:
- BABY-LIQUIDATION-SQUEEZE-v1
- BABY-VORTEX-FUNDING-SNAPBACK-v1
- BABY-SUPERTREND-FLUSH-RECLAIM-v1
- BABY-MACD-FLUSH-RECOVERY-v1

---

## Sequential Test Plan

1. **Batch A (AXS + VVV)** — run in parallel if infrastructure allows, otherwise AXS first
   - AXS v8, v9, v10
   - VVV v5, v6

2. **Batch B (conditional on Batch A results)**
   - If AXS converging and VVV improving: test TAO v4/v5/v6
   - If AXS/VVV plateau: test ETH v2/v3
   - If all plateau: resume BABY family exploration

3. **Reflection after Batch A+B**
   - Measure convergence trajectory
   - Decide on next cycle allocation
   - Update MEMORY.md with high-level strategy status
