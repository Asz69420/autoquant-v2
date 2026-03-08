#!/usr/bin/env python3
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
SKILLS = r"C:\Users\Clamps\.openclaw\skills"
PY = sys.executable
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
BOARD_SCRIPT = os.path.join(ROOT, "scripts", "agent-message-board.py")
BOARD_PATH = os.path.join(ROOT, "data", "state", "agent_messages.json")


def run_skill(args):
    try:
        r = subprocess.run([PY] + args, capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.stdout.strip() else {"status": "empty"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def load_agent_messages(limit=5):
    normalized = []

    if os.path.exists(BOARD_PATH):
        try:
            with open(BOARD_PATH, "r", encoding="utf-8") as f:
                board = json.load(f)

            raw_messages = board.get("messages")
            if isinstance(raw_messages, list):
                for m in raw_messages:
                    if isinstance(m, dict):
                        normalized.append(m)
            elif isinstance(raw_messages, dict):
                for agent, payload in raw_messages.items():
                    if not isinstance(payload, dict):
                        continue
                    obs = payload.get("observations") or []
                    next_actions = payload.get("next_actions") or []
                    snippets = []
                    if obs:
                        snippets.append("; ".join(obs[:2]))
                    if next_actions:
                        snippets.append("Next: " + "; ".join(next_actions[:1]))
                    msg_text = " | ".join(snippets) if snippets else json.dumps(payload)[:160]
                    normalized.append(
                        {
                            "ts_iso": board.get("updated_at", ""),
                            "from": agent,
                            "to": "oragorn",
                            "type": payload.get("priority", "note"),
                            "message": msg_text,
                            "read_by": [],
                        }
                    )
        except Exception:
            normalized = []

    if not normalized:
        fallback = run_skill([BOARD_SCRIPT, "--read", "--to-agent", "oragorn", "--limit", str(limit)])
        raw = fallback.get("messages", []) if isinstance(fallback, dict) else []
        if isinstance(raw, list):
            normalized = [m for m in raw if isinstance(m, dict)]

    return normalized[-limit:]


def main():
    ts = datetime.now(timezone.utc).isoformat()
    leaderboard = run_skill([os.path.join(SKILLS, "autoquant-leaderboard", "query.py"), "--limit", "5"])
    kpi = run_skill([os.path.join(SKILLS, "autoquant-kpi", "query.py"), "--days", "7"])
    scan = run_skill([os.path.join(SKILLS, "autoquant-market-data", "market.py"), "--scan"])
    funding = run_skill([os.path.join(SKILLS, "autoquant-market-data", "market.py"), "--funding"])
    messages = load_agent_messages(limit=5)

    daily_journal_path = os.path.join(ROOT, "agents", "quandalf", "memory", "daily_journal.md")
    cycle_journal_path = os.path.join(ROOT, "agents", "quandalf", "memory", "latest_journal.md")

    if os.path.exists(daily_journal_path):
        quandalf_journal = open(daily_journal_path, "r", encoding="utf-8").read()
    else:
        quandalf_journal = open(cycle_journal_path, "r", encoding="utf-8").read() if os.path.exists(cycle_journal_path) else ""
    quandalf_journal = quandalf_journal.strip()

    lines = []
    lines.append("🏰 <b>AutoQuant Daily Intel Brief</b>")
    lines.append(f"<code>{ts[:10]}</code>")
    lines.append("")

    lines.append("📊 <b>Leaderboard (Top 5)</b>")
    if leaderboard.get("strategies"):
        for s in leaderboard["strategies"][:5]:
            q = s.get("qscore", 0)
            emoji = "🟢" if q >= 3.0 else "🟡" if q >= 1.0 else "🔴"
            lines.append(
                f"<code>{emoji} {s.get('asset','?')}/{s.get('tf','?')} PF:{s.get('pf',0)} DD:{s.get('dd',0)}% QS:{q} {s.get('decision','?')}</code>"
            )
    else:
        lines.append("<code> No strategies yet</code>")
    lines.append("")

    lines.append("📈 <b>KPIs (7d)</b>")
    if kpi.get("total", 0) > 0:
        lines.append(
            f"<code> Tested: {kpi.get('total',0)} | Pass: {kpi.get('hit_rate_pct',0)}% | Promote: {kpi.get('promote_rate_pct',0)}%</code>"
        )
    else:
        lines.append("<code> No backtests in last 7 days</code>")
    lines.append("")

    lines.append("🔍 <b>Market Scan (Top 3)</b>")
    opps = scan.get("opportunities") or scan.get("top_opportunities") or []
    if opps:
        for opp in opps[:3]:
            name = opp.get("asset") or opp.get("name") or "?"
            lines.append(f"<code> {name}</code>")
    else:
        lines.append("<code> No scan data</code>")
    lines.append("")

    if funding.get("funding"):
        lines.append("💸 <b>Funding Extremes</b>")
        for row in funding.get("funding", [])[:3]:
            lines.append(
                f"<code> {row.get('asset','?')} fr={row.get('funding_rate',0)}</code>"
            )
        lines.append("")

    if quandalf_journal:
        lines.append("🧙 <b>Quandalf's Latest Journal</b>")
        journal_preview = quandalf_journal[:300]
        if len(quandalf_journal) > 300:
            journal_preview += "..."
        lines.append(f"<code>{journal_preview}</code>")
        lines.append("")

    if messages:
        lines.append("💬 <b>Agent Messages</b>")
        for m in messages[:3]:
            lines.append(
                f"<code> [{m.get('from','?')}→{m.get('to','?')}] {m.get('message','')[:180]}</code>"
            )
        lines.append("")

    lines.append("<code>⚡ End of brief</code>")

    brief_text = "\n".join(lines)
    subprocess.run([PY, TG_SCRIPT, "--message", brief_text, "--channel", "dm", "--bot", "oragorn"], capture_output=True)

    brief_path = os.path.join(ROOT, "data", "state", "latest_intel_brief.txt")
    os.makedirs(os.path.dirname(brief_path), exist_ok=True)
    with open(brief_path, "w", encoding="utf-8") as f:
        f.write(brief_text)

    print(json.dumps({"status": "sent", "brief_length": len(brief_text)}))


if __name__ == "__main__":
    main()
