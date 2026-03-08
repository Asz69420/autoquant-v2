#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
JOURNAL_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "latest_journal.md")

PHASE_EMOJIS = {
    "briefing": "📋",
    "cooking": "🍳",
    "reflecting": "🔮",
    "backtesting": "🧪",
    "complete": "✅",
    "error": "❌",
    "promotion": "🏆",
    "journal": "🧙",
    "scanning": "📡",
}

STATUS_EMOJIS = {
    "ok": "✅",
    "fail": "❌",
    "warn": "⚠️",
}


def send_tg(message, channel="dm"):
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as e:
        print(f"TG send failed: {e}", file=sys.stderr)


def build_log_card(phase, status, run_id, runtime_sec, activity_dict, note):
    phase_emoji = PHASE_EMOJIS.get(phase, "📋")
    status_emoji = STATUS_EMOJIS.get(status, "✅")
    runtime_str = f"{int(runtime_sec // 60)}m {int(runtime_sec % 60)}s" if runtime_sec else "0m 0s"
    run_id_short = run_id[-6:] if run_id and len(run_id) > 6 else (run_id or "------")

    lines = []
    lines.append(f"{phase_emoji} {phase.capitalize()}")
    lines.append(f"{status_emoji} | ▶ {runtime_str} | 🆔 {run_id_short}")
    lines.append("○──activity──────────────────")
    for k, v in activity_dict.items():
        lines.append(f"{k}: {v}")
    lines.append("○──note──────────────────────")
    for line in str(note)[:200].split("\n"):
        lines.append(line)
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since-minutes", type=int, default=30)
    a = p.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=a.since_minutes)).isoformat()
    start_time = time.time()

    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               score_total, score_decision, ts_iso
        FROM backtest_results
        WHERE ts_iso >= ?
        ORDER BY ts_iso DESC
        """,
        (cutoff,),
    ).fetchall()

    total_rows = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    conn.close()

    if not rows:
        print(json.dumps({"status": "no_new_results", "since_minutes": a.since_minutes, "total_in_db": total_rows}))
        return

    dm_lines = []
    dm_lines.append("🧪 <b>Research Cycle Results</b>")
    dm_lines.append("")

    best_qscore = 0
    best_strategy = None
    for r in rows:
        pf = round(r["profit_factor"], 3) if r["profit_factor"] else 0
        dd = round(r["max_drawdown_pct"], 1) if r["max_drawdown_pct"] else 0
        qs = round(r["score_total"], 2) if r["score_total"] else 0
        trades = r["total_trades"] or 0
        decision = r["score_decision"] or "?"

        emoji = "🟢" if qs >= 3.0 else "🟡" if qs >= 1.0 else "🔴"
        dm_lines.append(f"<code>{emoji} {r['asset']}/{r['timeframe']} PF:{pf} DD:{dd}% T:{trades} QS:{qs} {decision}</code>")

        if qs > best_qscore:
            best_qscore = qs
            best_strategy = f"{r['asset']}/{r['timeframe']}"

    dm_lines.append("")
    dm_lines.append(f"<code>Total in DB: {total_rows} | New this cycle: {len(rows)}</code>")

    dm_text = "\n".join(dm_lines)
    send_tg(dm_text, "dm")

    journal_text = ""
    if os.path.exists(JOURNAL_PATH):
        try:
            with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
                journal_text = f.read().strip()
        except Exception:
            pass

    if journal_text:
        journal_preview = journal_text[:500]
        if len(journal_text) > 500:
            journal_preview += "..."
        journal_msg = f"🧙 <b>Quandalf's Journal</b>\n\n<code>{journal_preview}</code>"
        send_tg(journal_msg, "dm")

    elapsed = round(time.time() - start_time, 1)

    best_pf = 0
    for r in rows:
        if r["profit_factor"] and r["profit_factor"] > best_pf:
            best_pf = r["profit_factor"]

    overall_status = (
        "ok"
        if any(r["score_total"] and r["score_total"] >= 1.0 for r in rows)
        else "warn"
        if any(r["total_trades"] and r["total_trades"] > 0 for r in rows)
        else "fail"
    )

    note = f"Cycle complete: {len(rows)} backtests run."
    if best_qscore >= 3.0:
        note += f" Promotion candidate: {best_strategy}!"
    elif best_qscore >= 1.0:
        note += f" Best: {best_strategy} (QS {best_qscore})"
    else:
        note += " No strong promotion yet."

    log_card = build_log_card(
        "cooking",
        overall_status,
        rows[0]["id"] if rows else "none",
        elapsed,
        {
            "Backtests": len(rows),
            "Best PF": round(best_pf, 3),
            "Best QScore": round(best_qscore, 2),
            "Promotions": sum(1 for r in rows if r["score_total"] and r["score_total"] >= 3.0),
        },
        note,
    )
    send_tg(f"<pre>{log_card}</pre>", "log")

    print(
        json.dumps(
            {
                "status": "processed",
                "new_results": len(rows),
                "total_in_db": total_rows,
                "best_qscore": best_qscore,
                "dm_sent": True,
                "log_card_sent": True,
                "journal_sent": bool(journal_text),
            }
        )
    )


if __name__ == "__main__":
    main()
