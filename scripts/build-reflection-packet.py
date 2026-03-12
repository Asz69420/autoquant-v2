#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

from cycle_state import PHASE_REFLECTION_READY, advance_cycle

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
CURRENT_CYCLE_SPECS = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
CURRENT_CYCLE_STATUS = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
REFLECTION_PACKET = os.path.join(ROOT, "agents", "quandalf", "memory", "reflection_packet.json")
RUN_STATE = os.path.join(ROOT, "data", "state", "research_cycle_started_at.json")
MIN_TRADES_FOR_VALID_JUDGMENT = 15


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
    for suffix in (".strategy_spec.json", ".json", ".strategy_spec"):
        if base.endswith(suffix):
            return base[: -len(suffix)]
    return base


def normalize_spec_path(path):
    text = str(path or "").strip()
    if not text:
        return ""
    if os.path.isabs(text):
        return text
    return os.path.join(ROOT, text)


def load_spec(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def safe_json_load(value, default=None):
    if default is None:
        default = {}
    if not value:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def summarize_variant(variant):
    params = variant.get("parameters") if isinstance(variant, dict) else None
    param_map = {}
    if isinstance(params, dict):
        param_map = dict(params)
    elif isinstance(params, list):
        for item in params:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            param_map[name] = item.get("value", item.get("default"))
    return {
        "name": (variant or {}).get("name") or (variant or {}).get("variant_id") or "default",
        "template_name": (variant or {}).get("template_name"),
        "parameters": param_map,
        "risk_policy": (variant or {}).get("risk_policy") or {},
        "execution_policy": (variant or {}).get("execution_policy") or {},
        "risk_rules": (variant or {}).get("risk_rules") or [],
    }


def classify_result_action(result):
    decision = str(result.get("score_decision") or "").lower()
    trades = int(result.get("total_trades") or 0)
    qscore = float(result.get("score_total") or 0.0)
    pf = float(result.get("profit_factor") or 0.0)
    dd = float(result.get("max_drawdown_pct") or 0.0)

    if trades <= 0:
        return "abort", "abort: zero trades"
    if trades < MIN_TRADES_FOR_VALID_JUDGMENT:
        return "abort", f"abort: low trade count ({trades} < {MIN_TRADES_FOR_VALID_JUDGMENT}) with QS {qscore:.2f}, PF {pf:.2f}, DD {dd:.1f}%"
    if decision == "promote":
        return "promote", f"promote: QS {qscore:.2f}, PF {pf:.2f}, DD {dd:.1f}%, trades {trades}"
    if decision == "pass":
        return "refine", f"refine: PASS with QS {qscore:.2f}, PF {pf:.2f}, DD {dd:.1f}%, trades {trades}"
    return "abort", f"abort: {decision or 'fail'} with QS {qscore:.2f}, PF {pf:.2f}, DD {dd:.1f}%, trades {trades}"


def classify_queue_only_action(queue_rows):
    skip_reasons = []
    for row in queue_rows:
        notes = safe_json_load(row.get("notes"), default={})
        note_text = str(row.get("notes") or "")
        if row.get("status") == "skipped" or 'integrity_skip' in note_text:
            reason = str(notes.get("error") or notes.get("reason") or "integrity_skip").strip()
            skip_reasons.append(reason)
    if skip_reasons:
        joined = "; ".join(skip_reasons[:3])
        if "zero_trades" in joined or "zero_trade" in joined:
            return "red_flag", f"0 trades on valid data ({joined}) — Quandalf must explicitly choose iterate or abort."
        return "fix_only", f"execution/data issue ({joined}) — fix the underlying issue before deciding strategy fate."
    return "pending", "pending: no backtest outcome recorded yet"


def derive_failure_diagnosis(spec, result_rows, queue_rows):
    spec = spec or {}
    queue_blob = json.dumps(queue_rows or []).lower()
    result_blob = json.dumps(result_rows or []).lower()
    text = queue_blob + " " + result_blob
    if "zero_trade" in text or "zero_trades" in text:
        return "too sparse"
    max_trades = max([int((r or {}).get("total_trades") or 0) for r in (result_rows or [])] + [0])
    if 0 < max_trades < MIN_TRADES_FOR_VALID_JUDGMENT:
        return "too sparse"
    if (spec.get("asset") or "") and (spec.get("timeframe") or ""):
        return "bad idea"
    return "bad implementation"


def summarize_stage_metrics(result_rows):
    summary = {
        "train": {"runs": 0, "trades": 0, "best_qscore": 0.0, "best_sharpe": 0.0, "best_pf": 0.0, "max_dd": 0.0, "best_return_pct": 0.0},
        "test": {"runs": 0, "trades": 0, "best_qscore": 0.0, "best_sharpe": 0.0, "best_pf": 0.0, "max_dd": 0.0, "best_return_pct": 0.0},
    }
    for row in result_rows or []:
        stage = str(row.get("stage") or "full").lower()
        bucket = "train" if stage == "screen" else "test"
        item = summary[bucket]
        item["runs"] += 1
        item["trades"] += int(row.get("total_trades") or 0)
        item["best_qscore"] = max(float(item["best_qscore"] or 0.0), float(row.get("score_total") or 0.0))
        item["best_pf"] = max(float(item["best_pf"] or 0.0), float(row.get("profit_factor") or 0.0))
        item["best_return_pct"] = max(float(item["best_return_pct"] or 0.0), float(row.get("total_return_pct") or 0.0))
        item["max_dd"] = max(float(item["max_dd"] or 0.0), float(row.get("max_drawdown_pct") or 0.0))
        metrics = safe_json_load(row.get("metrics"), default={})
        item["best_sharpe"] = max(float(item["best_sharpe"] or 0.0), float(metrics.get("sharpe_ratio") or row.get("sharpe_ratio") or 0.0))
    return summary


def build_strategy_entry(spec_id, spec_path, spec, result_rows, queue_rows):
    latest_result = result_rows[0] if result_rows else None
    if latest_result:
        action, rationale = classify_result_action(latest_result)
    else:
        synthetic_latest = None
        for row in queue_rows:
            notes = safe_json_load(row.get("notes"), default={})
            synthetic = notes.get("synthetic_result") if isinstance(notes, dict) else None
            if isinstance(synthetic, dict):
                synthetic_latest = {
                    "stage": synthetic.get("stage") or row.get("stage"),
                    "score_total": ((synthetic.get("outofsample") or {}).get("qscore")),
                    "profit_factor": ((synthetic.get("outofsample") or {}).get("profit_factor")),
                    "max_drawdown_pct": ((synthetic.get("outofsample") or {}).get("max_drawdown_pct")),
                    "total_trades": ((synthetic.get("outofsample") or {}).get("total_trades")),
                    "win_rate_pct": ((synthetic.get("outofsample") or {}).get("win_rate_pct")),
                    "total_return_pct": ((synthetic.get("outofsample") or {}).get("total_return_pct")),
                    "sharpe_ratio": ((synthetic.get("outofsample") or {}).get("sharpe_ratio")),
                    "walk_forward_config": synthetic.get("walk_forward_config") or {},
                    "fold_results": synthetic.get("fold_results") or [],
                    "metrics": synthetic,
                }
                break
        latest_result = synthetic_latest
        action, rationale = classify_queue_only_action(queue_rows)

    queue_summary = []
    for row in queue_rows:
        notes = safe_json_load(row.get("notes"), default={})
        queue_summary.append(
            {
                "queue_id": row.get("id"),
                "stage": row.get("stage"),
                "status": row.get("status"),
                "result_id": row.get("result_id"),
                "notes": notes,
                "synthetic_result": notes.get("synthetic_result") if isinstance(notes, dict) else None,
                "queued_at": row.get("queued_at"),
                "completed_at": row.get("completed_at"),
            }
        )

    results = []
    for row in result_rows:
        metrics = safe_json_load(row.get("metrics"), default={})
        regime_metrics = safe_json_load(row.get("regime_metrics"), default={})
        results.append(
            {
                "id": row.get("id"),
                "variant_id": row.get("variant_id"),
                "asset": row.get("asset"),
                "timeframe": row.get("timeframe"),
                "profit_factor": row.get("profit_factor"),
                "max_drawdown_pct": row.get("max_drawdown_pct"),
                "total_trades": row.get("total_trades"),
                "win_rate_pct": row.get("win_rate_pct"),
                "total_return_pct": row.get("total_return_pct"),
                "score_total": row.get("score_total"),
                "score_decision": row.get("score_decision"),
                "mutation_type": row.get("mutation_type"),
                "refinement_round": row.get("refinement_round"),
                "family_generation": row.get("family_generation"),
                "stage": row.get("stage"),
                "strategy_family": row.get("strategy_family"),
                "sharpe_ratio": metrics.get("sharpe_ratio") or row.get("sharpe_ratio"),
                "avg_trade_pct": metrics.get("avg_trade_pct") or row.get("avg_trade_pct"),
                "degradation_pct": row.get("degradation_pct"),
                "walk_forward_config": safe_json_load(row.get("walk_forward_config"), default={}),
                "fold_results": safe_json_load(row.get("fold_results"), default=[]),
                "metrics": metrics,
                "regime_metrics": regime_metrics,
                "ts_iso": row.get("ts_iso"),
            }
        )

    variants = [summarize_variant(v) for v in (spec.get("variants") or []) if isinstance(v, dict)]
    diagnosis_category = derive_failure_diagnosis(spec, result_rows, queue_rows)
    stage_metrics = summarize_stage_metrics(result_rows)
    return {
        "strategy_spec_id": spec_id,
        "spec_path": spec_path,
        "name": spec.get("name") or spec_id,
        "asset": spec.get("asset"),
        "timeframe": spec.get("timeframe"),
        "strategy_family": spec.get("family_name") or (latest_result or {}).get("strategy_family"),
        "edge_mechanism": spec.get("edge_mechanism"),
        "hypothesis": spec.get("hypothesis") or spec.get("thesis") or spec.get("rationale"),
        "expected_trade_density": spec.get("expected_trade_density"),
        "expected_outcome_pattern": spec.get("expected_outcome_pattern"),
        "success_criteria": spec.get("success_criteria") or spec.get("what_counts_as_success"),
        "failure_criteria": spec.get("failure_criteria") or spec.get("what_counts_as_failure"),
        "indicators": spec.get("indicators") or [],
        "entry_rules": spec.get("entry_rules") or {},
        "exit_rules": spec.get("exit_rules") or {},
        "trade_management": spec.get("trade_management"),
        "variants": variants,
        "queue": queue_summary,
        "result_count": len(results),
        "latest_result": results[0] if results else latest_result,
        "results": results,
        "stage_metrics": stage_metrics,
        "train_result": next((r for r in results if str(r.get("stage") or "").lower() == "screen"), None),
        "test_results": [r for r in results if str(r.get("stage") or "").lower() != "screen"],
        "outcome": action,
        "recommended_action": action,
        "decision_required": action in {"red_flag", "pending", "fix_only"},
        "allowed_next_actions": ["refine", "abort"] if action == "red_flag" else (["fix_only"] if action == "fix_only" else []),
        "diagnosis_category": diagnosis_category,
        "failure_diagnosis_categories_allowed": ["bad idea", "bad implementation", "wrong indicator role assignment", "wrong asset", "wrong timeframe", "wrong regime", "weak exit/risk logic", "too sparse", "too complex / overfit"],
        "rationale": rationale,
        "has_zero_trade_signal": any(
            (r.get("total_trades") or 0) <= 0 for r in results
        ) or any(
            "zero_trade" in json.dumps(q.get("notes") or {}).lower() or "zero_trades" in json.dumps(q.get("notes") or {}).lower()
            for q in queue_summary
        ),
    }


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=120)).isoformat()
    manifest = load_json(CURRENT_CYCLE_SPECS)
    cycle_status = load_json(CURRENT_CYCLE_STATUS)
    run_state = load_json(RUN_STATE)
    active_cycle_id = int(run_state.get("cycle_id") or manifest.get("cycle_id") or cycle_status.get("cycle_id") or 0)

    raw_spec_paths = list(manifest.get("spec_paths") or cycle_status.get("spec_paths") or [])
    current_cycle_specs = []
    seen = set()
    for raw_path in raw_spec_paths:
        spec_path = normalize_spec_path(raw_path)
        spec_id = normalize_spec_id(raw_path)
        if not spec_id or spec_id in seen:
            continue
        spec = load_spec(spec_path)
        spec_cycle_id = int(spec.get("cycle_id") or 0)
        if active_cycle_id > 0 and spec_cycle_id not in {0, active_cycle_id}:
            continue
        seen.add(spec_id)
        current_cycle_specs.append((spec_id, spec_path, spec))

    spec_ids = [item[0] for item in current_cycle_specs]
    results_by_spec = {spec_id: [] for spec_id in spec_ids}
    queue_by_spec = {spec_id: [] for spec_id in spec_ids}

    if spec_ids:
        placeholders = ",".join("?" for _ in spec_ids)
        bt_rows = conn.execute(
            f"""
            SELECT id, ts_iso, strategy_spec_id, variant_id, asset, timeframe,
                   profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
                   total_return_pct, score_total, score_decision,
                   metrics, regime_metrics, strategy_family, mutation_type,
                   refinement_round, family_generation, stage
            FROM backtest_results
            WHERE strategy_spec_id IN ({placeholders})
            ORDER BY ts_iso DESC
            """,
            tuple(spec_ids),
        ).fetchall()
        for row in bt_rows:
            results_by_spec.setdefault(normalize_spec_id(row["strategy_spec_id"]), []).append(dict(row))

        queue_rows = conn.execute(
            f"""
            SELECT id, cycle_id, strategy_spec_id, variant_id, stage, status, result_id,
                   notes, queued_at, started_at, completed_at
            FROM research_funnel_queue
            WHERE strategy_spec_id IN ({placeholders})
            ORDER BY queued_at ASC
            """,
            tuple(spec_ids),
        ).fetchall()
        for row in queue_rows:
            queue_by_spec.setdefault(normalize_spec_id(row["strategy_spec_id"]), []).append(dict(row))

    external_results = []
    recent_external = conn.execute(
        """
        SELECT id, ts_iso, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               total_return_pct, score_total, score_decision, strategy_family,
               mutation_type, refinement_round, family_generation, stage
        FROM backtest_results
        WHERE ts_iso >= ?
        ORDER BY ts_iso DESC
        LIMIT 20
        """,
        (cutoff,),
    ).fetchall()
    for row in recent_external:
        spec_id = normalize_spec_id(row["strategy_spec_id"])
        if spec_id in results_by_spec:
            continue
        external_results.append(dict(row))

    lessons = conn.execute(
        """
        SELECT observation, implication
        FROM lessons
        WHERE ts_iso >= ?
        ORDER BY ts_iso DESC
        LIMIT 12
        """,
        (cutoff,),
    ).fetchall()
    conn.close()

    strategy_outcomes = []
    for spec_id, spec_path, spec in current_cycle_specs:
        strategy_outcomes.append(
            build_strategy_entry(
                spec_id=spec_id,
                spec_path=spec_path,
                spec=spec,
                result_rows=results_by_spec.get(spec_id) or [],
                queue_rows=queue_by_spec.get(spec_id) or [],
            )
        )

    promote_count = sum(1 for item in strategy_outcomes if item.get("recommended_action") == "promote")
    refine_count = sum(1 for item in strategy_outcomes if item.get("recommended_action") == "refine")
    abort_count = sum(1 for item in strategy_outcomes if item.get("recommended_action") == "abort")
    zero_trade_count = sum(1 for item in strategy_outcomes if item.get("has_zero_trade_signal"))

    packet = {
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "type": "reflection",
        "cycle_id": active_cycle_id or manifest.get("cycle_id") or cycle_status.get("cycle_id"),
        "mode": cycle_status.get("mode"),
        "research_direction": cycle_status.get("research_direction"),
        "target_asset": cycle_status.get("target_asset"),
        "target_timeframe": cycle_status.get("target_timeframe"),
        "strategy_outcomes": strategy_outcomes,
        "recent_results": strategy_outcomes,
        "external_context_results": external_results,
        "recent_lessons": [{"observation": l["observation"], "implication": l["implication"]} for l in lessons],
        "result_count": sum(len(item.get("results") or []) for item in strategy_outcomes),
        "current_cycle_result_count": sum(len(item.get("results") or []) for item in strategy_outcomes),
        "current_cycle_strategy_count": len(strategy_outcomes),
        "external_result_count": len(external_results),
        "any_promising": any(item.get("recommended_action") in {"refine", "promote"} for item in strategy_outcomes),
        "best_pf": max(((item.get("latest_result") or {}).get("profit_factor") or 0) for item in strategy_outcomes) if strategy_outcomes else 0,
        "best_qscore": max(((item.get("latest_result") or {}).get("score_total") or 0) for item in strategy_outcomes) if strategy_outcomes else 0,
        "decision_summary": {
            "promote": promote_count,
            "refine": refine_count,
            "abort": abort_count,
            "zero_trade": zero_trade_count,
        },
        "guidance": {
            "focus_level": "strategy_and_queue",
            "instruction": "Work strategy-by-strategy and queue-row-by-queue-row. For each spec, choose exactly one overall decision: pass, refine, or abort. Inside that strategy decision, include one queue_decision for every queue row in the packet. If a strategy produced 0 trades on valid data, treat that as a red flag that must resolve explicitly as either refine or abort. Do not omit any tested row and do not use promote, fix_only, skip, pending, or undecided.",
        },
    }

    with open(REFLECTION_PACKET, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)

    if packet.get("cycle_id"):
        advance_cycle(int(packet.get("cycle_id") or 0), PHASE_REFLECTION_READY, result_count=packet.get("current_cycle_result_count", 0))

    print(
        json.dumps(
            {
                "status": "ready",
                "path": REFLECTION_PACKET,
                "current_cycle_strategy_count": len(strategy_outcomes),
                "current_cycle_result_count": packet["current_cycle_result_count"],
                "decision_summary": packet["decision_summary"],
            }
        )
    )


if __name__ == "__main__":
    sys.exit(main() or 0)
