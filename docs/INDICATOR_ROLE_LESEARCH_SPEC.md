# Indicator Role Learning Spec — Quandalf vNext

## Goal
Upgrade Quandalf from thinking in terms of indicator stacks to thinking in terms of:

**market mechanism -> component roles -> lane fit -> expected behavior -> test -> diagnosis -> refinement**

This spec extends the current strategy-learning loop so Quandalf can learn not only from whole strategies, but also from:
- indicator role usage
- component pairings
- management structure
- lane/regime fit

---

## 1. Core Principle
Indicators are not strategies.
Indicators are components.

The same indicator can serve different roles depending on context.
Examples:
- trend filter
- directional bias
- entry timing
- confirmation
- partial profit
- trailing exit
- risk-off signal
- full invalidation signal
- session filter
- volatility gate

Quandalf must stop thinking:
- “use RSI”

and start thinking:
- “use RSI as exhaustion timing inside a trend-filtered pullback structure”

---

## 2. Design Rule
Every strategy must explicitly assign each component a role.

### Required per-strategy fields
- hypothesis
- lane / validation basket
- component list
- role map
- expected behavior
- expected trade density
- expected outcome pattern
- success criteria
- failure criteria
- first refinement path

### Example
- EMA_50 = directional bias
- RSI_14 = entry timing
- ATR_14 = volatility gate + stop sizing
- Supertrend flip = full invalidation
- Bollinger upper band = partial profit cue

---

## 3. Required Role Categories
Allowed role vocabulary should include:
- regime filter
- directional bias
- entry timing
- confirmation
- exit logic
- risk / invalidation
- scale in
- scale out
- partial profit
- session filter
- volatility gate
- de-risk signal
- full invalidation signal

This list can expand later, but strategies must use explicit roles, not just indicator names.

---

## 4. New Memory Layer: Indicator Doctrine
Add a new living knowledge file:

`agents/quandalf/memory/indicator_doctrine.json`

Purpose:
Store what AutoQuant has learned about indicators by role, lane, regime, and pairing.

### Structure
For each indicator-role entry, track:
- indicator
- role
- lane(s)
- regime context
- usefulness score
- confidence
- evidence count
- common pairings
- anti-pairings
- success notes
- failure notes
- known anti-patterns
- review / expiry metadata

### Example record
- indicator: RSI_14
- role: entry timing
- lane: ETH 1h
- regime: chop / pullback
- usefulness: medium-high
- confidence: medium
- evidence_count: 7
- pairings: EMA_50 directional bias, ATR volatility gate
- anti_patterns: standalone trend continuation trigger in strong trend

---

## 5. Pairing Memory
A lot of edge lives in pairings, not isolated indicators.

Add pairing-level learning such as:
- trend filter + pullback timing
- breakout trigger + volatility expansion
- exhaustion cue + regime filter
- directional bias + partial profit structure

Store:
- component A
- role A
- component B
- role B
- lane/regime
- result quality
- notes

This can initially live inside `indicator_doctrine.json`, then split into a dedicated file later if it grows.

---

## 6. Management As First-Class Research
Management logic should be treated as seriously as entry logic.

Quandalf should actively experiment with:
- partial profits
- scale in / scale out
- trailing exits
- de-risk signals
- full invalidation signals
- regime-dependent management
- inside-session vs outside-session management

### Rule
A strategy may keep the same entry logic but still represent a meaningful new experiment if management structure changes materially.

---

## 7. Reflection Upgrade
After every backtest, Quandalf should reflect at multiple levels.

### Level 1 — Strategy level
- did the strategy work?
- was the thesis right?

### Level 2 — Role level
- was the directional bias correct?
- was the timing component too sparse?
- was confirmation redundant?
- was the invalidation logic too aggressive / too weak?

### Level 3 — Pairing level
- did these components work together?
- did one component help or choke the other?

### Level 4 — Thesis / family level
- is the broader mechanism real?
- is the idea lane-specific or portable?

This makes learning more granular and reusable.

---

## 8. Expectation vs Reality
Every strategy must state expected behavior before test.

Required expectation fields:
- expected trade density
- expected outcome pattern
- expected good lanes
- expected bad lanes
- expected failure mode if wrong

After test, Quandalf must compare:
- what I expected
- what actually happened
- where the mismatch occurred
- what that says about component roles, lane fit, or management

This is the core learning mechanism.

---

## 9. Iteration Quality Gate
Iteration must be structural and reasoned.

### Required refine fields
- iteration_intent
- structural_change
- expected_effect
- why this deserves another attempt

### Good iteration types
- role reassignment
- lane reassignment
- component replacement
- management restructure
- simplification
- density rescue
- robustness test
- regime specialization

### Bad iteration types
- cosmetic micro-parameter drift with no reason
- EMA 9 -> 10 with no hypothesis
- threshold nudge with no expected effect

---

## 10. Failure Diagnosis Expansion
Diagnosis should include whole-strategy and component-level insight.

Current categories remain:
- bad idea
- bad implementation
- wrong indicator role assignment
- wrong asset
- wrong timeframe
- wrong regime
- weak exit/risk logic
- too sparse
- too complex / overfit

But reflection should also answer:
- which role failed?
- which pairing failed?
- which management element hurt the result?

---

## 11. Required System Files
### New / upgraded files
- `agents/quandalf/memory/indicator_doctrine.json`
- `agents/quandalf/memory/latest_experiment_memory.json`
- `agents/quandalf/memory/latest_learning_loop.json`
- `agents/quandalf/memory/research_program.json`
- strategy specs must include role map + expected outcome fields

### Optional later split
- `pairing_doctrine.json`
- `management_doctrine.json`
- `family_thesis_memory.json`

---

## 12. Strategy Spec Contract Upgrade
Each strategy spec should support fields like:
- `component_roles`
- `expected_trade_density`
- `expected_outcome_pattern`
- `success_criteria`
- `failure_criteria`
- `validation_basket` / `test_lanes`
- `lane_expectations`
- `management_intent`

This gives the backtester and reflection loop the information needed for real learning.

---

## 13. Learning Hierarchy
We want learning at four levels:

### A. Strategy memory
What happened with this exact strategy?

### B. Component-role memory
How did this indicator behave in this role?

### C. Pairing memory
How did these components interact?

### D. Thesis/family memory
Is the broader idea improving, fragmenting, or dying?

This hierarchy allows much better reuse of lessons.

---

## 14. Rollout Plan
### Phase 1
- force explicit component-role mapping in every strategy
- force expected outcome fields in every strategy
- include role-level comparison in reflection

### Phase 2
- add `indicator_doctrine.json`
- start recording role-level and pairing-level lessons
- add management notes into experiment memory

### Phase 3
- enforce structural iteration gate
- reject cosmetic refine attempts unless justified
- promote role/pairing lessons into doctrine

### Phase 4
- split doctrine into component / pairing / management files if needed
- add confidence and expiry metadata
- auto-steer against repeated anti-patterns

---

## 15. Non-Negotiables
- Indicators must be treated as components with roles.
- Every strategy must state expected behavior before testing.
- Reflection must compare expectation vs reality.
- Iteration must be structural, not cosmetic.
- Management logic is first-class research.
- Learning must happen at strategy, role, pairing, and thesis level.

---

## 16. Final Outcome
Best target state:

Quandalf becomes a strategist who understands not only whether a strategy worked, but:
- which component worked
- which role worked
- which pairing worked
- which lane suited the mechanism
- which management logic improved resilience
- and how to recompose those parts intelligently next cycle

That is the path from indicator stacking to true strategy research.
