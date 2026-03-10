#!/usr/bin/env python3
"""Score normalized external intelligence for promotion relevance."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_PATH = ROOT / "data" / "external_intel" / "index.json"
RULES_PATH = ROOT / "config" / "external-intel-relevance.json"
OUT_PATH = ROOT / "data" / "state" / "external_intel_relevance.json"


def load(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return default


def score_item(item, rules):
    weights = rules.get("score_weights", {})
    text = (str(item.get("summary", "")) + " " + " ".join(item.get("asset_scope", []))).lower()
    score = 0
    if item.get("asset_scope"):
        score += int(weights.get("asset_match", 0))
    if item.get("category") in {"market_microstructure", "market_context", "structural_regime_inputs", "research_media"}:
        score += int(weights.get("category_match", 0))
    if any(k in text for k in rules.get("rules", {}).get("regime_keywords", [])):
        score += int(weights.get("regime_relevance", 0))
    if any(k in text for k in rules.get("rules", {}).get("family_keywords", [])):
        score += int(weights.get("strategy_family_relevance", 0))
    if any(k in text for k in rules.get("rules", {}).get("actionable_keywords", [])):
        score += int(weights.get("actionability", 0))
    if any(k in text for k in rules.get("rules", {}).get("drop_keywords", [])):
        score -= 5
    score += int(weights.get("freshness", 0))
    return score


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    index_data = load(INDEX_PATH, {"items": []})
    rules = load(RULES_PATH, {})
    thresholds = rules.get("promotion_thresholds", {})
    scored = []
    for item in list(reversed(index_data.get("items", [])))[: args.limit]:
        score = score_item(item, rules)
        if score >= int(thresholds.get("shared_memory", 8)):
            disposition = "shared_memory"
        elif score >= int(thresholds.get("handoff_only", 5)):
            disposition = "handoff_only"
        else:
            disposition = "archive_only"
        scored.append({
            "id": item.get("id"),
            "source_id": item.get("source_id"),
            "summary": item.get("summary"),
            "score": score,
            "disposition": disposition,
            "ts_iso": item.get("ts_iso") or datetime.now(timezone.utc).isoformat(),
        })
    payload = {
        "version": "external-intel-relevance-v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "items": scored,
    }
    OUT_PATH.write_text(json.dumps(payload, indent=2), encoding='utf-8')
    print(json.dumps(payload, indent=2))


if __name__ == '__main__':
    main()
