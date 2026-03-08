# Branch Map — Promising Strategy Families

Updated: 2026-03-08 23:27 AEST

This is the quick resume file.
Read this before diving into old specs.

---

## AXS Channel Family

### Thesis
EMA channel + RSI trigger works when the market is not stuck in low-quality ranging churn.

### Queue
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v7.strategy_spec.json` — TP extension baseline
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v8.strategy_spec.json` — ADX >= 20
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v9.strategy_spec.json` — ADX >= 19
- `QD-20260308-AXS-CHANNEL-SHORTBIAS-v10.strategy_spec.json` — ADX >= 18

### Current read
- Strongest practical family so far
- Transitional edge is best
- Ranging remains the main leak

### Next move
- Keep the strictest ADX floor that preserves viable trade count

---

## ETH Channel Family

### Thesis
AXS channel logic may transfer to ETH, but ETH needs churn control because costs are heavier.

### Queue
- `QD-20260308-ETH-CHANNEL-SHORTBIAS-v1.strategy_spec.json` — asset transfer baseline
- `QD-20260308-ETH-CHANNEL-SHORTBIAS-v2.strategy_spec.json` — ADX >= 20
- `QD-20260308-ETH-CHANNEL-SHORTBIAS-v3.strategy_spec.json` — ADX >= 19

### Current read
- Good density
- Acceptable PF
- Costs are the main threat

### Next move
- Decide whether ADX filtering improves net edge enough to justify reduced count

---

## VVV Funding Snapback Family

### Thesis
Funding extremes plus RSI reclaim can fade crowding, but trending states damage expectancy.

### Queue
- `QD-20260308-VVV-FUNDING-SNAPBACK-v1.strategy_spec.json` — best baseline so far
- `QD-20260308-VVV-FUNDING-SNAPBACK-v5.strategy_spec.json` — ADX <= 22 kill-switch
- `QD-20260308-VVV-FUNDING-SNAPBACK-v6.strategy_spec.json` — ADX <= 24 fallback

### Current read
- Best mean-reversion candidate with real trade density
- Baseline v1 still the benchmark to beat
- Later tweaks showed DD can expand fast

### Next move
- Prefer quality improvements only if density survives

---

## TAO Transition Supertrend Family

### Thesis
TAO has a real transitional pocket; the main problem is low sample size, not obvious anti-edge.

### Queue
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v3.strategy_spec.json` — strongest pure quality read
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v4.strategy_spec.json` — density unlock
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v5.strategy_spec.json` — further density expansion
- `QD-20260308-TAO-TRANSITION-SUPERTREND-v6.strategy_spec.json` — exit-shape TP 3.0

### Current read
- Real edge in transitional regime
- Low-N confidence issue persists
- Stop widening entry band unless exit-shape tests fail

### Next move
- Compare v6 against the best prior TAO version and freeze whichever keeps PF with acceptable DD

---

## Dead / Frozen Families

Do not reopen unless new evidence appears:
- BANANA funding reversion
- SOL funding reversion
- BTC carry squeeze family
- ETH VTX families
- ETH pivot-adaptive branch
- SOL pivot branches
- SS BTC chop fade
- test_ema_cross

---

## Resume Order

When resuming after interruption:
1. Read `next_reflection_checklist.md`
2. Read latest `reflection_packet.json`
3. Use this branch map to avoid re-deriving the tree
4. Decide one variable at a time
