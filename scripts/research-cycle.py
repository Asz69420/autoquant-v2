#!/usr/bin/env python3
from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = sys.executable
SKILLS_DIR = Path.home() / ".openclaw" / "skills"
BRIEFING_PATH = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
DB_PATH = ROOT / "db" / "autoquant.db"
CANDLES_DIR = ROOT / "data" / "candles"


def _run_skill(cmd: list[str]):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=120)
        raw = (p.stdout or "").strip()
        if not raw:
            return {"status": "empty", "stdout": "", "stderr": (p.stderr or "").strip()}
        try:
            return json.loads(raw)
        except Exception:
            return {"status": "non_json", "stdout": raw, "stderr": (p.stderr or "").strip()}
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "stdout": "", "stderr": "skill timed out after 120s"}
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


def read_cycle_counter():
    """Read current cycle_id from counter without incrementing.
    Only cycle-start.py should ever increment the counter."""
    counter_path = ROOT / "data" / "state" / "cycle_counter.json"
    try:
        data = json.loads(counter_path.read_text(encoding="utf-8"))
        return int(data.get("last_cycle_id", 0))
    except Exception:
        return 0


def load_cycle_run_state() -> dict:
    path = ROOT / "data" / "state" / "research_cycle_started_at.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def sync_current_cycle_status(cycle_id: int) -> None:
    status_path = ROOT / "agents" / "quandalf" / "memory" / "current_cycle_status.json"
    status = {}
    try:
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            if not isinstance(status, dict):
                status = {}
    except Exception:
        status = {}
    if int(status.get("cycle_id", 0) or 0) != int(cycle_id):
        status["cycle_id"] = int(cycle_id)
        status["mode"] = "pending"
        status["research_direction"] = "pending"
        status["target_asset"] = None
        status["target_timeframe"] = None
        status["exploration_targets"] = {}
        status["iterate_target"] = None
        status["specific_family_to_iterate"] = None
        status["spec_paths"] = []
        status["specs_produced"] = 0
        status["new_families"] = []
        status["iterated_families"] = []
        status["abandoned_families"] = []
        status["next_cycle_focus"] = "pending"
        status["rationale"] = "pending"
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")


def discover_backtest_universe() -> dict:
    assets_by_timeframe: dict[str, list[str]] = defaultdict(list)
    timeframes_by_asset: dict[str, list[str]] = defaultdict(list)

    if not CANDLES_DIR.exists():
        return {
            "assets": [],
            "timeframes": [],
            "assets_by_timeframe": {},
            "timeframes_by_asset": {},
            "pairs": [],
        }

    for path in sorted(CANDLES_DIR.glob("*.csv")):
        stem = path.stem
        if "_" not in stem:
            continue
        asset, timeframe = stem.rsplit("_", 1)
        asset = asset.strip().upper()
        timeframe = timeframe.strip()
        if not asset or not timeframe:
            continue
        if asset not in assets_by_timeframe[timeframe]:
            assets_by_timeframe[timeframe].append(asset)
        if timeframe not in timeframes_by_asset[asset]:
            timeframes_by_asset[asset].append(timeframe)

    assets = sorted(timeframes_by_asset.keys())
    timeframes = sorted(assets_by_timeframe.keys())
    pairs = [
        {"asset": asset, "timeframes": sorted(timeframes_by_asset[asset])}
        for asset in assets
    ]
    return {
        "assets": assets,
        "timeframes": timeframes,
        "assets_by_timeframe": {tf: sorted(vals) for tf, vals in assets_by_timeframe.items()},
        "timeframes_by_asset": {asset: sorted(vals) for asset, vals in timeframes_by_asset.items()},
        "pairs": pairs,
    }


def main() -> int:
    # Phase 1 only: Build briefing packet
    leaderboard = _run_skill([PY, str(SKILLS_DIR / "autoquant-leaderboard" / "query.py"), "--limit", "5"])
    kpi = _run_skill([PY, str(SKILLS_DIR / "autoquant-kpi" / "query.py"), "--days", "30"])
    lessons = _run_skill([PY, str(SKILLS_DIR / "autoquant-lessons" / "query.py"), "--limit", "5"])
    digest = _run_skill([PY, str(SKILLS_DIR / "autoquant-research-fetch" / "query.py"), "--limit", "5", "--unprocessed"])
    scan = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--scan"])
    funding_raw = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--funding"])
    # Trim funding to top 5 by absolute rate to save tokens
    if isinstance(funding_raw, dict) and "rates" in funding_raw:
        rates = funding_raw["rates"]
        if isinstance(rates, list) and len(rates) > 5:
            rates.sort(key=lambda x: abs(float(x.get("rate", 0) or 0)), reverse=True)
            funding_raw["rates"] = rates[:5]
            funding_raw["trimmed_from"] = len(rates)
    funding = funding_raw

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
        ORDER BY ts_iso DESC LIMIT 5
        """
    ).fetchall()
    conn.close()

    backtest_details = []
    for r in recent_results:
        detail = dict(r)
        # Strip heavy nested JSON blobs — Quandalf only needs top-level scores
        detail.pop("metrics", None)
        detail.pop("regime_metrics", None)
        backtest_details.append(detail)

    now = datetime.now(timezone.utc)
    run_state = load_cycle_run_state()
    cycle_id = int(run_state.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        cycle_id = read_cycle_counter()

    backtest_universe = discover_backtest_universe()

    sync_current_cycle_status(cycle_id)

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
        "supported_backtest_universe": backtest_universe,
        "strategy_research_contract": {
            "design_principle": "market mechanism -> component roles -> testable rules -> failure modes -> refinement path",
            "mandatory_pre_submit_reasoning": [
                "market behavior targeted",
                "why edge should exist",
                "asset/timeframe fit",
                "indicator role map",
                "expected regime",
                "likely failure mode",
                "first refinement path"
            ],
            "indicator_role_categories": [
                "regime filter",
                "directional bias",
                "entry timing",
                "confirmation",
                "exit logic",
                "risk/invalidation",
                "scale in / scale out",
                "partial profit",
                "session filter",
                "volatility gate"
            ],
            "pre_submit_density_checks": [
                "will this plausibly generate enough trades?",
                "are filters contradictory?",
                "is this too event-sparse?",
                "is asset/timeframe mismatched to mechanism?"
            ],
            "zero_trade_policy": {
                "rule": "0 trades is a red flag, not a silent fail",
                "allowed_paths": ["refine", "abort"],
                "max_rescue_attempts": 1,
                "rescue_options": [
                    "simplify",
                    "widen trigger",
                    "remove filter",
                    "change asset/timeframe",
                    "reassign indicator roles"
                ]
            },
            "failure_diagnosis_categories": [
                "bad idea",
                "bad implementation",
                "wrong indicator role assignment",
                "wrong asset",
                "wrong timeframe",
                "wrong regime",
                "weak exit/risk logic",
                "too sparse",
                "too complex / overfit"
            ],
            "pass_refinement_requirements": [
                "exit variants",
                "regime variants",
                "timeframe adjacency",
                "cross-asset checks",
                "simplification version",
                "position-management variants"
            ],
            "promotion_standard": "Promote only when a strategy thesis survives out-of-sample testing, credible trade count, acceptable drawdown, nearby perturbation, and some portability/stability."
        }
    }

    # Add strategy families
    try:
        conn2 = sqlite3.connect(str(db_path))
        conn2.row_factory = sqlite3.Row
        active_families = conn2.execute(
            "SELECT * FROM strategy_families WHERE status = 'active' ORDER BY best_qscore DESC LIMIT 10"
        ).fetchall()
        abandoned_recent = conn2.execute(
            "SELECT family_id, thesis, abandon_reason, iterations FROM strategy_families WHERE status = 'abandoned' ORDER BY ts_iso_updated DESC LIMIT 5"
        ).fetchall()
        conn2.close()
        packet["active_strategy_families"] = [dict(f) for f in active_families]
        packet["recently_abandoned"] = [dict(f) for f in abandoned_recent]
    except Exception:
        packet["active_strategy_families"] = []
        packet["recently_abandoned"] = []

    # Inject regime summary if available
    regime_summary_path = ROOT / "data" / "state" / "regime_summary.json"
    try:
        if regime_summary_path.exists():
            regime_data = json.loads(regime_summary_path.read_text(encoding="utf-8"))
            packet["regime_summary"] = regime_data.get("pairs", {})
            packet["regime_generated_at"] = regime_data.get("generated_at")
    except Exception:
        packet["regime_summary"] = {}

    # Inject normalized external intelligence if available
    external_intel_index_path = ROOT / "data" / "external_intel" / "index.json"
    try:
        if external_intel_index_path.exists():
            external_intel = json.loads(external_intel_index_path.read_text(encoding="utf-8"))
            packet["external_intel_sources"] = [
                s for s in (external_intel.get("sources") or []) if isinstance(s, dict) and s.get("enabled")
            ]
            packet["external_intel_recent"] = list(reversed(external_intel.get("items") or []))[:10]
    except Exception:
        packet["external_intel_sources"] = []
        packet["external_intel_recent"] = []

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
        "supported_assets": len(backtest_universe.get("assets", [])),
        "supported_timeframes": backtest_universe.get("timeframes", []),
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
