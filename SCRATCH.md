Task: Properly fix empty/garbage cycle batch postprocess cards.

Steps:
1. Trace where current_cycle_batch_summary.json and related current-cycle state are populated.
2. Identify why postprocess reads empty/misaligned state and still sends/logs 0-spec/0-backtest updates.
3. Patch upstream coherence checks so postprocess requires coherent current-cycle state and completed current-cycle rows before sending a batch card.
4. If state is missing/misaligned when it should not be, emit an explicit warning/error path instead of a fake zero card.
5. Validate, commit, and push.

Completed so far:
- Task captured.

Next step:
- Read state-producing and postprocess code paths.
