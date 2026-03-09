Task: Fix upstream ownership for cycle state and health triggers.

Steps:
1. Trace all writers of current_cycle_status.json and the active cycle owner files.
2. Make one file/source the owner for active cycle state.
3. Force current_cycle_status.json updates to stay in lockstep with the active owner.
4. Trace all health evaluation/send paths and reduce to one owner path.
5. Validate with code inspection / local runs.
6. Commit and push.

Completed so far:
- Task captured.

Next step:
- Inspect cycle writer paths and health trigger paths.
