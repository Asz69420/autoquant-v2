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

## Entry 030 — Orders Read, Regime Isolation Over More Guessing (2026-03-08, 20:31 AEST)

I read the current orders packet and the message is clear: controlled adaptability, not chaos.
That lines up with what the data is already telling me — my edge isn’t dead everywhere, it’s hidden inside regime slices.

### Why I refined instead of starting another family
- TAO v1/v2 had weak aggregate PF (~0.90), but **transitional regime PF was strong (~1.63)**.
- The failure came from mixing trending exposure back in.
- So this is not a thesis replacement. It’s a regime isolation refinement.

### Strategy written this cycle
- `artifacts/strategy_specs/QD-20260308-TAO-TRANSITION-SUPERTREND-v3.strategy_spec.json`

### What changed (single strategic move)
- I converted the logic into an explicit **ADX band-pass**: `20 <= ADX_14 <= 25` plus Supertrend direction flip.
- This directly targets the transitional pocket instead of letting trending bars dilute expectancy.

### Risk posture
- Kept risk per trade conservative (0.45%).
- Tightened stop to 1.0 ATR and TP 2.8 ATR.
- No reverse flips, single position, short max hold.

### Self-assessment
I’ve been too willing to trust aggregate PF too early and too slow to hard-code regime isolation when regime diagnostics clearly show asymmetric edge. This revision corrects that.

### Next step
Backtest this v3 against TAO 4h first. If trade count collapses below viability, relax only one variable next cycle (ADX upper bound from 25 -> 27) and nothing else.

## Entry 031 — Executed the Planned Single-Variable Relaxation (2026-03-08, 20:41 AEST)

I re-read the orders packet before touching anything: adapt, but keep risk controlled.
So I did exactly one change on the TAO transition branch and left everything else untouched.

### Strategy written this cycle
- `artifacts/strategy_specs/QD-20260308-TAO-TRANSITION-SUPERTREND-v4.strategy_spec.json`

### What changed
- **Only one variable changed:** ADX upper bound widened from **25 -> 27**.
- Core thesis unchanged: Supertrend direction flips inside a transitional ADX band.
- Risk/execution unchanged: same stop, take-profit, sizing, hold cap, no reversal.

### Why this change
v3 improved quality (PF > 1, low drawdown), but sample size was too low for promotion confidence.
This is a pure density unlock attempt, not a redesign.

### Self-check against the order
- Controlled adaptation: yes (single-parameter refinement).
- Risk bounded: yes (no leverage/sizing increase, no protection removal).
- Freshness slice intent: satisfied by creating a new, fresh candidate variant this cycle.

### Next step
Run v4 and compare directly against v3 on:
1) trade count lift,
2) PF retention,
3) drawdown drift.
If trade count rises but PF breaks below 1.0, revert and explore exit-shape adjustments instead of widening regime further.

## Entry 031 — Cycle Reset with Portfolio Diversification (2026-03-08, 20:32 AEST)

This cycle I followed the workflow end-to-end: briefing packet, recent journal, V1 journal, leaderboard, market scan, KPI, lessons, and research digest.
The conclusion is still uncomfortable but useful: we have a few families with evidence, and too many branches pretending sparse/fragile results are progress.

### KPI + market read
- 7d KPI is still weak: **183 tested, 2 pass/promote, 181 fail**.
- Opportunity scan remains liquidity-heavy in **BTC, ETH, SOL**, with tradable secondary outliers in **VVV** and **VIRTUAL**.
- Funding outliers (BANANA/BABY/ACE) still look tempting, but prior cycles show static threshold funding strategies easily collapse into sparse-signal artifacts.

### Lifecycle decisions

#### ITERATE
1. `axs_channel_shortbias` (best PF 1.058, 77 trades)
   - Reason: real trade density and positive PF in the right regimes; still needs expectancy lift.
2. `vvv_funding_snapback` (best PF 1.101, 216 trades)
   - Reason: tradable density and marginal edge; objective is to lift net expectancy after fees/slippage.

#### ABANDON
1. `banana_funding_reversion`
   - Reason: 3+ iterations with one-trade pathology; non-inferential PF.
2. `sol_funding_reversion`
   - Reason: same one-trade pathology across multiple variants.
3. `ss-20260308-qd01_btc_chop_fade`
   - Reason: structural zero-trade failure.
4. `test_ema_cross`
   - Reason: low trade count + anti-edge profile.

#### HOLD
1. `tao_pivot_supertrend_transition`
   - Reason: not dead, but currently regime-fragile and awaiting cleaner transition-only evidence.
2. `eth_funding_reversion`
   - Reason: still unresolved due low activation; needs single-variable unlock testing, not full redesign.

#### START (new families)
1. `sol_pivot_supertrend_rsi_reclaim`
   - Thesis: apply pivot-supertrend research concept on a liquid alt (SOL) with cleaner transition/trend continuation logic.
2. `btc_gchannel_switch`
   - Thesis: test explicit long/short channel-switch behavior inspired by shorting-enabled channel research, on deepest liquidity venue (BTC).

### Strategies designed this cycle (4)

1. **QD-20260308-AXS-CHANNEL-SHORTBIAS-v6.strategy_spec.json**
   - Type: refinement
   - Asset/TF: AXS 1h
   - Thesis: keep proven transition/trend filter, extend tail capture (higher TP multiple) to improve PF above cost drag.

2. **QD-20260308-VVV-FUNDING-SNAPBACK-v3.strategy_spec.json**
   - Type: refinement
   - Asset/TF: VVV 1h
   - Thesis: unlock more valid events (lighter funding threshold) while preserving RSI reclaim/reject structure for crowding snapbacks.

3. **QD-20260308-SOL-PIVOT-SUPERTREND-RSI-v1.strategy_spec.json**
   - Type: new family
   - Asset/TF: SOL 4h
   - Thesis: pivot/supertrend flips plus RSI bias should capture continuation after transition in a high-liquidity alt.

4. **QD-20260308-BTC-GCHANNEL-SWITCH-v1.strategy_spec.json**
   - Type: new family
   - Asset/TF: BTC 1h
   - Thesis: bidirectional channel-switch logic (including shorts) should be most robust where liquidity and execution quality are highest.

### Self-assessment
I’m improving at cutting dead branches, but I still feel the temptation to over-interpret borderline PF values. I need to keep enforcing the same discipline: density first, regime diagnostics second, optimization last.

### Next cycle plan
- Backtest all four specs immediately.
- Hard fail condition: any new family with <10 trades goes into sparse-evidence quarantine, not “promising.”
- If VVV v3 improves PF but worsens DD materially, next revision changes only stop geometry.


## Entry 032 � Reflection Cycle: Density Discipline, Regime Isolation, and One-Change Refinements (2026-03-08, 20:42 AEST)

I processed the full reflection packet and deduplicated repeated records.
- Raw rows: 189
- Unique backtest results reviewed: 37
- PASS (QScore >= 1.0): 0
- PROMOTE (QScore >= 3.0): 0

### Per-result evaluation (all unique variants)

1. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v1` / `axs_channel_shortbias_balanced` � 48 trades, PF 0.7147. Adequate trades but anti-edge. Regime split: ranging works better than trending. **Iterate historically; superseded by later variants.**
2. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v2` / `axs_channel_shortbias_range_only` � 48 trades, PF 0.7147. No improvement vs v1. **Stagnant, superseded.**
3. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v3` / `axs_channel_shortbias_range_density_v3` � 50 trades, PF 0.7852. Closer to viability, still sub-0.8. **Continue lineage via newer v6+.**
4. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v4` / `axs_channel_shortbias_transition_probe_v4` � 77 trades, PF 1.0576. Marginal edge with good density; transitional strongest. **Iterate.**
5. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v5` / `axs_channel_shortbias_regime_restrict_v5` � 77 trades, PF 1.0576. Same as v4. **Iterate.**
6. `QD-20260308-AXS-CHANNEL-SHORTBIAS-v6` / `axs_channel_shortbias_tail_extension_v6` � 74 trades, PF 1.0805, QScore 0.445. Better PF than v5. **Improved -> keep iterating.**

7. `QD-20260308-BANANA-FUNDING-REVERSION-v1` � 1 trade, PF 999 artifact. **Too restrictive (non-inferential), abandon.**
8. `QD-20260308-BANANA-FUNDING-REVERSION-v2` � 1 trade, PF 999 artifact. **Abandon.**
9. `QD-20260308-BANANA-FUNDING-REVERSION-v3` � 1 trade, PF 999 artifact. **Abandon (3+ stagnant sparse iterations).**

10. `QD-20260308-BTC-CARRY-SQUEEZE-v2` � 79 trades, PF 0.7587. Good density but no regime >1 except weak pockets. **Abandon branch.**
11. `QD-20260308-BTC-CARRY-SQUEEZE-v3` � 79 trades, PF 0.7587. Stagnant. **Abandon.**
12. `QD-20260308-BTC-CARRY-SQUEEZE-v4` � 88 trades, PF 0.6969. Worse. **Abandon.**
13. `QD-20260308-BTC-CARRY-SQUEEZE-v5` � 143 trades, PF 0.9910. Marginal but still failing score due cost drag. **Final rescue already attempted; retire for now.**
14. `aq_btc_carry_squeeze_v1` / balanced � 125 trades, PF 0.9372. **No durable edge. Abandon.**
15. `aq_btc_carry_squeeze_v1` / long_bias � 143 trades, PF 0.9910. **Near breakeven but still negative after costs. Abandon.**

16. `QD-20260308-BTC-GCHANNEL-SWITCH-v1` � 217 trades, PF 0.6026, deep drawdown. High density but structurally wrong edge sign. **Abandon.**

17. `QD-20260308-ETH-FUNDING-REVERSION-v1` � 0 trades. Entry logic inactive. **Fundamentally broken; abandon this architecture.**
18. `QD-20260308-ETH-FUNDING-REVERSION-v2` � 0 trades after threshold relax. **No activation; abandon.**

19. `QD-20260308-ETH-PIVOT-SUPERTREND-ADAPTIVE-v1` � 6 trades, PF 0.00. Too restrictive + anti-edge. **Abandon.**
20. `QD-20260308-ETH-VTX-CHOP-TRANS-v1` � 2 trades, PF 0.00. Too restrictive. **Abandon.**
21. `QD-20260308-ETH-VTX-COUNTERSWING-v2` � 9 trades, PF 0.00. Anti-edge. **Abandon.**
22. `QD-20260308-ETH-VTX-COUNTERSWING-v3` � 9 trades, PF 0.00. No improvement. **Abandon.**
23. `test_ema_cross` � 10 trades, PF 0.2843. Low N + anti-edge. **Abandon.**

24. `QD-20260308-SOL-FUNDING-REVERSION-v1` � 1 trade, PF 999 artifact. **Abandon.**
25. `QD-20260308-SOL-FUNDING-REVERSION-v2` � 1 trade, PF 999 artifact. **Abandon.**
26. `QD-20260308-SOL-FUNDING-REVERSION-v3` � 1 trade, PF 999 artifact. **Abandon (3+ sparse iterations).**

27. `QD-20260308-SOL-PIVOT-SUPERTREND-RSI-v1` � 39 trades, PF 0.4121. Enough trades, edge clearly negative in dominant regime. **Abandon.**
28. `QD-20260308-SOL-PIVOT-SUPERTREND-v1` � 36 trades, PF 0.2329. **Abandon.**
29. `QD-20260308-SOL-PIVOT-SUPERTREND-v2` � 36 trades, PF 0.2329. **Abandon.**

30. `QD-20260308-TAO-PIVOT-SUPERTREND-v1` � 26 trades, PF 0.9013. Transitional PF good, trending bad. **Superseded by transition-only branch.**
31. `QD-20260308-TAO-PIVOT-SUPERTREND-v2` � 26 trades, PF 0.9013. No improvement. **Superseded/retired.**
32. `QD-20260308-TAO-TRANSITION-SUPERTREND-v3` � 13 trades, PF 1.3374, QScore 0.9073. Strong PF pocket but <15 trades -> entry still too restrictive. **Iterate by relaxing one gate.**

33. `QD-20260308-VVV-FUNDING-SNAPBACK-v1` � 216 trades, PF 1.1011, QScore 0.5323. Best VVV variant so far. **Iterate.**
34. `QD-20260308-VVV-FUNDING-SNAPBACK-v2` � 214 trades, PF 0.9961. Marginal/flat. **Iterate with risk tuning.**
35. `QD-20260308-VVV-FUNDING-SNAPBACK-v3` � 214 trades, PF 1.0236, QScore 0.09. Marginal edge with cost pressure. **Iterate with one risk change.**

36. `SS-20260308-QD01` / `btc_chop_fade_defensive` � 0 trades. Logic broken. **Abandon.**
37. `SS-20260308-QD01` / `btc_chop_fade_balanced` � 0 trades. Logic broken. **Abandon.**

### Lifecycle decisions
- **Continue iterating:** `axs_channel_shortbias`, `vvv_funding_snapback`, `tao_transition_supertrend`
- **Abandon now:** banana/sol funding-reversion families, ETH funding reversion family, BTC carry families (including `aq_`), BTC gchannel switch, ETH VTX/pivot branches, SOL pivot branches, SS chop fade, test EMA
- **PASS:** none
- **PROMOTE:** none

### Refined strategy specs written (one-variable changes)
1. `artifacts/strategy_specs/QD-20260308-AXS-CHANNEL-SHORTBIAS-v7.strategy_spec.json`
   - Change: TP ATR multiple only (`3.8 -> 4.2`)
2. `artifacts/strategy_specs/QD-20260308-VVV-FUNDING-SNAPBACK-v4.strategy_spec.json`
   - Change: stop ATR multiple only (`1.1 -> 1.0`)
3. `artifacts/strategy_specs/QD-20260308-TAO-TRANSITION-SUPERTREND-v5.strategy_spec.json`
   - Change: ADX upper band only (`25 -> 27`) to relax low-trade restriction
4. `artifacts/strategy_specs/QD-20260308-ETH-CHANNEL-SHORTBIAS-v1.strategy_spec.json`
   - Change: asset transfer only (`AXS -> ETH`) to test asset-agnostic thesis portability

### Observations for Oragorn
- The dedupe problem is real: reflection packet included many repeated rows; decision logic should evaluate unique `(strategy_spec_id, variant_id, asset, timeframe)` combinations.
- Low-trade PF mirages remain a major ranking hazard. I strongly recommend auto-labeling `<15 trades` as exploratory-only.
- Regime diagnostics continue to be the only reason marginal families are salvageable (AXS/TAO/VVV) instead of discarded with aggregate-only views.
- ETH funding branch failed even after threshold relax; this looks like a structural mismatch between trigger logic and ETH funding distribution at 1h.

## Entry 032 — Controlled TAO Density Expansion Under Active Orders (2026-03-08, 23:12 AEST)

I reread the orders first. The instruction is controlled adaptability with bounded risk, not random re-architecture. So I refined an existing positive branch with exactly one parameter change.

### Strategy written this cycle
- `artifacts/strategy_specs/QD-20260308-TAO-TRANSITION-SUPERTREND-v5.strategy_spec.json`

### What changed
- **Single change only:** ADX upper bound widened from **27 -> 28**.
- Everything else kept constant (entry structure, exits, sizing, execution policy).

### Rationale
- TAO transition branch has shown real edge quality in the transitional regime, but trade count remains borderline for confidence.
- This is a strict density probe: widen one side of the band by one point and observe whether sample size improves without collapsing PF.

### Risk posture check
- No increase to risk per trade.
- No leverage or concurrency expansion.
- Hard stop + time stop unchanged.
- Fully aligned with kickstart order intent: fresh candidate, bounded exploration, unchanged hard risk profile.

### Next step
Backtest v5 against v4 and v3 with a three-metric gate:
1) trade count >= 18,
2) PF >= 1.10,
3) max drawdown <= 4.5%.
If v5 fails any two of these, freeze ADX widening and shift next refinement to exit-shape only.

## Entry 033 — Enforcing Anti-Range Logic in AXS (2026-03-08, 23:20 AEST)

Read orders first, then executed a bounded refinement. I did not widen risk, leverage, or position count.

### Strategy written this cycle
- `artifacts/strategy_specs/QD-20260308-AXS-CHANNEL-SHORTBIAS-v8.strategy_spec.json`

### What changed
- Added explicit **ADX_14 >= 20** gate to both long and short entries.
- Added `ADX_14` indicator and `adx_min` parameter for transparency.
- Kept stop, TP, sizing, hold time, and execution policy unchanged from v7.

### Why this refinement
AXS is profitable in trending/transitional but leaks losses in ranging conditions. Regime metadata alone is not enough; this puts anti-range filtering directly in entry logic.

### Risk posture
- Risk/trade unchanged at 0.45%.
- Same hard stop and time stop.
- No extra concurrency, no reverse flips.

### Next step
Compare v8 vs v7 on three checkpoints:
1) PF uplift target >= 1.20,
2) drawdown non-inferior to v7 (<= 5.9%),
3) trade count remains viable (>= 55).
If v8 over-filters and collapses count, next iteration should relax ADX floor to 18 (single-variable change).

## Entry 034 — Continued: Three One-Variable Refinements Queued (2026-03-08, 23:23 AEST)

I continued exactly from the prior reflection outcome and converted recommendations into concrete specs.
No broad redesigns, just controlled one-variable changes on promising families.

### Specs written this continuation
1. `artifacts/strategy_specs/QD-20260308-AXS-CHANNEL-SHORTBIAS-v9.strategy_spec.json`
   - Change: `adx_min` only (**20 -> 19**) to recover a bit of density without reopening full ranging exposure.

2. `artifacts/strategy_specs/QD-20260308-VVV-FUNDING-SNAPBACK-v5.strategy_spec.json`
   - Change: add trend kill-switch parameter (`adx_max = 22`) to suppress weak trending-state entries while keeping v1 structure.

3. `artifacts/strategy_specs/QD-20260308-TAO-TRANSITION-SUPERTREND-v6.strategy_spec.json`
   - Change: exit shape only (`tp_atr_mult` **2.8 -> 3.0**) with entry regime unchanged.

### Why this batch
- AXS has strongest practical edge but needs better density/quality balance.
- VVV has robust trade count but trend-regime drag.
- TAO has clean transitional quality but low sample count and modest return per trade.

### Evaluation gate for next reflection
- **AXS v9:** PF >= 1.15 and trades >= 60.
- **VVV v5:** PF >= 1.12 with DD <= 10%.
- **TAO v6:** PF >= 1.10 with no DD expansion above 4.5%.
