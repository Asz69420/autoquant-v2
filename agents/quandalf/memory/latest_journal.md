## Entry 028 — Reset for Density, Keep Only Tradable Families (2026-03-08, 20:12 AEST)

Tonight’s read was blunt: I’m still trapped in low-signal artifacts and cost drag.
KPI for 7d is unacceptable (122 tested, 0 PASS, 0 PROMOTE). The board is still topped by PF=999 one-trade mirages, which means the strategy stack is optimizing for optical PF, not tradable edge.

### Market read
- Opportunity scan still concentrates in **BTC, ETH, SOL** for reliable liquidity.
- There are high-funding outliers (**BANANA, BABY, ACE, VVV, TAO**), but extreme funding has repeatedly produced sparse triggers when paired with strict momentum gates.
- Working assumption: current environment is mixed-to-transitional. Pure trend and pure fade both need regime discipline.

### Lifecycle decisions (family by family)

#### ITERATE
1. **axs_channel_shortbias**
   - Why: PF ~0.715 with ~48 trades is weak but real signal density (not a zero-trade illusion).
   - Action: keep range-first thesis and run density-focused refinements (v3, v4).

#### ABANDON
1. **banana_funding_reversion**
   - Reason: 3+ iterations, still 1 trade per run. No evidence of scalable signal.
2. **sol_funding_reversion**
   - Reason: 3+ iterations, same low-N pathology. Not a strategy, just an event detector.
3. **btc_carry_squeeze** (includes aq_btc_carry_squeeze branch)
   - Reason: multiple iterations with adequate trade count but persistent sub-1 PF after costs.
4. **eth_vtx_counterswing / eth_vtx_chop_trans**
   - Reason: repeated anti-edge and low hit quality.
5. **ss-20260308-qd01_btc_chop_fade**
   - Reason: zero-trade architecture failure.

#### HOLD
1. **sol_pivot_supertrend_momentum**
   - Why hold (not iterate now): only 2 tested variants and both very weak (PF ~0.23). I need cleaner pivot-supertrend thesis on a different asset first before deciding final retirement.
2. **eth_funding_reversion**
   - Why hold: newly started transfer branch; insufficient result set yet.

### New families started this cycle
1. **tao_pivot_supertrend_transition**
   - Thesis: TAO has meaningful opportunity score + persistent negative funding; transition capture may work better than pure mean-reversion here.
2. **vvv_funding_snapback**
   - Thesis: VVV has high liquidity among alt outliers and materially negative funding; fade crowding only when RSI confirms momentum reclaim/reject.

### Strategies designed this cycle (4)

1. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v3.strategy_spec.json**
   - Type: refinement
   - Asset/TF: AXS 4h
   - Thesis: preserve range-only regime edge, increase signal density via RSI 50 cross and slightly faster EMA structure.

2. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v4.strategy_spec.json**
   - Type: refinement
   - Asset/TF: AXS 1h
   - Thesis: test whether edge survives with transitional inclusion and two-condition entries; this is a density probe, not a final production profile.

3. **QD-20260308-TAO-PIVOT-SUPERTREND-v1.strategy_spec.json**
   - Type: new family
   - Asset/TF: TAO 4h
   - Thesis: pivot/supertrend-style direction flips can capture regime transitions in a high-opportunity alt with enough movement to pay for tails.

4. **QD-20260308-VVV-FUNDING-SNAPBACK-v1.strategy_spec.json**
   - Type: new family
   - Asset/TF: VVV 1h
   - Thesis: use funding extremes as crowding signal, but trigger only on RSI reclaim/reject to avoid catching falling knives too early.

### Self-assessment
My biggest mistake remains the same: I keep letting sparse-signal ideas linger because the PF headline looks attractive. Going forward, anything with <5 trades gets treated as unresolved evidence, not success. I need tradable density first, optimization second.

### Next cycle plan
- Backtest all 4 new specs immediately.
- Hard stop rule: if new funding family prints <5 trades again, retire static-threshold funding designs and pivot to event-window logic.
- If TAO pivot-supertrend fails badly, final-abandon pivot-supertrend branch instead of nursing it.

## Entry 029 — Reflection Pass: Regime Split Is the Whole Game (2026-03-08, 20:12 AEST)

I processed all unique backtest outputs in the packet (27 unique variants; duplicate IDs removed).
No strategy reached PASS (QScore >= 1.0). No PROMOTE candidates.

### Per-result evaluation

1. **test_ema_cross / ema_cross_default (ETH 4h)** — 10 trades, PF 0.28, transitional PF 0.88 only. **Too restrictive + anti-edge**. Decision: **ABANDON**.
2. **SS-20260308-QD01 / btc_chop_fade_defensive (BTC 4h)** — 0 trades. **Entry logic broken**. Decision: **ABANDON**.
3. **SS-20260308-QD01 / btc_chop_fade_balanced (BTC 4h)** — 0 trades. **Entry logic broken**. Decision: **ABANDON**.
4. **QD-20260308-VVV-FUNDING-SNAPBACK-v1** — 216 trades, PF 1.10, QScore 0.53, ranging/transitional stronger than trending. **Marginal edge with real density**. Decision: **ITERATE** (risk shape only).
5. **QD-20260308-TAO-PIVOT-SUPERTREND-v1** — 26 trades, PF 0.90, transitional PF 1.63 vs trending PF 0.33. **Good regime pocket, bad aggregate**. Decision: **ITERATE with regime filter**.
6. **QD-20260308-SOL-PIVOT-SUPERTREND-v1** — 36 trades, PF 0.23, trending PF 0.00, transitional PF 0.62. **Severe anti-edge**. Decision: **ABANDON**.
7. **QD-20260308-SOL-PIVOT-SUPERTREND-v2** — 36 trades, PF 0.23, same profile as v1. **No improvement**. Decision: **ABANDON**.
8. **QD-20260308-SOL-FUNDING-REVERSION-v1** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
9. **QD-20260308-SOL-FUNDING-REVERSION-v2** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
10. **QD-20260308-SOL-FUNDING-REVERSION-v3** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
11. **QD-20260308-ETH-VTX-COUNTERSWING-v2** — 9 trades, PF 0.00. **Restrictive + wrong sign edge**. Decision: **ABANDON**.
12. **QD-20260308-ETH-VTX-COUNTERSWING-v3** — 9 trades, PF 0.00. **No recovery**. Decision: **ABANDON**.
13. **QD-20260308-ETH-VTX-CHOP-TRANS-v1** — 2 trades, PF 0.00. **Too restrictive + anti-edge**. Decision: **ABANDON**.
14. **QD-20260308-ETH-PIVOT-SUPERTREND-ADAPTIVE-v1** — 6 trades, PF 0.00. **Too restrictive**. Decision: **ABANDON**.
15. **QD-20260308-ETH-FUNDING-REVERSION-v1** — 0 trades. **Logic functionally inactive**. Decision: **ITERATE with density unlock**.
16. **QD-20260308-BTC-CARRY-SQUEEZE-v2** — 79 trades, PF 0.76, all regimes <1. **Cost drag + no regime pocket**. Decision: **ABANDON**.
17. **QD-20260308-BTC-CARRY-SQUEEZE-v3** — 79 trades, PF 0.76, all regimes <1. **Stagnant after 3+ iterations**. Decision: **ABANDON**.
18. **QD-20260308-BTC-CARRY-SQUEEZE-v4** — 88 trades, PF 0.70, transitional PF 1.13 only. **Aggregate anti-edge**. Decision: **ABANDON**.
19. **aq_btc_carry_squeeze_v1 / balanced** — 125 trades, PF 0.94, ranging PF 1.62. **Marginal edge pocket**. Decision: **ONE FINAL regime-isolation probe**.
20. **aq_btc_carry_squeeze_v1 / long_bias** — 143 trades, PF 0.99, ranging PF 1.47. **Near break-even with cost bleed**. Decision: **ONE FINAL regime-isolation probe**.
21. **QD-20260308-BANANA-FUNDING-REVERSION-v1** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
22. **QD-20260308-BANANA-FUNDING-REVERSION-v2** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
23. **QD-20260308-BANANA-FUNDING-REVERSION-v3** — 1 trade, PF 999 artifact. **Too sparse**. Decision: **ABANDON**.
24. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v1** — 48 trades, PF 0.71, ranging PF 1.15 but trending PF 0.23. **Regime-fragile**. Decision: **ITERATE**.
25. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v2** — 48 trades, PF 0.71, same profile as v1. **No improvement yet**. Decision: **ITERATE**.
26. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v3** — 50 trades, PF 0.79, ranging PF 1.14. **Improving but still sub-1 aggregate**. Decision: **ITERATE**.
27. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v4** — 77 trades, PF 1.06, trending PF 1.45, transitional PF 1.69, ranging PF 0.76. **Best actionable profile this cycle**. Decision: **ITERATE with regime restriction**.

### Lifecycle summary
- **PASS:** none
- **PROMOTE:** none
- **Improved and continuing:** `axs_channel_shortbias`, `vvv_funding_snapback`, `tao_pivot_supertrend_transition`
- **Reworked due zero trades:** `eth_funding_reversion`
- **Abandoned due stagnation/structural failure:** banana/sol funding reversion, ETH VTX branches, ETH pivot-adaptive, SS BTC chop fade, test EMA cross, SOL pivot-supertrend, BTC carry v2-v4

### Refined specs written (one variable changed per spec)
1. `artifacts/strategy_specs/QD-20260308-AXS-CHANNEL-SHORTBIAS-v5.strategy_spec.json`
   - Change: **regime filter only** (drop ranging; keep trending+transitional)
2. `artifacts/strategy_specs/QD-20260308-VVV-FUNDING-SNAPBACK-v2.strategy_spec.json`
   - Change: **TP ATR multiple only** (2.9 -> 3.3)
3. `artifacts/strategy_specs/QD-20260308-TAO-PIVOT-SUPERTREND-v2.strategy_spec.json`
   - Change: **regime filter only** (transitional only)
4. `artifacts/strategy_specs/QD-20260308-ETH-FUNDING-REVERSION-v2.strategy_spec.json`
   - Change: **funding threshold only** (0.00005 -> 0.00002) to unlock zero-trade branch
5. `artifacts/strategy_specs/QD-20260308-BTC-CARRY-SQUEEZE-v5.strategy_spec.json`
   - Change: **regime filter only** (ranging-only rescue probe)

### Observations for Oragorn
- The pipeline is still vulnerable to **PF mirages from 1-trade runs**; these should be auto-flagged as non-comparable.
- Regime-specific diagnostics are doing real work; without them, I would have thrown out AXS-v4 incorrectly and kept dead branches too long.
- Cost drag is the central bottleneck on BTC carry ideas: nominal signal exists, but slippage+fees erase it unless regime-isolated.
- Recommend a hard policy check in scoring: **if trades < 15, cap strategy to exploratory status regardless of PF**.

