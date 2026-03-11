#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
MANIFEST = ROOT / "data" / "state" / "current_cycle_specs.json"
CANDLES_DIR = ROOT / "data" / "candles"
MARKET_SKILL = ROOT.parent / "skills" / "autoquant-market-data" / "market.py"

DEFAULT_DAYS = {
    "15m": 14,
    "1h": 45,
    "4h": 180,
    "1d": 365,
}
FRESHNESS_HOURS = {
    "15m": 6,
    "1h": 12,
    "4h": 24,
    "1d": 72,
}


def load_json(path: Path, default=None):
    if default is None:
        default = {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def normalize_asset_filename(asset: str) -> str:
    return str(asset or "").replace(":", "_").replace("/", "_").upper()


def lane_csv_path(asset: str, timeframe: str) -> Path:
    return CANDLES_DIR / f"{normalize_asset_filename(asset)}_{timeframe}.csv"


def lane_is_fresh(path: Path, timeframe: str) -> bool:
    if not path.exists():
        return False
    max_age_hours = FRESHNESS_HOURS.get(str(timeframe), 24)
    age_hours = (time.time() - path.stat().st_mtime) / 3600.0
    return age_hours <= max_age_hours


def extract_requested_lanes(manifest: dict) -> list[tuple[str, str]]:
    lanes = []
    seen = set()
    for raw_path in manifest.get("spec_paths") or []:
        try:
            payload = json.loads(Path(raw_path).read_text(encoding="utf-8"))
        except Exception:
            continue
        asset = str(payload.get("asset") or payload.get("primary_asset") or "").strip().upper()
        timeframe = str(payload.get("timeframe") or payload.get("primary_timeframe") or "").strip()
        if not asset or not timeframe:
            continue
        key = (asset, timeframe)
        if key in seen:
            continue
        seen.add(key)
        lanes.append(key)
    return lanes


def fetch_lane(asset: str, timeframe: str) -> dict:
    days = int(DEFAULT_DAYS.get(timeframe, 60))
    cmd = [sys.executable, str(MARKET_SKILL), "--candles", "--asset", asset, "--tf", timeframe, "--days", str(days)]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    stdout = (proc.stdout or "").strip()
    stderr = (proc.stderr or "").strip()
    payload = {}
    if stdout:
        try:
            payload = json.loads(stdout)
        except Exception:
            payload = {"ok": False, "error": stdout}
    return {
        "returncode": proc.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "payload": payload,
    }


def main() -> int:
    manifest = load_json(MANIFEST, default={})
    lanes = extract_requested_lanes(manifest)
    if not lanes:
        print(json.dumps({"status": "idle", "reason": "no_requested_lanes", "ts_iso": datetime.now(timezone.utc).isoformat()}))
        return 0

    results = []
    CANDLES_DIR.mkdir(parents=True, exist_ok=True)
    for asset, timeframe in lanes:
        path = lane_csv_path(asset, timeframe)
        if lane_is_fresh(path, timeframe):
            results.append({"asset": asset, "timeframe": timeframe, "status": "ready", "csv_path": str(path)})
            continue
        fetched = fetch_lane(asset, timeframe)
        payload = fetched.get("payload") or {}
        ok = bool(payload.get("ok")) and lane_csv_path(asset, timeframe).exists()
        results.append({
            "asset": asset,
            "timeframe": timeframe,
            "status": "fetched" if ok else "error",
            "csv_path": str(lane_csv_path(asset, timeframe)),
            "details": payload if payload else {"returncode": fetched.get("returncode"), "stderr": fetched.get("stderr")},
        })
        if not ok:
            print(json.dumps({"status": "error", "lanes": results, "ts_iso": datetime.now(timezone.utc).isoformat()}, indent=2))
            return 1

    print(json.dumps({"status": "ready", "lanes": results, "ts_iso": datetime.now(timezone.utc).isoformat()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
