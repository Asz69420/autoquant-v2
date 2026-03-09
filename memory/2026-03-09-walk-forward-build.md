# Session: 2026-03-09 00:02:55 UTC

- **Session Key**: agent:oragorn:telegram:direct:1801759510
- **Session ID**: 3f82106c-5b78-4bc2-b550-b9ffb1d4b250
- **Source**: telegram

## Conversation Summary

assistant: Yes. I’m handing the build to Frodex directly now with a tight implementation brief, not another loose research prompt.
assistant: [[reply_to_current]] Yes. Frodex is on the actual build now with a hard implementation brief: build `scripts/walk_forward_engine.py`, wire `parallel_runner.py`, test it, commit it, and push it.
user: System: [2026-03-09 09:26:19 GMT+10] Exec completed (tidal-sa, code 0) :: Starting the build now. I’m delegating the implementation in-repo, then I’ll wire it, run the Supertrend 8:1 ETH 4h test, and come back with the exact files, command, output, comm…

Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.
When reading HEARTBEAT.md, use workspace file C:/Users/Clamps/.openclaw/workspace-oragorn/HEARTBEAT.md (exact case). Do not read docs/heartbeat.md.
Current time: Monday, March 9th, 2026 — 9:26 AM (Australia/Brisbane) / 2026-03-08 23:26 UTC
assistant: Attention needed: the build request misfired again — Frodex acknowledged the task but replied with another delegation-style status message instead of completed implementation evidence, so the walk-forward engine is still not built yet. The validation backlog also remains unhealthy at 60 unbacktested specs, which means the production research loop is still outrunning verified testing.
user: Conversation info (untrusted metadata):
```json
{
  "message_id": "1001",
  "sender_id": "1801759510",
  "sender": "Asz",
  "timestamp": "Mon 2026-03-09 09:33 GMT+10"
}
```

Sender (untrusted metadata):
```json
{
  "label": "Asz (1801759510)",
  "id": "1801759510",
  "name": "Asz",
  "username": "Rekn4w"
}
```

Finished it?
assistant: [[reply_to_current]] No. Not finished.

What happened:
- the build request misfired again
- instead of implementation evidence, Frodex came back with another “starting / delegating” style response

So the walk-forward engine is **still not built yet**.
user: Conversation info (untrusted metadata):
```json
{
  "message_id": "1014",
  "sender_id": "1801759510",
  "sender": "Asz",
  "timestamp": "Mon 2026-03-09 09:47 GMT+10"
}
```

Sender (untrusted metadata):
```json
{
  "label": "Asz (1801759510)",
  "id": "1801759510",
  "name": "Asz",
  "username": "Rekn4w"
}
```

, save this to file C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\walk_forward_engine.py

Then update parallel_runner.py to use walk_forward_engine.py instead of the old engine.py:
Change BACKTESTER path from:
 BACKTESTER = r"C:\Users\Clamps\.openclaw\skills\autoquant-backtester\engine.py"
To:
 BACKTESTER = r"C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\walk_forward_engine.py"

Then test on Supertrend 8:1:
python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec artifacts/strategy_specs/strategy-spec-20260301-claude-st9k3m5x.strategy_spec.json --variant supertrend_tail_harvester_8to1

Commit and push.


Here is the file to save:

# #!/usr/bin/env python3
“””
Walk-Forward Analysis Engine for AutoQuant

PRIMARY backtester — replaces traditional full-history backtesting.

Methodology:

1. Split historical data into rolling train/blind folds
1. Optimize strategy parameters on training window
1. Lock parameters, test on unseen blind window
1. Slide forward, repeat
1. Stitch out-of-sample results only for TRUE performance

This is how quant funds test. Traditional backtesting is curve fitting.

Usage:
python walk_forward_engine.py –asset ETH –tf 4h –strategy-spec SPEC.json –variant NAME
python walk_forward_engine.py –asset ETH –tf 4h –strategy-spec SPEC.json –variant NAME –dry-run
“””

import argparse
import json
import math
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone, timedelta
from itertools import product as iter_product

import numpy as np

# —————————————————————————

# Attempt optional imports; degrade gracefully

# —————————————————————————

try:
from scipy.signal import lfilter, butter
HAS_SCIPY = True
except ImportError:
HAS_SCIPY = False

# —————————————————————————

# Paths — adjust to your workspace layout

# —————————————————————————

ROOT = os.environ.get(
“AUTOQUANT_ROOT”,
r”C:\Users\Clamps.openclaw\workspace-oragorn”,
)
DB_PATH = os.path.join(ROOT, “db”, “autoquant.db”)
CANDLES_DIR = os.path.join(ROOT, “data”, “candles”)

# —————————————————————————

# HyperLiquid cost model

# —————————————————————————

TAKER_FEE_PCT = 0.075 # 0.075% per side
SLIPPAGE_PCT = 0.05 # 0.05% per side
TOTAL_COST_PCT = (TAKER_FEE_PCT + SLIPPAGE_PCT) / 100.0 # as decimal fraction per side

# ═══════════════════════════════════════════════════════════════════════════

# 1. ADAPTIVE WINDOW CONFIG

# ═══════════════════════════════════════════════════════════════════════════

WINDOW_CONFIG = {
# timeframe: (train_days, blind_days)
“1d”: (365, 90),
“4h”: (180, 42),
“1h”: (90, 21),
“15m”: (30, 7),
“5m”: (14, 3),
“1m”: (7, 2),
}

MIN_BLIND_TRADES = 15 # extend blind window if fewer trades

# ═══════════════════════════════════════════════════════════════════════════

# 2. CANDLE DATA LOADING

# ═══════════════════════════════════════════════════════════════════════════

def load_candles(asset: str, timeframe: str) -> list[dict]:
“”“Load OHLCV candle data from CSV cache.
Expected CSV columns: timestamp,open,high,low,close,volume
Files live at data/candles/{ASSET}_{TF}.csv
"""
fname = f"{asset}_{timeframe}.csv"
fpath = os.path.join(CANDLES_DIR, fname)

if not os.path.exists(fpath):
 # Try alternate naming conventions
 for alt in [f"{asset.upper()}_{timeframe}.csv",
 f"{asset.lower()}_{timeframe}.csv",
 f"{asset}-{timeframe}.csv"]:
 alt_path = os.path.join(CANDLES_DIR, alt)
 if os.path.exists(alt_path):
 fpath = alt_path
 break
 else:
 raise FileNotFoundError(
 f"Candle data not found for {asset}/{timeframe}. "
 f"Looked in {CANDLES_DIR} for {fname}"
 )

candles = []
with open(fpath, "r", encoding="utf-8") as f:
 header = f.readline().strip().split(",")
 # normalise header names
 header = [h.strip().lower() for h in header]
 for line in f:
 parts = line.strip().split(",")
 if len(parts) < 6:
 continue
 row = dict(zip(header, parts))
 try:
 candles.append({"ts": row.get("timestamp") or row.get("ts") or row.get("date") or row.get("time"),
 "open": float(row["open"]),
 "high": float(row["high"]),
 "low": float(row["low"]),
 "close": float(row["close"]),
 "volume": float(row.get("volume", 0)),
 })
 except (ValueError, KeyError):
 continue

if not candles:
 raise ValueError(f"No valid candles loaded from {fpath}")

return candles

# ═══════════════════════════════════════════════════════════════════════════

# 3. INDICATOR LIBRARY (forward-only — NO look-ahead)

# ═══════════════════════════════════════════════════════════════════════════

def sma(values: list[float], period: int) -> list[float | None]:
out = [None] * len(values)
for i in range(period - 1, len(values)):
out[i] = sum(values[i - period + 1: i + 1]) / period
return out

def ema(values: list[float], period: int) -> list[float | None]:
out = [None] * len(values)
k = 2.0 / (period + 1)
for i, v in enumerate(values):
if i == 0:
out[i] = v
else:
prev = out[i - 1] if out[i - 1] is not None else v
out[i] = v * k + prev * (1 - k)
return out

def rsi(closes: list[float], period: int = 14) -> list[float | None]:
out = [None] * len(closes)
if len(closes) < period + 1:
return out
gains = []
losses = []
for i in range(1, len(closes)):
delta = closes[i] - closes[i - 1]
gains.append(max(delta, 0))
losses.append(max(-delta, 0))
avg_gain = sum(gains[:period]) / period
avg_loss = sum(losses[:period]) / period
if avg_loss == 0:
out[period] = 100.0
else:
out[period] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
for i in range(period, len(gains)):
avg_gain = (avg_gain * (period - 1) + gains[i]) / period
avg_loss = (avg_loss * (period - 1) + losses[i]) / period
if avg_loss == 0:
out[i + 1] = 100.0
else:
out[i + 1] = 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
return out

def atr(candles: list[dict], period: int = 14) -> list[float | None]:
out = [None] * len(candles)
trs = []
for i in range(len(candles)):
if i == 0:
tr = candles[i][“high”] - candles[i][“low”]
else:
tr = max(
candles[i][“high”] - candles[i][“low”],
abs(candles[i][“high”] - candles[i - 1][“close”]),
abs(candles[i][“low”] - candles[i - 1][“close”]),
)
trs.append(tr)
# Wilder smoothing
if len(trs) >= period:
out[period - 1] = sum(trs[:period]) / period
for i in range(period, len(trs)):
out[i] = (out[i - 1] * (period - 1) + trs[i]) / period
return out

def supertrend(candles: list[dict], atr_period: int = 10, multiplier: float = 3.0):
“”“Supertrend indicator — returns list of (trend_value, direction) tuples.
direction: 1 = bullish, -1 = bearish
“””
atr_vals = atr(candles, atr_period)
n = len(candles)
upper_band = [0.0] * n
lower_band = [0.0] * n
supertrend_val = [0.0] * n
direction = [1] * n
for i in range(n):
 hl2 = (candles[i]["high"] + candles[i]["low"]) / 2.0
 a = atr_vals[i] if atr_vals[i] is not None else 0.0

 upper_band[i] = hl2 + multiplier * a
 lower_band[i] = hl2 - multiplier * a

 if i == 0:
 supertrend_val[i] = upper_band[i]
 direction[i] = 1
 continue

 # Adjust bands
 if lower_band[i] > lower_band[i - 1] or candles[i - 1]["close"] < lower_band[i - 1]:
 pass # keep current
 else:
 lower_band[i] = lower_band[i - 1]

 if upper_band[i] < upper_band[i - 1] or candles[i - 1]["close"] > upper_band[i - 1]:
 pass
 else:
 upper_band[i] = upper_band[i - 1]

 # Direction
 if direction[i - 1] == 1:
 if candles[i]["close"] < lower_band[i]:
 direction[i] = -1
 supertrend_val[i] = upper_band[i]
 else:
 direction[i] = 1
 supertrend_val[i] = lower_band[i]
 else:
 if candles[i]["close"] > upper_band[i]:
 direction[i] = 1
 supertrend_val[i] = lower_band[i]
 else:
 direction[i] = -1
 supertrend_val[i] = upper_band[i]

return list(zip(supertrend_val, direction))

def vortex(candles: list[dict], period: int = 14):“”“Vortex indicator — returns list of (vi_plus, vi_minus) tuples.”””
n = len(candles)
out = [(None, None)] * n
if n < period + 1:
return out
vm_plus = []
vm_minus = []
tr_list = []

for i in range(1, n):
 vm_p = abs(candles[i]["high"] - candles[i - 1]["low"])
 vm_m = abs(candles[i]["low"] - candles[i - 1]["high"])
 tr = max(
 candles[i]["high"] - candles[i]["low"],
 abs(candles[i]["high"] - candles[i - 1]["close"]),
 abs(candles[i]["low"] - candles[i - 1]["close"]),
 )
 vm_plus.append(vm_p)
 vm_minus.append(vm_m)
 tr_list.append(tr)

for i in range(period - 1, len(vm_plus)):
 sum_vmp = sum(vm_plus[i - period + 1: i + 1])
 sum_vmm = sum(vm_minus[i - period + 1: i + 1])
 sum_tr = sum(tr_list[i - period + 1: i + 1])
 if sum_tr == 0:
 continue
 out[i + 1] = (sum_vmp / sum_tr, sum_vmm / sum_tr)

return out

def cci(candles: list[dict], period: int = 20) -> list[float | None]:
“”“Commodity Channel Index.”””
out = [None] * len(candles)
tp = [(c[“high”] + c[“low”] + c[“close”]) / 3.0 for c in candles]
for i in range(period - 1, len(tp)):
window = tp[i - period + 1: i + 1]
mean_tp = sum(window) / period
mean_dev = sum(abs(v - mean_tp) for v in window) / period
if mean_dev == 0:
out[i] = 0.0
else:
out[i] = (tp[i] - mean_tp) / (0.015 * mean_dev)
return out

def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
“”“MACD — returns list of (macd_line, signal_line, histogram) tuples.”””
fast_ema = ema(closes, fast)
slow_ema = ema(closes, slow)
n = len(closes)
macd_line = [None] * n
for i in range(n):
if fast_ema[i] is not None and slow_ema[i] is not None:
macd_line[i] = fast_ema[i] - slow_ema[i]
macd_vals = [v if v is not None else 0.0 for v in macd_line]
sig = ema(macd_vals, signal)

out = [(None, None, None)] * n
for i in range(n):
 if macd_line[i] is not None and sig[i] is not None:
 out[i] = (macd_line[i], sig[i], macd_line[i] - sig[i])
return out

def butterworth_lfilter(values: list[float], cutoff_period: int = 20, order: int = 2) -> list[float]:
“”“Butterworth low-pass filter using lfilter (forward-only, NO look-ahead).
Uses lfilter NOT filtfilt — filtfilt uses future data.
“””
if not HAS_SCIPY:
# Fallback to simple EMA if scipy not available
return ema(values, cutoff_period)
nyquist = 0.5
normalised_cutoff = 1.0 / cutoff_period / nyquist
normalised_cutoff = min(normalised_cutoff, 0.99) # clamp
b_coeff, a_coeff = butter(order, normalised_cutoff, btype="low")
filtered = lfilter(b_coeff, a_coeff, values)
return filtered.tolist()

# ═══════════════════════════════════════════════════════════════════════════

# 4. STRATEGY EXECUTION ENGINE

# ═══════════════════════════════════════════════════════════════════════════

def parse_strategy_spec(spec_path: str, variant_name: str = “default”) -> dict:
“”“Load strategy spec JSON and extract the requested variant.”””
with open(spec_path, “r”, encoding=“utf-8”) as f:
spec = json.load(f)
variants = spec.get("variants", [])
variant = None
for v in variants:
 if v.get("name", "default") == variant_name:
 variant = v
 break
if variant is None and variants:
 variant = variants[0]
if variant is None:
 variant = {}

return {
 "spec": spec,
 "variant": variant,
 "strategy_name": spec.get("name", spec.get("id", "unknown")),
 "entry_rules": spec.get("entry_rules", variant.get("entry_rules", [])),
 "exit_rules": spec.get("exit_rules", variant.get("exit_rules", [])),
 "parameters": variant.get("parameters", spec.get("parameters", {})),
 "risk": variant.get("risk", spec.get("risk", {})),
}

def compute_indicators(candles: list[dict], params: dict) -> dict:
“”“Compute all indicators needed, based on strategy parameters.”””
closes = [c[“close”] for c in candles]
indicators = {“close”: closes}
# Always compute these basics
for p in [14, 20, 21, 50, 200]:
 indicators[f"sma_{p}"] = sma(closes, p)
 indicators[f"ema_{p}"] = ema(closes, p)

indicators["rsi_14"] = rsi(closes, 14)
indicators["atr_14"] = atr(candles, 14)
indicators["cci_20"] = cci(candles, 20)# Supertrend with configurable params
st_period = params.get("supertrend_period", params.get("atr_period", 10))
st_mult = params.get("supertrend_multiplier", params.get("multiplier", 3.0))
indicators["supertrend"] = supertrend(candles, int(st_period), float(st_mult))

# Vortex
vx_period = params.get("vortex_period", 14)
indicators["vortex"] = vortex(candles, int(vx_period))

# MACD
macd_fast = params.get("macd_fast", 12)
macd_slow = params.get("macd_slow", 26)
macd_sig = params.get("macd_signal", 9)
indicators["macd"] = macd(closes, int(macd_fast), int(macd_slow), int(macd_sig))

# Butterworth filtered close
bw_period = params.get("butterworth_period", 20)
indicators["bw_close"] = butterworth_lfilter(closes, int(bw_period))

return indicators

def evaluate_condition(condition: str, idx: int, indicators: dict, candles: list[dict]) -> bool:
“”“Evaluate a single rule condition string at the given candle index.
Supports conditions like:
 "supertrend_direction == 1"
 "RSI_14 < 30"
 "close > SMA_200"
 "vortex_plus > vortex_minus"
 "CCI_20 > 100"
 "MACD_histogram > 0"
"""
if not condition or not condition.strip():
 return True

condition = condition.strip()

def get_value(token: str) -> float | None:
 token = token.strip()

 # Try as a number
 try:
 return float(token)
 except ValueError:
 pass

 t = token.lower().replace("-", "_")

 # Close price
 if t in ("close", "price"):
 return candles[idx]["close"]
 if t in ("high",):
 return candles[idx]["high"]
 if t in ("low",):
 return candles[idx]["low"]
 if t in ("open",):
 return candles[idx]["open"]

 # SMA
 if t.startswith("sma_"):
 period = t.split("_")[1]
 key = f"sma_{period}"
 if key in indicators and indicators[key][idx] is not None:
 return indicators[key][idx]

 # EMA
 if t.startswith("ema_"):
 period = t.split("_")[1]
 key = f"ema_{period}"
 if key in indicators and indicators[key][idx] is not None:
 return indicators[key][idx]

 # RSI
 if t.startswith("rsi"):
 key = "rsi_14"
 if key in indicators and indicators[key][idx] is not None:
 return indicators[key][idx]

 # ATR
 if t.startswith("atr"):
 key = "atr_14"
 if key in indicators and indicators[key][idx] is not None:
 return indicators[key][idx]

 # CCI
 if t.startswith("cci"):
 key = "cci_20"
 if key in indicators and indicators[key][idx] is not None:
 return indicators[key][idx]

 # Supertrend
 if t in ("supertrend_direction", "st_direction", "supertrend_dir"):
 st = indicators.get("supertrend")
 if st and st[idx]:
 return float(st[idx][1]) # direction
 if t in ("supertrend_value", "st_value", "supertrend"):
 st = indicators.get("supertrend")
 if st and st[idx]:
 return float(st[idx][0]) # value

 # Vortex
 if t in ("vortex_plus", "vi_plus", "vi+"):
 vx = indicators.get("vortex")
 if vx and vx[idx] and vx[idx][0] is not None:
 return vx[idx][0]
 if t in ("vortex_minus", "vi_minus", "vi-"):
 vx = indicators.get("vortex")
 if vx and vx[idx] and vx[idx][1] is not None:
 return vx[idx][1]

 # MACD
 if t in ("macd_line", "macd"):
 m = indicators.get("macd")
 if m and m[idx] and m[idx][0] is not None:
 return m[idx][0]
 if t in ("macd_signal", "macd_sig"):
 m = indicators.get("macd")
 if m and m[idx] and m[idx][1] is not None:
 return m[idx][1]
 if t in ("macd_histogram", "macd_hist"):
 m = indicators.get("macd")
 if m and m[idx] and m[idx][2] is not None:
 return m[idx][2]

 # Butterworth close
 if t in ("bw_close", "butterworth", "filtered_close"):
 bw = indicators.get("bw_close")
 if bw and idx < len(bw) and bw[idx] is not None:
 return bw[idx]

 return None

# Parse comparison operators
for op_str, op_fn in [(">=", lambda a, b: a >= b),
 ("<=", lambda a, b: a <= b),
 ("==", lambda a, b: abs(a - b) < 1e-10),
 ("!=", lambda a, b: abs(a - b) >= 1e-10),
 (">", lambda a, b: a > b),
 ("<", lambda a, b: a < b),
]:
 if op_str in condition:
 parts = condition.split(op_str, 1)
 if len(parts) == 2:
 left = get_value(parts[0])
 right = get_value(parts[1])
 if left is not None and right is not None:
 return op_fn(left, right)
 return False

# Cross conditions (e.g., "RSI_14 crosses_above 30")
if "crosses_above" in condition.lower() or "cross_above" in condition.lower():
 parts = condition.lower().replace("crosses_above", "|").replace("cross_above", "|").split("|")
 if len(parts) == 2 and idx > 0:
 curr = get_value(parts[0])
 threshold = get_value(parts[1])
 # Need previous value
 prev = get_value(parts[0]) # simplified — uses current index
 if curr is not None and threshold is not None:
 return curr > threshold # simplified cross detection

return False

def run_strategy_on_candles(
candles: list[dict],
strategy: dict,
params_override: dict | None = None,
) -> dict:
“”“Execute a strategy on candle data and return performance metrics.
Returns dict with: trades, pf, max_dd, win_rate, total_return, etc.
"""
params = dict(strategy.get("parameters", {}))
if params_override:
 params.update(params_override)

entry_rules = strategy.get("entry_rules", [])
exit_rules = strategy.get("exit_rules", [])
risk = strategy.get("risk", {})

# Risk params
sl_pct = float(risk.get("stop_loss_pct", risk.get("stop_loss", 5.0)))
tp_pct = float(risk.get("take_profit_pct", risk.get("take_profit", 10.0)))
# Handle ratio-based TP (e.g., "8:1" means TP = SL * 8)
rr_ratio = risk.get("reward_risk_ratio", risk.get("rr_ratio"))
if rr_ratio:
 try:
 if isinstance(rr_ratio, str) and ":" in rr_ratio:
 tp_pct = sl_pct * float(rr_ratio.split(":")[0])
 else:
 tp_pct = sl_pct * float(rr_ratio)
 except (ValueError, IndexError):
 pass

indicators = compute_indicators(candles, params)

trades = []
position = None # None or {"entry_price", "entry_idx", "direction"}
equity_curve = [1.0]

# Warm-up: skip first 200 candles for indicator settling
warmup = min(200, len(candles) // 4)

for i in range(warmup, len(candles)):
 close = candles[i]["close"]

 # --- Check exit conditions if in position ---
 if position is not None:
 entry_price = position["entry_price"]
 direction = position["direction"]

 # Stop loss / take profit
 if direction == "long":
 pnl_pct = ((close - entry_price) / entry_price) * 100.0
 else:
 pnl_pct = ((entry_price - close) / entry_price) * 100.0

 exit_signal = False
 exit_reason = ""

 if pnl_pct <= -sl_pct:
 exit_signal = True
 exit_reason = "stop_loss"
 pnl_pct = -sl_pct
 elif pnl_pct >= tp_pct:
 exit_signal = True
 exit_reason = "take_profit"
 pnl_pct = tp_pct
 else:
 # Check exit rules
 for rule in exit_rules:
 cond = rule if isinstance(rule, str) else rule.get("condition", "")
 if evaluate_condition(cond, i, indicators, candles):
 exit_signal = True
 exit_reason = "exit_rule"
 break

 if exit_signal:
 # Apply costs (both entry and exit)
 net_pnl_pct = pnl_pct - (TOTAL_COST_PCT * 100.0 * 2) # 2 sides
 trades.append({
 "entry_idx": position["entry_idx"],
 "exit_idx": i,
 "entry_price": entry_price,
 "exit_price": close,
 "direction": direction,
 "pnl_pct": net_pnl_pct,
 "gross_pnl_pct": pnl_pct,
 "exit_reason": exit_reason,
 })
 equity_curve.append(equity_curve[-1] * (1 + net_pnl_pct / 100.0))position = None
 continue

 # --- Check entry conditions if not in position ---
 if position is None and entry_rules:
 all_met = True
 for rule in entry_rules:
 cond = rule if isinstance(rule, str) else rule.get("condition", "")
 if not evaluate_condition(cond, i, indicators, candles):
 all_met = False
 break

 if all_met:
 direction = "long" # default; could be parsed from rules
 # Detect short signals
 for rule in entry_rules:
 cond = (rule if isinstance(rule, str) else rule.get("condition", "")).lower()
 if "short" in cond or "sell" in cond or "direction == -1" in cond:
 direction = "short"
 break

 position = {
 "entry_price": close,
 "entry_idx": i,
 "direction": direction,
 }

 equity_curve.append(equity_curve[-1])

# Close any open position at end
if position is not None:
 close = candles[-1]["close"]
 entry_price = position["entry_price"]
 if position["direction"] == "long":
 pnl_pct = ((close - entry_price) / entry_price) * 100.0
 else:
 pnl_pct = ((entry_price - close) / entry_price) * 100.0
 net_pnl_pct = pnl_pct - (TOTAL_COST_PCT * 100.0 * 2)
 trades.append({
 "entry_idx": position["entry_idx"],
 "exit_idx": len(candles) - 1,
 "entry_price": entry_price,
 "exit_price": close,
 "direction": position["direction"],
 "pnl_pct": net_pnl_pct,
 "gross_pnl_pct": pnl_pct,
 "exit_reason": "end_of_data",
 })
 equity_curve.append(equity_curve[-1] * (1 + net_pnl_pct / 100.0))

return compute_metrics(trades, equity_curve)

def compute_metrics(trades: list[dict], equity_curve: list[float]) -> dict:
“”“Calculate performance metrics from trade list and equity curve.”””
if not trades:
return {
“total_trades”: 0,
“win_rate_pct”: 0.0,
“profit_factor”: 0.0,
“max_drawdown_pct”: 0.0,
“total_return_pct”: 0.0,
“avg_trade_pct”: 0.0,
“sharpe_ratio”: 0.0,
“trades”: trades,
“equity_curve”: equity_curve,
}
winners = [t for t in trades if t["pnl_pct"] > 0]
losers = [t for t in trades if t["pnl_pct"] <= 0]

gross_profit = sum(t["pnl_pct"] for t in winners) if winners else 0.0
gross_loss = abs(sum(t["pnl_pct"] for t in losers)) if losers else 0.0

pf = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)

# Max drawdown from equity curve
peak = equity_curve[0]
max_dd = 0.0
for val in equity_curve:
 if val > peak:
 peak = val
 dd = ((peak - val) / peak) * 100.0 if peak > 0 else 0.0
 if dd > max_dd:
 max_dd = dd

total_return = ((equity_curve[-1] / equity_curve[0]) - 1) * 100.0 if equity_curve[0] > 0 else 0.0

pnls = [t["pnl_pct"] for t in trades]
avg_trade = sum(pnls) / len(pnls) if pnls else 0.0

# Sharpe (simplified — annualised)
if len(pnls) > 1:
 mean_r = np.mean(pnls)
 std_r = np.std(pnls, ddof=1)
 sharpe = (mean_r / std_r) * math.sqrt(252) if std_r > 0 else 0.0
else:
 sharpe = 0.0

return {
 "total_trades": len(trades),
 "win_rate_pct": (len(winners) / len(trades)) * 100.0,
 "profit_factor": round(pf, 3),
 "max_drawdown_pct": round(max_dd, 2),
 "total_return_pct": round(total_return, 2),
 "avg_trade_pct": round(avg_trade, 3),
 "sharpe_ratio": round(sharpe, 3),
 "trades": trades,
 "equity_curve": equity_curve,
}

# ═══════════════════════════════════════════════════════════════════════════

# 5. QSCORE CALCULATION

# ═══════════════════════════════════════════════════════════════════════════

def calculate_qscore(metrics: dict) -> dict:
“”“Calculate QScore from performance metrics.
Formula: profit_factor - (max_drawdown / 10000) - complexity_penalty - gate_penalty
"""
pf = metrics.get("profit_factor", 0.0)
dd = metrics.get("max_drawdown_pct", 0.0)
trades = metrics.get("total_trades", 0)

# Base score
score_edge = pf
score_resilience = -(dd / 100.0) # normalised drawdown penalty# Complexity penalty (simplified)
complexity_penalty = 0.0

# Gate penalty: too few trades = unreliable
gate_penalty = 0.0
if trades < 15:
 gate_penalty = 0.5
elif trades < 30:
 gate_penalty = 0.2

# Suspect check: PF > 4.0 with < 25 trades = likely overfitting
suspect = pf > 4.0 and trades < 25

score_total = score_edge + score_resilience - complexity_penalty - gate_penalty

# Decision
if score_total >= 3.0:
 decision = "promote"
 grade = "A"
elif score_total >= 1.0:
 decision = "pass"
 grade = "B"
else:
 decision = "fail"
 grade = "C" if score_total >= 0.5 else "D"

flags = []
if suspect:
 flags.append("suspect_overfit")
if trades < 15:
 flags.append("low_trade_count")

return {
 "score_total": round(score_total, 3),
 "score_edge": round(score_edge, 3),
 "score_resilience": round(score_resilience, 3),
 "score_decision": decision,
 "score_grade": grade,
 "score_flags": json.dumps(flags),
 "suspect": suspect,
}

# ═══════════════════════════════════════════════════════════════════════════

# 6. WALK-FORWARD ENGINE (the core)

# ═══════════════════════════════════════════════════════════════════════════

def run_walk_forward(
candles: list[dict],
strategy: dict,
timeframe: str,
param_grid: dict | None = None,
) -> dict:
“”“Execute walk-forward analysis on the given candles + strategy.
Returns comprehensive results with in-sample, out-of-sample, and degradation.
"""
train_days, blind_days = WINDOW_CONFIG.get(timeframe, (180, 42))

# Convert days to approximate candle counts
candles_per_day = {
 "1d": 1, "4h": 6, "1h": 24, "15m": 96, "5m": 288, "1m": 1440,
}
cpd = candles_per_day.get(timeframe, 6)
train_candles = train_days * cpd
blind_candles = blind_days * cpd

total_candles = len(candles)
if total_candles < train_candles + blind_candles:
 return {
 "status": "error",
 "error": f"Not enough data: {total_candles} candles, need {train_candles + blind_candles}",
 "folds": 0,
 }

# Generate parameter grid for optimisation (if provided)
if param_grid is None:
 param_grid = {}

# Build fold schedule
folds = []
fold_start = 0

while fold_start + train_candles + blind_candles <= total_candles:
 train_end = fold_start + train_candles
 blind_end = train_end + blind_candles

 # Don't go past available data
 if blind_end > total_candles:
 blind_end = total_candles

 folds.append({
 "fold_num": len(folds) + 1,
 "train_start": fold_start,
 "train_end": train_end,
 "blind_start": train_end,
 "blind_end": blind_end,
 })

 # Slide forward by blind window size
 fold_start = train_end

if not folds:
 return {
 "status": "error",
 "error": "Could not create any folds with the given data",
 "folds": 0,
 }

# Run each fold
fold_results = []
all_oos_trades = []
all_oos_equity = [1.0]
all_is_trades = []

for fold in folds:
 train_data = candles[fold["train_start"]:fold["train_end"]]
 blind_data = candles[fold["blind_start"]:fold["blind_end"]]

 # --- IN-SAMPLE: Run strategy on training data ---
 is_result = run_strategy_on_candles(train_data, strategy)

 # --- Parameter optimisation on training data ---
 # If we have a param grid, try different combos and pick best
 best_params = None
 best_is_pf = is_result["profit_factor"]

 if param_grid:
 param_names = list(param_grid.keys())
 param_values = list(param_grid.values())

 for combo in iter_product(*param_values):
 override = dict(zip(param_names, combo))
 trial = run_strategy_on_candles(train_data, strategy, params_override=override)
 if trial["profit_factor"] > best_is_pf and trial["total_trades"] >= 10:
 best_is_pf = trial["profit_factor"]
 best_params = override
 is_result = trial

 # --- OUT-OF-SAMPLE: Lock params, test on blind data ---
 oos_result = run_strategy_on_candles(blind_data, strategy, params_override=best_params)

 # Accumulate OOS trades
 all_oos_trades.extend(oos_result["trades"])
 all_is_trades.extend(is_result["trades"])

 # Stitch OOS equity curve
 if oos_result["equity_curve"]:
 last_equity = all_oos_equity[-1]
 for eq_val in oos_result["equity_curve"][1:]:
 all_oos_equity.append(last_equity * eq_val)

 # QScore for this fold
 is_qs = calculate_qscore(is_result)
 oos_qs = calculate_qscore(oos_result)

 fold_results.append({
 "fold": fold["fold_num"],
 "train_candles": len(train_data),
 "blind_candles": len(blind_data),
 "best_params": best_params,
 "insample": {
 "trades": is_result["total_trades"],
 "pf": is_result["profit_factor"],
 "max_dd": is_result["max_drawdown_pct"],
 "return_pct": is_result["total_return_pct"],
 "win_rate": is_result["win_rate_pct"],
 "qscore": is_qs["score_total"],
 },
 "outofsample": {
 "trades": oos_result["total_trades"],
 "pf": oos_result["profit_factor"],
 "max_dd": oos_result["max_drawdown_pct"],
 "return_pct": oos_result["total_return_pct"],
 "win_rate": oos_result["win_rate_pct"],
 "qscore": oos_qs["score_total"],
 },
 })

# --- Aggregate metrics ---
agg_is = compute_metrics(all_is_trades, [1.0]) # simplified equity
agg_oos = compute_metrics(all_oos_trades, all_oos_equity)

is_qscore = calculate_qscore(agg_is)
oos_qscore = calculate_qscore(agg_oos)

# Degradation
is_qs_val = is_qscore["score_total"]
oos_qs_val = oos_qscore["score_total"]
if is_qs_val > 0:
 degradation_pct = round((1.0 - oos_qs_val / is_qs_val) * 100.0, 1)
else:
 degradation_pct = 0.0 if oos_qs_val >= 0 else 100.0

return {
 "status": "ok",
 "folds": len(fold_results),
 "fold_results": fold_results,
 "insample_aggregate": {
 "total_trades": agg_is["total_trades"],
 "profit_factor": agg_is["profit_factor"],
 "max_drawdown_pct": agg_is["max_drawdown_pct"],
 "total_return_pct": agg_is["total_return_pct"],
 "win_rate_pct": agg_is["win_rate_pct"],
 "sharpe_ratio": agg_is["sharpe_ratio"],
 "qscore": is_qscore["score_total"],
 "decision": is_qscore["score_decision"],
 },
 "outofsample_aggregate": {
 "total_trades": agg_oos["total_trades"],
 "profit_factor": agg_oos["profit_factor"],
 "max_drawdown_pct": agg_oos["max_drawdown_pct"],
 "total_return_pct": agg_oos["total_return_pct"],
 "win_rate_pct": agg_oos["win_rate_pct"],
 "sharpe_ratio": agg_oos["sharpe_ratio"],
 "qscore": oos_qscore["score_total"],
 "decision": oos_qscore["score_decision"],
 "grade": oos_qscore["score_grade"],
 "flags": oos_qscore["score_flags"],
 },
 "degradation_pct": degradation_pct,
 "walk_forward_config": {
 "train_days": train_days,
 "blind_days": blind_days,
 "timeframe": timeframe,
 "min_blind_trades": MIN_BLIND_TRADES,
 },
}

# ═══════════════════════════════════════════════════════════════════════════

# 7. DATABASE INTEGRATION

# ═══════════════════════════════════════════════════════════════════════════

def ensure_schema(conn: sqlite3.Connection):
“”“Add walk-forward columns to backtest_results if they don’t exist.”””
cursor = conn.cursor()
existing = set()
for row in cursor.execute(“PRAGMA table_info(backtest_results)”):
existing.add(row[1])
new_columns = {
 "qscore_insample": "REAL",
 "qscore_outofsample": "REAL",
 "degradation_pct": "REAL",
 "walk_forward_folds": "INTEGER",
 "walk_forward_config": "TEXT",
 "fold_results": "TEXT",
}

for col, col_type in new_columns.items():
 if col not in existing:
 try:
 cursor.execute(f"ALTER TABLE backtest_results ADD COLUMN {col} {col_type}")
 except sqlite3.OperationalError:
 pass # column might already exist

conn.commit()

def save_result(
conn: sqlite3.Connection,
spec_id: str,
variant_id: str,
asset: str,
timeframe: str,
wf_result: dict,
):“”“Save walk-forward result to the backtest_results table.”””
ensure_schema(conn)
oos = wf_result["outofsample_aggregate"]
ins = wf_result["insample_aggregate"]

result_id = f"wf_{uuid.uuid4().hex[:12]}"
now = datetime.now(timezone.utc).isoformat()

conn.execute(
 """
 INSERT INTO backtest_results (
 id, ts_iso, strategy_spec_id, variant_id, asset, timeframe,
 profit_factor, max_drawdown_pct, total_trades, win_rate_pct,
 total_return_pct, avg_trade_pct,
 score_total, score_decision, score_edge, score_resilience,
 score_grade, score_flags,
 qscore_insample, qscore_outofsample, degradation_pct,
 walk_forward_folds, walk_forward_config, fold_results
 ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
 """,
 (
 result_id, now, spec_id, variant_id, asset, timeframe,
 oos["profit_factor"], oos["max_drawdown_pct"],
 oos["total_trades"], oos["win_rate_pct"],
 oos["total_return_pct"], 0.0,
 oos["qscore"], oos["decision"],
 oos.get("qscore", 0.0), # score_edge = oos qscore for now
 -(oos["max_drawdown_pct"] / 100.0), # score_resilience
 oos["grade"], oos["flags"],
 ins["qscore"], oos["qscore"], wf_result["degradation_pct"],
 wf_result["folds"],
 json.dumps(wf_result["walk_forward_config"]),
 json.dumps(wf_result["fold_results"]),
 ),
)
conn.commit()

return result_id

# ═══════════════════════════════════════════════════════════════════════════

# 8. CLI ENTRY POINT

# ═══════════════════════════════════════════════════════════════════════════

def main():
ap = argparse.ArgumentParser(description=“Walk-Forward Analysis Engine for AutoQuant”)
ap.add_argument(”–asset”, required=True, help=“Asset symbol (ETH, BTC, SOL, etc.)”)
ap.add_argument(”–tf”, required=True, help=“Timeframe (1m, 5m, 15m, 1h, 4h, 1d)”)
ap.add_argument(”–strategy-spec”, required=True, help=“Path to strategy spec JSON”)
ap.add_argument(”–variant”, default=“default”, help=“Variant name from spec”)
ap.add_argument(”–dry-run”, action=“store_true”, help=“Print config without running”)
ap.add_argument(”–no-db”, action=“store_true”, help=“Skip database write”)
args = ap.parse_args()
# Validate timeframe
if args.tf not in WINDOW_CONFIG:
 print(json.dumps({
 "status": "error",
 "error": f"Unsupported timeframe: {args.tf}. Supported: {list(WINDOW_CONFIG.keys())}",
 }))
 return 1

# Load strategy
try:
 strategy = parse_strategy_spec(args.strategy_spec, args.variant)
except Exception as e:
 print(json.dumps({"status": "error", "error": f"Failed to load strategy spec: {e}"}))
 return 1

spec_id = os.path.basename(args.strategy_spec).replace(".strategy_spec.json", "").replace(".json", "")

if args.dry_run:
 train_days, blind_days = WINDOW_CONFIG[args.tf]
 print(json.dumps({
 "status": "dry_run",
 "asset": args.asset,
 "timeframe": args.tf,
 "strategy": strategy["strategy_name"],
 "variant": args.variant,
 "train_days": train_days,
 "blind_days": blind_days,
 "spec_id": spec_id,
 }, indent=2))
 return 0

# Load candles
try:
 candles = load_candles(args.asset, args.tf)
except (FileNotFoundError, ValueError) as e:
 print(json.dumps({"status": "error", "error": str(e)}))
 return 1

# Run walk-forward
result = run_walk_forward(candles, strategy, args.tf)

if result["status"] != "ok":
 print(json.dumps(result, indent=2))
 return 1

# Save to DB
if not args.no_db:
 try:
 conn = sqlite3.connect(DB_PATH)
 result_id = save_result(conn, spec_id, args.variant, args.asset, args.tf, result)
 conn.close()
 result["result_id"] = result_id
 result["db_saved"] = True
 except Exception as e:
 result["db_saved"] = False
 result["db_error"] = str(e)

# Print summary (without full trade lists to keep output clean)
output = {
 "status": result["status"],
 "asset": args.asset,
 "timeframe": args.tf,
 "strategy": strategy["strategy_name"],"variant": args.variant,
 "folds": result["folds"],
 "insample": result["insample_aggregate"],
 "outofsample": result["outofsample_aggregate"],
 "degradation_pct": result["degradation_pct"],
 "walk_forward_config": result["walk_forward_config"],
 "result_id": result.get("result_id"),
 "db_saved": result.get("db_saved", False),
}

# Per-fold summary
output["fold_summary"] = []
for fr in result["fold_results"]:
 output["fold_summary"].append({
 "fold": fr["fold"],
 "is_pf": fr["insample"]["pf"],
 "is_qs": fr["insample"]["qscore"],
 "oos_pf": fr["outofsample"]["pf"],
 "oos_qs": fr["outofsample"]["qscore"],
 "oos_trades": fr["outofsample"]["trades"],
 })

print(json.dumps(output, indent=2))
return 0

if name == “**main**”:
sys.exit(main())
assistant: I’m taking it direct. Saving the engine file, switching `parallel_runner.py`, then I’ll run the exact test and give you the real result.
assistant: I found one snag before writing the engine: the exact Supertrend test spec path you gave doesn’t exist in the repo right now. I’m still wiring the engine and `parallel_runner`, then I’ll run your exact command first and tell you if it fails on missing input or on engine logic.
assistant: The engine file is in and `parallel_runner.py` is switched. Your exact test command failed on a missing strategy spec file, not on the engine itself. I’m committing the code changes now, then I’ll tell you the hash and push result.
assistant: [[reply_to_current]] Done.

What changed:
- saved `scripts/walk_forward_engine.py`
- updated `scripts/parallel_runner.py` to use:
  - `C:\Users\Clamps\.openclaw\workspace-oragorn\scripts\walk_forward_engine.py`

Exact test command run:
```powershell
python scripts\walk_forward_engine.py --asset ETH --tf 4h --strategy-spec artifacts\strategy_specs\strategy-spec-20260301-claude-st9k3m5x.strategy_spec.json --variant supertrend_tail_harvester_8to1
```

Exact result:
```json
{"status": "error", "error": "Failed to load strategy spec: [Errno 2] No such file or directory: 'artifacts\\\\strategy_specs\\\\strategy-spec-20260301-claude-st9k3m5x.strategy_spec.json'"}
```

So:
- the **engine file is written**
- `parallel_runner.py` is **switched**
- your exact test failed because the **input spec file does not exist** in this repo right now

Commit + push:
- commit: `c583d07`
- push: **successful** to `origin/main`

One note:
- I saved a **syntactically corrected Python version** of the file you sent, because the pasted text had broken smart quotes / invalid characters and would not run as-is.
user: Conversation info (untrusted metadata):
```json
{
  "message_id": "1019",
  "sender_id": "1801759510",
  "sender": "Asz",
  "timestamp": "Mon 2026-03-09 09:59 GMT+10"
}
```

Sender (untrusted metadata):
```json
{
  "label": "Asz (1801759510)",
  "id": "1801759510",
  "name": "Asz",
  "username": "Rekn4w"
}
```

Oragorn, update Quandalf's knowledge base so he understands the new walk-forward backtester.

═══ 1. UPDATE QUANDALF'S SOUL.md ═══

Add this section to agents/quandalf/SOUL.md, replacing any existing backtesting references:

## Walk-Forward Backtester (PRIMARY)

Our backtester uses walk-forward analysis — the same method quant funds use. It does NOT test on full historical data (that's curve fitting).

How it works:
1. Splits candle data into rolling folds
2. Each fold: trains on a window, locks parameters, blind-tests on UNSEEN data
3. Slides forward, repeats
4. Only out-of-sample (blind) results count for scoring

Adaptive windows by timeframe:
- 1d: train 12mo, blind 3mo
- 4h: train 6mo, blind 6wk
- 1h: train 3mo, blind 3wk
- 15m: train 1mo, blind 1wk

What this means for you:
- QScore is calculated on OUT-OF-SAMPLE data only — this is the real score
- In-sample QScore is also reported for comparison
- degradation_pct shows how much performance drops on unseen data
- Low degradation (<30%) = robust edge, real strategy
- High degradation (>60%) = curve-fitted garbage, don't iterate on it
- A strategy scoring QS 1.0 on walk-forward is BETTER than QS 4.0 on traditional backtesting
- Every strategy you design gets tested honestly — no more fake returns

Transaction costs are included:
- 0.075% taker fee per side (HyperLiquid rate)
- 0.05% slippage per side
- Both applied automatically

CRITICAL MATH RULE: The engine uses lfilter (forward-only) for any filtering. NEVER request filtfilt — it uses future data and creates look-ahead bias that produces fake returns.

When reviewing results, always check:
1. Out-of-sample QScore (the real score)
2. Degradation % (is the edge real?)
3. Number of folds (more folds = more reliable)
4. Blind window trade count (minimum 15 for statistical validity)

Tool command:
python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec <SPEC_PATH> --variant <VARIANT_NAME>

Same interface as before. Results go to SQLite backtest_results with new columns: qscore_insample, qscore_outofsample, degradation_pct, walk_forward_folds, fold_results.

═══ 2. UPDATE QUANDALF'S TOOL LIST ═══

In the "Testing" section of his SOUL.md, replace the old backtest command with:

### Testing (Walk-Forward)
- Run Backtest: python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant VARIANT_NAME
 Walk-forward analysis: trains on rolling window, blind tests on unseen data, reports TRUE out-of-sample performance. Includes HyperLiquid transaction costs. Results auto-saved to SQLite.
- Dry Run: python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant VARIANT_NAME --dry-run
 Shows fold schedule without running.

═══ 3. UPDATE QSCORE THRESHOLDS IN SOUL.md ═══

Under "Strategy Evaluation", update to reflect walk-forward scoring:

When reviewing walk-forward results, commit to a verdict:
- FAIL (OOS QScore < 0.5 OR degradation > 70%): Not viable. The edge doesn't survive unseen data.
- PASS (OOS QScore >= 0.5 AND degradation < 50%): Real edge detected. Worth iterating.
- PROMOTE (OOS QScore >= 1.5 AND degradation < 30%): Strong robust edge. Leaderboard candidate.

NOTE: These thresholds will be recalibrated after testing V1 champions. Walk-forward scores are naturally lower than traditional backtest scores because they measure REAL performance on UNSEEN data.

═══ 4. VERIFY ═══

Show me the updated sections of agents/quandalf/SOUL.md to confirm.

Commit and push.
assistant: Updating Quandalf’s doctrine now, then I’ll show you the exact changed sections and push it.
assistant: The doctrine update is in. I’m committing and pushing it now, then I’ll show you the exact updated sections cleanly.
assistant: [[reply_to_current]] Done.

Updated sections now in `agents/quandalf/SOUL.md`:

```md
## Walk-Forward Backtester (PRIMARY)

Our backtester uses walk-forward analysis — the same method quant funds use. It does NOT test on full historical data (that's curve fitting).

How it works:
1. Splits candle data into rolling folds
2. Each fold: trains on a window, locks parameters, blind-tests on UNSEEN data
3. Slides forward, repeats
4. Only out-of-sample (blind) results count for scoring

Adaptive windows by timeframe:
- 1d: train 12mo, blind 3mo
- 4h: train 6mo, blind 6wk
- 1h: train 3mo, blind 3wk
- 15m: train 1mo, blind 1wk

What this means for you:
- QScore is calculated on OUT-OF-SAMPLE data only — this is the real score
- In-sample QScore is also reported for comparison
- degradation_pct shows how much performance drops on unseen data
- Low degradation (<30%) = robust edge, real strategy
- High degradation (>60%) = curve-fitted garbage, don't iterate on it
- A strategy scoring QS 1.0 on walk-forward is BETTER than QS 4.0 on traditional backtesting
- Every strategy you design gets tested honestly — no more fake returns

Transaction costs are included:
- 0.075% taker fee per side (HyperLiquid rate)
- 0.05% slippage per side
- Both applied automatically

CRITICAL MATH RULE: The engine uses lfilter (forward-only) for any filtering. NEVER request filtfilt — it uses future data and creates look-ahead bias that produces fake returns.

When reviewing results, always check:
1. Out-of-sample QScore (the real score)
2. Degradation % (is the edge real?)
3. Number of folds (more folds = more reliable)
4. Blind window trade count (minimum 15 for statistical validity)

Tool command:
python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec <SPEC_PATH> --variant <VARIANT_NAME>

Same interface as before. Results go to SQLite backtest_results with new columns: qscore_insample, qscore_outofsample, degradation_pct, walk_forward_folds, fold_results.
```

```md
## Strategy Evaluation

When reviewing walk-forward results, commit to a verdict:
- FAIL (OOS QScore < 0.5 OR degradation > 70%): Not viable. The edge doesn't survive unseen data.
- PASS (OOS QScore >= 0.5 AND degradation < 50%): Real edge detected. Worth iterating.
- PROMOTE (OOS QScore >= 1.5 AND degradation < 30%): Strong robust edge. Leaderboard candidate.

NOTE: These thresholds will be recalibrated after testing V1 champions. Walk-forward scores are naturally lower than traditional backtest scores because they measure REAL performance on UNSEEN data.
```

```md
### Testing (Walk-Forward)
- Run Backtest: python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant VARIANT_NAME
 Walk-forward analysis: trains on rolling window, blind tests on unseen data, reports TRUE out-of-sample performance. Includes HyperLiquid transaction costs. Results auto-saved to SQLite.
- Dry Run: python scripts/walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant VARIANT_NAME --dry-run
 Shows fold schedule without running.
```

Commit/push status:
- already committed by auto-sync: `2b097a8`
- push status: `Everything up-to-date`
