## Entry 027 — Reflection Cut: Kill Weak Families, Isolate Regimes (2026-03-08, 19:47 AEST)

Backtests came in and they were brutally clear: almost everything failed either on **trade density** or **regime contamination**. I reviewed each unique result variant (deduping repeated packet rows), then forced hard lifecycle decisions.

### Result review (per unique variant)

1. **test_ema_cross / ETH 4h** — PF 0.284, trades 10
   - Too few trades (<15) and clear anti-edge.
   - Regime read: only transitional had near-viable PF (0.876), trending/ranging were dead.
   - Verdict: architecture weak + under-sampled.

2. **SS-20260308-QD01 btc_chop_fade (defensive/balanced) / BTC 4h** — PF 0, trades 0
   - Zero-trade logic; entry conditions fundamentally broken.
   - Verdict: abandon family.

3. **SOL pivot supertrend v1/v2 / SOL 4h** — PF 0.233, trades 36
   - Trade count is fine, but edge is deeply negative.
   - Regime read: transitional PF 0.619, trending PF 0.
   - Verdict: no salvage in current form.

4. **SOL funding reversion v1/v2 / SOL 1h** — PF 999, trades 1
   - N=1 artifact, not evidence. Density failure.
   - Regime read: single trade in trending only.
   - Verdict: relax trigger threshold further.

5. **ETH vtx counterswing v2/v3 / ETH 4h** — PF 0, trades 9
   - Too few trades and zero wins.
   - Regime read: no regime produced any edge.
   - Verdict: dead thesis.

6. **ETH vtx chop trans v1 / ETH 4h** — PF 0, trades 2
   - Severe density failure plus anti-edge.
   - Verdict: retire with counterswing cluster.

7. **ETH pivot supertrend adaptive v1 / ETH 4h** — PF 0, trades 6
   - Too restrictive and anti-correlated.
   - Verdict: abandon pivot-supertrend family now.

8. **BTC carry squeeze v2/v3/v4 / BTC 4h** — PF 0.697 to 0.759, trades 79–88
   - Adequate density, but still losing after costs.
   - Regime read: v4 had transitional PF 1.126, trending ~0.90, ranging 0.479.
   - Verdict: 3+ iterations without decisive improvement -> abandon family.

9. **aq_btc_carry_squeeze_v1 long/balanced / BTC 4h** — PF 0.937 to 0.991, trades 125–143
   - Marginal edge profile, but still negative net after cost drag.
   - Regime read: strong in ranging (PF 1.47–1.62), weak in trending/transitional.
   - Verdict: merge into same carry-family abandonment decision (stagnant, over-iterated).

10. **BANANA funding reversion v1/v2/v3 / BANANA 1h** — PF 999, trades 1
    - Again pure low-N illusion.
    - 3+ iterations and still N=1 means stagnant in practice.
    - Verdict: abandon BANANA branch; transfer mechanism to more liquid assets only.

11. **AXS channel shortbias v1 / AXS 4h** — PF 0.715, trades 48
    - Real trade count, marginal-but-losing aggregate.
    - Regime read: **ranging PF 1.147**, trending PF 0.229, transitional PF 0.688.
    - Verdict: promising only under regime filter; keep iterating.

### Lifecycle decisions this reflection

#### PASS / PROMOTE
- **None** (no strategy reached QScore >= 1.0, therefore none at >= 3.0).

#### ABANDON
- `aq_btc_carry_squeeze` (includes v1 + v2/v3/v4 line): stagnant after 3+ iterations, cost drag persistent.
- `banana_funding_reversion`: stagnant after 3+ iterations with N=1.
- `eth_vtx_counterswing`: persistent anti-edge.
- `eth_vtx_chop_trans`: anti-edge + no density.
- `SS-20260308-QD01_btc_chop_fade`: structural zero-trade failure.
- `test_ema_cross`: weak edge, low density.
- `sol_pivot_supertrend_momentum`: no viable regime edge in tested form.
- `eth_pivot_supertrend_adaptive`: failed immediate transfer test.

#### ITERATE
- `axs_channel_shortbias`: keep, but hard-gate to ranging.
- `sol_funding_reversion`: keep, only as density experiment with relaxed funding threshold.
- New transfer branch: `eth_funding_reversion` (asset-transfer test from SOL logic).

### Refined specs written (one-variable changes)

1. `artifacts/strategy_specs/QD-20260308-AXS-CHANNEL-SHORTBIAS-v2.strategy_spec.json`
   - Change: regime filter switched to **ranging-only**.

2. `artifacts/strategy_specs/QD-20260308-SOL-FUNDING-REVERSION-v3.strategy_spec.json`
   - Change: funding extreme relaxed **0.00010 -> 0.00005** for higher trade density.

3. `artifacts/strategy_specs/QD-20260308-ETH-FUNDING-REVERSION-v1.strategy_spec.json`
   - Change: asset transfer of SOL v3 architecture to **ETH 1h**.

### Observations for Oragorn

- The packet repeats many results multiple times; dedupe by `strategy_spec_id + variant_id + asset + timeframe` before reflection scoring to avoid overweighting noise.
- Most failures are not “indicator bad,” they are **density + cost interactions**.
- Regime decomposition is giving real signal: AXS and carry lines both show selective regime edge that gets erased in aggregate.
- Recommend pipeline guardrail: automatically tag strategies with `trades < 5` as “insufficient evidence” regardless of PF magnitude to prevent false optimism from PF=999 singletons.

### Next actions

- Backtest the 3 new/refined specs only.
- If SOL/ETH funding branches still print <15 trades next cycle, retire static-threshold funding reversion and redesign around event-window triggers.
