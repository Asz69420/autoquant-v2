import sqlite3, json

conn = sqlite3.connect("db/autoquant.db")
r = conn.execute("SELECT COUNT(*) FROM backtest_results").fetchone()
avg = conn.execute("SELECT ROUND(AVG(score_total),2), ROUND(AVG(total_trades),1) FROM backtest_results").fetchone()
promoted = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE score_total >= 3.0").fetchone()
failing = conn.execute("SELECT COUNT(*) FROM backtest_results WHERE score_total < 1.0").fetchone()
assets = conn.execute("SELECT COUNT(DISTINCT asset) FROM backtest_results").fetchone()
families = conn.execute("SELECT COUNT(DISTINCT strategy_family) FROM backtest_results").fetchone()
recent = conn.execute("SELECT ROUND(AVG(score_total),2) FROM backtest_results ORDER BY ts_iso DESC LIMIT 50").fetchone()
top = conn.execute("SELECT strategy_family, asset, timeframe, score_total, total_trades, profit_factor FROM backtest_results WHERE score_total >= 3.0 ORDER BY score_total DESC LIMIT 5").fetchall()

print(json.dumps({
    "total_backtests": r[0],
    "avg_qscore": avg[0],
    "avg_trades": avg[1],
    "promoted_count": promoted[0],
    "failing_count": failing[0],
    "promote_rate": round(promoted[0]/r[0]*100, 1) if r[0] else 0,
    "assets_tested": assets[0],
    "families_tested": families[0],
    "recent_50_avg_qs": recent[0],
    "top_5": [{"family": t[0], "asset": t[1], "tf": t[2], "qs": t[3], "trades": t[4], "pf": t[5]} for t in top]
}, indent=2))
conn.close()
