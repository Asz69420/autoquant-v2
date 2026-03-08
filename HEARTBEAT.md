# Heartbeat Checklist

- Read the agent message board: read data/state/agent_messages.json — act on anything flagged high priority
- Check if any new strategy specs exist in artifacts/strategy_specs/ that haven't been backtested — if so, run: exec python scripts/cycle-postprocess.py --since-minutes 30
- Check Quandalf's journal age — if agents/quandalf/memory/latest_journal.md is older than 12 hours and Quandalf should have run, flag it
- If nothing needs attention, reply HEARTBEAT_OK
