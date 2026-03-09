Active task: Investigate why the pipeline's refinement mode runs but cooking/research does not.

Steps:
1. Check recent pipeline errors/logs/status for the failing research/cooking path.
2. Inspect the relevant pipeline/config/code paths to identify the root cause.
3. Fix or delegate the fix with clear success criteria.
4. Report the verdict and next action to Asz.

Completed so far:
- Captured task in SCRATCH.md
- Read coding-agent skill
- Checked gateway logs, cron jobs, and recent run history
- Verified current cycle orders are now TAO/4h and the old TAO support mismatch is no longer the active blocker
- Confirmed research-pipeline cron job exists but has failed 5 consecutive times with the same hard timeout
- Confirmed refinement-pipeline cron job is healthy

Current diagnosis:
- research-pipeline job `a6d9c3e4-2dc2-4a92-8b42-2c5bd7e62111` is timing out at exactly 1800s (`cron: job execution timed out`)
- refinement-pipeline job `e682dd88-5d1b-4cac-8b24-c8b1cd6d6c72` is succeeding
- This is now a branch-specific timeout/hang in the research path, not a missing schedule or global gateway issue

Next step:
- Report the root cause to Asz and ask for approval to patch the research pipeline timeout/instrument the hanging step.