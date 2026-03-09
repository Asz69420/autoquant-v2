Task: Fix agent-to-agent delegation so execution tasks actually run.

Steps:
1. Patch openclaw.json so Oragorn can spawn Frodex, Quandalf, and Logron via subagents.allowAgents.
2. Add explicit Delegation Rules to workspace-oragorn/SOUL.md: sessions_spawn for execution tasks, include runTimeoutSeconds, full context, exact commands/paths/outputs, sessions_send only for quick updates.
3. Validate config shape and hot-reload behavior.
4. Run a real fresh-session spawn test to Frodex and confirm it executes and announces back.
5. Commit and push changes.

Completed so far:
- Verified tools.agentToAgent.allow already includes oragorn/logron/quandalf/frodex.
- Verified root cause: Oragorn subagents.allowAgents does not include frodex/quandalf/logron.
- Confirmed docs: sessions_spawn is the intended isolated sub-agent tool; default timeout is 0 unless runTimeoutSeconds or defaults are set.

Next step:
- Patch openclaw.json and SOUL.md, then run the live Frodex spawn test.
