import json

path = r"C:\Users\Clamps\.openclaw\workspace-oragorn\artifacts\backtests\20260308\hl_20260308_a84914fe.backtest_result.json"
with open(path, "r", encoding="utf-8") as f:
    r = json.load(f)

res = r['results']
q = r.get('qscore', {})
print(f"Strategy: EMA Crossover Test on ETH 4h")
print(f"Trades: {res['total_trades']}")
print(f"Net Profit: {res['net_profit_pct']:.1f}%")
print(f"Profit Factor: {res['profit_factor']:.3f}")
print(f"Win Rate: {res['win_rate']:.1f}%")
print(f"Max Drawdown: {res['max_drawdown_pct']:.1f}%")
print(f"Avg Trade: {res['avg_trade_pnl_pct']:.2f}%")
print(f"Fees: ${res['total_fees_paid']:.2f}")
print(f"Regime PF: trending={res['regime_pf']['trending']:.2f} ranging={res['regime_pf']['ranging']:.2f} transitional={res['regime_pf']['transitional']:.2f}")
print(f"QScore: {q.get('score', 0):.2f} ({q.get('decision', 'N/A')})")
print(f" Edge: {q.get('edge', 0):.3f} Resilience: {q.get('resilience', 0):.3f} Grade: {q.get('grade', 0):.3f}")
if q.get('flags'):
    print(f" Flags: {q['flags']}")
