"""Check what the promoted strategies actually look like."""
import sqlite3, json

DB = r"C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("## All promoted strategies (QS >= 3.0)")
rows = conn.execute("""
    SELECT strategy_spec_id, variant_id, asset, timeframe, 
           score_total, profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
           strategy_family
    FROM backtest_results WHERE score_total >= 3.0 
    ORDER BY score_total DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  QS={d['score_total']:.2f} PF={d['profit_factor']:.2f} DD={d['max_drawdown_pct']:.1f}% trades={d['total_trades']} WR={d['win_rate_pct']:.0f}% | {d['asset']}/{d['timeframe']} | {d['variant_id']}")

print(f"\n## Promoted variant distribution")
variants = [dict(r)["variant_id"] for r in rows]
from collections import Counter
for v, c in Counter(variants).most_common():
    print(f"  {v}: {c}")

# Check if any promoted strategy has walk-forward or OOS validation
print(f"\n## Do promoted strategies have validation variants?")
for r in rows:
    d = dict(r)
    spec_id = d["strategy_spec_id"]
    val_rows = conn.execute("""
        SELECT variant_id, score_total FROM backtest_results 
        WHERE strategy_spec_id = ? AND variant_id LIKE '%valid%' OR variant_id LIKE '%oos%' OR variant_id LIKE '%walk%'
    """, (spec_id,)).fetchall()
    if val_rows:
        print(f"  {spec_id}: {len(val_rows)} validation variants")
    else:
        print(f"  {spec_id}: NO validation")

conn.close()
