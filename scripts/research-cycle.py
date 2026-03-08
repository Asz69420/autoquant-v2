#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = sys.executable
SKILLS_DIR = Path.home() / ".openclaw" / "skills"
BRIEFING_PATH = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
DB_PATH = ROOT / "db" / "autoquant.db"


def _run_skill(cmd: list[str]):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw = (p.stdout or "").strip()
        if not raw:
            return {"status": "empty", "stdout": "", "stderr": (p.stderr or "").strip()}
        try:
            return json.loads(raw)
        except Exception:
            return {"status": "non_json", "stdout": raw, "stderr": (p.stderr or "").strip()}
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "").strip()
        err = (e.stderr or "").strip()
        try:
            return json.loads(out) if out else {"status": "error", "returncode": e.returncode, "stderr": err}
        except Exception:
            return {"status": "error", "returncode": e.returncode, "stdout": out, "stderr": err}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _count_items(obj, key_hints: list[str]) -> int:
    if isinstance(obj, list):
        return len(obj)
    if isinstance(obj, dict):
        for k in key_hints:
            v = obj.get(k)
            if isinstance(v, list):
                return len(v)
        for v in obj.values():
            if isinstance(v, list):
                return len(v)
    return 0


def log_event(event_type, agent, message, severity="info", artifact_id=None, pipeline=None, step=None):
    try:
        conn = sqlite3.connect(str(DB_PATH))
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


def main() -> int:
    # Phase 1 only: Build briefing packet
    leaderboard = _run_skill([PY, str(SKILLS_DIR / "autoquant-leaderboard" / "query.py"), "--limit", "5"])
    kpi = _run_skill([PY, str(SKILLS_DIR / "autoquant-kpi" / "query.py"), "--days", "30"])
    lessons = _run_skill([PY, str(SKILLS_DIR / "autoquant-lessons" / "query.py"), "--limit", "5"])
    digest = _run_skill([PY, str(SKILLS_DIR / "autoquant-research-fetch" / "query.py"), "--limit", "5", "--unprocessed"])
    scan = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--scan"])
    funding = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--funding"])

    db_path = ROOT / "db" / "autoquant.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    recent_results = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               total_return_pct, avg_trade_pct, score_total, score_decision,
               score_edge, score_resilience, score_grade, score_flags,
               metrics, regime_metrics, period_start, period_end
        FROM backtest_results
        ORDER BY ts_iso DESC LIMIT 10
        """
    ).fetchall()
    conn.close()

    backtest_details = []
    for r in recent_results:
        detail = dict(r)
        if detail.get("metrics"):
            try:
                detail["metrics"] = json.loads(detail["metrics"])
            except Exception:
                pass
        if detail.get("regime_metrics"):
            try:
                detail["regime_metrics"] = json.loads(detail["regime_metrics"])
            except Exception:
                pass
        backtest_details.append(detail)

    now = datetime.now(timezone.utc)
    cycle_id = f"cycle_{now.strftime('%Y%m%d_%H%M%S')}"

    packet = {
        "ts_iso": now.isoformat(),
        "cycle_id": cycle_id,
        "leaderboard": leaderboard,
        "kpi": kpi,
        "recent_lessons": lessons,
        "research_digest": digest,
        "market_scan": scan,
        "funding_rates": funding,
        "recent_backtest_details": backtest_details,
    }

    BRIEFING_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEFING_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    top_opportunity = None
    if isinstance(scan, dict):
        top = scan.get("top_opportunities")
        if isinstance(top, list) and top:
            first = top[0]
            if isinstance(first, dict):
                top_opportunity = first.get("asset") or first.get("symbol") or first.get("name")

    leaderboard_count = _count_items(leaderboard, ["strategies", "items", "rows", "data"])
    lesson_count = _count_items(lessons, ["lessons", "items", "rows", "data"])
    research_count = _count_items(digest, ["items", "entries", "results", "data"])
    scan_count = _count_items(scan, ["top_opportunities", "opportunities", "items", "data"])

    summary = {
        "status": "briefing_ready",
        "cycle_id": cycle_id,
        "briefing_path": str(BRIEFING_PATH),
        "leaderboard_count": leaderboard_count,
        "lesson_count": lesson_count,
        "research_count": research_count,
        "scan_count": scan_count,
        "top_opportunity": top_opportunity,
    }

    log_event(
        "briefing_built",
        "oragorn",
        f"Cycle {cycle_id}: leaderboard={leaderboard_count}, lessons={lesson_count}, research={research_count}",
        pipeline="research_cycle",
        step="briefing",
    )

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
