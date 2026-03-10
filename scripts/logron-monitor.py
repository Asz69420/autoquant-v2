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
HEALTH_SEND_STATE_PATH = os.path.join(ROOT, "data", "state", "health_send_state.json")
HEALTH_COOLDOWN_SECONDS = 24 * 3600  # daily-only resend for identical health state
INTEGRITY_SCRIPT = os.path.join(ROOT, "scripts", "db_integrity_check.py")
HADES_CHAT_ID = "-5133891354"


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


def send_hades(message, bot="logron"):
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", "hades", "--bot", bot, "--chat-id", HADES_CHAT_ID],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        pass


def send_critical_escalation(message):
    send_hades(message, bot="logron")
    send_alert(message)
    try:
        subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", message, "--channel", "dm", "--bot", "oragorn", "--chat-id", "1801759510"],
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

    recent = board.get("messages", [])[-20:]
    now_dt = datetime.now(timezone.utc)
    for item in reversed(recent):
        if item.get("from") != from_agent or item.get("to") != to_agent or item.get("type") != msg_type or item.get("message") != message:
            continue
        try:
            ts = datetime.fromisoformat(str(item.get("ts_iso")).replace("Z", "+00:00"))
        except Exception:
            ts = None
        if ts and (now_dt - ts).total_seconds() < 6 * 3600:
            return

    entry = {
        "ts_iso": now_dt.isoformat(),
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
                # Gateway log is structured JSON with logLevelName field.
                # Only count actual ERROR-level entries, not data lines that
                # happen to contain the word "error" or "fail" (e.g.
                # score_decision='fail').
                if '"logLevelName":"ERROR"' in line:
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

    # DB integrity checks — failures must be loud, not silent
    try:
        proc = subprocess.run([sys.executable, INTEGRITY_SCRIPT], capture_output=True, text=True, timeout=20)
        integrity = json.loads((proc.stdout or "{}").strip() or "{}") if proc.returncode == 0 else {"status": "error", "stdout": proc.stdout, "stderr": proc.stderr}
    except Exception as e:
        integrity = {"status": "error", "error": str(e)}
    stats["integrity"] = integrity
    if integrity.get("status") == "fail":
        for issue in integrity.get("issues", []):
            issues.append(f"Integrity: {issue}")
    elif integrity.get("status") == "error":
        issues.append("Integrity check failed to run")

    if len(issues) == 0:
        status = "ok"
    elif any(("stalled" in i or "missing" in i or "Integrity:" in i or "failed to run" in i) for i in issues):
        status = "fail"
    else:
        status = "warn"

    return status, stats, issues


def seed_known_fixes_if_empty():
    conn = sqlite3.connect(DB)
    count = conn.execute("SELECT COUNT(*) FROM known_fixes").fetchone()[0]
    if count == 0:
        seeds = [
            ("stale briefing", "python " + os.path.join(ROOT, "scripts", "research-cycle.py"), "auto"),
            ("journal missing", "echo 'No auto-fix for missing journal — Quandalf cron may need manual trigger'", "manual"),
            ("workspace large", "python " + os.path.join(ROOT, "scripts", "data-cleanup.py"), "auto"),
        ]
        for pattern, action, fix_type in seeds:
            conn.execute(
                "INSERT INTO known_fixes (ts_iso_created, error_pattern, fix_action, fix_type) VALUES (?, ?, ?, ?)",
                (datetime.now(timezone.utc).isoformat(), pattern, action, fix_type),
            )
        conn.commit()
    conn.close()


def attempt_auto_fixes(issues):
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    fixes_applied = []

    for issue in issues:
        matches = conn.execute(
            """
            SELECT id, error_pattern, fix_action, fix_type, times_applied
            FROM known_fixes
            WHERE active = 1 AND ? LIKE '%' || error_pattern || '%'
            """,
            (issue,),
        ).fetchall()

        for fix in matches:
            fix_action = fix["fix_action"]
            try:
                result = subprocess.run(fix_action, shell=True, capture_output=True, text=True, timeout=30, cwd=ROOT)
                success = result.returncode == 0
                conn.execute(
                    """
                    UPDATE known_fixes
                    SET times_applied = times_applied + 1,
                        last_applied = ?,
                        success_rate = CASE
                            WHEN ? = 1 THEN COALESCE(success_rate, 0) * 0.9 + 0.1
                            ELSE COALESCE(success_rate, 1.0) * 0.9
                        END
                    WHERE id = ?
                    """,
                    (datetime.now(timezone.utc).isoformat(), 1 if success else 0, fix["id"]),
                )
                conn.commit()
                fix_row = {"pattern": fix["error_pattern"], "action": fix_action, "success": success}
                fixes_applied.append(fix_row)
            except Exception as e:
                fix_row = {"pattern": fix["error_pattern"], "action": fix_action, "success": False, "error": str(e)}
                fixes_applied.append(fix_row)

    conn.close()
    return fixes_applied


def build_health_card(status, stats, issues, auto_fixes):
    status_emoji = {"ok": "✅", "warn": "⚠️", "fail": "❌"}.get(status, "❓")
    lines = []
    lines.append("👁️ Health Check")
    lines.append(f"{status_emoji} | System {'Healthy' if status == 'ok' else 'Degraded' if status == 'warn' else 'Critical'}")
    lines.append("○────────stats────────")
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
        lines.append("○───────autofix───────")
        for fix in auto_fixes:
            pattern = fix.get("pattern", "?")
            success = "ok" if fix.get("success") else "fail"
            lines.append(f"🛠️ {pattern} ({success})")

    if issues:
        lines.append("○────────issues────────")
        for i in issues:
            lines.append(f"⚠️ {i}")
    else:
        lines.append("○────────note─────────")
        lines.append("All systems nominal.")

    return "\n".join(lines)


def _load_health_send_state():
    try:
        if os.path.exists(HEALTH_SEND_STATE_PATH):
            with open(HEALTH_SEND_STATE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _save_health_send_state(status, issues):
    os.makedirs(os.path.dirname(HEALTH_SEND_STATE_PATH), exist_ok=True)
    prev = _load_health_send_state()
    fail_streak = int(prev.get("consecutive_fail_count") or 0)
    if status == "fail":
        fail_streak += 1
    else:
        fail_streak = 0
    with open(HEALTH_SEND_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "last_status": status,
            "last_issues": sorted(issues),
            "sent_at": time.time(),
            "sent_at_iso": datetime.now(timezone.utc).isoformat(),
            "consecutive_fail_count": fail_streak,
        }, f, indent=2)


def _should_send_health_card(status, issues):
    prev = _load_health_send_state()
    if not prev.get("sent_at"):
        return True  # first run
    # Always send on status change (e.g. ok -> warn, warn -> fail)
    if prev.get("last_status") != status:
        return True
    # Always send on issue change
    if sorted(issues) != sorted(prev.get("last_issues", [])):
        return True
    # Same status+issues: enforce cooldown
    elapsed = time.time() - prev["sent_at"]
    if elapsed >= HEALTH_COOLDOWN_SECONDS:
        return True
    return False


def main():
    seed_known_fixes_if_empty()

    status, stats, issues = check_health()
    log_event("health_check", "logron", f"Status: {status}, issues: {len(issues)}", pipeline="health", step="check")

    auto_fixes = attempt_auto_fixes(issues)
    for fx in auto_fixes:
        log_event(
            "auto_fix",
            "logron",
            f"Applied fix for: {fx.get('pattern', '?')}, success: {fx.get('success', False)}",
            severity="info" if fx.get("success") else "warn",
            pipeline="health",
            step="autofix",
        )

    # Recompute unresolved issues after auto-fix attempts
    unresolved = []
    for issue in issues:
        matched = any((fx.get("pattern") or "").lower() in issue.lower() for fx in auto_fixes)
        if not matched:
            unresolved.append(issue)
    issues = unresolved

    if not issues and status != "ok":
        status = "warn" if auto_fixes else "ok"

    card = build_health_card(status, stats, issues, auto_fixes)

    if _should_send_health_card(status, issues):
        banner = os.path.join(BANNERS, "logron.jpg")
        send_log(f"<pre>{card}</pre>", photo=banner if os.path.exists(banner) else None)
        prev_state = _load_health_send_state()
        prior_fail_streak = int(prev_state.get("consecutive_fail_count") or 0)
        _save_health_send_state(status, issues)

        if status == "fail":
            alert = "🚨 <b>AutoQuant Alert</b>\n\nLogron detected critical issues:\n"
            for i in issues:
                alert += f"• {i}\n"
            if auto_fixes:
                alert += "\nAuto-fixes applied:\n"
                for fx in auto_fixes:
                    alert += f"• {fx.get('pattern', '?')} (success={fx.get('success', False)})\n"
            alert += "\nDetails sent to Hades."
            send_hades(alert, bot="logron")
            send_alert(alert)
            if prior_fail_streak >= 1:
                send_critical_escalation("🔥 <b>Repeated critical AutoQuant failure</b>\n\nThis is not the first consecutive failed health check. Review Hades and Oragorn alerts now.")

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
