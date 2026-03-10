#!/usr/bin/env python3
"""
Walk-Forward Analysis Engine for AutoQuant

PRIMARY backtester — replaces traditional full-history backtesting.

Methodology:
1. Split historical data into rolling train/blind folds
2. Optimize strategy parameters on training window
3. Lock parameters, test on unseen blind window
4. Slide forward, repeat
5. Stitch out-of-sample results only for TRUE performance

Usage:
python walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant NAME
python walk_forward_engine.py --asset ETH --tf 4h --strategy-spec SPEC.json --variant NAME --dry-run
"""

import argparse
import json
import math
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from itertools import product as iter_product

import numpy as np

from regime_tagger import get_regime_tags

try:
    from scipy.signal import butter, lfilter
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

ROOT = os.environ.get(
    "AUTOQUANT_ROOT",
    r"C:\Users\Clamps\.openclaw\workspace-oragorn",
)
DB_PATH = os.path.join(ROOT, "db", "autoquant.db")
CANDLES_DIR = os.path.join(ROOT, "data", "candles")

TAKER_FEE_PCT = 0.075
SLIPPAGE_PCT = 0.05
TOTAL_COST_PCT = (TAKER_FEE_PCT + SLIPPAGE_PCT) / 100.0

WINDOW_CONFIG = {
    "1d": (365, 90),
    "4h": (180, 42),
    "1h": (90, 21),
    "15m": (30, 7),
    "5m": (14, 3),
    "1m": (7, 2),
}

MIN_BLIND_TRADES = 50
MIN_PASS_TRADES = 50
MIN_PROMOTE_TRADES = 50
PF_MIRAGE_THRESHOLD = 3.0
PF_MIRAGE_TRADE_FLOOR = 100
SCREEN_MIN_TRADES = 30


def load_candles(asset: str, timeframe: str) -> list[dict]:
    fname = f"{asset}_{timeframe}.csv"
    fpath = os.path.join(CANDLES_DIR, fname)

    if not os.path.exists(fpath):
        for alt in [f"{asset.upper()}_{timeframe}.csv", f"{asset.lower()}_{timeframe}.csv", f"{asset}-{timeframe}.csv"]:
            alt_path = os.path.join(CANDLES_DIR, alt)
            if os.path.exists(alt_path):
                fpath = alt_path
                break
        else:
            raise FileNotFoundError(
                f"Candle data not found for {asset}/{timeframe}. Looked in {CANDLES_DIR} for {fname}"
            )

    candles = []
    with open(fpath, "r", encoding="utf-8") as f:
        header = [h.strip().lower() for h in f.readline().strip().split(",")]
        for line in f:
            parts = line.strip().split(",")
            if len(parts) < 6:
                continue
            row = dict(zip(header, parts))
            try:
                row_dict = dict(row) if not isinstance(row, dict) else row
                candles.append(
                    {
                        "ts": row_dict.get("timestamp") or row_dict.get("ts") or row_dict.get("date") or row_dict.get("time"),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row_dict.get("volume", 0)),
                    }
                )
            except (ValueError, KeyError):
                continue

    if not candles:
        raise ValueError(f"No valid candles loaded from {fpath}")

    return candles


def sma(values: list[float], period: int) -> list[float | None]:
    out = [None] * len(values)
    for i in range(period - 1, len(values)):
        out[i] = sum(values[i - period + 1 : i + 1]) / period
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
    out[period] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        out[i + 1] = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + avg_gain / avg_loss))
    return out


def atr(candles: list[dict], period: int = 14) -> list[float | None]:
    out = [None] * len(candles)
    trs = []
    for i in range(len(candles)):
        if i == 0:
            tr = candles[i]["high"] - candles[i]["low"]
        else:
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i - 1]["close"]),
                abs(candles[i]["low"] - candles[i - 1]["close"]),
            )
        trs.append(tr)

    if len(trs) >= period:
        out[period - 1] = sum(trs[:period]) / period
        for i in range(period, len(trs)):
            out[i] = (out[i - 1] * (period - 1) + trs[i]) / period
    return out


def supertrend(candles: list[dict], atr_period: int = 10, multiplier: float = 3.0):
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

        if not (lower_band[i] > lower_band[i - 1] or candles[i - 1]["close"] < lower_band[i - 1]):
            lower_band[i] = lower_band[i - 1]
        if not (upper_band[i] < upper_band[i - 1] or candles[i - 1]["close"] > upper_band[i - 1]):
            upper_band[i] = upper_band[i - 1]

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


def vortex(candles: list[dict], period: int = 14):
    n = len(candles)
    out = [(None, None)] * n
    if n < period + 1:
        return out

    vm_plus = []
    vm_minus = []
    tr_list = []
    for i in range(1, n):
        vm_plus.append(abs(candles[i]["high"] - candles[i - 1]["low"]))
        vm_minus.append(abs(candles[i]["low"] - candles[i - 1]["high"]))
        tr_list.append(
            max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i - 1]["close"]),
                abs(candles[i]["low"] - candles[i - 1]["close"]),
            )
        )

    for i in range(period - 1, len(vm_plus)):
        sum_vmp = sum(vm_plus[i - period + 1 : i + 1])
        sum_vmm = sum(vm_minus[i - period + 1 : i + 1])
        sum_tr = sum(tr_list[i - period + 1 : i + 1])
        if sum_tr != 0:
            out[i + 1] = (sum_vmp / sum_tr, sum_vmm / sum_tr)
    return out


def cci(candles: list[dict], period: int = 20) -> list[float | None]:
    out = [None] * len(candles)
    tp = [(c["high"] + c["low"] + c["close"]) / 3.0 for c in candles]
    for i in range(period - 1, len(tp)):
        window = tp[i - period + 1 : i + 1]
        mean_tp = sum(window) / period
        mean_dev = sum(abs(v - mean_tp) for v in window) / period
        out[i] = 0.0 if mean_dev == 0 else (tp[i] - mean_tp) / (0.015 * mean_dev)
    return out


def macd(closes: list[float], fast: int = 12, slow: int = 26, signal: int = 9):
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
    if not HAS_SCIPY:
        fallback = ema(values, cutoff_period)
        return [v if v is not None else 0.0 for v in fallback]
    nyquist = 0.5
    normalised_cutoff = min((1.0 / cutoff_period) / nyquist, 0.99)
    b_coeff, a_coeff = butter(order, normalised_cutoff, btype="low")
    return lfilter(b_coeff, a_coeff, values).tolist()


def normalize_parameter_map(raw_params) -> dict:
    if isinstance(raw_params, dict):
        return dict(raw_params)
    if isinstance(raw_params, list):
        out = {}
        for item in raw_params:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            if not name:
                continue
            out[str(name)] = item.get("value", item.get("default"))
        return out
    return {}


def normalize_directional_rules(raw_rules) -> dict:
    if isinstance(raw_rules, dict):
        return {
            "long": list(raw_rules.get("long") or []),
            "short": list(raw_rules.get("short") or []),
        }
    if isinstance(raw_rules, list):
        rules = list(raw_rules)
        return {"long": rules, "short": rules}
    return {"long": [], "short": []}


def normalize_risk(spec: dict, variant: dict) -> dict:
    risk = {}
    if isinstance(spec.get("risk"), dict):
        risk.update(spec.get("risk", {}))
    if isinstance(variant.get("risk"), dict):
        risk.update(variant.get("risk", {}))

    position_sizing = spec.get("position_sizing") if isinstance(spec.get("position_sizing"), dict) else {}
    risk_policy = variant.get("risk_policy") if isinstance(variant.get("risk_policy"), dict) else {}
    execution_policy = variant.get("execution_policy") if isinstance(variant.get("execution_policy"), dict) else {}
    risk_rules = variant.get("risk_rules") if isinstance(variant.get("risk_rules"), list) else []

    if "risk_per_trade_pct" in position_sizing and "risk_per_trade_pct" not in risk:
        risk["risk_per_trade_pct"] = position_sizing["risk_per_trade_pct"]
    risk.update(risk_policy)
    risk.update(execution_policy)

    for rule in risk_rules:
        if not isinstance(rule, str) or "=" not in rule:
            continue
        key, value = rule.split("=", 1)
        key = key.strip()
        value = value.strip()
        try:
            parsed_value = float(value)
            if parsed_value.is_integer():
                parsed_value = int(parsed_value)
        except ValueError:
            parsed_value = value
        risk[key] = parsed_value
    return risk


def parse_strategy_spec(spec_path: str, variant_name: str = "default") -> dict:
    with open(spec_path, "r", encoding="utf-8") as f:
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

    trade_management = spec.get("trade_management") if isinstance(spec.get("trade_management"), dict) else {}
    entry_style = str(trade_management.get("entry_style") or "one_shot").strip().lower()
    exit_style = str(trade_management.get("exit_style") or "one_shot").strip().lower()
    supported_entry_styles = {"one_shot"}
    supported_exit_styles = {"one_shot"}
    management_supported = entry_style in supported_entry_styles and exit_style in supported_exit_styles
    unsupported = []
    if entry_style not in supported_entry_styles:
        unsupported.append(f"entry_style:{entry_style}")
    if exit_style not in supported_exit_styles:
        unsupported.append(f"exit_style:{exit_style}")

    return {
        "spec": spec,
        "variant": variant,
        "strategy_name": spec.get("name", spec.get("id", "unknown")),
        "entry_rules": normalize_directional_rules(spec.get("entry_rules", variant.get("entry_rules", []))),
        "exit_rules": normalize_directional_rules(spec.get("exit_rules", variant.get("exit_rules", []))),
        "parameters": normalize_parameter_map(variant.get("parameters", spec.get("parameters", {}))),
        "risk": normalize_risk(spec, variant),
        "declared_indicators": list(spec.get("indicators") or []),
        "trade_management": trade_management,
        "management_supported": management_supported,
        "unsupported_management_styles": unsupported,
    }


def donchian_channels(candles: list[dict], period: int = 20):
    n = len(candles)
    lower = [None] * n
    middle = [None] * n
    upper = [None] * n
    for i in range(period - 1, n):
        window = candles[i - period + 1 : i + 1]
        low = min(c["low"] for c in window)
        high = max(c["high"] for c in window)
        lower[i] = low
        upper[i] = high
        middle[i] = (low + high) / 2.0
    return lower, middle, upper


def choppiness_index(candles: list[dict], period: int = 14) -> list[float | None]:
    out = [None] * len(candles)
    atr_vals = atr(candles, 1)
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        tr_sum = sum(v for v in atr_vals[i - period + 1 : i + 1] if v is not None)
        high_max = max(c["high"] for c in window)
        low_min = min(c["low"] for c in window)
        denom = high_max - low_min
        if denom > 0 and tr_sum > 0:
            out[i] = 100.0 * math.log10(tr_sum / denom) / math.log10(period)
    return out


def compute_indicators(candles: list[dict], params: dict, declared_indicators: list[str] | None = None) -> dict:
    closes = [c["close"] for c in candles]
    indicators = {"close": closes}
    declared_indicators = declared_indicators or []

    ema_periods = {14, 20, 21, 50, 200}
    sma_periods = {14, 20, 21, 50, 200}
    for key in ("ema_fast", "ema_slow", "fast_ema", "slow_ema"):
        value = params.get(key)
        if value is not None:
            ema_periods.add(int(value))
    for indicator_name in declared_indicators:
        upper_name = str(indicator_name).upper()
        if upper_name.startswith("EMA_"):
            try:
                ema_periods.add(int(upper_name.split("_")[1]))
            except (IndexError, ValueError):
                pass
        if upper_name.startswith("SMA_"):
            try:
                sma_periods.add(int(upper_name.split("_")[1]))
            except (IndexError, ValueError):
                pass

    for p in sorted(ema_periods | sma_periods):
        indicators[f"sma_{p}"] = sma(closes, p)
        indicators[f"ema_{p}"] = ema(closes, p)
    indicators["rsi_14"] = rsi(closes, 14)
    indicators["atr_14"] = atr(candles, 14)
    indicators["cci_20"] = cci(candles, 20)
    indicators["chop_14_1_100"] = choppiness_index(candles, 14)
    dcl_20, dcm_20, dcu_20 = donchian_channels(candles, 20)
    indicators["dcl_20_20"] = dcl_20
    indicators["dcm_20_20"] = dcm_20
    indicators["dcu_20_20"] = dcu_20
    dcl_10, dcm_10, dcu_10 = donchian_channels(candles, 10)
    indicators["dcl_10_10"] = dcl_10
    indicators["dcm_10_10"] = dcm_10
    indicators["dcu_10_10"] = dcu_10
    st_period = params.get("supertrend_period", params.get("atr_period", 10))
    st_mult = params.get("supertrend_multiplier", params.get("multiplier", 3.0))
    indicators["supertrend"] = supertrend(candles, int(st_period), float(st_mult))
    indicators["vortex"] = vortex(candles, int(params.get("vortex_period", 14)))
    indicators["macd"] = macd(
        closes,
        int(params.get("macd_fast", 12)),
        int(params.get("macd_slow", 26)),
        int(params.get("macd_signal", 9)),
    )
    indicators["bw_close"] = butterworth_lfilter(closes, int(params.get("butterworth_period", 20)))
    return indicators


def evaluate_condition(condition: str, idx: int, indicators: dict, candles: list[dict]) -> bool:
    if not condition or not condition.strip():
        return True
    condition = condition.strip()

    def get_value(token: str):
        token = token.strip()
        try:
            return float(token)
        except ValueError:
            pass
        t = token.lower().replace("-", "_")
        if t in ("close", "price"):
            return candles[idx]["close"]
        if t == "high":
            return candles[idx]["high"]
        if t == "low":
            return candles[idx]["low"]
        if t == "open":
            return candles[idx]["open"]
        if (t.startswith("sma_") or t.startswith("ema_") or t.startswith("dcl_") or t.startswith("dcm_") or t.startswith("dcu_") or t.startswith("chop_")) and t in indicators and indicators[t][idx] is not None:
            return indicators[t][idx]
        if t.startswith("rsi"):
            return indicators["rsi_14"][idx]
        if t.startswith("atr"):
            return indicators["atr_14"][idx]
        if t.startswith("cci"):
            return indicators["cci_20"][idx]
        if t in ("supertrend_direction", "st_direction", "supertrend_dir"):
            st = indicators.get("supertrend")
            return float(st[idx][1]) if st and st[idx] else None
        if t in ("supertrend_value", "st_value", "supertrend"):
            st = indicators.get("supertrend")
            return float(st[idx][0]) if st and st[idx] else None
        if t in ("vortex_plus", "vi_plus", "vi+", "vtxp_14"):
            vx = indicators.get("vortex")
            return vx[idx][0] if vx and vx[idx] and vx[idx][0] is not None else None
        if t in ("vortex_minus", "vi_minus", "vi-", "vtxm_14"):
            vx = indicators.get("vortex")
            return vx[idx][1] if vx and vx[idx] and vx[idx][1] is not None else None
        if t in ("macd_line", "macd"):
            m = indicators.get("macd")
            return m[idx][0] if m and m[idx] and m[idx][0] is not None else None
        if t in ("macd_signal", "macd_sig"):
            m = indicators.get("macd")
            return m[idx][1] if m and m[idx] and m[idx][1] is not None else None
        if t in ("macd_histogram", "macd_hist"):
            m = indicators.get("macd")
            return m[idx][2] if m and m[idx] and m[idx][2] is not None else None
        if t in ("bw_close", "butterworth", "filtered_close"):
            bw = indicators.get("bw_close")
            return bw[idx] if bw and idx < len(bw) else None
        return None

    for op_str, op_fn in [
        (">=", lambda a, b: a >= b),
        ("<=", lambda a, b: a <= b),
        ("==", lambda a, b: abs(a - b) < 1e-10),
        ("!=", lambda a, b: abs(a - b) >= 1e-10),
        (">", lambda a, b: a > b),
        ("<", lambda a, b: a < b),
    ]:
        if op_str in condition:
            left_text, right_text = condition.split(op_str, 1)
            left = get_value(left_text)
            right = get_value(right_text)
            return left is not None and right is not None and op_fn(left, right)

    lower_condition = condition.lower()
    if "crosses_above" in lower_condition or "cross_above" in lower_condition:
        parts = lower_condition.replace("crosses_above", "|").replace("cross_above", "|").split("|")
        if len(parts) == 2 and idx > 0:
            left_text = parts[0].strip()
            right_text = parts[1].strip()
            prev_left = evaluate_condition(f"{left_text} <= {right_text}", idx - 1, indicators, candles)
            curr_left = evaluate_condition(f"{left_text} > {right_text}", idx, indicators, candles)
            return prev_left and curr_left
    if "crosses_below" in lower_condition or "cross_below" in lower_condition:
        parts = lower_condition.replace("crosses_below", "|").replace("cross_below", "|").split("|")
        if len(parts) == 2 and idx > 0:
            left_text = parts[0].strip()
            right_text = parts[1].strip()
            prev_left = evaluate_condition(f"{left_text} >= {right_text}", idx - 1, indicators, candles)
            curr_left = evaluate_condition(f"{left_text} < {right_text}", idx, indicators, candles)
            return prev_left and curr_left
    return False


def run_strategy_on_candles(candles: list[dict], strategy: dict, params_override: dict | None = None) -> dict:
    params = dict(strategy.get("parameters", {}))
    unsupported_management_styles = list(strategy.get("unsupported_management_styles") or [])
    if params_override:
        params.update(params_override)

    entry_rules = normalize_directional_rules(strategy.get("entry_rules", []))
    exit_rules = normalize_directional_rules(strategy.get("exit_rules", []))
    risk = strategy.get("risk", {})

    sl_pct = float(risk.get("stop_loss_pct", risk.get("stop_loss", 5.0)))
    tp_pct = float(risk.get("take_profit_pct", risk.get("take_profit", 10.0)))
    rr_ratio = risk.get("reward_risk_ratio", risk.get("rr_ratio"))
    if rr_ratio:
        try:
            if isinstance(rr_ratio, str) and ":" in rr_ratio:
                tp_pct = sl_pct * float(rr_ratio.split(":")[0])
            else:
                tp_pct = sl_pct * float(rr_ratio)
        except (ValueError, IndexError):
            pass

    atr_period = int(risk.get("atr_period", 14))
    stop_atr_mult = risk.get("stop_atr_mult")
    tp_atr_mult = risk.get("tp_atr_mult")
    max_holding_bars = risk.get("max_holding_bars")
    try:
        max_holding_bars = int(max_holding_bars) if max_holding_bars is not None else None
    except (TypeError, ValueError):
        max_holding_bars = None

    indicators = compute_indicators(candles, params, strategy.get("declared_indicators"))
    trades = []
    position = None
    equity_curve = [1.0]
    warmup = min(200, max(1, len(candles) // 4))

    for i in range(warmup, len(candles)):
        close = candles[i]["close"]
        if position is not None:
            entry_price = position["entry_price"]
            direction = position["direction"]
            pnl_pct = ((close - entry_price) / entry_price) * 100.0 if direction == "long" else ((entry_price - close) / entry_price) * 100.0
            exit_signal = False
            exit_reason = ""

            atr_value = indicators.get(f"atr_{atr_period}", indicators.get("atr_14", []))[i]
            if stop_atr_mult and atr_value is not None:
                stop_move_pct = (float(stop_atr_mult) * atr_value / entry_price) * 100.0
                if pnl_pct <= -stop_move_pct:
                    exit_signal = True
                    exit_reason = "stop_loss"
                    pnl_pct = -stop_move_pct
            elif pnl_pct <= -sl_pct:
                exit_signal = True
                exit_reason = "stop_loss"
                pnl_pct = -sl_pct

            if not exit_signal:
                if tp_atr_mult and atr_value is not None:
                    tp_move_pct = (float(tp_atr_mult) * atr_value / entry_price) * 100.0
                    if pnl_pct >= tp_move_pct:
                        exit_signal = True
                        exit_reason = "take_profit"
                        pnl_pct = tp_move_pct
                elif pnl_pct >= tp_pct:
                    exit_signal = True
                    exit_reason = "take_profit"
                    pnl_pct = tp_pct

            if not exit_signal and max_holding_bars is not None and (i - position["entry_idx"]) >= max_holding_bars:
                exit_signal = True
                exit_reason = "time_stop"

            if not exit_signal:
                for rule in exit_rules.get(direction, []):
                    cond = rule if isinstance(rule, str) else rule.get("condition", "")
                    lower_cond = cond.lower()
                    if any(prefix in lower_cond for prefix in ("stop loss:", "take profit:", "time stop:")):
                        continue
                    if evaluate_condition(cond, i, indicators, candles):
                        exit_signal = True
                        exit_reason = "exit_rule"
                        break
            if exit_signal:
                net_pnl_pct = pnl_pct - (TOTAL_COST_PCT * 100.0 * 2)
                trades.append(
                    {
                        "entry_idx": position["entry_idx"],
                        "exit_idx": i,
                        "entry_price": entry_price,
                        "exit_price": close,
                        "direction": direction,
                        "pnl_pct": net_pnl_pct,
                        "gross_pnl_pct": pnl_pct,
                        "exit_reason": exit_reason,
                    }
                )
                equity_curve.append(equity_curve[-1] * (1 + net_pnl_pct / 100.0))
                position = None
                continue

        if position is None:
            for direction in ("long", "short"):
                direction_rules = entry_rules.get(direction, [])
                if not direction_rules:
                    continue
                all_met = True
                for rule in direction_rules:
                    cond = rule if isinstance(rule, str) else rule.get("condition", "")
                    if not evaluate_condition(cond, i, indicators, candles):
                        all_met = False
                        break
                if all_met:
                    position = {"entry_price": close, "entry_idx": i, "direction": direction}
                    break
        equity_curve.append(equity_curve[-1])

    if position is not None:
        close = candles[-1]["close"]
        entry_price = position["entry_price"]
        pnl_pct = ((close - entry_price) / entry_price) * 100.0 if position["direction"] == "long" else ((entry_price - close) / entry_price) * 100.0
        net_pnl_pct = pnl_pct - (TOTAL_COST_PCT * 100.0 * 2)
        trades.append(
            {
                "entry_idx": position["entry_idx"],
                "exit_idx": len(candles) - 1,
                "entry_price": entry_price,
                "exit_price": close,
                "direction": position["direction"],
                "pnl_pct": net_pnl_pct,
                "gross_pnl_pct": pnl_pct,
                "exit_reason": "end_of_data",
            }
        )
        equity_curve.append(equity_curve[-1] * (1 + net_pnl_pct / 100.0))

    metrics = compute_metrics(trades, equity_curve)
    if unsupported_management_styles:
        metrics["unsupported_management_style"] = unsupported_management_styles
    return metrics


def compute_metrics(trades: list[dict], equity_curve: list[float]) -> dict:
    if not trades:
        return {
            "total_trades": 0,
            "win_rate_pct": 0.0,
            "profit_factor": 0.0,
            "max_drawdown_pct": 0.0,
            "total_return_pct": 0.0,
            "avg_trade_pct": 0.0,
            "sharpe_ratio": 0.0,
            "trades": trades,
            "equity_curve": equity_curve,
        }
    winners = [t for t in trades if t["pnl_pct"] > 0]
    losers = [t for t in trades if t["pnl_pct"] <= 0]
    gross_profit = sum(t["pnl_pct"] for t in winners) if winners else 0.0
    gross_loss = abs(sum(t["pnl_pct"] for t in losers)) if losers else 0.0
    pf = gross_profit / gross_loss if gross_loss > 0 else (10.0 if gross_profit > 0 else 0.0)
    peak = equity_curve[0]
    max_dd = 0.0
    for val in equity_curve:
        if val > peak:
            peak = val
        dd = ((peak - val) / peak) * 100.0 if peak > 0 else 0.0
        max_dd = max(max_dd, dd)
    total_return = ((equity_curve[-1] / equity_curve[0]) - 1) * 100.0 if equity_curve[0] > 0 else 0.0
    pnls = [t["pnl_pct"] for t in trades]
    avg_trade = sum(pnls) / len(pnls) if pnls else 0.0
    if len(pnls) > 1:
        mean_r = float(np.mean(pnls))
        std_r = float(np.std(pnls, ddof=1))
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


def calculate_qscore(metrics: dict) -> dict:
    pf = float(metrics.get("profit_factor", 0.0) or 0.0)
    dd = float(metrics.get("max_drawdown_pct", 0.0) or 0.0)
    trades = int(metrics.get("total_trades", 0) or 0)
    score_edge = pf
    score_resilience = -(dd / 100.0)
    raw_score_total = score_edge + score_resilience
    confidence_discount = 1.0
    flags = []

    if trades < PF_MIRAGE_TRADE_FLOOR and pf > PF_MIRAGE_THRESHOLD:
        confidence_discount = max(0.0, min(1.0, trades / float(PF_MIRAGE_TRADE_FLOOR)))
        flags.append("pf_mirage_discount")

    score_total = raw_score_total * confidence_discount
    suspect = pf > 4.0 and trades < PF_MIRAGE_TRADE_FLOOR
    if suspect:
        flags.append("suspect_overfit")
    if trades < MIN_PASS_TRADES:
        flags.append("low_trade_count")
        flags.append("below_scoring_floor")

    if trades >= MIN_PROMOTE_TRADES and score_total >= 1.5:
        decision, grade = "promote", "A"
    elif trades >= MIN_PASS_TRADES and score_total >= 0.5:
        decision, grade = "pass", "B"
    else:
        decision, grade = "fail", ("C" if score_total >= 0.5 else "D")

    return {
        "score_total": round(score_total, 3),
        "score_edge": round(score_edge, 3),
        "score_resilience": round(score_resilience, 3),
        "score_decision": decision,
        "score_grade": grade,
        "score_flags": json.dumps(sorted(set(flags))),
        "suspect": suspect,
        "raw_score_total": round(raw_score_total, 3),
        "confidence_discount": round(confidence_discount, 3),
    }




def compute_regime_scores(trades: list[dict], regime_payload: dict) -> tuple[dict, float, str, list[str]]:
    tags = regime_payload.get("tags") or []
    regime_groups = {}
    total_trades = len(trades)
    for trade in trades:
        entry_idx = trade.get("entry_idx_abs", trade.get("entry_idx"))
        regime = "UNKNOWN"
        if isinstance(entry_idx, int) and 0 <= entry_idx < len(tags):
            regime = tags[entry_idx].get("regime") or "UNKNOWN"
        trade["entry_regime"] = regime
        regime_groups.setdefault(regime, []).append(trade)

    regime_scores = {}
    primary_regime = "UNKNOWN"
    primary_count = 0
    for regime, regime_trades in regime_groups.items():
        metrics = compute_metrics(regime_trades, [1.0])
        qscore = calculate_qscore(metrics) if metrics["total_trades"] >= 15 else None
        regime_scores[regime] = {
            "trade_count": metrics["total_trades"],
            "profit_factor": metrics["profit_factor"],
            "win_rate": round(metrics["win_rate_pct"], 2),
            "avg_return": metrics["avg_trade_pct"],
            "qscore": qscore["score_total"] if qscore else None,
        }
        if metrics["total_trades"] > primary_count:
            primary_count = metrics["total_trades"]
            primary_regime = regime

    concentration = round((primary_count / total_trades) * 100.0, 2) if total_trades else 0.0
    flags = []
    if concentration > 80.0:
        flags.append("regime_specialist")
    if total_trades and concentration < 40.0:
        flags.append("robust_across_regimes")
    chop_qs = (regime_scores.get("CHOP") or {}).get("qscore")
    if chop_qs is not None and chop_qs > 1.0:
        flags.append("valuable_in_chop")
    return regime_scores, concentration, primary_regime, flags

def extend_blind_window(candles: list[dict], blind_start: int, blind_end: int, strategy: dict, max_end: int) -> int:
    current_end = blind_end
    while current_end <= max_end:
        probe = run_strategy_on_candles(candles[blind_start:current_end], strategy)
        if probe["total_trades"] >= MIN_BLIND_TRADES or current_end == max_end:
            return current_end
        current_end = min(max_end, current_end + max(1, (current_end - blind_start) // 2))
    return blind_end


def trim_to_recent_months(candles: list[dict], months: int = 3) -> list[dict]:
    if not candles:
        return candles
    approx_days = max(1, months * 30)
    timeframe_guess = str(candles[0].get("ts", ""))
    cpd = 6
    if len(candles) > 1:
        first_ts = candles[0].get("ts")
        second_ts = candles[1].get("ts")
        try:
            a = datetime.fromisoformat(str(first_ts).replace("Z", "+00:00"))
            b = datetime.fromisoformat(str(second_ts).replace("Z", "+00:00"))
            delta_minutes = max(1, int((b - a).total_seconds() // 60))
            cpd = max(1, int(round((24 * 60) / delta_minutes)))
        except Exception:
            cpd = 6
    keep = min(len(candles), approx_days * cpd)
    return candles[-keep:]


def run_walk_forward(candles: list[dict], strategy: dict, timeframe: str, asset: str = "unknown", param_grid: dict | None = None, stage: str = "full") -> dict:
    if stage == "screen":
        screen_candles = trim_to_recent_months(candles, months=3)
        screen_metrics = run_strategy_on_candles(screen_candles, strategy)
        regime_payload = get_regime_tags("screen", timeframe, candles=screen_candles, force=True)
        regime_scores, regime_concentration, primary_regime, regime_flags = compute_regime_scores(screen_metrics["trades"], regime_payload)
        passed = (
            screen_metrics["total_trades"] >= SCREEN_MIN_TRADES
            and screen_metrics["profit_factor"] >= 1.0
            and screen_metrics["max_drawdown_pct"] <= 15.0
        )
        screen_qscore = calculate_qscore(screen_metrics)
        return {
            "status": "ok",
            "folds": 1,
            "fold_results": [{
                "fold": 1,
                "train_candles": 0,
                "blind_candles": len(screen_candles),
                "best_params": None,
                "insample": None,
                "outofsample": {
                    "trades": screen_metrics["total_trades"],
                    "pf": screen_metrics["profit_factor"],
                    "max_dd": screen_metrics["max_drawdown_pct"],
                    "return_pct": screen_metrics["total_return_pct"],
                    "win_rate": screen_metrics["win_rate_pct"],
                    "qscore": screen_qscore["score_total"],
                },
            }],
            "insample_aggregate": {
                "total_trades": 0,
                "profit_factor": 0.0,
                "max_drawdown_pct": 0.0,
                "total_return_pct": 0.0,
                "win_rate_pct": 0.0,
                "sharpe_ratio": 0.0,
                "qscore": 0.0,
                "decision": "screen",
            },
            "outofsample_aggregate": {
                "total_trades": screen_metrics["total_trades"],
                "profit_factor": screen_metrics["profit_factor"],
                "max_drawdown_pct": screen_metrics["max_drawdown_pct"],
                "total_return_pct": screen_metrics["total_return_pct"],
                "win_rate_pct": screen_metrics["win_rate_pct"],
                "sharpe_ratio": screen_metrics["sharpe_ratio"],
                "qscore": screen_qscore["score_total"],
                "decision": "pass" if passed else "fail",
                "grade": "S" if passed else "F",
                "flags": json.dumps((["screen_pass" if passed else "screen_fail"] + regime_flags + (screen_metrics.get("unsupported_management_style") or []))),
                "regime_scores": regime_scores,
                "regime_concentration": regime_concentration,
                "primary_regime": primary_regime,
            },
            "degradation_pct": 0.0,
            "regime_scores": regime_scores,
            "regime_concentration": regime_concentration,
            "primary_regime": primary_regime,
            "screen_passed": passed,
            "walk_forward_config": {
                "stage": "screen",
                "months": 3,
                "folds": 1,
                "timeframe": timeframe,
                "transaction_cost_pct": round(TOTAL_COST_PCT * 100.0, 4),
            },
        }

    train_days, blind_days = WINDOW_CONFIG.get(timeframe, (180, 42))
    candles_per_day = {"1d": 1, "4h": 6, "1h": 24, "15m": 96, "5m": 288, "1m": 1440}
    cpd = candles_per_day.get(timeframe, 6)
    train_candles = train_days * cpd
    blind_candles = blind_days * cpd
    total_candles = len(candles)
    if total_candles < train_candles + blind_candles:
        return {"status": "error", "error": f"Not enough data: {total_candles} candles, need {train_candles + blind_candles}", "folds": 0}

    param_grid = param_grid or {}
    folds = []
    fold_start = 0
    while fold_start + train_candles + blind_candles <= total_candles:
        train_end = fold_start + train_candles
        blind_end = min(total_candles, train_end + blind_candles)
        blind_end = extend_blind_window(candles, train_end, blind_end, strategy, total_candles)
        folds.append({
            "fold_num": len(folds) + 1,
            "train_start": fold_start,
            "train_end": train_end,
            "blind_start": train_end,
            "blind_end": blind_end,
        })
        fold_start = blind_end
    if not folds:
        return {"status": "error", "error": "Could not create any folds with the given data", "folds": 0}

    fold_results = []
    all_oos_trades = []
    all_oos_equity = [1.0]
    all_is_trades = []

    for fold in folds:
        train_data = candles[fold["train_start"] : fold["train_end"]]
        blind_data = candles[fold["blind_start"] : fold["blind_end"]]
        is_result = run_strategy_on_candles(train_data, strategy)
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
        oos_result = run_strategy_on_candles(blind_data, strategy, params_override=best_params)
        for trade in oos_result["trades"]:
            trade["entry_idx_abs"] = fold["blind_start"] + int(trade.get("entry_idx", 0))
            trade["exit_idx_abs"] = fold["blind_start"] + int(trade.get("exit_idx", 0))
        for trade in is_result["trades"]:
            trade["entry_idx_abs"] = fold["train_start"] + int(trade.get("entry_idx", 0))
            trade["exit_idx_abs"] = fold["train_start"] + int(trade.get("exit_idx", 0))
        all_oos_trades.extend(oos_result["trades"])
        all_is_trades.extend(is_result["trades"])
        if oos_result["equity_curve"]:
            last_equity = all_oos_equity[-1]
            for eq_val in oos_result["equity_curve"][1:]:
                all_oos_equity.append(last_equity * eq_val)
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

    agg_is = compute_metrics(all_is_trades, [1.0])
    agg_oos = compute_metrics(all_oos_trades, all_oos_equity)
    regime_payload = get_regime_tags(asset, timeframe, candles=candles)
    regime_scores, regime_concentration, primary_regime, regime_flags = compute_regime_scores(all_oos_trades, regime_payload)
    is_qscore = calculate_qscore(agg_is)
    oos_qscore = calculate_qscore(agg_oos)
    is_qs_val = is_qscore["score_total"]
    oos_qs_val = oos_qscore["score_total"]
    degradation_pct = round((1.0 - oos_qs_val / is_qs_val) * 100.0, 1) if is_qs_val > 0 else (0.0 if oos_qs_val >= 0 else 100.0)

    final_decision = "fail"
    final_grade = "D"
    if agg_oos["total_trades"] >= MIN_PROMOTE_TRADES and oos_qs_val >= 1.5 and degradation_pct < 30.0:
        final_decision = "promote"
        final_grade = "A"
    elif agg_oos["total_trades"] >= MIN_PASS_TRADES and oos_qs_val >= 0.5 and degradation_pct < 50.0:
        final_decision = "pass"
        final_grade = "B"
    elif oos_qs_val >= 0.5:
        final_grade = "C"

    final_flags = sorted(set(json.loads(oos_qscore["score_flags"]) + regime_flags))
    if agg_oos["total_trades"] < MIN_PASS_TRADES:
        final_flags.append("below_scoring_floor")
    if agg_oos["total_trades"] < MIN_PASS_TRADES or degradation_pct > 70.0:
        final_decision = "fail"

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
            "raw_qscore": oos_qscore.get("raw_score_total", oos_qscore["score_total"]),
            "confidence_discount": oos_qscore.get("confidence_discount", 1.0),
            "decision": final_decision,
            "grade": final_grade,
            "flags": json.dumps(sorted(set(final_flags))),
            "regime_scores": regime_scores,
            "regime_concentration": regime_concentration,
            "primary_regime": primary_regime,
        },
        "degradation_pct": degradation_pct,
        "regime_scores": regime_scores,
        "regime_concentration": regime_concentration,
        "primary_regime": primary_regime,
        "unsupported_management_style": agg_oos.get("unsupported_management_style") or [],
        "walk_forward_config": {
            "train_days": train_days,
            "blind_days": blind_days,
            "timeframe": timeframe,
            "min_blind_trades": MIN_BLIND_TRADES,
        },
    }


def ensure_schema(conn: sqlite3.Connection):
    cursor = conn.cursor()
    existing = {row[1] for row in cursor.execute("PRAGMA table_info(backtest_results)")}
    new_columns = {
        "qscore_insample": "REAL",
        "qscore_outofsample": "REAL",
        "degradation_pct": "REAL",
        "walk_forward_folds": "INTEGER",
        "walk_forward_config": "TEXT",
        "fold_results": "TEXT",
        "strategy_family": "TEXT DEFAULT ''",
        "parent_id": "TEXT",
        "mutation_type": "TEXT",
        "stage": "TEXT DEFAULT 'full'",
        "validation_target": "TEXT",
        "family_generation": "INTEGER DEFAULT 1",
        "killed": "INTEGER DEFAULT 0",
        "regime_scores": "TEXT",
        "regime_concentration": "REAL",
        "primary_regime": "TEXT",
        "portability_score": "REAL DEFAULT 0",
        "refinement_status": "TEXT",
        "refinement_round": "INTEGER DEFAULT 0",
        "weakness_profile": "TEXT",
        "fallback_source": "INTEGER DEFAULT 0",
    }
    for col, col_type in new_columns.items():
        if col not in existing:
            try:
                cursor.execute(f"ALTER TABLE backtest_results ADD COLUMN {col} {col_type}")
            except sqlite3.OperationalError:
                pass
    cursor.execute("UPDATE backtest_results SET stage = COALESCE(NULLIF(stage, ''), 'full')")
    cursor.execute("UPDATE backtest_results SET family_generation = COALESCE(family_generation, 1)")
    cursor.execute("UPDATE backtest_results SET killed = COALESCE(killed, 0)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_bt_family_stage_killed ON backtest_results(strategy_family, stage, killed)")
    conn.commit()


def save_result(
    conn: sqlite3.Connection,
    spec_id: str,
    variant_id: str,
    asset: str,
    timeframe: str,
    wf_result: dict,
    candles: list[dict],
    stage: str = "full",
    strategy_family: str | None = None,
    parent_id: str | None = None,
    # NOTE: 0-trade guard added at top of function body
    mutation_type: str | None = None,
    validation_target: str | None = None,
    family_generation: int = 1,
    refinement_round: int = 0,
    fallback_source: int = 0,
):
    ensure_schema(conn)
    oos = wf_result["outofsample_aggregate"]
    ins = wf_result["insample_aggregate"]

    # GUARD: Do not write 0-trade results to DB — they are noise, not signal
    oos_trades = int(oos.get("total_trades", 0) or 0)
    ins_trades = int(ins.get("total_trades", 0) or 0)
    if oos_trades == 0 and ins_trades == 0:
        return {
            "status": "skipped",
            "reason": "zero_trades_both_samples",
            "spec_id": spec_id,
            "variant_id": variant_id,
            "asset": asset,
            "timeframe": timeframe,
        }
    if oos_trades == 0:
        return {
            "status": "skipped",
            "reason": "zero_oos_trades",
            "spec_id": spec_id,
            "variant_id": variant_id,
            "asset": asset,
            "timeframe": timeframe,
            "insample_trades": ins_trades,
        }

    result_id = f"wf_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()
    period_start = candles[0]["ts"] if candles else now
    period_end = candles[-1]["ts"] if candles else now
    candle_count = len(candles)
    metrics_blob = {
        "insample": ins,
        "outofsample": oos,
        "degradation_pct": wf_result["degradation_pct"],
        "walk_forward_config": wf_result["walk_forward_config"],
        "regime_scores": wf_result.get("regime_scores") or {},
        "regime_concentration": wf_result.get("regime_concentration", 0.0),
        "primary_regime": wf_result.get("primary_regime") or "UNKNOWN",
    }
    score_details = {
        "method": "walk_forward_qscore",
        "insample_qscore": ins["qscore"],
        "outofsample_qscore": oos["qscore"],
        "degradation_pct": wf_result["degradation_pct"],
        "flags": oos.get("flags"),
        "regime_scores": wf_result.get("regime_scores") or {},
        "regime_concentration": wf_result.get("regime_concentration", 0.0),
        "primary_regime": wf_result.get("primary_regime") or "UNKNOWN",
    }
    conn.execute(
        """
        INSERT INTO backtest_results (
            id, ts_iso, strategy_spec_id, variant_id, asset, timeframe,
            period_start, period_end, candle_count,
            profit_factor, total_return_pct, max_drawdown_pct, total_trades, win_rate_pct,
            avg_trade_pct, sharpe_ratio, metrics,
            score_total, score_decision, score_edge, score_resilience,
            score_grade, score_flags, score_details,
            walk_forward, status,
            qscore_insample, qscore_outofsample, degradation_pct,
            walk_forward_folds, walk_forward_config, fold_results,
            strategy_family, parent_id, mutation_type, stage, validation_target, family_generation, killed,
            regime_scores, regime_concentration, primary_regime, portability_score, refinement_status, refinement_round, weakness_profile, fallback_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            result_id,
            now,
            spec_id,
            variant_id,
            asset,
            timeframe,
            period_start,
            period_end,
            candle_count,
            oos["profit_factor"],
            oos["total_return_pct"],
            oos["max_drawdown_pct"],
            oos["total_trades"],
            oos["win_rate_pct"],
            0.0,
            oos["sharpe_ratio"],
            json.dumps(metrics_blob),
            oos["qscore"],
            oos["decision"],
            oos.get("qscore", 0.0),
            -(oos["max_drawdown_pct"] / 100.0),
            oos["grade"],
            oos["flags"],
            json.dumps(score_details),
            json.dumps(True),
            "complete",
            ins["qscore"],
            oos["qscore"],
            wf_result["degradation_pct"],
            wf_result["folds"],
            json.dumps(wf_result["walk_forward_config"]),
            json.dumps(wf_result["fold_results"]),
            strategy_family,
            parent_id,
            mutation_type,
            stage,
            validation_target,
            int(family_generation or 1),
            0,
            json.dumps(wf_result.get("regime_scores") or {}),
            float(wf_result.get("regime_concentration") or 0.0),
            wf_result.get("primary_regime") or "UNKNOWN",
            0.0,
            None,
            int(refinement_round or 0),
            None,
            int(fallback_source or 0),
        ),
    )
    conn.commit()
    return result_id


def main():
    ap = argparse.ArgumentParser(description="Walk-Forward Analysis Engine for AutoQuant")
    ap.add_argument("--asset", required=True, help="Asset symbol (ETH, BTC, SOL, etc.)")
    ap.add_argument("--tf", required=True, help="Timeframe (1m, 5m, 15m, 1h, 4h, 1d)")
    ap.add_argument("--strategy-spec", required=True, help="Path to strategy spec JSON")
    ap.add_argument("--variant", default="default", help="Variant name from spec")
    ap.add_argument("--dry-run", action="store_true", help="Print config without running")
    ap.add_argument("--no-db", action="store_true", help="Skip database write")
    ap.add_argument("--stage", default="full", choices=["full", "screen"], help="Backtest stage")
    ap.add_argument("--strategy-family", default="", help="Strategy family name")
    ap.add_argument("--parent-id", default="", help="Parent backtest result id")
    ap.add_argument("--mutation-type", default="", help="Mutation type label")
    ap.add_argument("--validation-target", default="", help="Validation target asset/timeframe")
    ap.add_argument("--family-generation", type=int, default=1, help="Family generation counter")
    ap.add_argument("--refinement-round", type=int, default=0, help="Refinement round counter")
    args = ap.parse_args()

    if args.tf not in WINDOW_CONFIG:
        print(json.dumps({"status": "error", "error": f"Unsupported timeframe: {args.tf}. Supported: {list(WINDOW_CONFIG.keys())}"}))
        return 1

    try:
        strategy = parse_strategy_spec(args.strategy_spec, args.variant)
    except Exception as e:
        print(json.dumps({"status": "error", "error": f"Failed to load strategy spec: {e}"}))
        return 1

    spec_id = os.path.basename(args.strategy_spec).replace(".strategy_spec.json", "").replace(".json", "")
    fallback_source = 1 if str((strategy.get("spec") or {}).get("source") or "").strip().lower() == "fallback_cooker" or bool((strategy.get("spec") or {}).get("fallback_source")) else 0

    if args.dry_run:
        train_days, blind_days = WINDOW_CONFIG[args.tf]
        print(json.dumps({
            "status": "dry_run",
            "asset": args.asset,
            "timeframe": args.tf,
            "strategy": strategy["strategy_name"],
            "variant": args.variant,
            "stage": args.stage,
            "train_days": train_days,
            "blind_days": blind_days,
            "spec_id": spec_id,
        }, indent=2))
        return 0

    try:
        candles = load_candles(args.asset, args.tf)
    except (FileNotFoundError, ValueError) as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1

    result = run_walk_forward(candles, strategy, args.tf, asset=args.asset, stage=args.stage)
    if result["status"] != "ok":
        print(json.dumps(result, indent=2))
        return 1

    if not args.no_db:
        try:
            conn = sqlite3.connect(DB_PATH)
            save_outcome = save_result(
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
