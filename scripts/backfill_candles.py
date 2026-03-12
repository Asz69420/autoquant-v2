#!/usr/bin/env python3
import argparse
import csv
import os
import time
from datetime import datetime, timezone

import requests

ROOT = os.environ.get("AUTOQUANT_ROOT", r"C:\Users\Clamps\.openclaw\workspace-oragorn")
CANDLES_DIR = os.path.join(ROOT, "data", "candles")
API_URL = "https://api.hyperliquid.xyz/info"
MS = {"1h": 3600_000, "4h": 4 * 3600_000, "1d": 24 * 3600_000}
TARGET_ROWS = {"1h": 3200, "4h": 1500, "1d": 800}
BATCH_LIMIT = 500


def read_rows(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["timestamp", "open", "high", "low", "close", "volume"])
        w.writeheader()
        w.writerows(rows)


def fetch_batch(asset, timeframe, start_ms, end_ms):
    payload = {
        "type": "candleSnapshot",
        "req": {
            "coin": asset,
            "interval": timeframe,
            "startTime": int(start_ms),
            "endTime": int(end_ms),
        },
    }
    r = requests.post(API_URL, json=payload, timeout=30)
    r.raise_for_status()
    data = r.json()
    out = []
    for item in data or []:
        out.append({
            "timestamp": str(item.get("t")),
            "open": str(item.get("o")),
            "high": str(item.get("h")),
            "low": str(item.get("l")),
            "close": str(item.get("c")),
            "volume": str(item.get("v")),
        })
    return out


def backfill(asset, timeframe):
    path = os.path.join(CANDLES_DIR, f"{asset}_{timeframe}.csv")
    rows = read_rows(path)
    if not rows:
        raise SystemExit(f"missing candle file: {path}")
    target = TARGET_ROWS.get(timeframe, len(rows))
    step = MS[timeframe]
    seen = {r["timestamp"] for r in rows}
    oldest = int(rows[0]["timestamp"])
    added = 0
    while len(rows) < target:
        end_ms = oldest
        start_ms = max(0, end_ms - (BATCH_LIMIT * step))
        batch = fetch_batch(asset, timeframe, start_ms, end_ms)
        if not batch:
            break
        new_rows = [r for r in batch if r["timestamp"] not in seen]
        if not new_rows:
            break
        for r in new_rows:
            seen.add(r["timestamp"])
        rows = sorted(new_rows + rows, key=lambda r: int(r["timestamp"]))
        oldest = int(rows[0]["timestamp"])
        added += len(new_rows)
        time.sleep(0.2)
    write_rows(path, rows)
    return {"asset": asset, "timeframe": timeframe, "rows": len(rows), "added": added, "oldest": rows[0]["timestamp"], "newest": rows[-1]["timestamp"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", nargs="+", required=True)
    ap.add_argument("--timeframes", nargs="+", required=True)
    args = ap.parse_args()
    for asset in args.assets:
        for tf in args.timeframes:
            print(backfill(asset, tf))


if __name__ == "__main__":
    main()
