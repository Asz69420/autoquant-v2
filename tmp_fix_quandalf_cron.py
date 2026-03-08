import subprocess

openclaw = r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.CMD"
job_id = "bbfbe68d-00b8-46cf-a4d3-ad77b204368d"
msg = (
    "Research cycle. Follow your SOUL.md workflow: "
    "1) Read your briefing: read agents/quandalf/memory/briefing_packet.json "
    "2) Read your journal: read agents/quandalf/memory/latest_journal.md "
    "3) Read V1 knowledge: read agents/quandalf/memory/v1-journal.md "
    "4) Use your tools to gather context: "
    "exec python ~/.openclaw/skills/autoquant-leaderboard/query.py --limit 5 ; "
    "exec python ~/.openclaw/skills/autoquant-market-data/market.py --scan ; "
    "exec python ~/.openclaw/skills/autoquant-kpi/query.py --days 30 ; "
    "exec python ~/.openclaw/skills/autoquant-lessons/query.py --limit 5 "
    "5) Design ONE strategy. Write complete strategy_spec JSON to artifacts/strategy_specs/YOUR_SPEC_NAME.strategy_spec.json "
    "6) Write your journal to agents/quandalf/memory/latest_journal.md. Be honest, first person, thesis, reasoning, market assessment, next plan. "
    "7) Leave a message for Oragorn by updating data/state/agent_messages.json with key observations"
)

cmd = [
    openclaw, "cron", "edit", job_id,
    "--message", msg,
    "--announce",
    "--channel", "telegram",
    "--to", "1801759510",
    "--thinking", "medium",
]
r = subprocess.run(cmd, capture_output=True, text=True)
print(r.stdout)
print("rc=", r.returncode)
if r.stderr:
    print(r.stderr)
