#!/usr/bin/env python3
import json
import os
import sqlite3
import sys
from datetime import datetime, timezone, timedelta

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")


def main():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=60)).isoformat()

    recent = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
               total_return_pct, score_total, score_decision,
               metrics, regime_metrics
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
    for r in recent:
        entry = dict(r)
        for key in ["metrics", "regime_metrics"]:
            if entry.get(key):
                try:
                    entry[key] = json.loads(entry[key])
                except Exception:
                    pass
        results.append(entry)

    packet = {
        "ts_iso": datetime.now(timezone.utc).isoformat(),
        "type": "reflection",
        "recent_results": results,
        "recent_lessons": [{"observation": l["observation"], "implication": l["implication"]} for l in lessons],
        "result_count": len(results),
        "any_promising": any(
            r.get("profit_factor") and r["profit_factor"] > 0.8 and r.get("total_trades") and r["total_trades"] > 10
            for r in results
        ),
        "best_pf": max((r.get("profit_factor") or 0 for r in results), default=0),
        "best_qscore": max((r.get("score_total") or 0 for r in results), default=0),
    }

    path = os.path.join(ROOT, "agents", "quandalf", "memory", "reflection_packet.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(packet, f, indent=2)

    print(json.dumps({"status": "ready", "path": path, "results": len(results), "any_promising": packet["any_promising"]}))


if __name__ == "__main__":
    sys.exit(main() or 0)
