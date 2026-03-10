# Council Debate — Pipeline Efficiency and Edge Discovery

## Question
How should AutoQuant improve pipeline design, agent coordination, and search process to find profitable edge more efficiently?

## Round 1

### Quandalf
Diagnosis: AutoQuant is not failing from lack of activity; it is failing from **poor search geometry and corrupted learning state**. Too much effort is wasted on stale cycle context, weak family lineage, repetitive explore ideas, and refining branches that never earned refinement.

Top 5:
1. Enforce one canonical cycle/state object and hard-fail misaligned runs.
2. Split explore vs exploit properly.
3. Search trade expression, not just entries.
4. Adopt staged search geometry.
5. Upgrade lessons and family tracking.

### Frodex
Diagnosis: **the system is operational, but the search loop is wasting cycles on low-information refinements, weak state continuity, and a search space that is too narrow in practice.** It’s producing activity, not enough real learning.

Top 5:
1. Fix state lineage end-to-end.
2. Gate refinement hard.
3. Expand search to full strategy architecture.
4. Increase concept diversity; reduce fallback repetition.
5. Separate agent roles more sharply.

### Logron
Diagnosis: biggest issue is **system inefficiency and signal contamination**. Persistent gateway errors, weak journaling, and too much pipeline volume relative to durable wins.

Top 5:
1. Stabilize gateway first.
2. Add hard stage gates.
3. Tighten agent handoffs with explicit contracts.
4. Shift from brute force to guided exploration.
5. Track search efficiency metrics, not just volume.

## Round 2

### Quandalf response
- Low-information refinements are a major tax.
- Unstable orchestration and weak handoffs poison the learning loop.
- **Most important:** fix state integrity first.
- First: one canonical run record tying together cycle order, specs, backtests, reflections, and family lineage.
- Second: strict refinement gate (`trades >= 15`, real post-cost edge, explicit mutation target).
- Third: repair family tracking at concept level.
- Fourth: widen Stage 1 exploration and stop flooding later stages with weak concepts.
- Fifth: expand into exits/holding/scaling only after integrity and gating are fixed.

### Frodex response
- Agrees with Quandalf first: state integrity and family tracking are prerequisite.
- Agrees with Logron second: contracts and stage conversion matter.
- **Most important:** fix decision integrity, not just runtime stability.
- First: repair lineage fields end-to-end (`family_id`, `parent_id`, iteration, lessons, cycle context, status transitions).
- Then: hard refinement gates with minimum trades, minimum improvement delta, robustness sanity, and loser kill.
- Then: concept-level family tracking.
- Tighten contracts where they protect decisions: no stale state, no ambiguous outputs, no silent fallback overwrites.
- Only then optimize throughput.

### Logron response
- Agrees integrity/lineage/gates are the right priority order.
- **Most important:** system reliability + state integrity first.
- Second: repair lineage end-to-end so every result is traceable.
- Third: enforce strict refinement gates before expensive backtests.
- Strongly agrees with concept-level family tracking.
- Throughput optimization should wait until conversion improves.
- First concrete move: freeze scale-up, reduce nonessential search load, spend one cycle on gateway error reduction, lineage repair, and schema/gate enforcement.
- Then resume guided search with family-level tracking and stage KPIs.

## Round 3 — Final Vote

### Quandalf
1. Fix canonical cycle state and lineage integrity first.
2. Gate refinement aggressively and kill losers faster.
3. Expand explore mode across trade management styles, not just entry logic.

### Frodex
1. Fix state integrity and family lineage.
2. Enforce hard refinement gates with automatic loser killing.
3. Expand exploration to true concept and trade-management diversity.

### Logron
1. Restore reliability and state integrity first.
2. Repair lineage and enforce hard refinement gates.
3. Shift search to family-level guided exploration.

## Council Consensus
The council is aligned. AutoQuant should not scale search volume yet. The right order is:
1. **State integrity + reliability first** — canonical cycle record, stable gateway/control plane, traceable lineage.
2. **Hard refinement gates** — no refinement without density, edge, and clear mutation rationale; kill losers early.
3. **Broader, guided exploration** — family-level search with real concept and trade-management diversity, not entry-template churn.

## Recommended 7-Day Plan
1. Build/repair a canonical run record tying cycle, orders, specs, jobs, results, reflections, and lessons.
2. Enforce refinement admission rules (`trades >= 15`, post-cost PF threshold, improvement delta, no duplicate family churn).
3. Add family-level tracking fields and concept lineage.
4. Add stage conversion KPIs: candidates → valid specs → completed backtests → passes → promotions.
5. Widen Stage 1 to explore exits, holding, trailing, partials, and regime-aware management styles.
6. Keep fallback from dominating by penalizing overused concept clusters.
7. Only after the above, scale throughput.
