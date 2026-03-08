#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import subprocess
import sys
from collections import defaultdict

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")


def short_name(row):
    base = row.get("variant_id") or row.get("strategy_spec_id") or "STRAT"
    cleaned = "".join(ch for ch in str(base).upper() if ch.isalnum())
    return (cleaned[:4] if cleaned else "STR?").ljust(4)


def render_board():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        WITH ranked AS (
            SELECT
                strategy_spec_id,
                variant_id,
                asset,
                timeframe,
                COALESCE(xqscore_total, score_total, 0) AS xqs,
                COALESCE(score_total, 0) AS qs,
                COALESCE(profit_factor, 0) AS pf,
                COALESCE(total_return_pct, 0) AS net,
                COALESCE(max_drawdown_pct, 0) AS dd,
                COALESCE(total_trades, 0) AS tc,
                ROW_NUMBER() OVER (
                    PARTITION BY asset, timeframe
                    ORDER BY COALESCE(xqscore_total, score_total, 0) DESC, COALESCE(score_total, 0) DESC
                ) AS rn
            FROM backtest_results
            WHERE COALESCE(score_total, 0) >= 1.0
        )
        SELECT *
        FROM ranked
        WHERE rn <= 3
        ORDER BY asset, timeframe, xqs DESC
        """
    ).fetchall()

    total_backtests = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()[0]
    total_lessons = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    total_promotions = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE COALESCE(score_total, 0) >= 3.0").fetchone()[0]
    conn.close()

    grouped = defaultdict(lambda: defaultdict(list))
    for r in rows:
        grouped[r["asset"]][r["timeframe"]].append(dict(r))

    lines = []
    lines.append("📊 Leaderboard")
    lines.append("")

    assets = sorted(grouped.keys())
    for ai, asset in enumerate(assets):
        lines.append(f"▣ {asset} xQS QS PF Net DD TC")
        for tf in sorted(grouped[asset].keys()):
            lines.append(f"○──{tf}──────────────────────────")
            for r in grouped[asset][tf]:
                name = short_name(r)
                lines.append(
                    f" {name}"
                    f" {r['xqs']:>4.1f}"
                    f" {r['qs']:>4.1f}"
                    f" {r['pf']:>4.2f}"
                    f" {r['net']:>4.0f}%"
                    f" {r['dd']:>4.0f}%"
                    f" {int(r['tc']):>3d}"
                )
        if ai < len(assets) - 1:
            lines.append("")

    lines.append("")
    lines.append("───────────────────────────────")
    lines.append(f"{total_backtests} backtests │ {total_lessons} lessons │ {total_promotions} 🏆")

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
