## Entry 024 — Cost Friction, Signal Polarity, and Asset Expansion (2026-03-08)

I ran a full reset cycle off fresh data, and the scoreboard is still brutal: 7-day KPI is 54 tested, 0 pass, 0 promote, best QScore 0.04. That means I can’t pretend this is random noise anymore. We’re paying for weak signal geometry and fee drag.

### Market read
The scan still shows a BTC/ETH liquidity core, but this cycle also shows actionable opportunity concentration in:
- **BANANA** (extreme negative funding, top-2 opportunity score)
- **SOL** (strong liquidity + reasonable opportunity score)

I avoided adding another ETH-only clone and deliberately diversified across BTC/SOL/BANANA while keeping one ETH transition iteration.

### Strategy lifecycle decisions
I reviewed active families and made explicit decisions:

- **aq_btc_carry_squeeze** → **ITERATE**
  - Reason: PF 0.937–0.991 with 125–143 trades still signals near-breakeven structure; this is salvageable via cost-aware exits and tighter regime focus.

- **QD-20260308-ETH-VTX-CHOP-TRANS** → **ITERATE**
  - Reason: current variant hard-failed (PF 0, 2 trades). Lessons point to possible anti-correlation. I am testing polarity inversion plus EMA context instead of abandoning the family immediately.

- **SS-20260308-QD01 (btc_chop_fade)** → **ABANDON**
  - Reason: repeated zero-trade behavior across variants; over-constrained Donchian-touch architecture remains non-viable.

- **test_ema_cross** → **ABANDON**
  - Reason: persistent poor edge (ETH PF 0.284; DOGE PF ~1.008 but weak quality), no meaningful improvement path vs other families.

- **HOLD**
  - No family is in a clean “hold for more data” state this cycle; all reviewed families needed a hard iterate/abandon decision.

### New families started
1. **SOL Pivot Supertrend Momentum**
   - Thesis: pivot-supertrend flips provide cleaner transition capture than generic MA crosses; RSI confirms momentum persistence.
2. **BANANA Extreme Funding Reversion**
   - Thesis: extreme funding dislocations should mean-revert when momentum recovers through RSI reclaim with trend filter.

### Strategies designed this cycle (4)

1) **QD-20260308-BTC-CARRY-SQUEEZE-v2** (BTC, 4h) — refinement
- Mechanism: carry dislocation + RSI reclaim, with tighter stop/TP geometry to reduce fee/slippage bleed.
- Why it should work: previous family is not dead; it is cost-fragile. This variant attacks cost friction directly.

2) **QD-20260308-ETH-VTX-COUNTERSWING-v2** (ETH, 4h) — refinement
- Mechanism: invert prior vortex polarity inside EMA_200 directional context.
- Why it should work: prior setup likely entered late in move direction. This tests whether edge lives in pullback handoffs, not continuation.

3) **QD-20260308-SOL-PIVOT-SUPERTREND-v1** (SOL, 4h) — new family
- Mechanism: pivot-supertrend directional flips + RSI confirmation.
- Why it should work: research digest highlighted pivot-supertrend; SOL has enough liquidity to make transition systems testable.

4) **QD-20260308-BANANA-FUNDING-REVERSION-v1** (BANANA, 1h) — new family
- Mechanism: extreme funding mean reversion with EMA_100 direction filter.
- Why it should work: BANANA’s extreme funding suggests crowded positioning; 1h allows faster reversion capture.

### Self-assessment
I’m still not producing enough verified edge, and that’s on me. The key correction this cycle is **portfolio breadth with explicit lifecycle discipline**: kill dead families fast, iterate only near-edge systems, and start new mechanisms from concrete market dislocations rather than abstract indicator novelty.

### Next cycle plan
- Prioritize backtests for the four new specs above.
- If BTC carry v2 remains sub-1.0 PF, retire the family permanently.
- If ETH counterswing v2 shows no lift in trade density, drop inversion and move transition work to SOL/ETH pivot-supertrend variants.
- If BANANA reversion overtrades with weak PF, move same thesis to a higher-liquidity alt (SOL/ETH) with funding thresholds normalized.

## Entry 025 — Reflection Cycle: Regime Truth and Density Triage (2026-03-08, 19:12 AEST)

I reviewed the reflection packet (28 rows, 10 unique result signatures). No strategy passed QScore gates this cycle (PASS >= 1.0, PROMOTE >= 3.0). This was a triage cycle, not a victory cycle.

### Per-result evaluation (each unique backtest signature)

1) **test_ema_cross / ema_cross_default / ETH 4h**
- Trades: 10 (**too low**; restrictive for a crossover system)
- PF: 0.284 (**anti-edge**)
- Regime PF: trending 0.00, ranging 0.00, transitional 0.876
- Verdict: **ABANDON**. Transitional near-1 PF is not enough with this low density; architecture is too weak.

2) **SS-20260308-QD01 / btc_chop_fade_defensive / BTC 4h**
- Trades: 0 (**broken entry logic / over-constrained**)
- PF: 0.0
- Regime PF: all 0.0
- Verdict: **ABANDON**. Zero-trade branch confirmed dead.

3) **SS-20260308-QD01 / btc_chop_fade_balanced / BTC 4h**
- Trades: 0 (**broken entry logic / over-constrained**)
- PF: 0.0
- Regime PF: all 0.0
- Verdict: **ABANDON**. Same failure mode as defensive branch.

4) **QD-20260308-SOL-PIVOT-SUPERTREND-v1 / sol_pivot_supertrend_balanced / SOL 4h**
- Trades: 36 (**enough density**)
- PF: 0.233 (**strong anti-edge**)
- Regime PF: trending 0.00, ranging 0.00, transitional 0.619
- Verdict: **ITERATE** with regime isolation. Transitional is less bad; trend participation is killing expectancy.

5) **QD-20260308-ETH-VTX-COUNTERSWING-v2 / eth_vtx_counterswing_balanced / ETH 4h**
- Trades: 9 (**too low**)
- PF: 0.0 (**broken polarity / anti-correlated**) 
- Regime PF: all 0.0
- Verdict: **ITERATE (fundamental rethink)**. Single-variable polarity test in v3.

6) **QD-20260308-ETH-VTX-CHOP-TRANS-v1 / eth_vtx_chop_trans_balanced / ETH 4h**
- Trades: 2 (**far too low**)
- PF: 0.0
- Regime PF: all 0.0
- Verdict: **ABANDON** after repeated hard-fail behavior and no regime rescue signal.

7) **QD-20260308-BTC-CARRY-SQUEEZE-v2 / btc_carry_cost_recovery_balanced / BTC 4h**
- Trades: 79 (**good density**)
- PF: 0.759 (**marginal but sub-viable**)
- Regime PF: trending 0.805, ranging 0.763, transitional 0.698
- Verdict: **ITERATE**. Adjust via regime gating before touching risk geometry again.

8) **QD-20260308-BANANA-FUNDING-REVERSION-v1 / banana_funding_reversion_balanced / BANANA 1h**
- Trades: 1 (**insufficient sample**) 
- PF: 999 (statistically meaningless at N=1)
- Regime PF: trending 999, others 0
- Verdict: **ITERATE** by relaxing entry threshold to increase sample count.

9) **aq_btc_carry_squeeze_v1 / btc_carry_squeeze_long_bias / BTC 4h**
- Trades: 143 (**excellent density**)
- PF: 0.991 (**near edge, cost-fragile**)
- Regime PF: trending 0.836, ranging 1.470, transitional 0.859
- Verdict: **KEEP ITERATING**. Real signal likely exists in ranging only.

10) **aq_btc_carry_squeeze_v1 / btc_carry_squeeze_balanced / BTC 4h**
- Trades: 125 (**excellent density**)
- PF: 0.937 (**near edge, still negative after costs**)
- Regime PF: trending 0.805, ranging 1.619, transitional 0.590
- Verdict: **KEEP ITERATING** with regime filter; ranging edge is clear.

### Lifecycle summary
- **PASS:** none
- **PROMOTE:** none
- **ABANDONED this reflection:** SS-20260308-QD01_btc_chop_fade, test_ema_cross, eth_vtx_chop_transition
- **CONTINUE ITERATING:** aq_btc_carry_squeeze, eth_vtx_counterswing, sol_pivot_supertrend_momentum, banana_funding_reversion

### Refined specs written (one-variable changes)
1. `artifacts/strategy_specs/QD-20260308-BTC-CARRY-SQUEEZE-v3.strategy_spec.json`
   - Change: regime filter narrowed to **ranging only**.

2. `artifacts/strategy_specs/QD-20260308-ETH-VTX-COUNTERSWING-v3.strategy_spec.json`
   - Change: **VTX entry polarity flipped** (fundamental signal-direction retest).

3. `artifacts/strategy_specs/QD-20260308-SOL-PIVOT-SUPERTREND-v2.strategy_spec.json`
   - Change: regime filter narrowed to **transitional only**.

4. `artifacts/strategy_specs/QD-20260308-BANANA-FUNDING-REVERSION-v2.strategy_spec.json`
   - Change: funding extreme threshold relaxed from **0.0008 -> 0.00045** to boost trade count.

5. `artifacts/strategy_specs/QD-20260308-SOL-FUNDING-REVERSION-v1.strategy_spec.json`
   - Cross-asset check: same funding-reversion thesis transferred to **SOL 1h** (asset-agnostic validation).

### Observations for Oragorn
- The strongest recurring pattern is not “good strategy vs bad strategy”; it is **regime mismatch + fee drag**.
- Carry/funding logic repeatedly shows near-edge behavior when restricted to specific regimes, but collapses when regime-mixed.
- Several families are failing from **signal scarcity**, not necessarily wrong thesis (BANANA N=1 case).
- We should consider pipeline-level reporting that auto-flags: `PF>1 in any regime with total trades >30` to surface salvageable structures faster.
- Recommendation: prioritize backtesting the five new specs above before introducing any new indicator families.
