#!/usr/bin/env python3
import argparse
import hashlib
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
BACKTESTER = os.path.join(ROOT, "scripts", "walk_forward_engine.py")
BALROG = r"C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\balrog-validate.py"
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
BOARD_PATH = os.path.join(ROOT, "data", "state", "agent_messages.json")
CARD_STATE_PATH = os.path.join(ROOT, "data", "state", "cycle_postprocess_card_state.json")
CURRENT_CYCLE_SPECS_PATH = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
CURRENT_CYCLE_STATUS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
CURRENT_CYCLE_METRICS_PATH = os.path.join(ROOT, "data", "state", "current_cycle_metrics.json")
RUN_STATE_PATH = os.path.join(ROOT, "data", "state", "research_cycle_started_at.json")

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
        proc = subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel, "--bot", bot],
            capture_output=True,
            text=True,
            timeout=15,
        )
        return proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")
    except Exception as e:
        print(f"TG send failed: {e}", file=sys.stderr)
        return False


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


def load_json_file(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def load_run_state():
    state = load_json_file(RUN_STATE_PATH)
    return state if isinstance(state, dict) else {}


def persist_run_state(state):
    os.makedirs(os.path.dirname(RUN_STATE_PATH), exist_ok=True)
    with open(RUN_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def resolve_cycle_id(run_state=None):
    run_state = run_state or load_run_state()
    run_cycle_id = int(run_state.get("cycle_id", 0) or 0)
    if run_cycle_id > 0:
        return run_cycle_id

    manifest = load_json_file(CURRENT_CYCLE_SPECS_PATH)
    manifest_cycle_id = int(manifest.get("cycle_id", 0) or 0)
    if manifest_cycle_id > 0:
        return manifest_cycle_id

    counter_path = os.path.join(ROOT, "data", "state", "cycle_counter.json")
    try:
        with open(counter_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("last_cycle_id", 0))
    except Exception:
        return 0


def observe_run_state(cycle_id=None):
    state = load_run_state()
    now_epoch = time.time()
    now_iso = datetime.now(timezone.utc).isoformat()
    state["reporting_last_seen_at_epoch"] = now_epoch
    state["reporting_last_seen_at_iso"] = now_iso
    if cycle_id and int(state.get("cycle_id", 0) or 0) <= 0:
        state["cycle_id"] = int(cycle_id)
    persist_run_state(state)
    return state


def finalize_run_state(cycle_id):
    state = observe_run_state(cycle_id)
    if int(state.get("cycle_id", 0) or 0) != int(cycle_id):
        return state

    started = float(state.get("started_at_epoch", 0) or 0)
    if started > 0 and not state.get("ended_at_epoch"):
        ended = time.time()
        state["status"] = "completed"
        state["ended_at_epoch"] = ended
        state["ended_at_iso"] = datetime.now(timezone.utc).isoformat()
        state["run_elapsed_seconds"] = round(max(0, ended - started), 1)
        persist_run_state(state)
    return state


def compute_timing_metrics(run_state):
    started = float(run_state.get("started_at_epoch", 0) or 0)
    ended = float(run_state.get("ended_at_epoch", 0) or 0)
    seen = float(run_state.get("reporting_last_seen_at_epoch", 0) or 0)

    run_elapsed = float(run_state.get("run_elapsed_seconds", 0) or 0)
    if run_elapsed <= 0 and started > 0:
        anchor = ended if ended > 0 else time.time()
        run_elapsed = round(max(0, anchor - started), 1)

    report_delay = 0.0
    if started > 0 and ended > 0 and seen > ended:
        report_delay = round(max(0, seen - ended), 1)

    return {
        "run_elapsed_seconds": run_elapsed,
        "report_delay_seconds": report_delay,
        "is_completed": ended > 0,
        "started_at_epoch": started,
        "ended_at_epoch": ended,
    }


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def normalize_spec_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    base = os.path.basename(text)
    suffix = ".strategy_spec.json"
    if base.endswith(suffix):
        base = base[: -len(suffix)]
    return base


def build_cycle_metrics(cycle_id, rows, elapsed_seconds, backtest_count, run_state=None):
    rows_dict = [dict(r) if not isinstance(r, dict) else r for r in rows]
    cycle_specs = load_json_file(CURRENT_CYCLE_SPECS_PATH)
    cycle_status = load_json_file(CURRENT_CYCLE_STATUS_PATH)
    run_state = run_state or load_run_state()
    timing = compute_timing_metrics(run_state)

    manifest_cycle_id = safe_int(cycle_specs.get("cycle_id", 0) or 0)
    status_cycle_id = safe_int(cycle_status.get("cycle_id", 0) or 0)
    status_matches_cycle = status_cycle_id == int(cycle_id) and status_cycle_id != 0

    manifest_matches_cycle = manifest_cycle_id == int(cycle_id) and manifest_cycle_id != 0
    spec_paths = cycle_specs.get("spec_paths") or [] if manifest_matches_cycle else []
    normalized_manifest_spec_ids = {normalize_spec_id(path) for path in spec_paths if normalize_spec_id(path)}
    row_spec_ids = {normalize_spec_id(r.get("strategy_spec_id")) for r in rows_dict if normalize_spec_id(r.get("strategy_spec_id"))}

    specs_written = int(cycle_specs.get("spec_count", 0) or 0) if manifest_matches_cycle else 0
    if not specs_written and row_spec_ids:
        specs_written = len(row_spec_ids)

    new_families = len(cycle_status.get("new_families", [])) if status_matches_cycle else 0
    iterated_families = len(cycle_status.get("iterated_families", [])) if status_matches_cycle else 0
    active = new_families + iterated_families
    abandoned = len(cycle_status.get("abandoned_families", [])) if status_matches_cycle else 0

    promotions = sum(1 for r in rows_dict if r.get("score_total") and r["score_total"] >= 3.0)
    best_qs = max((r.get("score_total", 0) or 0 for r in rows_dict), default=0)

    return {
        "cycle_id": int(cycle_id),
        "manifest_cycle_id": manifest_cycle_id,
        "status_cycle_id": status_cycle_id,
        "status_matches_cycle": status_matches_cycle,
        "spec_paths": spec_paths,
        "spec_ids": sorted(normalized_manifest_spec_ids or row_spec_ids),
        "specs_written": specs_written,
        "new_families": new_families,
        "iterated_families": iterated_families,
        "active_families": active,
        "backtests": backtest_count,
        "promotions": promotions,
        "abandoned_families": abandoned,
        "best_qscore": best_qs,
        "elapsed_seconds": elapsed_seconds,
        "run_elapsed_seconds": timing["run_elapsed_seconds"],
        "report_delay_seconds": timing["report_delay_seconds"],
        "is_completed": timing["is_completed"],
        "started_at_epoch": timing["started_at_epoch"],
        "ended_at_epoch": timing["ended_at_epoch"],
    }


def build_log_card(cycle_id, rows, elapsed_seconds, backtest_count, run_state=None):
    metrics = build_cycle_metrics(cycle_id, rows, elapsed_seconds, backtest_count, run_state=run_state)
    run_elapsed = metrics.get("run_elapsed_seconds", elapsed_seconds)
    elapsed_str = f"{int(run_elapsed // 60)}m {int(run_elapsed % 60)}s" if run_elapsed else "?"

    lines = []
    lines.append("🍳 Cooking")
    header_status = '✅' if metrics['promotions'] > 0 else '⚠️'
    lines.append(f"{header_status} | ▶ {elapsed_str} run | 🆔 {cycle_id}")
    lines.append("○──activity──────────────────")
    lines.append(f"New strategies: {metrics['specs_written']}")
    lines.append(f"New families: {metrics['new_families']}")
    lines.append(f"Active families: {metrics['active_families']}")
    lines.append(f"Backtests: {metrics['backtests']}")
    lines.append(f"Promotions: {metrics['promotions']}")
    lines.append(f"Abandoned: {metrics['abandoned_families']}")
    if metrics.get("is_completed"):
        lines.append(f"Report delay: +{int(metrics['report_delay_seconds'] // 60)}m {int(metrics['report_delay_seconds'] % 60)}s")
    lines.append("○──note──────────────────────")
    if metrics['promotions'] > 0:
        lines.append(f"🏆 {metrics['promotions']} promotion(s)! Best QS: {metrics['best_qscore']:.2f}")
    elif metrics['best_qscore'] > 0:
        lines.append(f"Best QS: {metrics['best_qscore']:.2f}. Iterating.")
    else:
        lines.append("No strong results yet. Quandalf refining.")
    if metrics.get("is_completed") and metrics.get("report_delay_seconds", 0) > 0:
        lines.append("Run already completed; this was a later report-only pass.")

    return "\n".join(lines), metrics


def count_backtests(rows):
    seen_ids = set()
    for row in rows:
        if isinstance(row, dict):
            row_id = row.get("id")
        else:
            row_id = row["id"]
        if row_id:
            seen_ids.add(str(row_id))
    return len(seen_ids)


def write_cycle_metrics(metrics):
    try:
        os.makedirs(os.path.dirname(CURRENT_CYCLE_METRICS_PATH), exist_ok=True)
        with open(CURRENT_CYCLE_METRICS_PATH, "w", encoding="utf-8") as f:
            json.dump(metrics, f, indent=2)
    except Exception:
        pass


def should_send_card(cycle_id, card_text):
    fingerprint = hashlib.sha256(card_text.encode("utf-8")).hexdigest()
    state = {}
    try:
        if os.path.exists(CARD_STATE_PATH):
            with open(CARD_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
    except Exception:
        state = {}

    last = state.get("last_card") if isinstance(state, dict) else None
    if isinstance(last, dict) and int(last.get("cycle_id", -1) or -1) == int(cycle_id) and last.get("fingerprint") == fingerprint:
        return False, fingerprint
    return True, fingerprint


def remember_card_send(cycle_id, card_text, fingerprint):
    os.makedirs(os.path.dirname(CARD_STATE_PATH), exist_ok=True)
    state = {
        "last_card": {
            "cycle_id": int(cycle_id),
            "fingerprint": fingerprint,
            "sent_at_iso": datetime.now(timezone.utc).isoformat(),
            "preview": card_text.splitlines(),
        }
    }
    with open(CARD_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def send_log_card(cycle_id, log_card):
    should_send, fingerprint = should_send_card(cycle_id, log_card)
    if not should_send:
        return False

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

    remember_card_send(cycle_id, log_card, fingerprint)
    return True


def read_text_best_effort(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin-1"]
    for encoding in encodings:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except Exception:
        return ""


def format_journal_html(raw_text):
    import html
    import re

    text = html.escape(raw_text)
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
        file_spec_id = f.replace(".strategy_spec.json", "")

        try:
            with open(spec_path, "r", encoding="utf-8") as fh:
                spec = json.load(fh)
            explicit_spec_id = (spec.get("id") or "").strip()
            spec_ids = [file_spec_id]
            if explicit_spec_id and explicit_spec_id not in spec_ids:
                spec_ids.append(explicit_spec_id)

            asset = str(spec.get("asset", "ETH")).strip()
            timeframe = str(spec.get("timeframe", "4h")).strip()
            variants = spec.get("variants", [])
            if not variants:
                continue

            placeholders = ",".join("?" * len(spec_ids))
            existing_for_spec = conn.execute(
                f"SELECT COUNT(*) FROM backtest_results WHERE strategy_spec_id IN ({placeholders})",
                tuple(spec_ids),
            ).fetchone()[0]
            if existing_for_spec > 0:
                continue

            seen_variant_names = set()
            for v in variants:
                vname = str(v.get("name", "default")).strip()
                if not vname or vname in seen_variant_names:
                    continue
                seen_variant_names.add(vname)

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
                            log_event("balrog_block", "balrog", f"Blocked spec {file_spec_id}: {errors}", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                        except Exception:
                            print(f"Balrog BLOCKED {f}: validation failed", file=sys.stderr)
                            log_event("balrog_block", "balrog", f"Blocked spec {file_spec_id}: validation failed", severity="warn", artifact_id=file_spec_id, pipeline="research_cycle", step="validation")
                        continue

                    existing_variant = conn.execute(
                        f"""
                        SELECT COUNT(*) FROM backtest_results
                        WHERE strategy_spec_id IN ({placeholders})
                          AND lower(variant_id) = lower(?)
                          AND lower(asset) = lower(?)
                          AND lower(timeframe) = lower(?)
                        """,
                        tuple(spec_ids + [vname, asset, timeframe]),
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
                            f"""
                            SELECT id, profit_factor, score_total
                            FROM backtest_results
                            WHERE strategy_spec_id IN ({placeholders})
                              AND lower(variant_id) = lower(?)
                              AND lower(asset) = lower(?)
                              AND lower(timeframe) = lower(?)
                            ORDER BY ts_iso DESC LIMIT 1
                            """,
                            tuple(spec_ids + [vname, asset, timeframe]),
                        ).fetchone()
                        result_id = bt_row[0] if bt_row else None
                        pf = bt_row[1] if bt_row and bt_row[1] is not None else 0
                        qs = bt_row[2] if bt_row and bt_row[2] is not None else 0
                        log_event(
                            "backtest_complete",
                            "frodex",
                            f"Backtested {file_spec_id} variant {vname}: PF {pf}, QS {qs}",
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
    p.add_argument("--send-card-only", action="store_true")
    p.add_argument("--backfill-unbacktested", action="store_true")
    a = p.parse_args()

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=a.since_minutes)).isoformat()

    if a.send_card_only:
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

        run_state = observe_run_state()
        cycle_id = resolve_cycle_id(run_state)
        run_state = observe_run_state(cycle_id)
        timing = compute_timing_metrics(run_state)
        elapsed_seconds = timing["run_elapsed_seconds"]

        backtest_count = count_backtests(rows)
        log_card, metrics = build_log_card(cycle_id, rows, elapsed_seconds, backtest_count, run_state=run_state)
        write_cycle_metrics(metrics)
        sent = send_log_card(cycle_id, log_card)

        print(json.dumps({"status": "card_sent" if sent else "card_skipped_duplicate", "since_minutes": a.since_minutes, "cycle_id": cycle_id, "rows": len(rows), "backtests": backtest_count, "total_in_db": total_rows, "card_metrics": metrics}))
        return

    new_backtests = backtest_new_specs() if a.backfill_unbacktested else 0
    log_token_event("frodex", "research_cycle", f"cycle-postprocess run; new_backtests={new_backtests}")
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
        run_state = finalize_run_state(resolve_cycle_id())
        print(json.dumps({"status": "no_new_results", "since_minutes": a.since_minutes, "total_in_db": total_rows, "new_backtests": new_backtests, "cycle_id": resolve_cycle_id(run_state), "run_state": run_state}))
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
        send_tg_as(part, "hades", "oragorn")

    journal_text = ""
    if os.path.exists(JOURNAL_PATH):
        journal_text = read_text_best_effort(JOURNAL_PATH).strip()

    journal_sent = False
    if journal_text:
        formatted = format_journal_html(journal_text)
        journal_parts = split_message(formatted, 4000)
        send_results = []
        for i, part in enumerate(journal_parts):
            header = "🧙 <b>Quandalf's Journal</b>\n\n" if i == 0 else ""
            send_results.append(send_tg_as(header + part, "hades", "quandalf"))
        journal_sent = all(send_results) if send_results else False

    log_event(
        "notification_sent",
        "oragorn",
        f"Sent {len(rows)} result updates to Hades and a cooking card to log",
        pipeline="research_cycle",
        step="notify",
    )

    run_state = finalize_run_state(resolve_cycle_id())
    cycle_id = resolve_cycle_id(run_state)
    run_state = finalize_run_state(cycle_id)
    timing = compute_timing_metrics(run_state)
    elapsed = timing["run_elapsed_seconds"] or round(time.time() - start_time, 1)

    best_pf = 0
    for r in rows:
        if r["profit_factor"] and r["profit_factor"] > best_pf:
            best_pf = r["profit_factor"]

    backtest_count = count_backtests(rows)
    log_card, metrics = build_log_card(cycle_id, rows, elapsed, backtest_count, run_state=run_state)
    write_cycle_metrics(metrics)
    log_card_sent = send_log_card(cycle_id, log_card)

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
                "card_backtests": backtest_count,
                "new_results": len(rows),
                "total_in_db": total_rows,
                "best_qscore": best_qscore,
                "dm_sent": True,
                "log_card_sent": log_card_sent,
                "journal_sent": journal_sent,
                "lessons_added": lessons_added,
                "card_metrics": metrics,
            }
        )
    )


if __name__ == "__main__":
    main()
