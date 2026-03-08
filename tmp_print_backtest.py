import json

path = r"C:\Users\Clamps\.openclaw\workspace-oragorn\artifacts\backtests\20260308\hl_20260308_03e7a731.backtest_result.json"
with open(path, "r", encoding="utf-8") as f:
    r = json.load(f)

res = r["results"]
print("Strategy: EMA Crossover Test")
print("Asset: ETH 4h")
print(f"Period: {res['start_ts']} to {res['end_ts']}")
print(f"Trades: {res['total_trades']}")
print(f"Net Profit: ${res['net_profit']:.2f} ({res['net_profit_pct']:.1f}%)")
print(f"Profit Factor: {res['profit_factor']:.3f}")
print(f"Win Rate: {res['win_rate']*100:.1f}%")
print(f"Max Drawdown: ${res['max_drawdown']:.2f} ({res['max_drawdown_pct']:.1f}%)")
print(f"Total Fees: ${res['total_fees_paid']:.2f}")
print(f"Regime PF: trending={res['regime_pf']['trending']:.2f} ranging={res['regime_pf']['ranging']:.2f} transitional={res['regime_pf']['transitional']:.2f}")
print(f"Gate: {r['gate']['gate_reason']}")
if r.get('ppr'):
    print(f"PPR Score: {r['ppr']['score']:.2f} Decision: {r['ppr']['decision']}")
