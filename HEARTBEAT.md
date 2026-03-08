# Heartbeat Checklist

- Read the agent message board: read data/state/agent_messages.json — act on anything flagged high priority
- Check if any new strategy specs exist in artifacts/strategy_specs/ that haven't been backtested — if so, run: exec python scripts/cycle-postprocess.py --since-minutes 30
- Check Quandalf's journal age — if agents/quandalf/memory/latest_journal.md is older than 12 hours and Quandalf should have run, flag it
- Check data/state/agent_messages.json for pending alerts from any agent
- If Logron flagged a critical issue, investigate and delegate fix
- If Quandalf reported a concern about strategy quality, adjust next cycle orders
- Read Quandalf's latest journal at agents/quandalf/memory/ for insights and complaints
- Synthesize important bits from all agent reports — you are the single point of awareness
- If nothing needs attention, reply HEARTBEAT_OK
