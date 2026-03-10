#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
CURRENT_CYCLE_SPECS = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
CURRENT_CYCLE_STATUS = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")


def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def normalize_spec_id(value):
    text = str(value or "").strip()
    if not text:
        return ""
    base = os.path.basename(text)
    for suffix in (".strategy_spec.json", ".json"):
        if base.endswith(suffix):
            return base[:-len(suffix)]
    return base


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()

    manifest = load_json(CURRENT_CYCLE_SPECS)
    cycle_status = load_json(CURRENT_CYCLE_STATUS)
    current_cycle_spec_ids = {
        normalize_spec_id(p)
        for p in (manifest.get("spec_paths") or cycle_status.get("spec_paths") or [])
        if normalize_spec_id(p)
    }

    recent = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               total_return_pct, score_total, score_decision,
               metrics, regime_metrics, strategy_family, mutation_type, refinement_round, family_generation
        FROM backtest_results
        WHERE ts_iso >= ?
        ORDER BY ts_iso DESC
        """,
        (cutoff,),
    ).fetchall()

    lessons = conn.execute(
        """
        SELECT observation, implication
        FROM lessons
        WHERE ts_iso >= ?
        ORDER BY ts_iso DESC LIMIT 10
        """,
        (cutoff,),
    ).fetchall()

    conn.close()

    results = []
    cycle_results = []
    external_results = []
    management_summary = {}
    for r in recent:
        entry = dict(r)
        for key in ["metrics", "regime_metrics"]:
            if entry.get(key):
                try:
                    entry[key] = json.loads(entry[key])
                except Exception:
                    pass
        spec_id = normalize_spec_id(entry.get("strategy_spec_id"))
        entry["is_current_cycle"] = spec_id in current_cycle_spec_ids if current_cycle_spec_ids else False
        tm_style = "unknown"
        try:
            trade_mgmt = ((entry.get("metrics") or {}).get("trade_management") or {})
            if isinstance(trade_mgmt, dict):
                tm_style = f"{trade_mgmt.get('entry_style','one_shot')}->{trade_mgmt.get('exit_style','one_shot')}"
        except Exception:
            pass
        if spec_id in current_cycle_spec_ids:
            cycle_results.append(entry)
        else:
            external_results.append(entry)
        if entry.get("mutation_type"):
            key = str(entry.get("mutation_type"))
            management_summary.setdefault(key, {"count": 0, "pass": 0, "best_qscore": None})
            management_summary[key]["count"] += 1
            if str(entry.get("score_decision") or "").lower() in {"pass", "promote"}:
                management_summary[key]["pass"] += 1
            qs = float(entry.get("score_total") or 0.0)
            best_qs = management_summary[key]["best_qscore"]
            management_summary[key]["best_qscore"] = qs if best_qs is None else max(best_qs, qs)
        results.append(entry)

    focus_results = cycle_results if cycle_results else []

    packet = {
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "type": "reflection",
        "recent_results": focus_results,
        "external_context_results": external_results[:10],
        "recent_lessons": [{"observation": l["observation"], "implication": l["implication"]} for l in lessons],
        "result_count": len(focus_results),
        "current_cycle_result_count": len(cycle_results),
        "external_result_count": len(external_results),
        "management_summary": management_summary,
        "any_promising": any(
            (r.get("score_decision") in {"pass", "promote"}) and (r.get("total_trades") or 0) >= 50
            for r in focus_results
        ),
        "best_pf": max((r.get("profit_factor") or 0 for r in focus_results), default=0),
        "best_qscore": max((r.get("score_total") or 0 for r in focus_results), default=0),
    }

    path = os.path.join(ROOT, "agents", "quandalf", "memory", "reflection_packet.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)

    print(json.dumps({"status": "ready", "path": path, "results": len(results), "any_promising": packet["any_promising"]}))


if __name__ == "__main__":
    sys.exit(main() or 0)
