Task: Fix cycle state coherence and re-enable pipeline crons.

Steps:
1. Inspect all cycle_id/state tracking files in data/state, manifests, cycle_orders, and pipeline/scripts.
2. Identify source of truth for cycle_id.
3. Reset drifted state files to coherent current value 148.
4. Patch code so cycle_id advances in one place and other files read/sync from that source.
5. Add startup sanity check to warn and sync mismatched cycle state.
6. Re-enable research cron after state fix.
7. Re-enable refinement cron only if refinement pipeline exists and is functional.
8. Watch one full research cycle and verify cycle advance, cooking card, and gateway responsiveness.
9. Commit and push repo-side cycle-state fix.

Completed so far:
- Task captured.

Next step:
- Run isolated coding agent on repo + host config validation and watch cycle behavior.
