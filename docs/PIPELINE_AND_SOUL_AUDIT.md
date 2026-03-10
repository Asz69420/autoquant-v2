# Pipeline and Soul Audit

## Verdict
The system is materially stronger than before and the new memory/governance layer is now real, but the live operating model was partially out of sync with the written role model. The safest current model is: **direct execution first, deterministic pipeline second, delegation only where it clearly helps**.

## Pipeline Strengths
- SQLite/leaderboard/backtest truth layer remains intact
- research → backtest → reflection → postprocess flow is structurally sound
- memory governance, promotion, compaction, audit, and status loops are now wired in
- external-intel scaffold is already connected into briefing/orders
- daily maintenance loop now keeps the system cleaner and more self-managing

## Pipeline Weaknesses
- delegation/background completion handoff is less reliable than direct execution
- the cycle can still finish with terminal queue failures and no DB results while appearing superficially complete
- `agent_messages.json` is noisy and repetitive; Oragorn synthesis should rely on summarized signals, not raw repetition
- live cycles still show recurring gateway-error drift that needs root-cause follow-up
- some prompts are long and brittle; they work, but they are not yet minimal/robust

## Soul/Role Strengths
- Oragorn SOUL is now closer to reality: direct, decisive, hands-on
- Quandalf is correctly framed as the strategy intelligence core
- Frodex and Logron now have better retrieval and shared-memory hooks
- role separation is fundamentally good: thinker / doer / watcher / commander

## Soul/Role Weaknesses
- AGENTS.md previously contradicted reality by describing Oragorn as never executing
- delegation assumptions were stronger than actual tool/runtime reliability
- some agent guidance is still more verbose than necessary for day-to-day reliability
- Logron's status still says specification/implementation pending, which understates what now exists operationally

## Highest-ROI Fixes
1. Keep direct execution as default until delegation reliability is proven
2. Treat terminal queue failures as first-class health signals, not just passive observations
3. Add an agent feedback/synthesis loop so Oragorn gets compressed issues, improvements, and self-heal candidates on schedule
4. Reduce noise in raw agent message streams by summarizing repeated identical alerts
5. Keep prompts/contracts tight: enough structure to constrain drift, not so much that they become fragile

## Safe Immediate Changes
- updated AGENTS.md roster line so Oragorn execution model matches reality
- keep pipeline restart cautious: run one observed cycle before trusting full unattended operation
- keep maintenance loop as the single tidy place for recurring governance tasks

## Defer / Don't Touch Yet
- do not redesign the SQLite/leaderboard layer; it is already the right factual backbone
- do not overcomplicate with more permanent agents
- do not add fake live-feed connectors without finalized providers/endpoints
- do not loosen strategy constraints so far that Quandalf starts drifting into unsupported assets/timeframes or noisy prose

## Recommended Next Focus
- build the scheduled agent feedback + Oragorn synthesis loop
- root-cause the recurring gateway/backtest terminal-failure pattern
- then resume/observe one clean cycle and iterate from evidence
