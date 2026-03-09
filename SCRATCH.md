Task: Fix sub-agent stalling.

Steps:
1. Diagnose current sub-agent state: list workers/sessions if possible, inspect logs, inspect model/thinking/timeout/approval config.
2. Patch host openclaw.json: cheap subagent model, thinking off, runTimeoutSeconds 300, archiveAfterMinutes 60, maxConcurrent 3, exec ask off if supported.
3. Check ~/.openclaw/exec-approvals.json for python/git preapproval; patch if needed.
4. Update Oragorn SOUL.md with explicit <30 seconds do-it-yourself delegation rule.
5. Clear any stalled sub-agents/workers if possible.
6. Report diagnosis findings and changes.

Completed so far:
- Task captured.

Next step:
- Inspect runtime config and sub-agent state.
