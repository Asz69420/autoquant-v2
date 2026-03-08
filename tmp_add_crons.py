import subprocess

openclaw = r"C:\Users\Clamps\AppData\Roaming\npm\openclaw.CMD"

quandalf_msg = """Research cycle. Follow your SOUL.md workflow:

1. Read your briefing: read agents/quandalf/memory/briefing_packet.json
2. Read your journal: read agents/quandalf/memory/latest_journal.md 
3. Read V1 knowledge: read agents/quandalf/memory/v1-journal.md
4. Use your tools to gather context:
 exec python ~/.openclaw/skills/autoquant-leaderboard/query.py --limit 5
 exec python ~/.openclaw/skills/autoquant-market-data/market.py --scan
 exec python ~/.openclaw/skills/autoquant-kpi/query.py --days 30
 exec python ~/.openclaw/skills/autoquant-lessons/query.py --limit 5
5. Design ONE strategy. Write the complete strategy_spec JSON to: write artifacts/strategy_specs/YOUR_SPEC_NAME.strategy_spec.json
6. Write your journal entry to: write agents/quandalf/memory/latest_journal.md
 Be honest. First person. What you researched, your thesis, reasoning, market assessment, what you plan next.
7. Leave a message for Oragorn: write data/state/agent_messages.json with your key observations"""

post_msg = r"exec python C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\cycle-postprocess.py --since-minutes 30"

cmd1 = [
    openclaw, "cron", "add",
    "--name", "quandalf-research",
    "--cron", "5 14 * * *",
    "--tz", "Australia/Brisbane",
    "--session", "isolated",
    "--agent", "quandalf",
    "--message", quandalf_msg,
    "--announce",
    "--channel", "telegram",
    "--to", "1801759510",
    "--thinking", "medium",
]

cmd2 = [
    openclaw, "cron", "add",
    "--name", "cycle-postprocess",
    "--cron", "20 14 * * *",
    "--tz", "Australia/Brisbane",
    "--session", "isolated",
    "--agent", "main",
    "--message", post_msg,
    "--announce",
    "--channel", "telegram",
    "--to", "-5038734156",
]

for i, cmd in enumerate((cmd1, cmd2), start=1):
    r = subprocess.run(cmd, capture_output=True, text=True)
    print(f"=== CMD {i} RC={r.returncode} ===")
    print(r.stdout)
    if r.stderr:
        print(r.stderr)
