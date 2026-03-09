#!/usr/bin/env python3
import argparse
import copy
import hashlib
import json
import math
import os
import sqlite3
import subprocess
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
THROTTLE = os.path.join(ROOT, "config", "throttle.json")
BACKTESTER = os.path.join(ROOT, "scripts", "walk_forward_engine.py")
CURRENT_CYCLE_SPECS = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
BRANCH_DIR = os.path.join(SPECS_DIR, "auto_funnel")
QUANDALF_JOURNAL_STATUS = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")

SCREEN_LIMIT = 10
FULL_LIMIT = 3
VALIDATION_LIMIT = 5
BUCKET_RATIOS = {"explore": 0.4, "refine": 0.4, "validate": 0.2}
TIMEFRAME_ORDER = ["1m", "5m", "15m", "1h", "4h", "1d"]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def parse_json_from_output(text):
    if not text:
        return None
    text = text.strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    lines = [line for line in text.splitlines() if line.strip()]
    for start in range(len(lines)):
        candidate = "\n".join(lines[start:]).strip()
        if not candidate.startswith("{"):
            continue
        try:
            return json.loads(candidate)
        except Exception:
            continue
    return None


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


def read_throttle():
    with open(THROTTLE, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    mode = cfg.get("current_mode", "normal")
    max_parallel = int(cfg.get("modes", {}).get(mode, {}).get("max_parallel", 1))
    return mode, max(1, max_parallel)


def load_spec(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_spec_path(spec_arg):
    if not spec_arg:
        raise ValueError("missing spec path")
    if spec_arg != "LATEST_SPEC":
        return spec_arg
    if not os.path.exists(CURRENT_CYCLE_SPECS):
        raise FileNotFoundError(f"LATEST_SPEC requested but manifest missing: {CURRENT_CYCLE_SPECS}")
    manifest = load_manifest(CURRENT_CYCLE_SPECS)
    latest = (manifest.get("latest_spec_path") or "").strip()
    if not latest:
        raise ValueError(f"LATEST_SPEC requested but latest_spec_path missing in manifest: {CURRENT_CYCLE_SPECS}")
    return latest


def expand_manifest_specs(manifest_path):
    manifest = load_manifest(manifest_path)
    spec_paths = manifest.get("spec_paths") or []
    if not isinstance(spec_paths, list):
        return []
    normalized = []
    for item in spec_paths:
        path = str(item).strip()
        if not path:
            continue
        if not os.path.exists(path):
            raise FileNotFoundError(f"manifest spec path missing: {path}")
        normalized.append(path)
    return normalized


def log_event(conn, event_type, agent, message, severity="info", pipeline="parallel_runner", step=None, artifact_id=None, metadata=None):
    conn.execute(
        """
        INSERT INTO event_log (ts_iso, event_type, agent, pipeline, step, artifact_id, severity, message, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            now_iso(),
            event_type,
            agent,
            pipeline,
            step,
            artifact_id,
            severity,
            message,
            json.dumps(metadata) if metadata is not None else None,
        ),
    )


def create_pipeline_run(conn, parent_run_id, status="running", steps_total=0):
    pid = f"pr_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO pipeline_runs (id, ts_iso_start, pipeline_name, mode, run_id, parent_run_id, status, steps_total, steps_completed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (pid, now_iso(), "parallel_runner", "parallel", pid, parent_run_id, status, steps_total, 0),
    )
    return pid


def ensure_schema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS research_funnel_queue (
            id TEXT PRIMARY KEY,
            cycle_id INTEGER,
            spec_path TEXT NOT NULL,
            strategy_spec_id TEXT NOT NULL,
            variant_id TEXT NOT NULL,
            asset TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            stage TEXT NOT NULL,
            bucket TEXT NOT NULL,
            priority INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'queued',
            queued_at TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            parent_result_id TEXT,
            mutation_type TEXT,
            family_generation INTEGER NOT NULL DEFAULT 1,
            strategy_family TEXT,
            validation_target TEXT DEFAULT '',
            source_queue_id TEXT,
            notes TEXT,
            result_id TEXT,
            novelty_score REAL DEFAULT 0,
            UNIQUE(spec_path, variant_id, asset, timeframe, stage, validation_target)
        )
        """
    )
    existing = {row[1] for row in conn.execute("PRAGMA table_info(research_funnel_queue)")}
    if "novelty_score" not in existing:
        try:
            conn.execute("ALTER TABLE research_funnel_queue ADD COLUMN novelty_score REAL DEFAULT 0")
        except sqlite3.OperationalError:
            pass
    conn.execute("CREATE TABLE IF NOT EXISTS mechanism_priors (mechanism TEXT PRIMARY KEY, success_rate REAL, total_tested INTEGER, avg_best_qs REAL, priority_modifier REAL DEFAULT 1.0, updated_at TEXT)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_funnel_queue_status ON research_funnel_queue(status, stage, bucket, priority, queued_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_funnel_queue_cycle ON research_funnel_queue(cycle_id, status, bucket, priority)")
    conn.commit()


def bucket_quota(total_slots):
    raw = {bucket: total_slots * ratio for bucket, ratio in BUCKET_RATIOS.items()}
    quota = {bucket: int(math.floor(value)) for bucket, value in raw.items()}
    remainder = total_slots - sum(quota.values())
    order = sorted(raw.items(), key=lambda kv: (kv[1] - math.floor(kv[1])), reverse=True)
    for bucket, _ in order[:remainder]:
        quota[bucket] += 1
    return quota


def normalize_validation_target(target, fallback_timeframe=None):
    if isinstance(target, str):
        return {"asset": target, "timeframe": fallback_timeframe}
    if isinstance(target, dict):
        out = dict(target)
        out.setdefault("timeframe", fallback_timeframe)
        return out
    return None


def derive_family_name(spec):
    explicit = str(spec.get("family_name") or "").strip()
    if explicit:
        return explicit
    indicators = spec.get("indicators") or []
    names = []
    for item in indicators:
        if isinstance(item, str):
            names.append(item.lower())
        elif isinstance(item, dict):
            names.append(str(item.get("name") or "").lower())
    if names:
        return "-".join(sorted(n for n in names if n))[:120]
    return str(spec.get("name") or spec.get("id") or "unknown-family").strip().lower().replace(" ", "-")


def safe_spec_id_from_path(spec_path):
    return os.path.basename(spec_path).replace(".strategy_spec.json", "").replace(".json", "")


def variant_names_for_spec(spec, variant_mode=None):
    variants = spec.get("variants") or []
    if variant_mode == "all":
        names = [str(v.get("name") or v.get("variant_id") or "default").strip() for v in variants]
    elif variant_mode:
        names = [variant_mode]
    else:
        names = [str(variants[0].get("name") or variants[0].get("variant_id") or "default").strip()] if variants else ["default"]
    out = []
    seen = set()
    for name in names:
        if not name or name in seen:
            continue
        seen.add(name)
        out.append(name)
    return out or ["default"]




def indicator_signature(spec):
    names = []
    for item in spec.get("indicators") or []:
        if isinstance(item, str):
            names.append(item.lower())
        elif isinstance(item, dict):
            names.append(str(item.get("name") or "").lower())
    return sorted([n for n in names if n])


def core_threshold_signature(spec, variant):
    params = variant_parameter_map(variant)
    core = {}
    for key, value in sorted(params.items()):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            core[key] = value
    return core


def branch_dedupe_key(spec, variant, asset, timeframe):
    payload = {
        "indicators": indicator_signature(spec),
        "thresholds": core_threshold_signature(spec, variant),
        "asset": str(asset).upper(),
        "timeframe": str(timeframe),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def recent_queue_keys(conn, limit=50):
    rows = conn.execute("SELECT notes FROM research_funnel_queue ORDER BY queued_at DESC LIMIT ?", (int(limit),)).fetchall()
    keys = set()
    for (notes,) in rows:
        if not notes:
            continue
        try:
            obj = json.loads(notes) if str(notes).strip().startswith("{") else {}
        except Exception:
            obj = {}
        dedupe = obj.get("dedupe_key") if isinstance(obj, dict) else None
        if dedupe:
            keys.add(dedupe)
    return keys


def novelty_score_for_spec(conn, spec, asset, timeframe):
    rows = conn.execute(
        "SELECT asset, timeframe, strategy_spec_id FROM research_funnel_queue ORDER BY queued_at DESC LIMIT 50"
    ).fetchall()
    seen_assets = {str(r[0]).upper() for r in rows}
    seen_tfs = {str(r[1]) for r in rows}
    recent_spec_ids = [str(r[2]) for r in rows]
    recent_specs = []
    for spec_id in recent_spec_ids[:10]:
        try:
            recent_specs.append(load_spec(os.path.join(SPECS_DIR, spec_id + '.strategy_spec.json')))
        except Exception:
            continue
    score = 0
    sig = set(indicator_signature(spec))
    if recent_specs:
        if all(sig != set(indicator_signature(other)) for other in recent_specs):
            score += 3
        if all(str(spec.get("edge_mechanism") or "") != str(other.get("edge_mechanism") or "") for other in recent_specs):
            score += 3
    else:
        score += 6
    if str(asset).upper() not in seen_assets:
        score += 2
    if str(timeframe) not in seen_tfs:
        score += 2
    return float(max(0, min(10, score)))


def mechanism_priority_modifier(conn, spec):
    mech = str(spec.get("edge_mechanism") or "").strip()
    if not mech:
        return 1.0
    row = conn.execute("SELECT priority_modifier FROM mechanism_priors WHERE mechanism = ?", (mech,)).fetchone()
    return float(row[0]) if row and row[0] is not None else 1.0


def effective_priority(conn, item):
    try:
        spec = load_spec(item["spec_path"])
    except Exception:
        spec = {}
    base = float(item.get("priority") or 3)
    novelty = float(item.get("novelty_score") or 0.0)
    modifier = mechanism_priority_modifier(conn, spec)
    adjusted = base / modifier
    if novelty >= 7:
        adjusted -= 0.5
    elif novelty < 3:
        adjusted += 0.5
    return adjusted


def family_stage_stats(conn, family, stage):
    rows = conn.execute(
        "SELECT COALESCE(MAX(family_generation),1), SUM(CASE WHEN lower(COALESCE(score_decision,'')) IN ('pass','promote') THEN 1 ELSE 0 END), SUM(CASE WHEN lower(COALESCE(score_decision,''))='promote' THEN 1 ELSE 0 END) FROM backtest_results WHERE lower(COALESCE(strategy_family,'')) = lower(?) AND stage = ? AND COALESCE(killed,0)=0",
        (family, stage),
    ).fetchone()
    return {"max_generation": int(rows[0] or 1), "passes": int(rows[1] or 0), "promotes": int(rows[2] or 0)}


def family_caps(conn, candidates, stage):
    total = max(1, min(stage_limit(stage), len(candidates)))
    base_cap = max(1, int(math.floor(total * 0.30)))
    validate_promote_cap = max(1, int(math.floor(total * 0.40))) if stage == "validation" else None
    caps = {}
    family_counts = {}
    for item in candidates:
        family = item.get("strategy_family") or "unknown-family"
        family_counts[family] = family_counts.get(family, 0) + 1
    new_families = [f for f, _ in family_counts.items() if family_stage_stats(conn, f, "full")["max_generation"] <= 1]
    guaranteed = {f: 2 for f in new_families} if stage == "screen" else {}
    for family in family_counts:
        stats = family_stage_stats(conn, family, "full")
        cap = base_cap
        if stats["max_generation"] >= 3 and stats["passes"] == 0:
            cap = max(1, int(math.floor(cap / 2.0)))
        if stage == "validation" and stats["promotes"] > 0:
            cap = max(cap, validate_promote_cap)
        if family in guaranteed:
            cap = max(cap, guaranteed[family])
        caps[family] = min(family_counts[family], cap)
    return caps, guaranteed

def queue_item_exists(conn, item):
    row = conn.execute(
        """
        SELECT id FROM research_funnel_queue
        WHERE spec_path = ? AND variant_id = ? AND asset = ? AND timeframe = ? AND stage = ?
          AND validation_target = ?
        LIMIT 1
        """,
        (
            item["spec_path"], item["variant_id"], item["asset"], item["timeframe"], item["stage"], item.get("validation_target") or ""
        ),
    ).fetchone()
    return row[0] if row else None


def enqueue_item(conn, item):
    ensure_schema(conn)
    existing_id = queue_item_exists(conn, item)
    if existing_id:
        return existing_id, False
    qid = f"rq_{uuid.uuid4().hex[:12]}"
    conn.execute(
        """
        INSERT INTO research_funnel_queue (
            id, cycle_id, spec_path, strategy_spec_id, variant_id, asset, timeframe,
            stage, bucket, priority, status, queued_at, parent_result_id, mutation_type,
            family_generation, strategy_family, validation_target, source_queue_id, notes, novelty_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'queued', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            qid,
            item.get("cycle_id"),
            item["spec_path"],
            item.get("strategy_spec_id") or safe_spec_id_from_path(item["spec_path"]),
            item.get("variant_id") or "default",
            item["asset"],
            item["timeframe"],
            item["stage"],
            item["bucket"],
            int(item.get("priority", 3)),
            item.get("queued_at") or now_iso(),
            item.get("parent_result_id"),
            item.get("mutation_type"),
            int(item.get("family_generation") or 1),
            item.get("strategy_family"),
            item.get("validation_target") or "",
            item.get("source_queue_id"),
            item.get("notes"),
            float(item.get("novelty_score") or 0.0),
        ),
    )
    return qid, True


def build_seed_items(spec_path, variant_mode=None, cycle_id=None):
    spec = load_spec(spec_path)
    family = derive_family_name(spec)
    items = []
    for variant_name in variant_names_for_spec(spec, variant_mode):
        items.append(
            {
                "cycle_id": cycle_id,
                "spec_path": spec_path,
                "strategy_spec_id": str(spec.get("id") or safe_spec_id_from_path(spec_path)),
                "variant_id": variant_name,
                "asset": str(spec.get("asset", "ETH")),
                "timeframe": str(spec.get("timeframe", "4h")),
                "stage": "screen",
                "bucket": "explore",
                "priority": 3,
                "mutation_type": str(spec.get("mutation_type") or "initial"),
                "family_generation": int(spec.get("family_generation", 1) or 1),
                "parent_result_id": spec.get("parent_id"),
                "strategy_family": family,
                "notes": "cycle seed",
            }
        )
    return items


def seed_queue_from_specs(conn, spec_paths, variant_mode=None, cycle_id=None):
    seeded = []
    for spec_path in spec_paths:
        for item in build_seed_items(spec_path, variant_mode=variant_mode, cycle_id=cycle_id):
            qid, created = enqueue_item(conn, item)
            if created:
                seeded.append(qid)
    conn.commit()
    return seeded


def stage_limit(stage):
    if stage == "screen":
        return SCREEN_LIMIT
    if stage == "full":
        return FULL_LIMIT
    if stage == "validation":
        return VALIDATION_LIMIT
    return 0


def fetch_candidates(conn, cycle_id=None, stage=None):
    ensure_schema(conn)
    params = []
    sql = """
        SELECT id, cycle_id, spec_path, strategy_spec_id, variant_id, asset, timeframe,
               stage, bucket, priority, status, queued_at, parent_result_id, mutation_type,
               family_generation, strategy_family, validation_target, source_queue_id, notes, novelty_score
        FROM research_funnel_queue
        WHERE status = 'queued'
    """
    if cycle_id is not None:
        sql += " AND cycle_id = ?"
        params.append(int(cycle_id))
    if stage is not None:
        sql += " AND stage = ?"
        params.append(stage)
    conn.row_factory = sqlite3.Row
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    return sorted(rows, key=lambda item: (effective_priority(conn, item), item.get("queued_at") or ""))


def pick_stage_batch(conn, candidates, stage, bucket_quota, bucket_used, stage_used, allow_bucket_override=True):
    selected = []
    leftovers = []
    remaining_stage = stage_limit(stage) - stage_used.get(stage, 0)
    if remaining_stage <= 0:
        return []
    caps, guaranteed = family_caps(conn, [item for item in candidates if item["stage"] == stage], stage)
    family_used = {}

    def can_take(item, bucket_override=False):
        bucket = item["bucket"]
        family = item.get("strategy_family") or "unknown-family"
        if stage_used.get(stage, 0) + len(selected) >= stage_limit(stage):
            return False
        if family_used.get(family, 0) >= caps.get(family, 1):
            return False
        if not bucket_override and bucket_used[bucket] >= bucket_quota[bucket]:
            return False
        return True

    stage_candidates = [item for item in candidates if item["stage"] == stage]
    if stage == "screen":
        for family, minimum in guaranteed.items():
            family_items = [item for item in stage_candidates if (item.get("strategy_family") or "unknown-family") == family]
            for item in family_items[:minimum]:
                if len(selected) >= remaining_stage:
                    break
                if can_take(item, bucket_override=True):
                    selected.append(item)
                    bucket_used[item["bucket"]] += 1
                    family_used[family] = family_used.get(family, 0) + 1
    for item in stage_candidates:
        if item["id"] in {s["id"] for s in selected}:
            continue
        if len(selected) >= remaining_stage:
            break
        if can_take(item):
            selected.append(item)
            bucket_used[item["bucket"]] += 1
            family = item.get("strategy_family") or "unknown-family"
            family_used[family] = family_used.get(family, 0) + 1
        else:
            leftovers.append(item)

    if allow_bucket_override:
        for item in leftovers:
            if len(selected) >= remaining_stage:
                break
            if can_take(item, bucket_override=True):
                selected.append(item)
                bucket_used[item["bucket"]] += 1
                family = item.get("strategy_family") or "unknown-family"
                family_used[family] = family_used.get(family, 0) + 1

    stage_used[stage] = stage_used.get(stage, 0) + len(selected)
    return selected


def mark_running(conn, items):
    ts = now_iso()
    for item in items:
        conn.execute("UPDATE research_funnel_queue SET status = 'running', started_at = ? WHERE id = ?", (ts, item["id"]))
    conn.commit()


def mark_done(conn, queue_id, result_id=None, notes=None):
    conn.execute(
        "UPDATE research_funnel_queue SET status = 'done', completed_at = ?, result_id = ?, notes = COALESCE(?, notes) WHERE id = ?",
        (now_iso(), result_id, notes, queue_id),
    )


def mark_failed_back_to_queue(conn, queue_id, notes=None):
    conn.execute(
        "UPDATE research_funnel_queue SET status = 'queued', started_at = NULL, notes = COALESCE(?, notes) WHERE id = ?",
        (notes, queue_id),
    )


def timeframe_neighbors(tf):
    if tf not in TIMEFRAME_ORDER:
        return None, None
    idx = TIMEFRAME_ORDER.index(tf)
    faster = TIMEFRAME_ORDER[idx - 1] if idx > 0 else None
    slower = TIMEFRAME_ORDER[idx + 1] if idx < len(TIMEFRAME_ORDER) - 1 else None
    return faster, slower


def perturb_value(value, pct):
    if isinstance(value, bool):
        return value
    try:
        num = float(value)
    except Exception:
        return value
    nudged = num * (1.0 + pct)
    if abs(num) >= 1:
        nudged = round(nudged)
        nudged = nudged if nudged != 0 else (1 if num > 0 else -1)
        return int(nudged)
    return round(nudged, 6)


def clone_variant_with_params(variant, param_updates, new_name):
    out = copy.deepcopy(variant)
    out["name"] = new_name
    params = out.get("parameters")
    if isinstance(params, list):
        for param in params:
            if not isinstance(param, dict):
                continue
            pname = str(param.get("name") or "")
            if pname in param_updates:
                param["value"] = param_updates[pname]
    elif isinstance(params, dict):
        for key, value in param_updates.items():
            params[key] = value
        out["parameters"] = params
    else:
        out["parameters"] = dict(param_updates)
    return out


def variant_parameter_map(variant):
    params = variant.get("parameters")
    if isinstance(params, dict):
        return dict(params)
    if isinstance(params, list):
        out = {}
        for param in params:
            if not isinstance(param, dict):
                continue
            name = str(param.get("name") or "")
            if name:
                out[name] = param.get("value", param.get("default"))
        return out
    return {}


def write_generated_spec(base_spec, spec_path, asset, timeframe, variant, mutation_type, family_generation, parent_result_id):
    spec = copy.deepcopy(base_spec)
    base_id = str(spec.get("id") or safe_spec_id_from_path(spec_path))
    branch_suffix = uuid.uuid4().hex[:6]
    spec["asset"] = asset
    spec["timeframe"] = timeframe
    spec["parent_id"] = parent_result_id
    spec["mutation_type"] = mutation_type
    spec["family_generation"] = int(family_generation)
    spec["source"] = "funnel_autobranch"
    spec["ts_iso"] = now_iso()
    spec["version"] = str(spec.get("version") or "1.0")
    spec["variants"] = [variant]
    spec["id"] = f"{base_id}-{mutation_type}-{asset.lower()}-{timeframe}-{branch_suffix}"
    spec["name"] = f"{spec.get('name', base_id)} [{mutation_type} {asset}/{timeframe}]"
    os.makedirs(BRANCH_DIR, exist_ok=True)
    out_path = os.path.join(BRANCH_DIR, spec["id"] + ".strategy_spec.json")
    write_json(out_path, spec)
    return out_path, spec


def queue_validation_items(conn, queue_item, spec, full_result, promote=False):
    targets = spec.get("validation_targets") or []
    created = []
    for raw_target in targets:
        target = normalize_validation_target(raw_target, fallback_timeframe=spec.get("timeframe"))
        if not target or not target.get("asset"):
            continue
        item = {
            "cycle_id": queue_item.get("cycle_id"),
            "spec_path": queue_item["spec_path"],
            "strategy_spec_id": queue_item["strategy_spec_id"],
            "variant_id": queue_item["variant_id"],
            "asset": str(target.get("asset")),
            "timeframe": str(target.get("timeframe") or spec.get("timeframe") or queue_item["timeframe"]),
            "stage": "validation",
            "bucket": "validate",
            "priority": 1 if promote else 2,
            "mutation_type": queue_item.get("mutation_type") or "validation_seed",
            "family_generation": int(queue_item.get("family_generation") or 1),
            "parent_result_id": full_result.get("result_id"),
            "strategy_family": queue_item.get("strategy_family") or derive_family_name(spec),
            "validation_target": json.dumps(target),
            "source_queue_id": queue_item["id"],
            "notes": "queued from full pass",
        }
        qid, was_created = enqueue_item(conn, item)
        if was_created:
            created.append(qid)
    return created


def queue_branch_items(conn, queue_item, spec, full_result):
    created = []
    base_variant = None
    for variant in spec.get("variants") or []:
        vname = str(variant.get("name") or variant.get("variant_id") or "default")
        if vname == queue_item["variant_id"]:
            base_variant = variant
            break
    if base_variant is None:
        base_variant = (spec.get("variants") or [{}])[0]

    next_generation = int(queue_item.get("family_generation") or 1) + 1
    parent_result_id = full_result.get("result_id")
    family = queue_item.get("strategy_family") or derive_family_name(spec)
    params = variant_parameter_map(base_variant)
    numeric_keys = [k for k, v in params.items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    numeric_keys = numeric_keys[:3]
    perturbations = [-0.1, -0.05, 0.05, 0.1, 0.15]

    for idx, pct in enumerate(perturbations[: max(3, min(5, len(perturbations)))]):
        if not numeric_keys:
            break
        updates = {}
        key = numeric_keys[idx % len(numeric_keys)]
        updates[key] = perturb_value(params[key], pct)
        new_variant = clone_variant_with_params(base_variant, updates, f"{queue_item['variant_id']}_param_{idx + 1}")
        branch_path, branch_spec = write_generated_spec(spec, queue_item["spec_path"], queue_item["asset"], queue_item["timeframe"], new_variant, "param_tweak", next_generation, parent_result_id)
        dedupe_key = branch_dedupe_key(branch_spec, new_variant, branch_spec["asset"], branch_spec["timeframe"])
        if dedupe_key in recent_queue_keys(conn, limit=50):
            log_event(conn, "branch_duplicate_skipped", "frodex", f"Skipped duplicate auto-branch {branch_spec['id']}", step="dedupe", artifact_id=queue_item["id"], metadata={"dedupe_key": dedupe_key})
        else:
            novelty = novelty_score_for_spec(conn, branch_spec, branch_spec["asset"], branch_spec["timeframe"])
            qid, was_created = enqueue_item(
                conn,
                {
                "cycle_id": queue_item.get("cycle_id"),
                "spec_path": branch_path,
                "strategy_spec_id": branch_spec["id"],
                "variant_id": new_variant["name"],
                "asset": branch_spec["asset"],
                "timeframe": branch_spec["timeframe"],
                "stage": "screen",
                "bucket": "refine",
                "priority": 2,
                "mutation_type": "param_tweak",
                "family_generation": next_generation,
                "parent_result_id": parent_result_id,
                "strategy_family": family,
                "source_queue_id": queue_item["id"],
                "notes": json.dumps({"message": f"auto branch param tweak {updates}", "dedupe_key": dedupe_key}),
                "novelty_score": novelty,
            },
            )
            if was_created:
                created.append(qid)

    faster, slower = timeframe_neighbors(queue_item["timeframe"])
    for tf in [faster, slower]:
        if not tf:
            continue
        branch_path, branch_spec = write_generated_spec(spec, queue_item["spec_path"], queue_item["asset"], tf, copy.deepcopy(base_variant), "tf_transfer", next_generation, parent_result_id)
        dedupe_key = branch_dedupe_key(branch_spec, new_variant, branch_spec["asset"], branch_spec["timeframe"])
        if dedupe_key in recent_queue_keys(conn, limit=50):
            log_event(conn, "branch_duplicate_skipped", "frodex", f"Skipped duplicate auto-branch {branch_spec['id']}", step="dedupe", artifact_id=queue_item["id"], metadata={"dedupe_key": dedupe_key})
        else:
            novelty = novelty_score_for_spec(conn, branch_spec, branch_spec["asset"], branch_spec["timeframe"])
            qid, was_created = enqueue_item(
                conn,
                {
                "cycle_id": queue_item.get("cycle_id"),
                "spec_path": branch_path,
                "strategy_spec_id": branch_spec["id"],
                "variant_id": str(branch_spec["variants"][0].get("name") or "default"),
                "asset": branch_spec["asset"],
                "timeframe": branch_spec["timeframe"],
                "stage": "screen",
                "bucket": "refine",
                "priority": 2,
                "mutation_type": "tf_transfer",
                "family_generation": next_generation,
                "parent_result_id": parent_result_id,
                "strategy_family": family,
                "source_queue_id": queue_item["id"],
                "notes": json.dumps({"message": f"auto branch timeframe {tf}", "dedupe_key": dedupe_key}),
                "novelty_score": novelty,
            },
            )
        if was_created:
            created.append(qid)

    targets = spec.get("validation_targets") or []
    transfer_target = None
    for raw_target in targets:
        target = normalize_validation_target(raw_target, fallback_timeframe=queue_item["timeframe"])
        if target and str(target.get("asset") or "").upper() != str(queue_item["asset"] or "").upper():
            transfer_target = target
            break
    if transfer_target:
        branch_path, branch_spec = write_generated_spec(
            spec,
            queue_item["spec_path"],
            str(transfer_target["asset"]),
            str(transfer_target.get("timeframe") or queue_item["timeframe"]),
            copy.deepcopy(base_variant),
            "asset_transfer",
            next_generation,
            parent_result_id,
        )
        dedupe_key = branch_dedupe_key(branch_spec, new_variant, branch_spec["asset"], branch_spec["timeframe"])
        if dedupe_key in recent_queue_keys(conn, limit=50):
            log_event(conn, "branch_duplicate_skipped", "frodex", f"Skipped duplicate auto-branch {branch_spec['id']}", step="dedupe", artifact_id=queue_item["id"], metadata={"dedupe_key": dedupe_key})
        else:
            novelty = novelty_score_for_spec(conn, branch_spec, branch_spec["asset"], branch_spec["timeframe"])
            qid, was_created = enqueue_item(
                conn,
                {
                "cycle_id": queue_item.get("cycle_id"),
                "spec_path": branch_path,
                "strategy_spec_id": branch_spec["id"],
                "variant_id": str(branch_spec["variants"][0].get("name") or "default"),
                "asset": branch_spec["asset"],
                "timeframe": branch_spec["timeframe"],
                "stage": "screen",
                "bucket": "refine",
                "priority": 4,
                "mutation_type": "asset_transfer",
                "family_generation": next_generation,
                "parent_result_id": parent_result_id,
                "strategy_family": family,
                "source_queue_id": queue_item["id"],
                "notes": json.dumps({"message": "auto branch validation asset transfer", "dedupe_key": dedupe_key}),
                "novelty_score": novelty,
            },
            )
        if was_created:
            created.append(qid)
    return created


def queue_reduced_complexity_variant(conn, queue_item, spec, full_result):
    variants = spec.get("variants") or [{}]
    base_variant = copy.deepcopy(variants[0])
    indicators = list(spec.get("indicators") or [])
    reduced_spec = copy.deepcopy(spec)
    if indicators:
        reduced_spec["indicators"] = indicators[:-1]
    for side in ("long", "short"):
        rules = list((reduced_spec.get("entry_rules") or {}).get(side) or []) if isinstance(reduced_spec.get("entry_rules"), dict) else None
        if rules:
            reduced_spec["entry_rules"][side] = rules[:-1]
            break
    base_variant["name"] = str(base_variant.get("name") or queue_item["variant_id"]) + "_reduced"
    next_generation = int(queue_item.get("family_generation") or 1) + 1
    out_path, out_spec = write_generated_spec(
        reduced_spec,
        queue_item["spec_path"],
        queue_item["asset"],
        queue_item["timeframe"],
        base_variant,
        "param_tweak",
        next_generation,
        full_result.get("result_id"),
    )
    qid, created = enqueue_item(
        conn,
        {
            "cycle_id": queue_item.get("cycle_id"),
            "spec_path": out_path,
            "strategy_spec_id": out_spec["id"],
            "variant_id": base_variant["name"],
            "asset": out_spec["asset"],
            "timeframe": out_spec["timeframe"],
            "stage": "screen",
            "bucket": "refine",
            "priority": 1,
            "mutation_type": "param_tweak",
            "family_generation": next_generation,
            "parent_result_id": full_result.get("result_id"),
            "strategy_family": queue_item.get("strategy_family") or derive_family_name(spec),
            "source_queue_id": queue_item["id"],
            "notes": "reduced complexity promote branch",
        },
    )
    return [qid] if created else []


def family_refinement_owned(conn, family):
    if not family:
        return False
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM backtest_results WHERE lower(COALESCE(strategy_family,'')) = lower(?) AND refinement_status IS NOT NULL",
            (family,),
        ).fetchone()
        return bool(row and int(row[0] or 0) > 0)
    except sqlite3.OperationalError:
        return False


def note_leaderboard_candidate(full_result, spec):
    status = load_json(QUANDALF_JOURNAL_STATUS, default={})
    candidates = status.get("leaderboard_candidates") or []
    candidates.append(
        {
            "ts_iso": now_iso(),
            "result_id": full_result.get("result_id"),
            "strategy_spec_id": spec.get("id"),
            "asset": spec.get("asset"),
            "timeframe": spec.get("timeframe"),
            "qscore": (full_result.get("outofsample") or {}).get("qscore"),
            "degradation_pct": full_result.get("degradation_pct"),
        }
    )
    status["leaderboard_candidates"] = candidates[-20:]
    write_json(QUANDALF_JOURNAL_STATUS, status)


def execute_job(job):
    cmd = [
        sys.executable,
        BACKTESTER,
        "--asset",
        job["asset"],
        "--tf",
        job["timeframe"],
        "--strategy-spec",
        job["spec_path"],
        "--variant",
        job["variant_id"],
        "--stage",
        job["stage"],
    ]
    if job.get("strategy_family"):
        cmd.extend(["--strategy-family", job["strategy_family"]])
    if job.get("parent_result_id"):
        cmd.extend(["--parent-id", job["parent_result_id"]])
    if job.get("mutation_type"):
        cmd.extend(["--mutation-type", job["mutation_type"]])
    if job.get("validation_target"):
        cmd.extend(["--validation-target", job["validation_target"]])
    if job.get("family_generation"):
        cmd.extend(["--family-generation", str(job["family_generation"])])
    if job.get("refinement_round") is not None:
        cmd.extend(["--refinement-round", str(job["refinement_round"])])

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return {"ok": False, "job": job, "error": str(e)}

    payload = parse_json_from_output(proc.stdout or "")
    if proc.returncode != 0:
        return {"ok": False, "job": job, "returncode": proc.returncode, "stdout": (proc.stdout or "")[:1200], "stderr": (proc.stderr or "")[:1200], "payload": payload}
    if not payload:
        return {"ok": False, "job": job, "error": "engine_output_json_not_found", "stdout": (proc.stdout or "")[:1200], "stderr": (proc.stderr or "")[:1200]}
    return {"ok": True, "job": job, "payload": payload, "stdout": (proc.stdout or "")[:1200], "stderr": (proc.stderr or "")[:1200], "result_id": payload.get("result_id")}


def run_stage_jobs(jobs, concurrency):
    if not jobs:
        return []
    results = []
    with ThreadPoolExecutor(max_workers=max(1, concurrency)) as pool:
        futures = [pool.submit(execute_job, job) for job in jobs]
        for future in as_completed(futures):
            results.append(future.result())
    return results


def near_pass_priority(payload):
    qs = ((payload.get("outofsample") or {}).get("qscore") or 0)
    return 2 if 0.4 <= qs < 0.5 else None


def process_result_effects(conn, queue_item, result):
    payload = result.get("payload") or {}
    spec = load_spec(queue_item["spec_path"])
    if queue_item["stage"] == "screen":
        if payload.get("screen_passed"):
            priority = 2 if near_pass_priority(payload) else 3
            enqueue_item(
                conn,
                {
                    "cycle_id": queue_item.get("cycle_id"),
                    "spec_path": queue_item["spec_path"],
                    "strategy_spec_id": queue_item["strategy_spec_id"],
                    "variant_id": queue_item["variant_id"],
                    "asset": queue_item["asset"],
                    "timeframe": queue_item["timeframe"],
                    "stage": "full",
                    "bucket": queue_item.get("bucket") or "explore",
                    "priority": priority,
                    "mutation_type": queue_item.get("mutation_type") or "screen_passed",
                    "family_generation": int(queue_item.get("family_generation") or 1),
                    "parent_result_id": queue_item.get("parent_result_id"),
                    "strategy_family": queue_item.get("strategy_family") or derive_family_name(spec),
                    "source_queue_id": queue_item["id"],
                    "notes": "queued from screen pass",
                },
            )
            return {"screen_to_full": True}
        log_event(conn, "screen_failed", "frodex", f"Screen failed for {queue_item['strategy_spec_id']}:{queue_item['variant_id']}", severity="warn", step="screen", artifact_id=queue_item["id"])
        return {"screen_to_full": False}

    if queue_item["stage"] == "full":
        out = payload.get("outofsample") or {}
        qs = float(out.get("qscore") or 0)
        degradation = float(payload.get("degradation_pct") or 0)
        passed = qs >= 0.5 and degradation < 50.0
        promoted = qs >= 1.5 and degradation < 30.0
        effects = {"full_pass": passed, "promote": promoted, "branch_queue_ids": [], "validation_queue_ids": [], "reduced_queue_ids": []}
        if passed:
            effects["validation_queue_ids"] = queue_validation_items(conn, queue_item, spec, payload, promote=promoted)
            if family_refinement_owned(conn, queue_item.get("strategy_family") or derive_family_name(spec)):
                log_event(conn, "funnel_branch_skip_refinement_owned", "frodex", f"Skipped auto-branch for refinement-owned family {(queue_item.get('strategy_family') or derive_family_name(spec))}", step="full", artifact_id=payload.get("result_id"))
            else:
                effects["branch_queue_ids"] = queue_branch_items(conn, queue_item, spec, payload)
            log_event(conn, "funnel_full_pass", "frodex", f"Full PASS {queue_item['strategy_spec_id']}:{queue_item['variant_id']} QS={qs:.3f} degradation={degradation:.1f}%", step="full", artifact_id=payload.get("result_id"))
        else:
            log_event(conn, "funnel_full_fail", "frodex", f"Full FAIL {queue_item['strategy_spec_id']}:{queue_item['variant_id']} QS={qs:.3f} degradation={degradation:.1f}%", severity="warn", step="full", artifact_id=payload.get("result_id"))
        if promoted:
            effects["reduced_queue_ids"] = queue_reduced_complexity_variant(conn, queue_item, spec, payload)
            note_leaderboard_candidate(payload, spec)
            log_event(conn, "leaderboard_candidate", "quandalf", f"Promote candidate {queue_item['strategy_spec_id']} queued for full validation", step="promote", artifact_id=payload.get("result_id"))
        return effects

    if queue_item["stage"] == "validation":
        log_event(conn, "validation_complete", "frodex", f"Validation complete for {queue_item['strategy_spec_id']}:{queue_item['variant_id']} on {queue_item['asset']}/{queue_item['timeframe']}", step="validation", artifact_id=payload.get("result_id"))
        return {"validation_complete": True}

    return {}


def run_parallel_cycle(conn, cycle_id=None, dry_run=False, parent_run_id=None, max_parallel=None, max_jobs=None, apply_effects=True):
    ensure_schema(conn)
    quotas = bucket_quota(SCREEN_LIMIT + FULL_LIMIT + VALIDATION_LIMIT)
    bucket_used = {k: 0 for k in quotas}
    stage_used = {"screen": 0, "full": 0, "validation": 0}

    selected = []
    primary_bucket_used = {k: 0 for k in quotas}
    primary_stage_used = {"screen": 0, "full": 0, "validation": 0}
    for stage in ("screen", "full", "validation"):
        selected.extend(pick_stage_batch(conn, fetch_candidates(conn, cycle_id=cycle_id, stage=stage), stage, quotas, primary_bucket_used, primary_stage_used, allow_bucket_override=False))

    bucket_used = dict(primary_bucket_used)
    stage_used = dict(primary_stage_used)
    for stage in ("screen", "full", "validation"):
        selected.extend([item for item in pick_stage_batch(conn, fetch_candidates(conn, cycle_id=cycle_id, stage=stage), stage, quotas, bucket_used, stage_used, allow_bucket_override=True) if item["id"] not in {s["id"] for s in selected}])
    if not apply_effects and max_jobs is not None:
        selected = []
        remaining = int(max_jobs)
        for stage in ("screen", "full", "validation"):
            if remaining <= 0:
                break
            items = fetch_candidates(conn, cycle_id=cycle_id, stage=stage)
            selected.extend(items[:remaining])
            remaining -= min(len(items), remaining)
        bucket_used = {k: 0 for k in quotas}
        stage_used = {"screen": 0, "full": 0, "validation": 0}
        for item in selected:
            bucket_used[item["bucket"]] = bucket_used.get(item["bucket"], 0) + 1
            stage_used[item["stage"]] = stage_used.get(item["stage"], 0) + 1

    pipeline_id = create_pipeline_run(conn, parent_run_id or "manual", status="running", steps_total=len(selected))
    log_event(conn, "parallel_start", "oragorn", f"Research funnel cycle: selected={len(selected)}", step="start", artifact_id=pipeline_id, metadata={"bucket_quota": quotas, "bucket_used": bucket_used, "stage_used": stage_used, "primary_bucket_used": primary_bucket_used, "primary_stage_used": primary_stage_used})
    conn.commit()

    if dry_run:
        conn.execute("UPDATE pipeline_runs SET ts_iso_end=?, status=?, steps_completed=?, error_message=? WHERE id=?", (now_iso(), "complete", len(selected), "dry_run", pipeline_id))
        conn.commit()
        return {"pipeline_id": pipeline_id, "dry_run": True, "selected": selected, "bucket_quota": quotas, "bucket_used": bucket_used, "stage_used": stage_used, "primary_bucket_used": primary_bucket_used, "primary_stage_used": primary_stage_used}

    ok_count = 0
    fail_count = 0
    all_results = []
    effect_summary = {"screen_to_full": 0, "full_pass": 0, "promote": 0, "branch_specs": 0, "validation_queued": 0, "reduced_queued": 0}

    def finalize_results(results):
        nonlocal ok_count, fail_count
        for result in results:
            queue_item = result["job"]
            all_results.append(result)
            if result.get("ok"):
                ok_count += 1
                effects = process_result_effects(conn, queue_item, result) if apply_effects else {}
                effect_summary["screen_to_full"] += 1 if effects.get("screen_to_full") else 0
                effect_summary["full_pass"] += 1 if effects.get("full_pass") else 0
                effect_summary["promote"] += 1 if effects.get("promote") else 0
                effect_summary["branch_specs"] += len(effects.get("branch_queue_ids") or [])
                effect_summary["validation_queued"] += len(effects.get("validation_queue_ids") or [])
                effect_summary["reduced_queued"] += len(effects.get("reduced_queue_ids") or [])
                mark_done(conn, queue_item["id"], result_id=result.get("result_id"), notes=json.dumps({"status": "ok", "effects": effects}))
                log_event(conn, "parallel_backtest_complete", "frodex", f"{queue_item['stage']} {queue_item['strategy_spec_id']}:{queue_item['variant_id']} complete", step="worker", artifact_id=result.get("result_id"), metadata={"queue_id": queue_item["id"], "stage": queue_item["stage"]})
            else:
                fail_count += 1
                mark_failed_back_to_queue(conn, queue_item["id"], notes=json.dumps({"status": "retry", "error": result.get("error"), "stderr": result.get("stderr")}))
                log_event(conn, "parallel_backtest_fail", "frodex", f"{queue_item['stage']} {queue_item['strategy_spec_id']}:{queue_item['variant_id']} failed", severity="warn", step="worker", artifact_id=queue_item["id"], metadata={"error": result.get("error"), "stderr": result.get("stderr"), "stdout": result.get("stdout")})
            conn.execute("UPDATE pipeline_runs SET steps_completed = COALESCE(steps_completed,0) + 1 WHERE id=?", (pipeline_id,))
            conn.commit()

    remaining_budget = int(max_jobs) if max_jobs is not None else None

    def clip_jobs(items):
        nonlocal remaining_budget
        if remaining_budget is None:
            return items
        if remaining_budget <= 0:
            return []
        clipped = items[:remaining_budget]
        remaining_budget -= len(clipped)
        return clipped

    if not apply_effects and max_jobs is not None:
        screen_jobs = clip_jobs(fetch_candidates(conn, cycle_id=cycle_id, stage="screen"))
        full_jobs = clip_jobs(fetch_candidates(conn, cycle_id=cycle_id, stage="full"))
        validation_jobs = clip_jobs(fetch_candidates(conn, cycle_id=cycle_id, stage="validation"))
        mark_running(conn, screen_jobs)
        finalize_results(run_stage_jobs(screen_jobs, concurrency=1))
        mark_running(conn, full_jobs)
        finalize_results(run_stage_jobs(full_jobs, concurrency=min(FULL_LIMIT, max_parallel or FULL_LIMIT)))
        mark_running(conn, validation_jobs)
        finalize_results(run_stage_jobs(validation_jobs, concurrency=min(VALIDATION_LIMIT, max_parallel or VALIDATION_LIMIT)))
        current_bucket_used = {k: 0 for k in quotas}
        stage_progress = {"screen": len(screen_jobs), "full": len(full_jobs), "validation": len(validation_jobs)}
    else:
        screen_jobs = clip_jobs(pick_stage_batch(conn, fetch_candidates(conn, cycle_id=cycle_id, stage="screen"), "screen", quotas, {k: 0 for k in quotas}, {"screen": 0, "full": 0, "validation": 0}, allow_bucket_override=False))
        mark_running(conn, screen_jobs)
        finalize_results(run_stage_jobs(screen_jobs, concurrency=1))

        current_bucket_used = {k: 0 for k in quotas}
        for item in screen_jobs:
            current_bucket_used[item["bucket"]] += 1
        stage_progress = {"screen": len(screen_jobs), "full": 0, "validation": 0}

        full_jobs = clip_jobs(pick_stage_batch(conn, fetch_candidates(conn, cycle_id=cycle_id, stage="full"), "full", quotas, current_bucket_used, stage_progress, allow_bucket_override=False))
        mark_running(conn, full_jobs)
        finalize_results(run_stage_jobs(full_jobs, concurrency=min(FULL_LIMIT, max_parallel or FULL_LIMIT)))

        validation_jobs = clip_jobs(pick_stage_batch(conn, fetch_candidates(conn, cycle_id=cycle_id, stage="validation"), "validation", quotas, current_bucket_used, stage_progress, allow_bucket_override=False))
        mark_running(conn, validation_jobs)
        finalize_results(run_stage_jobs(validation_jobs, concurrency=min(VALIDATION_LIMIT, max_parallel or VALIDATION_LIMIT)))

    used_summary = {
        "screen": len(screen_jobs),
        "full": len(full_jobs),
        "validation": len(validation_jobs),
    }
    conn.execute("UPDATE pipeline_runs SET ts_iso_end=?, status=?, error_message=? WHERE id=?", (now_iso(), "complete", None, pipeline_id))
    log_event(conn, "parallel_summary", "oragorn", f"Research funnel cycle done: ok={ok_count}, fail={fail_count}", step="summary", artifact_id=pipeline_id, metadata={"effects": effect_summary, "bucket_quota": quotas, "bucket_used": current_bucket_used, "stage_used": used_summary})
    conn.commit()
    return {"pipeline_id": pipeline_id, "total_jobs": len(screen_jobs) + len(full_jobs) + len(validation_jobs), "ok": ok_count, "fail": fail_count, "results": all_results, "bucket_quota": quotas, "bucket_used": current_bucket_used, "stage_used": used_summary, "effects": effect_summary}


def load_job_manifest(path):
    payload = load_manifest(path)
    jobs = payload.get("jobs") or []
    if not isinstance(jobs, list):
        raise ValueError("job manifest missing jobs[]")
    return payload, jobs


def seed_queue_from_job_manifest(conn, manifest_path, cycle_id=None):
    payload, jobs = load_job_manifest(manifest_path)
    effective_cycle_id = cycle_id if cycle_id is not None else (int(payload.get("cycle_id") or 0) or None)
    seeded = []
    for item in jobs:
        entry = dict(item)
        if effective_cycle_id is not None:
            entry["cycle_id"] = effective_cycle_id
        qid, created = enqueue_item(conn, entry)
        if created:
            seeded.append(qid)
    conn.commit()
    return effective_cycle_id, seeded


def queue_snapshot(conn, cycle_id=None):
    ensure_schema(conn)
    params = []
    sql = "SELECT stage, bucket, priority, status, COUNT(*) FROM research_funnel_queue"
    if cycle_id is not None:
        sql += " WHERE cycle_id = ?"
        params.append(int(cycle_id))
    sql += " GROUP BY stage, bucket, priority, status ORDER BY status, bucket, priority, stage"
    rows = conn.execute(sql, params).fetchall()
    return [
        {"stage": row[0], "bucket": row[1], "priority": row[2], "status": row[3], "count": row[4]}
        for row in rows
    ]


def main():
    ap = argparse.ArgumentParser(description="Parallel research funnel runner")
    ap.add_argument("--spec", help="Single strategy spec path")
    ap.add_argument("--variant", default=None, help="Variant name or 'all'")
    ap.add_argument("--batch", nargs="*", help="Multiple spec paths")
    ap.add_argument("--manifest", help="Manifest JSON containing spec_paths/latest_spec_path")
    ap.add_argument("--job-manifest", help="Manifest JSON containing explicit queue jobs")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cycle-id", type=int, default=None)
    ap.add_argument("--seed-only", action="store_true")
    ap.add_argument("--queue-report", action="store_true")
    ap.add_argument("--max-jobs", type=int, default=None)
    ap.add_argument("--no-funnel-effects", action="store_true")
    args = ap.parse_args()

    mode, throttle_parallel = read_throttle()
    max_parallel = max(1, throttle_parallel)
    parent_run_id = f"parallel_{uuid.uuid4().hex[:8]}"
    cycle_id = args.cycle_id
    if cycle_id is None and args.manifest and os.path.exists(args.manifest):
        cycle_id = int((load_manifest(args.manifest).get("cycle_id") or 0) or 0) or None
    if cycle_id is None and args.job_manifest and os.path.exists(args.job_manifest):
        cycle_id = int((load_job_manifest(args.job_manifest)[0].get("cycle_id") or 0) or 0) or None

    spec_paths = []
    try:
        if args.manifest:
            spec_paths.extend(expand_manifest_specs(args.manifest))
        elif args.spec:
            spec_paths.append(resolve_spec_path(args.spec))
        elif args.batch:
            for sp in args.batch:
                spec_paths.append(resolve_spec_path(sp))
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 1

    conn = sqlite3.connect(DB)
    ensure_schema(conn)
    seeded = []
    if args.job_manifest:
        cycle_id, seeded = seed_queue_from_job_manifest(conn, args.job_manifest, cycle_id=cycle_id)
    elif spec_paths:
        seeded = seed_queue_from_specs(conn, spec_paths, variant_mode=args.variant, cycle_id=cycle_id)
    if args.seed_only:
        out = {"status": "seeded", "seeded": len(seeded), "queue": queue_snapshot(conn, cycle_id=cycle_id), "cycle_id": cycle_id}
        conn.close()
        print(json.dumps(out, indent=2))
        return 0
    if args.queue_report:
        out = {"status": "queue_report", "queue": queue_snapshot(conn, cycle_id=cycle_id), "cycle_id": cycle_id}
        conn.close()
        print(json.dumps(out, indent=2))
        return 0

    run_out = run_parallel_cycle(conn, cycle_id=cycle_id, dry_run=args.dry_run, parent_run_id=parent_run_id, max_parallel=max_parallel, max_jobs=args.max_jobs, apply_effects=(not args.no_funnel_effects))
    run_out["mode"] = mode
    run_out["max_parallel"] = max_parallel
    run_out["seeded"] = len(seeded)
    run_out["queue_after"] = queue_snapshot(conn, cycle_id=cycle_id)
    conn.close()
    print(json.dumps(run_out, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
