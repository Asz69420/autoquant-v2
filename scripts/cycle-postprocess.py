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
BACKTESTER = r"C:\Users\Clamps\.openclaw\skills\autoquant-backtester\engine.py"
BALROG = r"C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\balrog-validate.py"
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
BOARD_PATH = os.path.join(ROOT, "data", "state", "agent_messages.json")

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


def send_tg_as(message, channel="dm", bot="oragorn"):
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel, "--bot", bot],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception as e:
        print(f"TG send failed: {e}", file=sys.stderr)


def post_agent_message(from_agent, to_agent, msg_type, message):
    board = {"messages": []}
    if os.path.exists(BOARD_PATH):
        try:
            with open(BOARD_PATH, "r", encoding="utf-8") as f:
                current = json.load(f)
            if isinstance(current.get("messages"), list):
                board = current
            elif isinstance(current.get("messages"), dict):
                board = {"messages": []}
                for legacy_agent, payload in current["messages"].items():
                    if not isinstance(payload, dict):
                        continue
                    observations = payload.get("observations") or []
                    msg_text = "; ".join(observations[:2]) if observations else json.dumps(payload)[:160]
                    board["messages"].append(
                        {
                            "ts_iso": current.get("updated_at", datetime.now(timezone.utc).isoformat()),
                            "from": legacy_agent,
                            "to": "oragorn",
                            "type": payload.get("priority", "note"),
                            "message": msg_text,
                            "read_by": [],
                        }
                    )
        except Exception:
            board = {"messages": []}

    entry = {
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "from": from_agent,
        "to": to_agent,
        "type": msg_type,
        "message": message,
        "read_by": [],
    }
    board.setdefault("messages", []).append(entry)
    if len(board["messages"]) > 100:
        board["messages"] = board["messages"][-100:]

    os.makedirs(os.path.dirname(BOARD_PATH), exist_ok=True)
    with open(BOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)


def log_event(event_type, agent, message, severity="info", artifact_id=None, pipeline=None, step=None):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            """
            INSERT INTO event_log (ts_iso, event_type, agent, pipeline, step, artifact_id, severity, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                event_type,
                agent,
                pipeline,
                step,
                artifact_id,
                severity,
                message,
                None,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def log_token_event(agent, pipeline, description):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            """
            INSERT INTO token_spend (ts_iso, agent, pipeline, run_id, input_tokens, output_tokens, total_tokens, model, cost_usd)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                agent,
                pipeline,
                description,
                0,
                0,
                0,
                "tracked_externally",
                0,
            ),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def next_cycle_id():
    counter_path = os.path.join(ROOT, "data", "state", "cycle_counter.json")
    try:
        with open(counter_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {"last_cycle_id": 0}

    data["last_cycle_id"] = int(data.get("last_cycle_id", 0)) + 1
    os.makedirs(os.path.dirname(counter_path), exist_ok=True)
    with open(counter_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data["last_cycle_id"]


def build_log_card(cycle_id, rows, elapsed_seconds, new_backtests):
    status_path = os.path.join(ROOT, "agents", "quandalf", "memory", "strategy_status.json")
    status = {}
    if os.path.exists(status_path):
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                status = json.load(f)
        except Exception:
            pass

    rows_dict = [dict(r) if not isinstance(r, dict) else r for r in rows]

    new_families = len(status.get("new_this_cycle", []))
    abandoned = len(status.get("abandoned_this_cycle", []))
    active = len(status.get("active_families", []))
    specs_written = len(status.get("specs_written", []))

    promotions = sum(1 for r in rows_dict if r.get("score_total") and r["score_total"] >= 3.0)
    best_qs = max((r.get("score_total", 0) or 0 for r in rows_dict), default=0)

    elapsed_str = f"{int(elapsed_seconds // 60)}m {int(elapsed_seconds % 60)}s" if elapsed_seconds else "?"

    lines = []
    lines.append("🍳 Cooking")
    lines.append(f"{'✅' if promotions > 0 else '⚠️'} | ▶ {elapsed_str} | 🆔 {cycle_id}")
    lines.append("○──activity──────────────────")
    lines.append(f"New strategies: {specs_written}")
    lines.append(f"New families: {new_families}")
    lines.append(f"Active families: {active}")
    lines.append(f"Backtests: {new_backtests}")
    lines.append(f"Promotions: {promotions}")
    lines.append(f"Abandoned: {abandoned}")
    lines.append("○──note──────────────────────")
    if promotions > 0:
        lines.append(f"🏆 {promotions} promotion(s)! Best QS: {best_qs:.2f}")
    elif best_qs > 0:
        lines.append(f"Best QS: {best_qs:.2f}. Iterating.")
    else:
        lines.append("No strong results yet. Quandalf refining.")

    return "\n".join(lines)


def format_journal_html(raw_text):
    import re

    text = raw_text
    text = re.sub(r'^### (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<b>\1</b>', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def split_message(text, max_len=4000):
    if len(text) <= max_len:
        return [text]
    parts = []
    while text:
        if len(text) <= max_len:
            parts.append(text)
            break
        split_at = text.rfind('\n', 0, max_len)
        if split_at == -1:
            split_at = max_len
        parts.append(text[:split_at])
        text = text[split_at:].lstrip('\n')
    return parts


def backtest_new_specs():
    if not os.path.exists(SPECS_DIR):
        return 0

    conn = sqlite3.connect(DB)
    backtested = 0

    for f in os.listdir(SPECS_DIR):
        if not f.endswith(".strategy_spec.json"):
            continue

        spec_path = os.path.join(SPECS_DIR, f)
        spec_id = f.replace(".strategy_spec.json", "")

        existing_for_spec = conn.execute(
            "SELECT COUNT(*) FROM backtest_results WHERE strategy_spec_id = ?",
            (spec_id,),
        ).fetchone()[0]
        if existing_for_spec > 0:
            continue

        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec = json.load(fh)
            asset = spec.get("asset", "ETH")
            timeframe = spec.get("timeframe", "4h")
            variants = spec.get("variants", [])
            if not variants:
                continue

            for v in variants:
                vname = v.get("name", "default")
                try:
                    balrog_result = subprocess.run(
                        [sys.executable, BALROG, "--spec", spec_path],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if balrog_result.returncode != 0:
                        try:
                            balrog_out = json.loads(balrog_result.stdout or "{}")
                            errors = balrog_out.get("errors", [])
                            print(f"Balrog BLOCKED {f}: {errors}", file=sys.stderr)
                            log_event("balrog_block", "balrog", f"Blocked spec {spec_id}: {errors}", severity="warn", artifact_id=spec_id, pipeline="research_cycle", step="validation")
                        except Exception:
                            print(f"Balrog BLOCKED {f}: validation failed", file=sys.stderr)
                            log_event("balrog_block", "balrog", f"Blocked spec {spec_id}: validation failed", severity="warn", artifact_id=spec_id, pipeline="research_cycle", step="validation")
                        continue

                    existing_variant = conn.execute(
                        """
                        SELECT COUNT(*) FROM backtest_results
                        WHERE strategy_spec_id = ? AND variant_id = ? AND asset = ? AND timeframe = ?
                        """,
                        (spec_id, vname, asset, timeframe),
                    ).fetchone()[0]
                    if existing_variant > 0:
                        continue

                    result = subprocess.run(
                        [
                            sys.executable,
                            BACKTESTER,
                            "--asset",
                            asset,
                            "--tf",
                            timeframe,
                            "--strategy-spec",
                            spec_path,
                            "--variant",
                            vname,
                        ],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0:
                        backtested += 1
                        bt_row = conn.execute(
                            """
                            SELECT id, profit_factor, score_total
                            FROM backtest_results
                            WHERE strategy_spec_id = ? AND variant_id = ? AND asset = ? AND timeframe = ?
                            ORDER BY ts_iso DESC LIMIT 1
                            """,
                            (spec_id, vname, asset, timeframe),
                        ).fetchone()
                        result_id = bt_row[0] if bt_row else None
                        pf = bt_row[1] if bt_row and bt_row[1] is not None else 0
                        qs = bt_row[2] if bt_row and bt_row[2] is not None else 0
                        log_event(
                            "backtest_complete",
                            "frodex",
                            f"Backtested {spec_id} variant {vname}: PF {pf}, QS {qs}",
                            artifact_id=result_id,
                            pipeline="research_cycle",
                            step="backtest",
                        )
                    else:
                        print(f"Backtest failed for {vname}: {result.stderr[:200]}", file=sys.stderr)
                except Exception as e:
                    print(f"Backtest error for {vname}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Spec read failed for {f}: {e}", file=sys.stderr)

    conn.close()
    return backtested


def extract_lessons(rows):
    conn = sqlite3.connect(DB)
    lessons_added = 0

    for r in rows:
        if not r["total_trades"] or r["total_trades"] == 0:
            continue

        pf = r["profit_factor"] or 0
        dd = r["max_drawdown_pct"] or 0
        trades = r["total_trades"]
        qs = r["score_total"] or 0
        decision = r["score_decision"] or "?"
        spec_id = r["strategy_spec_id"] or "unknown"
        result_id = r["id"]

        existing = conn.execute("SELECT id FROM lessons WHERE backtest_result_id = ?", (result_id,)).fetchone()
        if existing:
            continue

        if pf < 0.5:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} has very low PF ({pf:.3f}). Entry logic may be anti-correlated with price movement."
            implication = "Consider inverting entry conditions or switching to a different indicator combination."
        elif pf < 1.0:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} is slightly losing (PF {pf:.3f}). Edge exists but costs eat it."
            implication = "Try tightening stops, widening TP, or adding a regime filter to trade only in favorable conditions."
        elif pf >= 1.0 and trades < 15:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} shows edge (PF {pf:.3f}) but too few trades ({trades}). Signal is too rare."
            implication = "Relax entry conditions slightly to increase trade frequency while monitoring if PF holds."
        elif pf >= 1.5:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']} shows strong edge (PF {pf:.3f}, {trades} trades). Worth iterating."
            implication = "Test across multiple assets for robustness. If PF holds, candidate for promotion."
        else:
            observation = f"Strategy {spec_id} on {r['asset']}/{r['timeframe']}: PF {pf:.3f}, DD {dd:.1f}%, {trades} trades, QScore {qs:.2f} ({decision})."
            implication = "Marginal edge. Consider parameter optimization or regime filtering."

        lesson_id = f"lesson_{result_id}"
        conn.execute(
            """
            INSERT OR IGNORE INTO lessons (
                id, ts_iso, backtest_result_id, strategy_spec_id, lesson_type,
                observation, implication, actionable, suggested_action, confidence
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                lesson_id,
                datetime.now(timezone.utc).isoformat(),
                result_id,
                spec_id,
                "backtest_analysis",
                observation,
                implication,
                1,
                implication,
                "medium",
            ),
        )
        lessons_added += 1

    conn.commit()
    conn.close()
    return lessons_added


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since-minutes", type=int, default=30)
    a = p.parse_args()

    new_backtests = backtest_new_specs()
    log_token_event("frodex", "research_cycle", f"cycle-postprocess run; new_backtests={new_backtests}")
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
        GROUP BY id
        ORDER BY ts_iso DESC
        """,
        (cutoff,),
    ).fetchall()

    total_rows = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    conn.close()

    if not rows:
        print(json.dumps({"status": "no_new_results", "since_minutes": a.since_minutes, "total_in_db": total_rows, "new_backtests": new_backtests}))
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
    dm_parts = split_message(dm_text, 4000)
    for part in dm_parts:
        send_tg_as(part, "dm", "oragorn")

    journal_text = ""
    if os.path.exists(JOURNAL_PATH):
        try:
            with open(JOURNAL_PATH, "r", encoding="utf-8") as f:
                journal_text = f.read().strip()
        except Exception:
            pass

    if journal_text:
        formatted = format_journal_html(journal_text)
        journal_parts = split_message(formatted, 4000)
        for i, part in enumerate(journal_parts):
            header = "🧙 <b>Quandalf's Journal</b>\n\n" if i == 0 else ""
            send_tg_as(header + part, "dm", "quandalf")

    log_event(
        "notification_sent",
        "oragorn",
        f"Sent {len(rows)} results + journal DM",
        pipeline="research_cycle",
        step="notify",
    )

    elapsed = round(time.time() - start_time, 1)

    best_pf = 0
    for r in rows:
        if r["profit_factor"] and r["profit_factor"] > best_pf:
            best_pf = r["profit_factor"]

    cycle_id = next_cycle_id()
    log_card = build_log_card(cycle_id, rows, elapsed, new_backtests)
    log_card_formatted = f"<pre>{log_card}</pre>"
    banner_path = os.path.join(r"C:\Users\Clamps\.openclaw\workspace-oragorn\assets\banners", "cooking.jpg")
    if os.path.exists(banner_path):
        subprocess.run(
            [
                sys.executable,
                TG_SCRIPT,
                "--message",
                log_card_formatted,
                "--channel",
                "log",
                "--bot",
                "logron",
                "--photo",
                banner_path,
            ],
            capture_output=True,
            text=True,
            timeout=15,
        )
    else:
        send_tg_as(log_card_formatted, "log", "logron")

    post_agent_message(
        "logron",
        "oragorn",
        "observation",
        f"Cycle postprocess: {len(rows)} backtests, best PF {best_pf:.3f}, best QS {best_qscore:.2f}, {sum(1 for r in rows if r['score_total'] and r['score_total'] >= 3.0)} promotions",
    )

    lessons_added = extract_lessons(rows)
    log_event(
        "lessons_extracted",
        "logron",
        f"Extracted {lessons_added} lessons",
        pipeline="research_cycle",
        step="postprocess",
    )

    print(
        json.dumps(
            {
                "status": "processed",
                "new_backtests": new_backtests,
                "new_results": len(rows),
                "total_in_db": total_rows,
                "best_qscore": best_qscore,
                "dm_sent": True,
                "log_card_sent": True,
                "journal_sent": bool(journal_text),
                "lessons_added": lessons_added,
            }
        )
    )


if __name__ == "__main__":
    main()
