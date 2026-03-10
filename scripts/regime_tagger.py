#!/usr/bin/env python3
import argparse
import csv
import json
import os
from datetime import datetime, timezone

ROOT = os.environ.get(
    "AUTOQUANT_ROOT",
    r"C:\Users\Clamps\.openclaw\workspace-oragorn",
)
CANDLES_DIR = os.path.join(ROOT, "data", "candles")
CACHE_DIR = os.path.join(ROOT, "data", "regime_cache")


def sma(values, period):
    out = [None] * len(values)
    if period <= 0:
        return out
    for i in range(period - 1, len(values)):
        window = [v for v in values[i - period + 1 : i + 1] if v is not None]
        if len(window) == period:
            out[i] = sum(window) / period
    return out


def ema(values, period):
    out = [None] * len(values)
    if not values:
        return out
    k = 2.0 / (period + 1)
    prev = None
    for i, value in enumerate(values):
        if value is None:
            out[i] = prev
            continue
        if prev is None:
            prev = float(value)
        else:
            prev = float(value) * k + prev * (1 - k)
        out[i] = prev
    return out


def atr(candles, period=14):
    trs = []
    out = [None] * len(candles)
    for i, candle in enumerate(candles):
        if i == 0:
            tr = candle["high"] - candle["low"]
        else:
            prev_close = candles[i - 1]["close"]
            tr = max(
                candle["high"] - candle["low"],
                abs(candle["high"] - prev_close),
                abs(candle["low"] - prev_close),
            )
        trs.append(tr)
    if len(trs) >= period:
        out[period - 1] = sum(trs[:period]) / period
        for i in range(period, len(trs)):
            out[i] = ((out[i - 1] * (period - 1)) + trs[i]) / period
    return out


def adx(candles, period=14):
    n = len(candles)
    if n == 0:
        return []
    tr = [0.0] * n
    dm_plus = [0.0] * n
    dm_minus = [0.0] * n
    for i in range(1, n):
        up_move = candles[i]["high"] - candles[i - 1]["high"]
        down_move = candles[i - 1]["low"] - candles[i]["low"]
        dm_plus[i] = up_move if up_move > down_move and up_move > 0 else 0.0
        dm_minus[i] = down_move if down_move > up_move and down_move > 0 else 0.0
        tr[i] = max(
            candles[i]["high"] - candles[i]["low"],
            abs(candles[i]["high"] - candles[i - 1]["close"]),
            abs(candles[i]["low"] - candles[i - 1]["close"]),
        )

    atr_smooth = [None] * n
    plus_smooth = [None] * n
    minus_smooth = [None] * n
    dx = [None] * n
    out = [None] * n
    if n <= period:
        return out

    atr_smooth[period] = sum(tr[1 : period + 1])
    plus_smooth[period] = sum(dm_plus[1 : period + 1])
    minus_smooth[period] = sum(dm_minus[1 : period + 1])

    for i in range(period, n):
        if i > period:
            atr_smooth[i] = atr_smooth[i - 1] - (atr_smooth[i - 1] / period) + tr[i]
            plus_smooth[i] = plus_smooth[i - 1] - (plus_smooth[i - 1] / period) + dm_plus[i]
            minus_smooth[i] = minus_smooth[i - 1] - (minus_smooth[i - 1] / period) + dm_minus[i]
        if not atr_smooth[i]:
            continue
        plus_di = 100.0 * (plus_smooth[i] / atr_smooth[i]) if atr_smooth[i] else 0.0
        minus_di = 100.0 * (minus_smooth[i] / atr_smooth[i]) if atr_smooth[i] else 0.0
        denom = plus_di + minus_di
        dx[i] = 100.0 * abs(plus_di - minus_di) / denom if denom else 0.0

    first_adx_idx = (period * 2) - 1
    if first_adx_idx < n:
        seed = [v for v in dx[period:first_adx_idx + 1] if v is not None]
        if len(seed) == period:
            out[first_adx_idx] = sum(seed) / period
            for i in range(first_adx_idx + 1, n):
                if dx[i] is None:
                    continue
                out[i] = ((out[i - 1] * (period - 1)) + dx[i]) / period
    return out


def load_candles(asset, timeframe, csv_path=None):
    path = csv_path or os.path.join(CANDLES_DIR, f"{asset}_{timeframe}.csv")
    if not os.path.exists(path):
        for alt in [f"{asset.upper()}_{timeframe}.csv", f"{asset.lower()}_{timeframe}.csv", f"{asset}-{timeframe}.csv"]:
            alt_path = os.path.join(CANDLES_DIR, alt)
            if os.path.exists(alt_path):
                path = alt_path
                break
    if not os.path.exists(path):
        raise FileNotFoundError(f"Candle data not found for {asset}/{timeframe}")
    candles = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                row_dict = dict(row) if not isinstance(row, dict) else row
                candles.append(
                    {
                        "ts": row_dict.get("timestamp") or row_dict.get("ts") or row_dict.get("date") or row_dict.get("time"),
                        "open": float(row["open"]),
                        "high": float(row["high"]),
                        "low": float(row["low"]),
                        "close": float(row["close"]),
                        "volume": float(row_dict.get("volume", 0) or 0),
                    }
                )
            except Exception:
                continue
    if not candles:
        raise ValueError("No valid candles loaded")
    return candles


def cache_path(asset, timeframe):
    os.makedirs(CACHE_DIR, exist_ok=True)
    return os.path.join(CACHE_DIR, f"{asset.lower()}_{timeframe}.json")


def classify_regimes(candles):
    closes = [c["close"] for c in candles]
    ema20 = ema(closes, 20)
    ema50 = ema(closes, 50)
    adx14 = adx(candles, 14)
    atr14 = atr(candles, 14)
    atr_sma20 = sma(atr14, 20)
    tags = []
    for i in range(len(candles)):
        current_adx = adx14[i]
        prev_adx = adx14[i - 1] if i > 0 else None
        e20 = ema20[i]
        e50 = ema50[i]
        prev_e20 = ema20[i - 1] if i > 0 else None
        prev_e50 = ema50[i - 1] if i > 0 else None
        atr_value = atr14[i]
        atr_avg = atr_sma20[i]

        regime = "TRANSITION"
        reason = "default_transition"
        if atr_value is not None and atr_avg is not None and atr_avg > 0:
            if atr_value > (1.5 * atr_avg):
                regime = "EXPANSION"
                reason = "atr_expansion"
            elif atr_value < (0.7 * atr_avg):
                regime = "COMPRESSION"
                reason = "atr_compression"

        ema_cross = False
        if None not in (e20, e50, prev_e20, prev_e50):
            ema_cross = ((prev_e20 <= prev_e50 and e20 > e50) or (prev_e20 >= prev_e50 and e20 < e50))
        adx_transition = current_adx is not None and (20 <= current_adx <= 25 or (prev_adx is not None and ((prev_adx < 20 <= current_adx) or (prev_adx > 25 >= current_adx))))

        if current_adx is not None and current_adx < 20:
            regime = "CHOP"
            reason = "adx_below_20"
        elif adx_transition or ema_cross:
            regime = "TRANSITION"
            reason = "adx_transition_or_ema_cross"
        elif current_adx is not None and current_adx > 25 and None not in (e20, e50, prev_e20, prev_e50):
            if e20 > e50 and e20 >= prev_e20 and e50 >= prev_e50:
                regime = "TREND_UP"
                reason = "adx_strong_ema_rising"
            elif e20 < e50 and e20 <= prev_e20 and e50 <= prev_e50:
                regime = "TREND_DOWN"
                reason = "adx_strong_ema_falling"

        tags.append(
            {
                "index": i,
                "ts": candles[i].get("ts"),
                "regime": regime,
                "adx14": round(current_adx, 4) if current_adx is not None else None,
                "ema20": round(e20, 6) if e20 is not None else None,
                "ema50": round(e50, 6) if e50 is not None else None,
                "atr14": round(atr_value, 6) if atr_value is not None else None,
                "atr_sma20": round(atr_avg, 6) if atr_avg is not None else None,
                "reason": reason,
            }
        )
    return tags


def get_regime_tags(asset, timeframe, candles=None, force=False):
    candles = candles or load_candles(asset, timeframe)
    path = cache_path(asset, timeframe)
    signature = {
        "asset": asset,
        "timeframe": timeframe,
        "candle_count": len(candles),
        "first_ts": candles[0].get("ts") if candles else None,
        "last_ts": candles[-1].get("ts") if candles else None,
    }
    if (not force) and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                cached = json.load(handle)
            if cached.get("signature") == signature:
                return cached
        except Exception:
            pass
    tags = classify_regimes(candles)
    payload = {
        "asset": asset,
        "timeframe": timeframe,
        "signature": signature,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "tag_count": len(tags),
        "tags": tags,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    return payload


def main():
    ap = argparse.ArgumentParser(description="Tag OHLCV candles with cached market regimes")
    ap.add_argument("--asset", required=True)
    ap.add_argument("--tf", required=True)
    ap.add_argument("--csv", default=None)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--preview", type=int, default=5)
    args = ap.parse_args()

    candles = load_candles(args.asset, args.tf, args.csv)
    payload = get_regime_tags(args.asset, args.tf, candles=candles, force=args.force)
    preview = payload["tags"][: max(0, args.preview)]
    counts = {}
    for row in payload["tags"]:
        counts[row["regime"]] = counts.get(row["regime"], 0) + 1
    print(json.dumps({
        "status": "ok",
        "asset": args.asset,
        "timeframe": args.tf,
        "cache_path": cache_path(args.asset, args.tf),
        "tag_count": payload["tag_count"],
        "counts": counts,
        "preview": preview,
    }, indent=2))


if __name__ == "__main__":
    main()
