import json
import math
import pathlib
import subprocess

ROOT = pathlib.Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = "python"

SPECS = [
    ("DOGE", "4h", ROOT / "artifacts/strategy_specs/QD-20260312-C067-DOGE-4H-STATE-CHANGE-HOLD-EXPANSION-v1.strategy_spec.json"),
    ("ETH", "4h", ROOT / "artifacts/strategy_specs/QD-20260312-C067-ETH-4H-EXHAUSTION-REACCEPTANCE-ROTATION-v1.strategy_spec.json"),
    ("TAO", "4h", ROOT / "artifacts/strategy_specs/QD-20260312-C067-TAO-4H-DELAYED-RETEST-CONTINUATION-v1.strategy_spec.json"),
]


def run_json(cmd):
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=True)
    return json.loads(proc.stdout)


def approx_equal(a, b, tol=1e-9):
    return abs(float(a or 0.0) - float(b or 0.0)) <= tol


def main():
    rows = []
    for asset, tf, spec in SPECS:
        simple = run_json([PY, "scripts/simple_backtest_engine.py", "--asset", asset, "--tf", tf, "--strategy-spec", str(spec), "--variant", "default", "--stage", "screen", "--no-db"])
        wf = run_json([PY, "scripts/walk_forward_engine.py", "--asset", asset, "--tf", tf, "--strategy-spec", str(spec), "--variant", "default", "--stage", "screen", "--no-db"])

        s = simple["outofsample"]
        w = wf["outofsample"]
        row = {
            "spec": spec.name,
            "asset": asset,
            "timeframe": tf,
            "simple_trades": s["total_trades"],
            "wf_trades": w["total_trades"],
            "simple_pf": s["profit_factor"],
            "wf_pf": w["profit_factor"],
            "simple_return_pct": s["total_return_pct"],
            "wf_return_pct": w["total_return_pct"],
            "match": (
                int(s["total_trades"]) == int(w["total_trades"])
                and approx_equal(s["profit_factor"], w["profit_factor"])
                and approx_equal(s["total_return_pct"], w["total_return_pct"])
                and approx_equal(s["max_drawdown_pct"], w["max_drawdown_pct"])
            ),
        }
        rows.append(row)

    failures = [r for r in rows if not r["match"]]
    payload = {"status": "ok" if not failures else "mismatch", "rows": rows, "failure_count": len(failures)}
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if not failures else 1)


if __name__ == "__main__":
    main()
