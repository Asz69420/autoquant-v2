# Quandalf Build Spec — AutoQuant Research System vNext

## Goal
Turn Quandalf into a disciplined autonomous strategy researcher with:
- tight experiment loops
- explicit thesis-driven lane selection
- automatic data provisioning
- harsh anti-overfitting truth filters
- durable but non-bloated memory
- clean handoff from research -> refinement -> promotion

This is not a generic agent lab. It is a trading research system.

---

## 1. Core Operating Principle

Quandalf operates as:

**market mechanism -> best test environment -> component roles -> testable rules -> experiment -> diagnosis -> next decision**

Not:
- stack indicators
- run backtest
- hope score goes up

Every strategy must be a falsifiable market hypothesis.

---

## 2. System Shape

### A. Cooking / Research Loop
Always running unless paused.
Completion-driven, not timer-driven.

Loop:
1. load active research program
2. retrieve relevant memory
3. choose thesis + best-fit lane(s)
4. auto-provision required candle data
5. write strategy specs with reasoning
6. run screen/backtest
7. classify outcomes
8. reflect + diagnose
9. update durable learning
10. immediately start next cycle

### B. Refinement Loop
Event-driven only.
Runs only when Quandalf explicitly queues refinement work.

Loop:
1. take PASS candidates or explicit refine decisions
2. run full refinement pack for each strategy
3. compare whole pack
4. return one decision per strategy:
   - Iterated
   - Passed
   - Aborted
   - Promoted

### C. Promotion Layer
Promotion is not just “highest score this cycle”.
Promotion requires survival under stronger truth checks.

---

## 3. Research Contract

Every research cycle must produce:
- one or more explicit hypotheses
- one bounded mutation surface
- one evaluation contract
- one keep/discard decision per strategy
- one durable learning update

Every strategy spec must include a reasoning block with:
- market behavior targeted
- why edge should exist
- asset/timeframe fit
- indicator/component role map
- expected regime
- likely failure mode
- first refinement path
- what would justify continuation
- what would justify rotation away

---

## 4. Lane Authority

Quandalf controls:
- asset
- timeframe
- validation basket
- whether a mechanism should be screened cross-asset or cross-timeframe

System responsibility:
- if required lane data is missing or stale, fetch/build it automatically
- validate data freshness and completeness before backtest
- classify data failure separately from strategy failure

### Validation basket default
For new concepts, default basket should usually contain:
- primary asset/timeframe
- one adjacent timeframe
- one similar asset
- one structurally different asset

### Example
If thesis is session-drive continuation:
- SOL 1h primary
- SOL 15m adjacent
- ETH 1h similar
- TAO 1h structurally different

---

## 5. Experiment Object

Every tested strategy should create a compact experiment object:
- strategy_spec_id
- hypothesis
- chosen lane
- component roles
- mutation surface
- expected effect
- actual effect
- trade count
- PF
- DD
- QScore
- regime context
- diagnosis
- decision
- lesson extracted

This becomes the base unit of memory and audit.

---

## 6. Mutation Discipline

Quandalf should not mutate everything at once.
Each cycle must declare the allowed mutation surface.

Allowed mutation domains:
- lane (asset/timeframe)
- entry logic
- exit logic
- management logic
- indicator role assignment
- regime filter
- confirmation density

### Rule
One experiment packet = one thesis + one bounded mutation surface.

That keeps learning attributable.

---

## 7. Truth Filter

Trading is deceptive. So research cannot optimize only for short-run score.

### Screen layer
Cheap falsification:
- does it trade?
- is trade count plausible?
- obvious contradiction / sparsity?
- obvious lane mismatch?

### Validity layer
Only strategies that survive screen proceed to meaningful evaluation.

### Hard evaluation layer
Must include, where applicable:
- walk-forward
- trade count sanity
- drawdown sanity
- regime slicing
- nearby perturbation / robustness
- management simplification check
- family comparison

### Promotion rule
Promote only when the thesis survives:
- good out-of-sample behavior
- credible trade count
- acceptable drawdown
- nearby perturbation
- some stability across lane or regime variation
- thesis still makes sense after testing

---

## 8. Zero-Trade Policy

0 trades is a red flag.
Not a silent fail.
Not fake completion.

Required handling:
1. diagnose cause
2. allow one rescue attempt only
3. rescue types allowed:
   - simplify
   - widen trigger
   - remove filter
   - change lane
   - reassign indicator roles
4. if still 0 trades -> abort/archive

Visible outcomes must remain decision outcomes.
Internal execution detail can exist, but user-facing decision must be:
- Iterated
- Passed
- Aborted
- Promoted

---

## 9. Failure Diagnosis Taxonomy

Every failed strategy must be tagged with one primary diagnosis:
- bad idea
- bad implementation
- wrong indicator role assignment
- wrong asset
- wrong timeframe
- wrong regime
- weak exit/risk logic
- too sparse
- too complex / overfit

Optional secondary tags allowed.

This diagnosis must flow into:
- reflection
- memory
- next cycle steering

---

## 10. PASS Workflow

PASS is not the end.
PASS means the strategy earned structured refinement.

PASS refinement pack should usually include:
- exit variants
- management variants
- simplification version
- regime variants
- adjacent timeframe checks
- cross-asset checks
- position sizing / partial-profit variants

Decision is made after the full pack, not one mutation at a time.

Unit of judgment:
**strategy -> full refinement pack -> one outcome**

---

## 11. Memory Model

Keep the 3-layer memory model, but simplify Quandalf’s default working surface.

### Layer 0 — Active Scratchpad
Cycle-local working memory.
Messy, fast, disposable.
Contains:
- active hypotheses
- candidate lanes
- quick comparisons
- immediate notes

### Layer 1 — Experiment Memory
Structured experiment objects.
Contains:
- what was tested
- under what conditions
- what happened
- diagnosis
- decision

### Layer 2 — Distilled Lessons
Only promoted, evidence-backed lessons.
Contains:
- reusable principles
- repeated failure patterns
- stable lane or mechanism insights
- confidence / evidence metadata
- expiry / review metadata

### Layer 3 — Archive / Audit
Full history, journals, raw artifacts.
Write-heavy, read-light.
Not default retrieval.

### Retrieval policy
Default Quandalf retrieval should use:
- active scratchpad
- recent experiment memory
- distilled lessons

Do NOT dump archive by default.

### Anti-bloat rules
- promote by evidence, not by verbosity
- dedupe repeated lessons
- merge family memory instead of endless append
- expire stale lessons by regime age
- compress old experiments into summary forms

---

## 12. Research Program File

Add a live research operating file, separate from SOUL.

Suggested file: `agents/quandalf/memory/research_program.json`

It should contain:
- current search priorities
- banned failure patterns
- active hypotheses
- preferred mutation surfaces
- lane rotation policy
- current anti-patterns
- what counts as meaningful refinement
- current intervention directives from Asz/Oragorn

This acts like Quandalf’s research org file.

---

## 13. Loop Control

### Cooking
Completion-driven chaining only.
No blind schedule as control plane.
Timer only allowed as watchdog.

### Refinement
Queue-triggered only.
No blind polling loop as primary behavior.

### Pause
Research must stop only when explicitly paused.

---

## 14. Reporting Rules

Cards should reflect reality.

### Cooking card
Activity order:
- Generated
- Iterated
- Backtests
- Passed
- Aborted

Where:
- Backtests = tests actually executed
- Aborted = explicit decision outcomes, not internal execution metadata

### Refinement card
Keep:
- First
- Second
- Third
- Backtests
- Upgraded
- Rejected
- Promoted

### Notes
Notes should explain:
- what happened
- why it mattered
- what decision was made

Not vague status noise.

---

## 15. What To Borrow From Autoresearch

Borrow:
- tight experiment loop
- explicit experiment contract
- constrained mutation surfaces
- fixed comparable run discipline where useful
- small active working memory
- compact experiment logs
- researcher operating file

Do NOT borrow blindly:
- optimizing to a single short-run metric
- weak memory promotion
- loose truth checks
- assuming local gains are real progress
- unrestricted mutation chaos

---

## 16. Rollout Order

### Phase 1 — already mostly in motion
- strategy-level decisions
- 0-trade red flag handling
- queue-triggered refinement
- continuous cooking
- durable learning update each cycle

### Phase 2 — immediate next build
- add `research_program.json`
- add formal experiment objects
- add lane validator + automatic fetch quality gate
- add diagnosis taxonomy enforcement
- add default validation basket logic everywhere

### Phase 3 — refinement hardening
- full-pack refinement execution per strategy
- pack-level decisioning
- simplification / management / adjacency templates
- family-level promotion checks

### Phase 4 — memory optimization
- local scratchpad layer
- evidence-based promotion to distilled lessons
- expiry/review metadata
- archive compression and retrieval tightening

### Phase 5 — research quality control
- forced rotation when lane concentration is too high
- mechanism diversity quotas
- regime-aware retrieval and lesson weighting
- intervention thresholds when too many abort-only cycles happen

---

## 17. Non-Negotiables

- Quandalf owns strategy thinking.
- Pipeline executes and validates.
- Every strategy ends with a decision.
- 0 trades must be addressed explicitly.
- Research lane choice must be thesis-driven.
- Missing lane data must be auto-prepared.
- Promotion requires robustness, not just one good score.
- Memory must stay layered and disciplined.
- Archive is not default context.

---

## 18. Final Build Decision

Best build for AutoQuant is:

**A continuous local research system with thesis-driven lane freedom, automatic data provisioning, structured experiment objects, harsh trading truth filters, queue-driven refinement, and a disciplined 3-layer memory model with a simpler scratchpad front-end for Quandalf.**

That gives us:
- the speed and focus of autoresearch
- without sacrificing the truth discipline trading requires
- and without bloating memory into useless sludge
