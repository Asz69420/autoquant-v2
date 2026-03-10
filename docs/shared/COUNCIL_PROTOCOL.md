# Fellowship Council Protocol

Use this when Asz says any of:
- invoke the council
- fellowship debate
- council on [topic]
- what does the fellowship think about
- ask the team about

This is for high-stakes decisions only: architecture changes, promotion decisions, strategy direction, and major system changes.

## Structure
The debate has 3 rounds max.

### Round 1 — Independent positions
- Oragorn: architecture, system health, priorities, realism
- Quandalf: strategy, market, research direction, edge quality
- Frodex: technical feasibility, implementation complexity, infrastructure risk
- No cross-reading yet
- Max 300 words each

### Round 2 — Challenges and responses
- All agents read all Round 1 positions
- Each responds with agreement, challenge, and what others missed
- Max 200 words each

### Round 3 — Final positions
- Final recommendation only
- do it / don't do it / do it with these changes
- No hedging
- Max 150 words each

## Hard constraints
- 3 rounds only
- Sequential, not parallel
- 120 second timeout per external agent per round
- If no response: record NO RESPONSE and continue
- The council advises; Asz decides
- Total wall clock target: under 15 minutes

## Output
Write the full result to `docs/shared/council_debate.md` with:
- Topic
- Context
- Round 1
- Round 2
- Round 3
- Commander's Synthesis

## Practical runner
Use:

```powershell
python scripts/run_council_debate.py "Should we prioritize fixing the YouTube digest split or building the strategic dashboard next?" --context "Current system is operational but still being stabilized."
```

This runner queries Quandalf and Frodex sequentially through `openclaw agent`, writes the debate markdown, and preserves strict round limits. Oragorn then sends the resulting file content to Asz.
