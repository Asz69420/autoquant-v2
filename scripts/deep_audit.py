"""Deep audit: is the pipeline actually finding edge?"""
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path

DB = r"C:\Users\Clamps\.openclaw\workspace-oragorn\db\autoquant.db"
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print("=" * 60)
print("EDGE DISCOVERY AUDIT")
print("=" * 60)

# 1. Are we actually improving over time?
print("\n## QScore trend by cycle batch (last 20 cycles)")
rows = conn.execute("""
    SELECT 
        CAST(SUBSTR(strategy_spec_id, 13, 4) AS INTEGER) as cycle_approx,
        COUNT(*) as n,
        ROUND(AVG(score_total), 3) as avg_qs,
        MAX(score_total) as best_qs,
        ROUND(AVG(total_trades), 0) as avg_trades,
        SUM(CASE WHEN score_total >= 1.0 THEN 1 ELSE 0 END) as passing
    FROM backtest_results
    WHERE strategy_spec_id LIKE 'QD-202603%'
    GROUP BY SUBSTR(strategy_spec_id, 1, 16)
    ORDER BY strategy_spec_id DESC
    LIMIT 20
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  batch ~{d['cycle_approx']}: n={d['n']} avg_qs={d['avg_qs']} best={d['best_qs']:.2f} trades={d['avg_trades']} pass={d['passing']}")

# 2. Asset diversity in results
print("\n## Results by asset")
rows = conn.execute("""
    SELECT asset, COUNT(*) as n, ROUND(AVG(score_total), 3) as avg_qs,
           MAX(score_total) as best, SUM(CASE WHEN score_total >= 3.0 THEN 1 ELSE 0 END) as promoted
    FROM backtest_results GROUP BY asset ORDER BY n DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['asset']}: n={d['n']} avg_qs={d['avg_qs']} best={d['best']:.2f} promoted={d['promoted']}")

# 3. Timeframe performance
print("\n## Results by timeframe")
rows = conn.execute("""
    SELECT timeframe, COUNT(*) as n, ROUND(AVG(score_total), 3) as avg_qs,
           MAX(score_total) as best, SUM(CASE WHEN score_total >= 3.0 THEN 1 ELSE 0 END) as promoted
    FROM backtest_results GROUP BY timeframe ORDER BY n DESC
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['timeframe']}: n={d['n']} avg_qs={d['avg_qs']} best={d['best']:.2f} promoted={d['promoted']}")

# 4. Trade count distribution — are strategies getting enough trades?
print("\n## Trade count distribution")
rows = conn.execute("""
    SELECT 
        CASE 
            WHEN total_trades < 15 THEN '<15 (hard fail)'
            WHEN total_trades < 30 THEN '15-29 (low)'
            WHEN total_trades < 60 THEN '30-59 (ok)'
            WHEN total_trades < 100 THEN '60-99 (good)'
            ELSE '100+ (excellent)'
        END as bracket,
        COUNT(*) as n,
        ROUND(AVG(score_total), 3) as avg_qs
    FROM backtest_results GROUP BY bracket ORDER BY bracket
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['bracket']}: n={d['n']} avg_qs={d['avg_qs']}")

# 5. Profit factor distribution
print("\n## Profit factor distribution")
rows = conn.execute("""
    SELECT 
        CASE 
            WHEN profit_factor < 0.8 THEN '<0.8 (terrible)'
            WHEN profit_factor < 1.0 THEN '0.8-1.0 (losing)'
            WHEN profit_factor < 1.2 THEN '1.0-1.2 (breakeven)'
            WHEN profit_factor < 1.5 THEN '1.2-1.5 (marginal)'
            WHEN profit_factor < 2.0 THEN '1.5-2.0 (good)'
            ELSE '2.0+ (excellent)'
        END as bracket,
        COUNT(*) as n,
        ROUND(AVG(score_total), 3) as avg_qs
    FROM backtest_results GROUP BY bracket ORDER BY bracket
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['bracket']}: n={d['n']} avg_qs={d['avg_qs']}")

# 6. Walk-forward / out-of-sample check
print("\n## Variant types (screen vs full vs validation)")
rows = conn.execute("""
    SELECT variant_id, COUNT(*) as n, ROUND(AVG(score_total), 3) as avg_qs
    FROM backtest_results GROUP BY variant_id ORDER BY n DESC LIMIT 10
""").fetchall()
for r in rows:
    d = dict(r)
    print(f"  {d['variant_id']}: n={d['n']} avg_qs={d['avg_qs']}")

# 7. How many families ever produced a passing strategy?
print("\n## Family success rate")
families = conn.execute("""
    SELECT strategy_family, COUNT(*) as n, MAX(score_total) as best,
           SUM(CASE WHEN score_total >= 1.0 THEN 1 ELSE 0 END) as passing
    FROM backtest_results WHERE strategy_family != '' AND strategy_family IS NOT NULL
    GROUP BY strategy_family ORDER BY best DESC
""").fetchall()
total_fam = len(families)
passing_fam = sum(1 for f in families if dict(f)["passing"] > 0)
promoted_fam = sum(1 for f in families if dict(f)["best"] >= 3.0)
print(f"  Total families: {total_fam}")
print(f"  Families with >= 1 passing result: {passing_fam} ({passing_fam*100//max(total_fam,1)}%)")
print(f"  Families with promoted result: {promoted_fam} ({promoted_fam*100//max(total_fam,1)}%)")

# 8. Lessons learned count and recent quality
print("\n## Lessons table")
try:
    lesson_count = conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]
    recent_lessons = conn.execute("SELECT COUNT(*) FROM lessons WHERE ts_iso >= '2026-03-09'").fetchone()[0]
    print(f"  Total lessons: {lesson_count}")
    print(f"  Lessons since Mar 9: {recent_lessons}")
except:
    print("  Lessons table not found or empty")

conn.close()
