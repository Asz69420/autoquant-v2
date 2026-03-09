#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
PY = sys.executable
BACKTESTER = os.path.join(ROOT, "scripts", "walk_forward_engine.py")
BALROG = os.path.join(ROOT, "scripts", "balrog-validate.py")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
REFLECTION_SCRIPT = os.path.join(ROOT, "scripts", "build-reflection-packet.py")
BRIEFING_SCRIPT = os.path.join(ROOT, "scripts", "research-cycle.py")
POSTPROCESS_SCRIPT = os.path.join(ROOT, "scripts", "cycle-postprocess.py")

QUANDALF_RESEARCH_JOB = "bbfbe68d-00b8-46cf-a4d3-ad77b204368d"
QUANDALF_REFLECT_JOB = "999d2e18-8ea7-4bd9-ac3f-332cd1797cc1"


def send_tg(message, bot="oragorn", channel="dm"):
    try:
        subprocess.run(
            [PY, TG_SCRIPT, "--message", message, "--bot", bot, "--channel", channel],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        pass


def send_log(message):
    try:
        subprocess.run(
            [PY, TG_SCRIPT, "--message", f"<pre>{message}</pre>", "--bot", "logron", "--channel", "log"],
            capture_output=True,
            text=True,
            timeout=15,
        )
    except Exception:
        pass


def log_event(event_type, agent, message, severity="info"):
    try:
        conn = sqlite3.connect(DB)
        conn.execute(
            "INSERT INTO event_log (ts_iso, event_type, agent, severity, message) VALUES (?, ?, ?, ?, ?)",
            (datetime.now(timezone.utc).isoformat(), event_type, agent, severity, message),
        )
        conn.commit()
        conn.close()
    except Exception:
        pass


def run_script(script_path, args=None, timeout=120):
    cmd = [PY, script_path]
    if args:
        cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=ROOT)
        return result.returncode == 0, result.stdout
    except Exception as e:
        return False, str(e)


def trigger_quandalf(job_id, timeout=360):
    try:
        result = subprocess.run(
            ["openclaw", "cron", "run", job_id, "--expect-final", "--timeout", "300000"],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=ROOT,
        )
        return result.returncode == 0
    except Exception:
        return False


def find_new_specs(since_seconds=600):
    new_specs = []
    cutoff = time.time() - since_seconds
    if not os.path.exists(SPECS_DIR):
        return new_specs
    for f in os.listdir(SPECS_DIR):
        if not f.endswith(".strategy_spec.json"):
            continue
        path = os.path.join(SPECS_DIR, f)
        try:
            if os.path.getmtime(path) > cutoff:
                new_specs.append(path)
        except OSError:
            continue
    return new_specs


def backtest_spec(spec_path):
    results = []
    try:
        with open(spec_path, "r", encoding="utf-8") as f:
            spec = json.load(f)
    except Exception:
        return results

    balrog = subprocess.run([PY, BALROG, "--spec", spec_path], capture_output=True, text=True, timeout=30)
    if balrog.returncode != 0:
        log_event("balrog_block", "balrog", f"Blocked: {os.path.basename(spec_path)}", "warn")
        return results

    asset = spec.get("asset", "ETH")
    timeframe = spec.get("timeframe", "4h")

    for v in spec.get("variants", []):
        vname = v.get("name", "default")
        try:
            result = subprocess.run(
                [
                    PY,
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
                conn = sqlite3.connect(DB)
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM backtest_results ORDER BY ts_iso DESC LIMIT 1").fetchone()
                conn.close()
                if row:
                    rowd = dict(row)
                    results.append(rowd)
                    pf = rowd.get("profit_factor") or 0
                    qs = rowd.get("score_total") or 0
                    log_event("backtest_complete", "frodex", f"{asset}/{timeframe} {vname}: PF {pf:.3f}, QS {qs:.2f}")
        except Exception as e:
            log_event("backtest_error", "frodex", f"Error: {vname}: {e}", "error")
    return results


def get_best(results, key):
    if not results:
        return 0
    return max((r.get(key, 0) or 0) for r in results)


def main():
    p = argparse.ArgumentParser(description="AutoQuant Grind Loop")
    p.add_argument("--target-qscore", type=float, default=3.0)
    p.add_argument("--max-iterations", type=int, default=20)
    p.add_argument("--max-hours", type=float, default=6.0)
    a = p.parse_args()

    start_time = time.time()
    max_seconds = a.max_hours * 3600
    iteration = 0
    best_qs = 0
    best_pf = 0
    all_results = []
    target_hit = False

    send_tg(
        f"🔥 <b>Grind Mode Activated</b>\n\nTarget: QScore >= {a.target_qscore}\nMax iterations: {a.max_iterations}\nMax time: {a.max_hours}h"
    )
    send_log(f"🔥 Grind Mode\n Target QS: {a.target_qscore}\n Max iters: {a.max_iterations}")
    log_event("grind_start", "oragorn", f"Grind: target QS {a.target_qscore}, max {a.max_iterations} iters")

    while iteration < a.max_iterations:
        elapsed = time.time() - start_time
        if elapsed > max_seconds:
            send_tg(
                f"⏰ Grind stopped: time limit ({a.max_hours}h)\nIterations: {iteration}\nBest QS: {best_qs:.2f} | Best PF: {best_pf:.3f}"
            )
            break

        iteration += 1
        cycle_start = time.time()

        # Phase 1: Briefing
        run_script(BRIEFING_SCRIPT, timeout=60)

        # Phase 2: Quandalf designs or reflects
        if iteration == 1:
            send_log(f"🧙 Grind #{iteration}: Designing...")
            trigger_quandalf(QUANDALF_RESEARCH_JOB)
        else:
            run_script(REFLECTION_SCRIPT, timeout=30)
            send_log(f"🔮 Grind #{iteration}: Reflecting + refining...")
            trigger_quandalf(QUANDALF_REFLECT_JOB)

        # Phase 3: Find and backtest new specs
        time.sleep(5)
        new_specs = find_new_specs(since_seconds=600)
        cycle_results = []
        for spec_path in new_specs:
            results = backtest_spec(spec_path)
            cycle_results.extend(results)
            all_results.extend(results)

        # Phase 4: Extract lessons
        run_script(POSTPROCESS_SCRIPT, ["--since-minutes", "10"], timeout=120)

        # Phase 5: Evaluate
        cycle_qs = get_best(cycle_results, "score_total")
        cycle_pf = get_best(cycle_results, "profit_factor")
        best_qs = max(best_qs, cycle_qs)
        best_pf = max(best_pf, cycle_pf)
        cycle_time = int(time.time() - cycle_start)

        emoji = "🟢" if cycle_qs >= a.target_qscore else "🟡" if cycle_pf > 0.8 else "🔴"
        send_log(
            f"{emoji} Grind #{iteration}\n Specs: {len(new_specs)} | Tests: {len(cycle_results)}\n PF: {cycle_pf:.3f} | QS: {cycle_qs:.2f}\n Best: PF {best_pf:.3f} QS {best_qs:.2f}\n Time: {cycle_time}s"
        )

        if cycle_qs >= a.target_qscore:
            send_tg(
                f"🏆 <b>TARGET HIT!</b>\n\nQScore: {cycle_qs:.2f} >= {a.target_qscore}\nPF: {cycle_pf:.3f}\nIterations: {iteration}\nTotal tests: {len(all_results)}"
            )
            log_event("grind_target_hit", "oragorn", f"QScore {cycle_qs:.2f} hit target")
            target_hit = True
            break

        if iteration % 5 == 0:
            send_tg(
                f"⚙️ <b>Grind Progress</b>\n\nIteration: {iteration}/{a.max_iterations}\nBest QS: {best_qs:.2f} / {a.target_qscore}\nBest PF: {best_pf:.3f}\nTotal tests: {len(all_results)}\nElapsed: {int(elapsed/60)}min"
            )

    if not target_hit:
        send_tg(
            f"🛑 <b>Grind Complete</b>\n\nMax iterations ({a.max_iterations})\nBest QS: {best_qs:.2f}\nBest PF: {best_pf:.3f}\nTotal tests: {len(all_results)}"
        )

    log_event("grind_end", "oragorn", f"Grind done: {iteration} iters, best QS {best_qs:.2f}")
    print(
        json.dumps(
            {
                "iterations": iteration,
                "total_backtests": len(all_results),
                "best_qscore": best_qs,
                "best_pf": best_pf,
                "target_hit": target_hit,
            }
        )
    )


if __name__ == "__main__":
    main()
