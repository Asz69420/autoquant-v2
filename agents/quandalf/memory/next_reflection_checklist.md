# Next Reflection Checklist — Prepared Branch Decisions

Updated: 2026-03-08 23:26 AEST

Use this file when the next `reflection_packet.json` lands.
Evaluate unique `(strategy_spec_id, variant_id, asset, timeframe)` rows only.

---

## Ranking Order

For each candidate, score in this order:
1. Profit factor (PF)
2. Trade count
3. Max drawdown
4. Regime PF consistency
5. Fee + slippage burden

### Hard labels
- `< 15 trades` -> **EXPLORATORY ONLY**
- `PF = 999` with `1 trade` -> **IGNORE FOR PROMOTION**
- `0 trades` -> **STRUCTURAL FAILURE / NO SIGNAL**

---

## AXS Branch

### Active queue
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v8.strategy_spec.json` -> ADX >= 20
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v9.strategy_spec.json` -> ADX >= 19
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v10.strategy_spec.json` -> ADX >= 18

### Decision gates
- **Promising:** PF >= 1.15, trades >= 60, DD <= 6.2%
- **Strong:** PF >= 1.20, trades >= 65, DD <= 5.9%

### Decision logic
- If stricter version keeps PF strongest and trades stay viable -> keep stricter gate
- If PF holds but trades collapse -> move one step looser on ADX
- If looser version raises trades but PF drops below 1.10 -> revert one step tighter

---

## ETH Branch

### Active queue
- `QD-20260308-ETH-CHANNEL-SHORTBIAS-v2.strategy_spec.json` -> ADX >= 20
- `QD-20260308-ETH-CHANNEL-SHORTBIAS-v3.strategy_spec.json` -> ADX >= 19

### Decision gates
- PF >= 1.10
- DD < 9.5%
- trades >= 130

### Decision logic
- If v2 passes all three -> keep v2 as baseline
- If v2 preserves PF but trades < 130 -> move to v3
- If v3 still under-delivers -> stop ADX relaxation and test TP/stop refinement next

---

## VVV Branch

### Active queue
- `QD-20260308-VVV-FUNDING-SNAPBACK-v5.strategy_spec.json` -> ADX <= 22
- `QD-20260308-VVV-FUNDING-SNAPBACK-v6.strategy_spec.json` -> ADX <= 24

### Decision gates
- PF >= 1.12
- DD <= 10%
- trades > 170

### Decision logic
- If v5 improves PF and controls DD -> keep v5
- If v5 quality improves but count falls too much -> move to v6
- If v6 restores count but DD blows out -> revert to v1 baseline and explore stop refinement instead

---

## TAO Branch

### Active queue
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v6.strategy_spec.json` -> TP 3.0

### Comparison set
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v3.strategy_spec.json`
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v4.strategy_spec.json`
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v5.strategy_spec.json`
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v6.strategy_spec.json`

### Decision gates
- PF >= 1.10
- DD <= 4.5%
- trades >= 14

### Decision logic
- If v6 lifts return/trade without DD drift -> keep exit-shape refinement line
- If v6 weakens PF materially -> revert to best prior TAO version (likely v3/v4)
- Do not widen ADX further until exit-shape evidence is exhausted

---

## Automatic Abandon Rules

Abandon or freeze immediately if:
- 2 consecutive variants show `0 trades`
- 3 consecutive variants stay `< 15 trades` without clear PF improvement
- PF < 1.0 across all regimes with adequate trade count
- cost burden dominates edge and no regime pocket remains

---

## Reflection Packet Hygiene

Before deciding anything:
- dedupe repeated packet rows
- ignore mirrored duplicates with identical metrics
- compare only latest unique variant instance

This should reduce wasted cycles and stop PF mirages from hijacking iteration decisions.
