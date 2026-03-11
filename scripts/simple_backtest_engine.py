#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone

import walk_forward_engine as wfe

DB_PATH = wfe.DB_PATH


def build_simple_result(candles, strategy, asset, timeframe, stage):
    policy = wfe.load_train_test_policy(timeframe)
    if stage == "screen":
        train_days = int(policy.get("train_days") or wfe.WINDOW_CONFIG.get(timeframe, (90, 21))[0])
        cpd = {"1d": 1, "4h": 6, "1h": 24, "15m": 96, "5m": 288, "1m": 1440}.get(timeframe, 6)
        keep = min(len(candles), max(1, train_days * cpd))
        test_candles = candles[-keep:]
        config = {"mode": "train_gate", "train_days": train_days}
    else:
        test_candles = candles
        config = {"mode": "simple_full_history"}

    metrics = wfe.run_strategy_on_candles(test_candles, strategy)
    qscore = wfe.calculate_qscore(metrics)
    regime_payload = wfe.get_regime_tags(asset, timeframe, candles=test_candles, force=True)
    regime_scores, regime_concentration, primary_regime, regime_flags = wfe.compute_regime_scores(metrics["trades"], regime_payload)

    out = {
        "total_trades": int(metrics.get("total_trades") or 0),
        "profit_factor": float(metrics.get("profit_factor") or 0.0),
        "max_drawdown_pct": float(metrics.get("max_drawdown_pct") or 0.0),
        "total_return_pct": float(metrics.get("total_return_pct") or 0.0),
        "win_rate_pct": float(metrics.get("win_rate_pct") or 0.0),
        "avg_trade_pct": float(metrics.get("avg_trade_pct") or 0.0),
        "sharpe_ratio": float(metrics.get("sharpe_ratio") or 0.0),
        "qscore": float(qscore.get("score_total") or 0.0),
        "decision": str(qscore.get("score_decision") or "fail"),
        "grade": str(qscore.get("score_grade") or "D"),
        "flags": qscore.get("score_flags") or "[]",
    }
    train_gate = metrics["total_trades"] >= int(policy.get("min_train_trades") or wfe.SCREEN_MIN_TRADES) and float(qscore.get("score_total") or 0.0) >= float(policy.get("train_qscore_gate") or 1.0)
    # simple engine treats insample and outofsample identically to avoid walk-forward complexity
    result = {
        "status": "ok",
        "screen_passed": train_gate,
        "folds": 1,
        "fold_results": [
            {
                "fold": 1,
                "train_candles": len(test_candles),
                "blind_candles": len(test_candles),
                "best_params": None,
                "insample": {
                    "trades": out["total_trades"],
                    "pf": out["profit_factor"],
                    "max_dd": out["max_drawdown_pct"],
                    "qscore": out["qscore"],
                },
                "outofsample": {
                    "trades": out["total_trades"],
                    "pf": out["profit_factor"],
                    "max_dd": out["max_drawdown_pct"],
                    "qscore": out["qscore"],
                },
            }
        ],
        "insample_aggregate": dict(out),
        "outofsample_aggregate": dict(out),
        "degradation_pct": 0.0,
        "walk_forward_config": {**config, "min_train_trades": int(policy.get("min_train_trades") or wfe.SCREEN_MIN_TRADES), "train_qscore_gate": float(policy.get("train_qscore_gate") or 1.0)},
        "regime_scores": regime_scores,
        "regime_concentration": regime_concentration,
        "primary_regime": primary_regime,
    }
    flags = sorted(set(json.loads(out["flags"]) + regime_flags))
    result["insample_aggregate"]["flags"] = json.dumps(flags)
    result["outofsample_aggregate"]["flags"] = json.dumps(flags)
    return result


def main():
    ap = argparse.ArgumentParser(description="Simple Backtest Engine for AutoQuant")
    ap.add_argument("--asset", required=True)
    ap.add_argument("--tf", required=True)
    ap.add_argument("--strategy-spec", required=True)
    ap.add_argument("--variant", default="default")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-db", action="store_true")
    ap.add_argument("--stage", default="full", choices=["full", "screen", "validation"])
    ap.add_argument("--strategy-family", default="")
    ap.add_argument("--parent-id", default="")
    ap.add_argument("--mutation-type", default="")
    ap.add_argument("--validation-target", default="")
    ap.add_argument("--family-generation", type=int, default=1)
    ap.add_argument("--refinement-round", type=int, default=0)
    args = ap.parse_args()

    try:
        strategy = wfe.parse_strategy_spec(args.strategy_spec, args.variant)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Failed to load strategy spec: {e}"}))
        return 1

    spec_id = os.path.basename(args.strategy_spec).replace(".strategy_spec.json", "").replace(".json", "")
    fallback_source = 1 if str((strategy.get("spec") or {}).get("source") or "").strip().lower() == "fallback_cooker" or bool((strategy.get("spec") or {}).get("fallback_source")) else 0

    if args.dry_run:
        print(json.dumps({
            "status": "dry_run",
            "asset": args.asset,
            "timeframe": args.tf,
            "strategy": strategy["strategy_name"],
            "variant": args.variant,
            "stage": args.stage,
            "spec_id": spec_id,
            "engine": "simple_backtest_engine"
        }, indent=2))
        return 0

    try:
        candles = wfe.load_candles(args.asset, args.tf)
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1

    stage = "full" if args.stage == "validation" else args.stage
    result = build_simple_result(candles, strategy, args.asset, args.tf, stage)

    if not args.no_db:
        try:
            conn = sqlite3.connect(DB_PATH)
            save_outcome = wfe.save_result(
                conn,
                spec_id,
                args.variant,
                args.asset,
                args.tf,
                result,
                candles,
                stage=args.stage,
                strategy_family=args.strategy_family or None,
                parent_id=args.parent_id or None,
                mutation_type=args.mutation_type or None,
                validation_target=args.validation_target or None,
                family_generation=args.family_generation,
                refinement_round=args.refinement_round,
                fallback_source=fallback_source,
            )
            conn.close()
            if isinstance(save_outcome, dict) and save_outcome.get("status") == "skipped":
                result["status"] = "skipped"
                result["result_id"] = None
                result["db_saved"] = False
                result["integrity_issue"] = save_outcome
            else:
                result["result_id"] = save_outcome
                result["db_saved"] = True
        except Exception as e:
            result["db_saved"] = False
            result["db_error"] = str(e)

    output = {
        "status": result["status"],
        "asset": args.asset,
        "timeframe": args.tf,
        "strategy": strategy["strategy_name"],
        "variant": args.variant,
        "stage": args.stage,
        "engine": "simple_backtest_engine",
        "screen_passed": result.get("screen_passed"),
        "folds": result["folds"],
        "insample": result["insample_aggregate"],
        "outofsample": result["outofsample_aggregate"],
        "degradation_pct": result["degradation_pct"],
        "walk_forward_config": result["walk_forward_config"],
        "regime_scores": result.get("regime_scores"),
        "regime_concentration": result.get("regime_concentration"),
        "primary_regime": result.get("primary_regime"),
        "result_id": result.get("result_id"),
        "db_saved": result.get("db_saved", False),
        "integrity_issue": result.get("integrity_issue"),
        "reason": (result.get("integrity_issue") or {}).get("reason") if isinstance(result.get("integrity_issue"), dict) else None,
        "fold_summary": [
            {
                "fold": fr["fold"],
                "is_pf": (fr.get("insample") or {}).get("pf"),
                "is_qs": (fr.get("insample") or {}).get("qscore"),
                "oos_pf": fr["outofsample"]["pf"],
                "oos_qs": fr["outofsample"]["qscore"],
                "oos_trades": fr["outofsample"]["trades"],
            }
            for fr in result["fold_results"]
        ],
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
