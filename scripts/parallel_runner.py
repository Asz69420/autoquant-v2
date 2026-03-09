#!/usr/bin/env python3
import argparse
import json
import multiprocessing as mp
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone


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

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
THROTTLE = os.path.join(ROOT, "config", "throttle.json")
BACKTESTER = r"C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\walk_forward_engine.py"
CURRENT_CYCLE_SPECS = os.path.join(ROOT, "data", "state", "current_cycle_specs.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


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
        return []  # Empty manifest is allowed (agent may not have completed or no orders issued)
    normalized = []
    for item in spec_paths:
        path = str(item).strip()
        if not path:
            continue
        if not os.path.exists(path):
            raise FileNotFoundError(f"manifest spec path missing: {path}")
        normalized.append(path)
    return normalized  # Return empty list if no specs (allowed, just means nothing to backtest)


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
        (
            pid,
            now_iso(),
            "parallel_runner",
            "parallel",
            pid,
            parent_run_id,
            status,
            steps_total,
            0,
        ),
    )
    return pid


def worker(job):
    spec_path = job["spec_path"]
    variant = job["variant"]
    asset = job["asset"]
    tf = job["timeframe"]
    spec_id = job["strategy_spec_id"]

    cmd = [
        sys.executable,
        BACKTESTER,
        "--asset",
        asset,
        "--tf",
        tf,
        "--strategy-spec",
        spec_path,
        "--variant",
        variant,
    ]

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    except Exception as e:
        return {"ok": False, "job": job, "error": str(e)}

    stdout_text = (proc.stdout or "").strip()
    stderr_text = (proc.stderr or "").strip()

    if proc.returncode != 0:
        return {
            "ok": False,
            "job": job,
            "stdout": stdout_text[:1000],
            "stderr": stderr_text[:1000],
            "returncode": proc.returncode,
        }

    payload = parse_json_from_output(stdout_text)
    if not payload:
        return {
            "ok": False,
            "job": job,
            "error": "engine_output_json_not_found",
            "stdout": stdout_text[:1000],
            "stderr": stderr_text[:1000],
        }

    outofsample = payload.get("outofsample") if isinstance(payload.get("outofsample"), dict) else {}
    qscore = outofsample.get("qscore")
    max_dd = outofsample.get("max_drawdown_pct")
    pf = outofsample.get("profit_factor")
    result_id = payload.get("result_id")

    db_result_id = None
    try:
        conn = sqlite3.connect(DB)
        row = conn.execute(
            """
            SELECT id
            FROM backtest_results
            WHERE strategy_spec_id = ? AND variant_id = ? AND asset = ? AND timeframe = ?
            ORDER BY ts_iso DESC LIMIT 1
            """,
            (spec_id, variant, asset, tf),
        ).fetchone()
        conn.close()
        if row:
            db_result_id = row[0]
    except Exception:
        db_result_id = None

    return {
        "ok": True,
        "job": job,
        "result_id": db_result_id or result_id,
        "artifact_result_id": result_id,
        "backtest_result_path": None,
        "trade_list_path": None,
        "qscore": qscore,
        "max_dd": max_dd,
        "pf": pf,
        "stdout": stdout_text[:1000],
        "stderr": stderr_text[:1000],
        "payload": payload,
    }


def build_jobs_for_spec(spec_path, variant_mode):
    spec_id = os.path.basename(spec_path).replace(".strategy_spec.json", "")

    if not os.path.exists(spec_path):
        raise FileNotFoundError(f"strategy spec not found: {spec_path}")

    spec = load_spec(spec_path)
    asset = spec.get("asset", "ETH")
    tf = spec.get("timeframe", "4h")
    variants = spec.get("variants", []) or []

    if variant_mode == "all":
        vnames = [v.get("name", "default") for v in variants]
    elif variant_mode:
        vnames = [variant_mode]
    else:
        vnames = [variants[0].get("name", "default")] if variants else ["default"]

    jobs = []
    for vn in vnames:
        jobs.append(
            {
                "spec_path": spec_path,
                "strategy_spec_id": spec_id,
                "variant": vn,
                "asset": asset,
                "timeframe": tf,
            }
        )
    return jobs


def run_parallel(jobs, max_parallel, dry_run=False, parent_run_id=None):
    conn = sqlite3.connect(DB)
    pipeline_id = create_pipeline_run(conn, parent_run_id or "manual", status="running", steps_total=len(jobs))
    log_event(conn, "parallel_start", "oragorn", f"Parallel run started: {len(jobs)} jobs, max_parallel={max_parallel}", step="start", artifact_id=pipeline_id)
    conn.commit()

    if dry_run:
        conn.execute(
            "UPDATE pipeline_runs SET ts_iso_end=?, status=?, steps_completed=?, error_message=? WHERE id=?",
            (now_iso(), "complete", len(jobs), "dry_run", pipeline_id),
        )
        log_event(conn, "parallel_dry_run", "oragorn", f"Dry-run only: {len(jobs)} jobs", step="summary", artifact_id=pipeline_id)
        conn.commit()
        conn.close()
        return {"dry_run": True, "jobs": jobs, "pipeline_id": pipeline_id}

    results = []
    with mp.Pool(processes=max_parallel) as pool:
        for res in pool.imap_unordered(worker, jobs):
            results.append(res)
            if res.get("ok"):
                log_event(
                    conn,
                    "parallel_backtest_complete",
                    "frodex",
                    f"{res['job']['strategy_spec_id']}:{res['job']['variant']} QS={res.get('qscore', 0)} DD={res.get('max_dd', 0)}",
                    step="worker",
                    artifact_id=res.get("result_id"),
                )
            else:
                log_event(
                    conn,
                    "parallel_backtest_fail",
                    "frodex",
                    f"{res['job']['strategy_spec_id']}:{res['job']['variant']} failed",
                    severity="warn",
                    step="worker",
                    artifact_id=res['job'].get('strategy_spec_id'),
                    metadata={"error": res.get("error"), "stderr": res.get("stderr")},
                )
            conn.execute("UPDATE pipeline_runs SET steps_completed = COALESCE(steps_completed,0) + 1 WHERE id=?", (pipeline_id,))
            conn.commit()

    dd_breaker = any((r.get("max_dd") or 0) > 25 for r in results if r.get("ok"))
    ok_count = sum(1 for r in results if r.get("ok"))
    fail_count = len(results) - ok_count

    log_event(
        conn,
        "parallel_summary",
        "oragorn",
        f"Parallel done: ok={ok_count}, fail={fail_count}, dd_breaker={dd_breaker}",
        severity="warn" if dd_breaker else "info",
        step="summary",
        artifact_id=pipeline_id,
    )

    conn.execute(
        "UPDATE pipeline_runs SET ts_iso_end=?, status=?, error_message=? WHERE id=?",
        (now_iso(), "complete", "DD circuit breaker triggered" if dd_breaker else None, pipeline_id),
    )
    conn.commit()
    conn.close()

    return {
        "pipeline_id": pipeline_id,
        "total_jobs": len(jobs),
        "ok": ok_count,
        "fail": fail_count,
        "dd_circuit_breaker": dd_breaker,
        "results": results,
    }


def main():
    ap = argparse.ArgumentParser(description="Parallel backtest runner")
    ap.add_argument("--spec", help="Single strategy spec path")
    ap.add_argument("--variant", default=None, help="Variant name or 'all'")
    ap.add_argument("--batch", nargs="*", help="Multiple spec paths")
    ap.add_argument("--manifest", help="Manifest JSON containing spec_paths/latest_spec_path")
    ap.add_argument("--grind", help="Spec path for iterative grind")
    ap.add_argument("--max-iters", type=int, default=5)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    mode, max_parallel = read_throttle()
    parent_run_id = f"parallel_{uuid.uuid4().hex[:8]}"

    jobs = []
    try:
        if args.manifest:
            for sp in expand_manifest_specs(args.manifest):
                jobs.extend(build_jobs_for_spec(sp, args.variant))
        elif args.spec:
            jobs.extend(build_jobs_for_spec(resolve_spec_path(args.spec), args.variant))
        elif args.batch:
            for sp in args.batch:
                jobs.extend(build_jobs_for_spec(resolve_spec_path(sp), None))
        elif args.grind:
            # Simplified grind: repeat same spec job graph up to max-iters
            resolved_grind = resolve_spec_path(args.grind)
            for _ in range(max(1, args.max_iters)):
                jobs.extend(build_jobs_for_spec(resolved_grind, "all"))
        else:
            ap.error("Use one of --spec, --batch, --manifest, or --grind")
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return 1

    out = run_parallel(jobs, max_parallel=max_parallel, dry_run=args.dry_run, parent_run_id=parent_run_id)
    out["mode"] = mode
    out["max_parallel"] = max_parallel
    print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
