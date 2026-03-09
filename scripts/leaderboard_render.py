#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import subprocess
import sys

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")


def short_name(row):
    base = row.get("variant_id") or row.get("strategy_spec_id") or "STRAT"
    cleaned = "".join(ch for ch in str(base).upper() if ch.isalnum())
    return (cleaned[:4] if cleaned else "STR?").ljust(4)


def parse_json(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def validation_summary(conn, result_id):
    rows = conn.execute(
        "SELECT asset, timeframe, score_decision FROM backtest_results WHERE parent_id = ? AND stage = 'validation' ORDER BY asset, timeframe",
        (result_id,),
    ).fetchall()
    passed = []
    failed = []
    for asset, timeframe, decision in rows:
        label = f"{asset}/{timeframe}"
        if str(decision or "").lower() in ("pass", "promote"):
            passed.append(label)
        else:
            failed.append(label)
    return {"passed": passed, "failed": failed, "count": len(rows)}


def family_depth(conn, family, result_id):
    row = conn.execute(
        "SELECT COALESCE(MAX(family_generation),1), COUNT(*) FROM backtest_results WHERE lower(COALESCE(strategy_family,'')) = lower(?)",
        (family,),
    ).fetchone()
    siblings = conn.execute(
        "SELECT COUNT(*) FROM backtest_results WHERE parent_id = (SELECT parent_id FROM backtest_results WHERE id = ?) AND id <> ?",
        (result_id, result_id),
    ).fetchone()[0]
    return {"generations": int(row[0] or 1), "siblings_tested": int(siblings or 0), "family_total": int(row[1] or 0)}


def regime_summary(regime_scores):
    if not regime_scores:
        return "n/a"
    parts = []
    for regime, data in sorted(regime_scores.items()):
        parts.append(f"{regime}:{int(data.get('trade_count') or 0)}t/{float(data.get('profit_factor') or 0):.2f}pf")
    return ", ".join(parts[:4])


def render_board():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    promoted = conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe,
               COALESCE(score_total, 0) AS qs,
               COALESCE(profit_factor, 0) AS pf,
               COALESCE(total_return_pct, 0) AS net,
               COALESCE(max_drawdown_pct, 0) AS dd,
               COALESCE(total_trades, 0) AS tc,
               COALESCE(degradation_pct, 0) AS degradation_pct,
               COALESCE(primary_regime, 'UNKNOWN') AS primary_regime,
               COALESCE(regime_concentration, 0) AS regime_concentration,
               COALESCE(regime_scores, '{}') AS regime_scores,
               COALESCE(strategy_family, '') AS strategy_family,
               COALESCE(portability_score, 0) AS portability_score
        FROM backtest_results
        WHERE lower(COALESCE(score_decision,'')) = 'promote' AND stage = 'full'
        ORDER BY qs DESC, portability_score DESC, pf DESC
        LIMIT 12
        """
    ).fetchall()

    total_backtests = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    total_lessons = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    total_promotions = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE lower(COALESCE(score_decision,'')) = 'promote'").fetchone()[0]

    lines = ["📊 Leaderboard", "", "🏆 Promote candidates"]
    if not promoted:
        lines.append("No promote entries yet.")
    for row in promoted:
        item = dict(row)
        name = short_name(item)
        validations = validation_summary(conn, item["id"])
        depth = family_depth(conn, item["strategy_family"], item["id"])
        regimes = parse_json(item["regime_scores"], {})
        lines.append(f"○ {name} {item['asset']}/{item['timeframe']} QS {item['qs']:.2f} deg {item['degradation_pct']:.1f}%")
        lines.append(f"   val ✅{len(validations['passed'])} ❌{len(validations['failed'])} | pass:{', '.join(validations['passed'][:3]) or '-'} | fail:{', '.join(validations['failed'][:3]) or '-'}")
        lines.append(f"   regime {item['primary_regime']} {item['regime_concentration']:.1f}% | {regime_summary(regimes)}")
        lines.append(f"   family gen {depth['generations']} | siblings {depth['siblings_tested']} | portability {item['portability_score']:.0f}%")

    lines.append("")
    lines.append("───────────────────────────────────")
    lines.append(f"{total_backtests} backtests │ {total_lessons} lessons │ {total_promotions} 🏆")
    conn.close()
    return "<pre>" + "\n".join(lines) + "</pre>"


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    p = argparse.ArgumentParser()
    p.add_argument("--preview", action="store_true")
    a = p.parse_args()

    message = render_board()

    if a.preview:
        print(message)
        return

    subprocess.run(
        [sys.executable, TG_SCRIPT, "--message", message, "--bot", "oragorn", "--channel", "dm"],
        capture_output=True,
        text=True,
        timeout=20,
    )
    print(json.dumps({"status": "sent"}))


if __name__ == "__main__":
    main()
