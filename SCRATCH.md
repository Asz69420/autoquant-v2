Active task: Split YouTube research digest into Quandalf trading feed and Oragorn architecture feed; re-enable/fix broken channels; update digest references; test manually; commit/push.

Steps:
1. Inspect current watcher config/scripts and current digest references.
2. Patch watcher/config for feed tags and split output files with rolling caps.
3. Repair/re-enable broken channels and adjust failure retry logic.
4. Update Quandalf SOUL.md/reference path if needed.
5. Run manual test of grabber and confirm routing.
6. Commit/push and report channels changed + split status.

Completed so far:
- Captured task in SCRATCH.md

Next step:
- Inspect watcher config/scripts and Quandalf digest references.