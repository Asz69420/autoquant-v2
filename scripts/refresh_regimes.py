#!/usr/bin/env python3
"""Refresh regime tags for all available candle data. Runs before briefing."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("AUTOQUANT_ROOT", r"C:\Users\Clamps\.openclaw\workspace-oragorn"))
sys.path.insert(0, str(ROOT / "scripts"))

from regime_tagger import get_regime_tags, load_candles, CANDLES_DIR, CACHE_DIR

SUMMARY_PATH = ROOT / "data" / "state" / "regime_summary.json"


def current_regime_label(tags: list) -> dict:
    """Extract the current (latest) regime and a short distribution summary."""
    if not tags:
        return {"current": "UNKNOWN", "confidence": 0.0, "distribution": {}}
    last_tag = tags[-1]
    # Distribution over last 20 bars
    window = tags[-20:] if len(tags) >= 20 else tags
    counts = {}
    for t in window:
        r = t.get("regime", "UNKNOWN")
        counts[r] = counts.get(r, 0) + 1
    total = len(window)
    dist = {k: round(v / total * 100, 1) for k, v in sorted(counts.items(), key=lambda x: -x[1])}
    current = last_tag.get("regime", "UNKNOWN")
    confidence = dist.get(current, 0.0)
    return {
        "current": current,
        "confidence": confidence,
        "adx14": last_tag.get("adx14"),
        "atr14": last_tag.get("atr14"),
        "distribution_20bar": dist,
    }


def main():
    candle_dir = Path(CANDLES_DIR)
    if not candle_dir.exists():
        print(json.dumps({"status": "error", "reason": "candles dir not found"}))
        return

    results = {}
    errors = []
    for f in sorted(candle_dir.glob("*.csv")):
        stem = f.stem
        parts = stem.rsplit("_", 1)
        if len(parts) != 2:
            continue
        asset, tf = parts[0].upper(), parts[1]
        try:
            candles = load_candles(asset, tf, str(f))
            payload = get_regime_tags(asset, tf, candles=candles, force=True)
            label = current_regime_label(payload.get("tags", []))
            results[f"{asset}/{tf}"] = label
        except Exception as e:
            errors.append({"pair": f"{asset}/{tf}", "error": str(e)})

    summary = {
        "generated_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
        "pairs": results,
        "errors": errors,
        "count": len(results),
    }
    SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "tagged": len(results), "errors": len(errors)}))


if __name__ == "__main__":
    main()
