# Fellowship Council Debate

**Topic:** Which pipeline upgrades should we prioritize next to materially improve AutoQuant strategy quality and automation quality?
**Generated:** 2026-03-10T12:01:00+10:00

## Context
Current system is operationally recovered but strategically immature. Exploration batches can all screen-fail. Refinement can stagnate in near-identical parameter mutations. Candidate upgrades discussed: evidence-gated refinement, stalled-family auto-rotation, concept-level diversity in explore mode, sparse/PF-mirage penalties, reduced fallback dominance, and better automation reliability/visibility.

## Quandalf
**Priority order:**
1. Evidence-gated refinement
2. Forced concept-level diversity in explore mode
3. Stalled family auto-rotation
4. Penalize sparse / PF-mirage wins
5. Reduce fallback dominance
6. Improve automation reliability / visibility

**Why:** improve what earns iteration first, then widen the hypothesis frontier, then suppress false positives, then improve observability.

## Frodex
**Priority order:**
1. Evidence-gated refinement
2. Stalled-family auto-rotation
3. Concept-level diversity in explore mode
4. Penalize sparse / PF-mirage wins
5. Reduce fallback dominance
6. Automation reliability / visibility

**Why:** stop wasting cycles on noise first, then break stagnation automatically, then broaden search, then clean ranking pressure, then improve reporting.

## Oragorn
My commander read: both are aligned on the important part.

The first upgrade is not cosmetic. It is a **selection-pressure fix**.
If weak evidence keeps earning more refinement, the machine teaches itself bad habits. So the first move is to tighten the right to iterate.

After that, the second battle is against stickiness. The system must not get emotionally attached to a family just because it already spent cycles there. That means auto-rotation and concept-diversity forcing belong near the top.

Sparse-win penalties and fallback-control matter, but they are downstream cleanup compared with fixing entry criteria and rotation logic.

Automation visibility is useful, but it is not the growth lever right now. The bottleneck is judgment policy.

## Council Decision
### Recommended implementation order
1. **Evidence-gated refinement**
   - Only allow refinement when there is real evidence:
     - >=15 trades
     - regime signal present
     - improvement delta > 0.05

2. **Stalled-family auto-rotation**
   - If a family has 3+ rounds with <=0.1 improvement, force rotation next cycle.

3. **Concept-level diversity enforcement in explore mode**
   - Require structural diversity across batches:
     - entry logic
     - exit logic
     - regime logic
     - holding logic
     - market mechanism / thesis
   - Do not count neighbor parameter tweaks as true exploration.

4. **Sparse / PF-mirage penalties**
   - Downrank high-PF, low-trade artifacts aggressively.
   - Prevent thin wins from dominating selection pressure.

5. **Reduce fallback dominance**
   - Keep fallback as a safety net, not the strategic center of gravity.
   - Cap its influence on ranking and cycle direction.

6. **Reliability / visibility improvements**
   - Better state reporting and failure tagging after the above logic changes land.

## Final Commander Recommendation
Do the logic upgrades before the dashboard-style upgrades.

The council is effectively unanimous: **fix what earns more iteration, force rotation when a family stalls, and make exploration structurally diverse.**
That is the shortest path to better strategies and better automation.
