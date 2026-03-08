#!/usr/bin/env python3
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
BANNERS = os.path.join(ROOT, "assets", "banners")
GATEWAY_LOG_DIR = r"C:\tmp\openclaw"
BOARD_PATH = os.path.join(ROOT, "data", "state", "agent_messages.json")


def send_log(message, bot="logron", channel="log", photo=None):
    cmd = [sys.executable, TG_SCRIPT, "--message", message, "--channel", channel, "--bot", bot]
    if photo and os.path.exists(photo):
        cmd.extend(["--photo", photo])
    try:
        subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except Exception:
        pass


def send_alert(message):
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", "dm", "--bot", "oragorn"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        pass


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


def table_exists(conn, table_name):
    row = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone()
    return row is not None


def safe_count(conn, table_name):
    if not table_exists(conn, table_name):
        return 0
    return conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]


def count_backtests_24h(conn, cutoff_24h):
    if not table_exists(conn, "backtest_results"):
        return 0
    return conn.execute(
        "SELECT COUNT(*) FROM backtest_results WHERE ts_iso >= ?",
        (cutoff_24h,),
    ).fetchone()[0]


def count_strategy_specs_24h(cutoff_epoch):
    specs_dir = os.path.join(ROOT, "artifacts", "strategy_specs")
    if not os.path.exists(specs_dir):
        return 0

    count = 0
    for name in os.listdir(specs_dir):
        if not name.endswith(".strategy_spec.json"):
            continue
        path = os.path.join(specs_dir, name)
        try:
            if os.path.getmtime(path) >= cutoff_epoch:
                count += 1
        except OSError:
            continue
    return count


def latest_gateway_log_path(now):
    candidates = [
        os.path.join(GATEWAY_LOG_DIR, f"openclaw-{now.strftime('%Y-%m-%d')}.log"),
    ]
    existing = [p for p in candidates if os.path.exists(p)]
    if existing:
        return existing[0]

    try:
        logs = sorted(
            [p for p in Path(GATEWAY_LOG_DIR).glob("*.log") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return str(logs[0]) if logs else None
    except Exception:
        return None


def count_gateway_errors(now):
    gateway_errors = 0
    log_path = latest_gateway_log_path(now)
    if not log_path:
        return gateway_errors

    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                uline = line.upper()
                if "ERROR" in uline or "FAIL" in uline:
                    gateway_errors += 1
    except Exception:
        pass

    return gateway_errors


def workspace_size_mb(paths):
    total_bytes = 0
    for p in paths:
        if not os.path.exists(p):
            continue
        for dirpath, _, filenames in os.walk(p):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_bytes += os.path.getsize(fp)
                except OSError:
                    continue
    return round(total_bytes / (1024 * 1024), 1)


def check_health():
    now = datetime.now(timezone.utc)
    cutoff_24h_dt = now - timedelta(hours=24)
    cutoff_24h_iso = cutoff_24h_dt.isoformat()
    cutoff_24h_epoch = cutoff_24h_dt.timestamp()

    issues = []
    stats = {}

    conn = sqlite3.connect(DB)

    backtests_24h = count_backtests_24h(conn, cutoff_24h_iso)
    stats["backtests_24h"] = backtests_24h

    total_backtests = safe_count(conn, "backtest_results")
    stats["total_backtests"] = total_backtests

    if table_exists(conn, "backtest_results"):
        passed = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE score_total >= 1.0").fetchone()[0]
        promoted = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE score_total >= 3.0").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE score_decision = 'fail'").fetchone()[0]
    else:
        passed = promoted = failed = 0

    stats["passed"] = passed
    stats["promoted"] = promoted
    stats["failed"] = failed

    lessons = safe_count(conn, "lessons")
    stats["lessons"] = lessons

    known_fixes_active = 0
    if table_exists(conn, "known_fixes"):
        known_fixes_active = conn.execute("SELECT COUNT(*) FROM known_fixes WHERE active = 1").fetchone()[0]
    stats["known_fixes"] = known_fixes_active

    table_counts = {}
    for (table_name,) in conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
        try:
            table_counts[table_name] = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
        except Exception:
            table_counts[table_name] = -1
    stats["table_counts"] = table_counts

    conn.close()

    strategy_specs_24h = count_strategy_specs_24h(cutoff_24h_epoch)
    stats["strategy_specs_24h"] = strategy_specs_24h

    journal_path = os.path.join(ROOT, "agents", "quandalf", "memory", "latest_journal.md")
    if os.path.exists(journal_path):
        journal_age_hrs = (time.time() - os.path.getmtime(journal_path)) / 3600
        stats["journal_age_hrs"] = round(journal_age_hrs, 1)
        if journal_age_hrs > 24:
            issues.append("Quandalf journal stale (>24h)")
    else:
        issues.append("Quandalf journal missing")
        stats["journal_age_hrs"] = -1

    briefing_path = os.path.join(ROOT, "agents", "quandalf", "memory", "briefing_packet.json")
    if os.path.exists(briefing_path):
        briefing_age_hrs = (time.time() - os.path.getmtime(briefing_path)) / 3600
        stats["briefing_age_hrs"] = round(briefing_age_hrs, 1)
        if briefing_age_hrs > 24:
            issues.append("Briefing packet stale (>24h)")
    else:
        issues.append("Briefing packet missing")
        stats["briefing_age_hrs"] = -1

    gateway_errors = count_gateway_errors(now)
    stats["gateway_errors"] = gateway_errors
    if gateway_errors > 20:
        issues.append(f"High gateway errors ({gateway_errors})")

    candles_dir = os.path.join(ROOT, "data", "candles")
    artifacts_dir = os.path.join(ROOT, "artifacts")
    ws_size = workspace_size_mb([candles_dir, artifacts_dir])
    stats["workspace_mb"] = ws_size
    if ws_size > 10_000:
        issues.append(f"Workspace large ({ws_size}MB)")

    if backtests_24h == 0:
        issues.append("No backtests in 24h — pipeline may be stalled")
    if strategy_specs_24h == 0:
        issues.append("No strategy specs in 24h")

    if len(issues) == 0:
        status = "ok"
    elif any("stalled" in i or "missing" in i for i in issues):
        status = "fail"
    else:
        status = "warn"

    return status, stats, issues


def attempt_auto_resolve(issues):
    """Placeholder deterministic auto-fix hooks keyed by known issue phrases."""
    applied = []
    remaining = []

    for issue in issues:
        # Add deterministic auto-fixes here when known patterns are formalized.
        # For now, we only classify and pass through.
        remaining.append(issue)

    return applied, remaining


def build_health_card(status, stats, issues, auto_fixes):
    status_emoji = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "❓")
    lines = []
    lines.append("👁️ Health Check")
    lines.append(f"{status_emoji} | System {'Healthy' if status == 'ok' else 'Degraded' if status == 'warn' else 'Critical'}")
    lines.append("○──stats───────────────────────")
    lines.append(f"Backtests (24h): {stats.get('backtests_24h', 0)}")
    lines.append(f"Specs (24h): {stats.get('strategy_specs_24h', 0)}")
    lines.append(f"Total backtests: {stats.get('total_backtests', 0)}")
    lines.append(f"Passed: {stats.get('passed', 0)} | Failed: {stats.get('failed', 0)} | Promoted: {stats.get('promoted', 0)}")
    lines.append(f"Lessons: {stats.get('lessons', 0)}")
    lines.append(f"Journal age: {stats.get('journal_age_hrs', '?')}h")
    lines.append(f"Briefing age: {stats.get('briefing_age_hrs', '?')}h")
    lines.append(f"Workspace: {stats.get('workspace_mb', '?')}MB")
    lines.append(f"GW errors: {stats.get('gateway_errors', 0)}")

    if auto_fixes:
        lines.append("○──autofix──────────────────────")
        for fix in auto_fixes:
            lines.append(f"🛠️ {fix}")

    if issues:
        lines.append("○──issues──────────────────────")
        for i in issues:
            lines.append(f"⚠️ {i}")
    else:
        lines.append("○──note────────────────────────")
        lines.append("All systems nominal.")

    return "\n".join(lines)


def main():
    status, stats, issues = check_health()
    auto_fixes, issues = attempt_auto_resolve(issues)

    # Recompute final status if all issues were auto-resolved
    if not issues and status != "ok":
        status = "warn" if auto_fixes else "ok"

    card = build_health_card(status, stats, issues, auto_fixes)
    banner = os.path.join(BANNERS, "logron.jpg")
    send_log(f"<pre>{card}</pre>", photo=banner if os.path.exists(banner) else None)

    if status == "fail":
        alert = "🚨 <b>AutoQuant Alert</b>\n\nLogron detected critical issues:\n"
        for i in issues:
            alert += f"• {i}\n"
        if auto_fixes:
            alert += "\nAuto-fixes applied:\n"
            for fx in auto_fixes:
                alert += f"• {fx}\n"
        alert += "\nCheck the log channel for details."
        send_alert(alert)

    if issues:
        post_agent_message(
            "logron",
            "oragorn",
            "observation",
            f"Health check: {status}. Issues: {'; '.join(issues)}",
        )

    print(json.dumps({"status": status, "stats": stats, "issues": issues, "auto_fixes": auto_fixes}))


if __name__ == "__main__":
    main()
