#!/usr/bin/env python3
import argparse
import copy
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
PARALLEL_RUNNER = os.path.join(ROOT, "scripts", "parallel_runner.py")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
REFINEMENT_DIR = os.path.join(SPECS_DIR, "refinement")
CURRENT_STATUS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
STRATEGY_STATUS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "strategy_status.json")
REFINEMENT_STATE_PATH = os.path.join(ROOT, "data", "state", "refinement_cycle_state.json")
REFINEMENT_JOBS_PATH = os.path.join(ROOT, "data", "state", "refinement_jobs.json")

STATUS_ORDER = {
    None: 0,
    "PASS.REFINING": 1,
    "PASS.STABLE": 2,
    "PASS.STALLED": 3,
    "PASS.REJECTED": 4,
    "PROMOTE.CANDIDATE": 5,
}
TIMEFRAME_ORDER = ["1m", "5m", "15m", "1h", "4h", "1d"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_json(path, default=None):
    if default is None:
        default = {}
    if not os.path.exists(path):
        return copy.deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return copy.deepcopy(default)


def write_json(path, payload):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)


def ensure_schema(conn):
    existing = {row[1] for row in conn.execute("PRAGMA table_info(backtest_results)")}
    additions = {
        "refinement_status": "TEXT",
        "refinement_round": "INTEGER DEFAULT 0",
        "weakness_profile": "TEXT",
    }
    for col, ddl in additions.items():
        if col not in existing:
            try:
                conn.execute(f"ALTER TABLE backtest_results ADD COLUMN {col} {ddl}")
            except sqlite3.OperationalError:
                pass
    conn.execute("UPDATE backtest_results SET refinement_round = COALESCE(refinement_round, 0)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_bt_refinement_status ON backtest_results(refinement_status, refinement_round, strategy_family)")
    conn.commit()


def log_event(conn, event_type, agent, message, severity="info", step=None, artifact_id=None, metadata=None):
    conn.execute(
        """
        INSERT INTO event_log (ts_iso, event_type, agent, pipeline, step, artifact_id, severity, message, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_iso(),
            event_type,
            agent,
            "refinement_cycle",
            step,
            artifact_id,
            severity,
            message,
            json.dumps(metadata) if metadata is not None else None,
        ),
    )
    conn.commit()


def append_status_summary(summary):
    current = load_json(CURRENT_STATUS_PATH, default={})
    current["latest_refinement_summary"] = summary
    history = current.get("refinement_history") or []
    history.append(summary)
    current["refinement_history"] = history[-20:]
    write_json(CURRENT_STATUS_PATH, current)

    strategy = load_json(STRATEGY_STATUS_PATH, default={})
    strategy.setdefault("refinement_cycles", []).append(summary)
    strategy["refinement_cycles"] = strategy["refinement_cycles"][-50:]
    write_json(STRATEGY_STATUS_PATH, strategy)


def send_log_card(card_text):
    try:
        proc = subprocess.run(
            [sys.executable, TG_SCRIPT, "--message", f"<pre>{card_text}</pre>", "--channel", "log", "--bot", "logron"],
            capture_output=True,
            text=True,
            timeout=20,
        )
        return proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")
    except Exception:
        return False


def elapsed_text(started_at):
    try:
        started = datetime.fromisoformat(str(started_at).replace("Z", "+00:00"))
        seconds = max(0, int((datetime.now(timezone.utc) - started).total_seconds()))
    except Exception:
        seconds = 0
    return f"{seconds // 60}m {seconds % 60}s"


def find_spec_path(strategy_spec_id):
    candidates = [
        os.path.join(SPECS_DIR, f"{strategy_spec_id}.strategy_spec.json"),
        os.path.join(SPECS_DIR, f"{strategy_spec_id}.json"),
        os.path.join(SPECS_DIR, "auto_funnel", f"{strategy_spec_id}.strategy_spec.json"),
        os.path.join(SPECS_DIR, "auto_funnel", f"{strategy_spec_id}.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    for base, _, files in os.walk(SPECS_DIR):
        for name in files:
            if name in {f"{strategy_spec_id}.strategy_spec.json", f"{strategy_spec_id}.json"}:
                return os.path.join(base, name)
    return None


def load_spec(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_spec(spec):
    os.makedirs(REFINEMENT_DIR, exist_ok=True)
    out_path = os.path.join(REFINEMENT_DIR, f"{spec['id']}.strategy_spec.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(spec, f, indent=2)
    return out_path


def variant_by_name(spec, variant_id):
    variants = spec.get("variants") or []
    for variant in variants:
        name = str(variant.get("name") or variant.get("variant_id") or "default")
        if name == variant_id:
            return copy.deepcopy(variant)
    return copy.deepcopy(variants[0] if variants else {"name": variant_id or "default"})


def param_map(variant):
    raw = variant.get("parameters")
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, list):
        out = {}
        for item in raw:
            if isinstance(item, dict) and item.get("name"):
                out[str(item["name"])] = item.get("value", item.get("default"))
        return out
    return {}


def set_params(variant, updates):
    raw = variant.get("parameters")
    if isinstance(raw, dict):
        raw.update(updates)
        variant["parameters"] = raw
        return variant
    if isinstance(raw, list):
        seen = set()
        for item in raw:
            if isinstance(item, dict) and item.get("name") in updates:
                item["value"] = updates[item["name"]]
                seen.add(item["name"])
        for name, value in updates.items():
            if name not in seen:
                raw.append({"name": name, "value": value})
        variant["parameters"] = raw
        return variant
    variant["parameters"] = dict(updates)
    return variant


def perturb(value, pct):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        candidate = int(round(value * (1.0 + pct)))
        if candidate == value:
            candidate += 1 if pct > 0 else -1
        return max(1, candidate)
    if isinstance(value, float):
        candidate = round(value * (1.0 + pct), 6)
        if candidate == value:
            candidate = round(value + (0.05 if pct > 0 else -0.05), 6)
        return candidate
    return value


def timeframe_faster(tf):
    if tf not in TIMEFRAME_ORDER:
        return None
    idx = TIMEFRAME_ORDER.index(tf)
    return TIMEFRAME_ORDER[idx - 1] if idx > 0 else None


def complexity_score(spec):
    indicators = len(spec.get("indicators") or [])
    entry_rules = spec.get("entry_rules") or {}
    exit_rules = spec.get("exit_rules") or {}
    rule_count = 0
    if isinstance(entry_rules, dict):
        rule_count += sum(len(v or []) for v in entry_rules.values())
    elif isinstance(entry_rules, list):
        rule_count += len(entry_rules)
    if isinstance(exit_rules, dict):
        rule_count += sum(len(v or []) for v in exit_rules.values())
    elif isinstance(exit_rules, list):
        rule_count += len(exit_rules)
    return indicators + rule_count


def build_variant_spec(base_spec, base_variant, source_row, mutation_type, suffix, *, asset=None, timeframe=None, param_updates=None, regime_filter=None, complexity_reduce=False, stop_override=None, trailing=False):
    spec = copy.deepcopy(base_spec)
    variant = copy.deepcopy(base_variant)
    if param_updates:
        variant = set_params(variant, param_updates)
    variant["name"] = f"{str(base_variant.get('name') or source_row['variant_id'])}_{suffix}"
    if stop_override is not None:
        risk = variant.get("risk_policy") if isinstance(variant.get("risk_policy"), dict) else {}
        risk["stop_loss_pct"] = stop_override
        variant["risk_policy"] = risk
    if trailing:
        risk = variant.get("risk_policy") if isinstance(variant.get("risk_policy"), dict) else {}
        risk["trailing_stop_pct"] = float(risk.get("trailing_stop_pct") or risk.get("stop_loss_pct") or 2.0)
        variant["risk_policy"] = risk
    spec["variants"] = [variant]
    spec["asset"] = asset or source_row["asset"]
    spec["timeframe"] = timeframe or source_row["timeframe"]
    spec["parent_id"] = source_row["id"]
    spec["mutation_type"] = mutation_type
    spec["family_generation"] = int(source_row["family_generation"] or 1) + 1
    spec["source"] = "refinement_cycle"
    spec["ts_iso"] = now_iso()
    spec["id"] = f"{source_row['strategy_spec_id']}-{suffix}-{uuid.uuid4().hex[:6]}"
    spec["name"] = f"{base_spec.get('name') or source_row['strategy_spec_id']} [{suffix}]"
    if regime_filter:
        spec["regime_filter"] = regime_filter
    if complexity_reduce:
        indicators = list(spec.get("indicators") or [])
        if len(indicators) > 1:
            spec["indicators"] = indicators[:-1]
        if isinstance(spec.get("entry_rules"), dict):
            for side in ("long", "short"):
                rules = list(spec["entry_rules"].get(side) or [])
                if len(rules) > 1:
                    spec["entry_rules"][side] = rules[:-1]
                    break
        spec["complexity_score"] = max(0, complexity_score(spec) - 1)
    return spec


def family_has_neighbor_history(conn, family, source_id):
    row = conn.execute(
        "select count(*) from backtest_results where lower(coalesce(strategy_family,''))=lower(?) and parent_id=? and mutation_type like 'param_neighbor%'",
        (family, source_id),
    ).fetchone()
    return int(row[0] or 0) > 0


def family_has_cross_asset_history(conn, family, source_asset):
    row = conn.execute(
        "select count(distinct upper(asset)) from backtest_results where lower(coalesce(strategy_family,''))=lower(?) and upper(asset)<>upper(?)",
        (family, source_asset),
    ).fetchone()
    return int(row[0] or 0) > 0


def classify_weaknesses(conn, row):
    weaknesses = []
    if int(row["total_trades"] or 0) < 25:
        weaknesses.append("LOW_TRADES")
    if float(row["max_drawdown_pct"] or 0.0) > 8.0:
        weaknesses.append("HIGH_DD")
    if float(row["regime_concentration"] or 0.0) > 70.0:
        weaknesses.append("REGIME_NARROW")
    if not family_has_neighbor_history(conn, row["strategy_family"], row["id"]):
        weaknesses.append("FRAGILE_PARAMS")
    if not family_has_cross_asset_history(conn, row["strategy_family"], row["asset"]):
        weaknesses.append("SINGLE_ASSET")
    if float(row["score_total"] or 0.0) >= 1.2 and float(row["degradation_pct"] or 999.0) < 40.0:
        weaknesses.append("NEAR_PROMOTE")
    return weaknesses


def pick_validation_targets(spec, limit=None):
    out = []
    for item in spec.get("validation_targets") or []:
        if isinstance(item, str):
            out.append({"asset": item, "timeframe": spec.get("timeframe")})
        elif isinstance(item, dict) and item.get("asset"):
            out.append({"asset": item.get("asset"), "timeframe": item.get("timeframe") or spec.get("timeframe")})
    if limit is not None:
        out = out[:limit]
    return out


def targeted_round_results(conn, source_id, round_number):
    rows = conn.execute(
        "select id, score_decision, score_total, mutation_type, asset, timeframe from backtest_results where parent_id=? and refinement_round=? order by ts_iso desc",
        (source_id, round_number),
    ).fetchall()
    return [dict(zip(["id", "score_decision", "score_total", "mutation_type", "asset", "timeframe"], r)) for r in rows]


def generate_pack(conn, row, spec, round_number):
    base_variant = variant_by_name(spec, row["variant_id"])
    weaknesses = json.loads(row["weakness_profile"] or "[]") if row["weakness_profile"] else classify_weaknesses(conn, row)
    numeric = [(k, v) for k, v in param_map(base_variant).items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    pack = []

    neighbor_target = 5 if "FRAGILE_PARAMS" in weaknesses else 3
    pct_plan = [-0.10, -0.05, 0.05, 0.10, 0.15]
    for idx in range(min(neighbor_target, len(pct_plan))):
        if numeric:
            key, value = numeric[idx % len(numeric)]
            updates = {key: perturb(value, pct_plan[idx])}
        else:
            updates = {}
        pack.append((build_variant_spec(spec, base_variant, row, f"param_neighbor_r{round_number}", f"neighbor{idx+1}", param_updates=updates), "param_neighbor"))

    pack.append((build_variant_spec(spec, base_variant, row, f"simplification_r{round_number}", f"simple{round_number}", complexity_reduce=True), "simplification"))

    if "LOW_TRADES" in weaknesses:
        faster = timeframe_faster(row["timeframe"])
        if faster:
            pack.append((build_variant_spec(spec, base_variant, row, f"tf_transfer_r{round_number}", f"fastertf{round_number}", timeframe=faster), "tf_transfer"))
    if "HIGH_DD" in weaknesses:
        base_stop = 2.0
        risk = base_variant.get("risk_policy") if isinstance(base_variant.get("risk_policy"), dict) else {}
        try:
            base_stop = float(risk.get("stop_loss_pct") or 2.0)
        except Exception:
            base_stop = 2.0
        pack.append((build_variant_spec(spec, base_variant, row, f"stop_tight_r{round_number}", f"tightstop{round_number}", stop_override=max(0.2, round(base_stop * 0.8, 3))), "stop_tight"))
        pack.append((build_variant_spec(spec, base_variant, row, f"trailing_stop_r{round_number}", f"trail{round_number}", trailing=True), "trailing_stop"))
    if "REGIME_NARROW" in weaknesses and row["primary_regime"]:
        pack.append((build_variant_spec(spec, base_variant, row, f"regime_filter_r{round_number}", f"regime{round_number}", regime_filter={"mode": "only", "regime": row["primary_regime"]}), "regime_filter"))
    if "SINGLE_ASSET" in weaknesses:
        for idx, target in enumerate(pick_validation_targets(spec, limit=2), start=1):
            pack.append((build_variant_spec(spec, base_variant, row, f"cross_asset_r{round_number}", f"cross{idx}", asset=target["asset"], timeframe=target["timeframe"]), "cross_asset"))
    if "NEAR_PROMOTE" in weaknesses:
        for idx, target in enumerate(pick_validation_targets(spec, limit=None), start=1):
            pack.append((build_variant_spec(spec, base_variant, row, f"promote_cross_asset_r{round_number}", f"promocross{idx}", asset=target["asset"], timeframe=target["timeframe"]), "cross_asset"))
        pack.append((build_variant_spec(spec, base_variant, row, f"reduced_complexity_r{round_number}", f"reduced{round_number}", complexity_reduce=True), "simplification"))

    if round_number == 2:
        prior = targeted_round_results(conn, row["id"], 1)
        weak_mutations = {item["mutation_type"] for item in prior if str(item["score_decision"] or "").lower() == "pass"}
        pack = [item for item in pack if item[1] in weak_mutations or item[1] in {"param_neighbor", "cross_asset", "simplification"}][:5]
    elif round_number == 3:
        near = float(row["score_total"] or 0.0) >= 1.3 or "NEAR_PROMOTE" in weaknesses
        pack = pack[:3] if near else []

    deduped = []
    seen = set()
    for spec_obj, kind in pack:
        key = (spec_obj["asset"], spec_obj["timeframe"], kind, json.dumps(spec_obj.get("regime_filter") or {}, sort_keys=True), json.dumps(spec_obj.get("variants") or [], sort_keys=True))
        if key in seen:
            continue
        seen.add(key)
        deduped.append((spec_obj, kind))
    return weaknesses, deduped


def candidate_rows(conn):
    query = """
    select *
    from backtest_results
    where lower(coalesce(score_decision,''))='pass'
      and coalesce(killed,0)=0
      and (
        refinement_status is null
        or (refinement_status in ('PASS.REFINING','PASS.STABLE','PASS.STALLED') and coalesce(refinement_round,0) < 3)
      )
    order by coalesce(refinement_round,0) asc, score_total desc, ts_iso asc
    """
    conn.row_factory = sqlite3.Row
    return conn.execute(query).fetchall()


def build_jobs(conn, cycle_id, max_jobs):
    jobs = []
    touched_rows = []
    round_counts = {1: 0, 2: 0, 3: 0}
    for row in candidate_rows(conn):
        spec_path = find_spec_path(row["strategy_spec_id"])
        if not spec_path:
            continue
        spec = load_spec(spec_path)
        next_round = int(row["refinement_round"] or 0) + 1
        if next_round > 3:
            continue
        weaknesses, pack = generate_pack(conn, row, spec, next_round)
        if not pack:
            continue
        conn.execute("update backtest_results set weakness_profile=?, refinement_status=coalesce(refinement_status, 'PASS.REFINING') where id=?", (json.dumps(weaknesses), row["id"]))
        conn.commit()
        for spec_obj, kind in pack:
            if len(jobs) >= max_jobs:
                break
            path = save_spec(spec_obj)
            jobs.append(
                {
                    "cycle_id": cycle_id,
                    "spec_path": path,
                    "strategy_spec_id": spec_obj["id"],
                    "variant_id": str(spec_obj["variants"][0].get("name") or "default"),
                    "asset": spec_obj["asset"],
                    "timeframe": spec_obj["timeframe"],
                    "stage": "full",
                    "bucket": "refine",
                    "priority": 1,
                    "mutation_type": kind,
                    "family_generation": int(spec_obj.get("family_generation") or 1),
                    "parent_result_id": row["id"],
                    "strategy_family": row["strategy_family"],
                    "validation_target": json.dumps({"asset": spec_obj["asset"], "timeframe": spec_obj["timeframe"], "kind": kind}),
                    "notes": json.dumps({"source": "refinement_cycle", "refinement_round": next_round, "weakness_profile": weaknesses}),
                    "refinement_round": next_round,
                }
            )
        touched_rows.append(dict(row))
        round_counts[next_round] += min(len(pack), max(0, max_jobs - len(jobs) + min(len(pack), max_jobs)))
        if len(jobs) >= max_jobs:
            break
    write_json(REFINEMENT_JOBS_PATH, {"cycle_id": cycle_id, "jobs": jobs, "created_at": now_iso()})
    return jobs, touched_rows


def parse_runner_output(text):
    text = (text or "").strip()
    if not text:
        return {}
    try:
        return json.loads(text)
    except Exception:
        pass
    for idx, line in enumerate(text.splitlines()):
        if line.strip().startswith("{"):
            try:
                return json.loads("\n".join(text.splitlines()[idx:]))
            except Exception:
                continue
    return {}


def run_jobs(job_manifest_path, dry_run=False):
    cmd = [sys.executable, PARALLEL_RUNNER, "--job-manifest", job_manifest_path, "--max-jobs", "5", "--no-funnel-effects"]
    if dry_run:
        cmd.append("--dry-run")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    payload = parse_runner_output(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "parallel_runner failed")
    return payload


def fetch_child_results(conn, source_id, round_number=None):
    sql = "select * from backtest_results where parent_id=?"
    params = [source_id]
    if round_number is not None:
        sql += " and refinement_round=?"
        params.append(round_number)
    conn.row_factory = sqlite3.Row
    return conn.execute(sql, params).fetchall()


def result_pass(row):
    return str(row["score_decision"] or "").lower() in {"pass", "promote"}


def evaluate_source(conn, row):
    current_round = int(row["refinement_round"] or 0)
    child_rows = fetch_child_results(conn, row["id"], current_round if current_round > 0 else None)
    if not child_rows:
        return None
    neighbor_passes = sum(1 for r in child_rows if str(r["mutation_type"] or "").startswith("param_neighbor") and result_pass(r))
    cross_asset_passes = sum(1 for r in child_rows if str(r["asset"] or "").upper() != str(row["asset"] or "").upper() and result_pass(r))
    simplification_rows = [r for r in child_rows if str(r["mutation_type"] or "").startswith("simplification")]
    simplification_hold = any(float(r["score_total"] or 0.0) >= float(row["score_total"] or 0.0) * 0.8 for r in simplification_rows if result_pass(r))
    child_avg = sum(float(r["score_total"] or 0.0) for r in child_rows) / max(1, len(child_rows))
    trend = "up" if child_avg > float(row["score_total"] or 0.0) + 0.05 else "down" if child_avg < float(row["score_total"] or 0.0) - 0.05 else "flat"
    regime_specialist = "regime_specialist" in json.loads(row["score_flags"] or "[]") if row["score_flags"] else False

    promote_gate = all(
        [
            float(row["score_total"] or 0.0) >= 1.5,
            float(row["degradation_pct"] or 999.0) < 30.0,
            neighbor_passes >= 2,
            cross_asset_passes >= 1,
            int(row["total_trades"] or 0) >= 20,
            float(row["regime_concentration"] or 0.0) < 80.0 or regime_specialist,
            current_round >= 1,
        ]
    )
    stable_gate = neighbor_passes >= 2 and simplification_hold and (cross_asset_passes >= 1 or "SINGLE_ASSET" not in json.loads(row["weakness_profile"] or "[]"))
    severe_failures = sum(1 for r in child_rows if not result_pass(r))

    if promote_gate:
        status = "PROMOTE.CANDIDATE"
    elif stable_gate and trend in {"up", "flat"}:
        status = "PASS.STABLE"
    elif current_round >= 3:
        status = "PASS.STALLED" if child_avg >= float(row["score_total"] or 0.0) * 0.8 else "PASS.REJECTED"
    elif severe_failures == len(child_rows):
        status = "PASS.STALLED"
    else:
        status = "PASS.REFINING"

    return {
        "status": status,
        "neighbor_passes": neighbor_passes,
        "cross_asset_passes": cross_asset_passes,
        "simplification_hold": simplification_hold,
        "qscore_trend": trend,
        "tests": len(child_rows),
        "round": current_round,
    }


def stamp_refinement_rounds(conn, runner_payload, jobs):
    by_spec = {job.get("strategy_spec_id"): int(job.get("refinement_round") or 0) for job in jobs}
    for item in runner_payload.get("results") or []:
        result_id = item.get("result_id")
        payload = item.get("payload") or {}
        spec_id = item.get("job", {}).get("strategy_spec_id") or payload.get("strategy") or ""
        refinement_round = by_spec.get(spec_id, 0)
        if result_id and refinement_round:
            conn.execute("update backtest_results set refinement_round=? where id=?", (refinement_round, result_id))
    conn.commit()


def update_source_statuses(conn, touched_rows):
    upgrades = 0
    rejected = 0
    promoted = 0
    per_round = {1: 0, 2: 0, 3: 0}
    note_parts = []
    for original in touched_rows:
        refreshed = conn.execute("select * from backtest_results where id=?", (original["id"],)).fetchone()
        if refreshed is None:
            continue
        refreshed = dict(zip([col[0] for col in conn.execute('select * from backtest_results where id=?', (original['id'],)).description], refreshed))
        evaluation = evaluate_source(conn, refreshed)
        if not evaluation:
            continue
        old_status = original.get("refinement_status")
        new_status = evaluation["status"]
        conn.execute(
            "update backtest_results set refinement_status=?, refinement_round=? where id=?",
            (new_status, evaluation["round"], original["id"]),
        )
        per_round[evaluation["round"]] = per_round.get(evaluation["round"], 0) + 1
        if STATUS_ORDER.get(new_status, 0) > STATUS_ORDER.get(old_status, 0):
            upgrades += 1
        if new_status in {"PASS.REJECTED", "PASS.STALLED"}:
            rejected += 1
        if new_status == "PROMOTE.CANDIDATE":
            promoted += 1
        family_label = original.get("strategy_family") or original.get("strategy_spec_id") or "This family"
        note_parts.append(f"{family_label} is {new_status.lower()} with {evaluation['neighbor_passes']} neighbor passes, {evaluation['cross_asset_passes']} cross-asset passes, simplification {'holding' if evaluation['simplification_hold'] else 'fading'}, and QScore trend {evaluation['qscore_trend']}")
    conn.commit()
    note = "; ".join(note_parts[:2]) if note_parts else "No eligible PASS family produced a refinement decision this cycle"
    note = note[:349].rstrip(";,. ") + "."
    return upgrades, rejected, promoted, per_round, note


def build_card(cycle_id, started_at, tests_this_cycle, upgrades, rejected, promoted, round_counts, note, had_error=False):
    if had_error:
        status_emoji = "❌"
    elif promoted > 0:
        status_emoji = "🏆"
    elif upgrades > 0:
        status_emoji = "⬆️"
    elif rejected > 0 and upgrades == 0 and promoted == 0:
        status_emoji = "⚠️"
    else:
        status_emoji = "🔬"
    lines = [
        "🔬 Refining",
        f"{status_emoji} | ▶ {elapsed_text(started_at)} | 🆔 {cycle_id}",
        "○──activity──────────────────",
        f"Round 1 {int(round_counts.get(1, 0))}",
        f"Round 2 {int(round_counts.get(2, 0))}",
        f"Round 3 {int(round_counts.get(3, 0))}",
        f"Backtests {int(tests_this_cycle)}",
        f"Upgraded {int(upgrades)}",
        f"Rejected {int(rejected)}",
        f"Promoted {int(promoted)}",
        "○──note──────────────────────",
        note,
    ]
    return "\n".join(lines)


def next_cycle_id():
    state = load_json(REFINEMENT_STATE_PATH, default={})
    cycle_id = int(state.get("last_cycle_id") or 0) + 1
    state["last_cycle_id"] = cycle_id
    write_json(REFINEMENT_STATE_PATH, state)
    return cycle_id


def main():
    ap = argparse.ArgumentParser(description="PASS refinement cycle")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-jobs", type=int, default=5)
    args = ap.parse_args()

    cycle_id = next_cycle_id()
    started_at = now_iso()
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    ensure_schema(conn)
    had_error = False
    payload = {}
    touched_rows = []
    jobs = []

    try:
        jobs, touched_rows = build_jobs(conn, cycle_id, max(1, min(5, args.max_jobs)))
        if jobs:
            for row in touched_rows:
                next_round = int(row["refinement_round"] or 0) + 1
                conn.execute("update backtest_results set refinement_status='PASS.REFINING', refinement_round=? where id=?", (next_round, row["id"]))
            conn.commit()
            payload = run_jobs(REFINEMENT_JOBS_PATH, dry_run=args.dry_run)
            if not args.dry_run:
                stamp_refinement_rounds(conn, payload, jobs)
        else:
            payload = {"status": "idle", "total_jobs": 0, "ok": 0, "fail": 0}
        upgrades, rejected, promoted, round_counts, note = update_source_statuses(conn, touched_rows)
    except Exception as exc:
        had_error = True
        upgrades, rejected, promoted, round_counts = 0, 0, 0, {1: 0, 2: 0, 3: 0}
        note = f"Refinement cycle hit an error before completion: {str(exc).strip()[:290]}."
        log_event(conn, "refinement_cycle_error", "frodex", str(exc), severity="error", step="run")
    finally:
        summary = {
            "cycle_id": cycle_id,
            "started_at": started_at,
            "finished_at": now_iso(),
            "jobs_requested": len(jobs),
            "runner": payload,
            "had_error": had_error,
        }
        append_status_summary(summary)
        card = build_card(cycle_id, started_at, len(jobs), upgrades, rejected, promoted, round_counts, note, had_error=had_error)
        sent = False if args.dry_run else send_log_card(card)
        log_event(conn, "refinement_cycle_complete", "frodex", f"refinement cycle {cycle_id} complete", step="summary", metadata={"jobs": len(jobs), "upgrades": upgrades, "rejected": rejected, "promoted": promoted, "log_card_sent": sent, "dry_run": args.dry_run})
        conn.close()

    out = {
        "status": "error" if had_error else "ok",
        "cycle_id": cycle_id,
        "jobs": len(jobs),
        "runner": payload,
        "card": card,
        "log_card_sent": sent,
        "touched_families": [row["strategy_family"] for row in touched_rows],
    }
    print(json.dumps(out, indent=2))
    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
