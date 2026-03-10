#!/usr/bin/env python3
"""Bootstrap normalized external intelligence storage and registry index."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SOURCES_PATH = ROOT / "config" / "external-intel-sources.json"
RAW_DIR = ROOT / "data" / "external_intel" / "raw"
NORMALIZED_DIR = ROOT / "data" / "external_intel" / "normalized"
INDEX_PATH = ROOT / "data" / "external_intel" / "index.json"
STATE_PATH = ROOT / "data" / "state" / "external_intel_state.json"


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def make_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return "EXT-{0}-{1}".format(stamp, uuid4().hex[:4].upper())


def load_sources():
    return json.loads(SOURCES_PATH.read_text(encoding="utf-8"))


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)


def bootstrap_index(sources):
    if INDEX_PATH.exists():
        return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    data = {
        "version": "external-intel-index-v1",
        "generated_at": now_iso(),
        "sources": sources.get("sources", []),
        "items": []
    }
    INDEX_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def bootstrap_state(sources):
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state = {
        "version": "external-intel-state-v1",
        "updated_at": now_iso(),
        "enabled_sources": [s["id"] for s in sources.get("sources", []) if s.get("enabled")],
        "last_ingested_at": {},
        "status": "bootstrapped"
    }
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return state


def ingest_stub(source_id, summary, category, asset_scope, importance, tags):
    index = json.loads(INDEX_PATH.read_text(encoding="utf-8"))
    item_id = make_id()
    date_key = datetime.now(timezone.utc).strftime("%Y%m%d")
    raw_path = RAW_DIR / date_key
    norm_path = NORMALIZED_DIR / date_key
    raw_path.mkdir(parents=True, exist_ok=True)
    norm_path.mkdir(parents=True, exist_ok=True)

    raw_file = raw_path / (item_id + ".raw.json")
    normalized_file = norm_path / (item_id + ".external_intel_item.json")

    raw_payload = {
        "source_id": source_id,
        "captured_at": now_iso(),
        "summary": summary,
        "raw": {"stub": True}
    }
    normalized_payload = {
        "version": "external-intel-item-v1",
        "id": item_id,
        "ts_iso": now_iso(),
        "source_id": source_id,
        "category": category,
        "asset_scope": asset_scope,
        "importance": importance,
        "summary": summary,
        "market_implication": None,
        "promotion_candidate": False,
        "raw_path": str(raw_file.relative_to(ROOT)),
        "normalized_path": str(normalized_file.relative_to(ROOT)),
        "tags": tags,
        "status": "ingested"
    }
    raw_file.write_text(json.dumps(raw_payload, indent=2), encoding="utf-8")
    normalized_file.write_text(json.dumps(normalized_payload, indent=2), encoding="utf-8")

    index.setdefault("items", []).append({
        "id": item_id,
        "source_id": source_id,
        "category": category,
        "summary": summary,
        "importance": importance,
        "asset_scope": asset_scope,
        "normalized_path": str(normalized_file.relative_to(ROOT)),
        "ts_iso": normalized_payload["ts_iso"]
    })
    index["generated_at"] = now_iso()
    INDEX_PATH.write_text(json.dumps(index, indent=2), encoding="utf-8")

    state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    state.setdefault("last_ingested_at", {})[source_id] = normalized_payload["ts_iso"]
    state["updated_at"] = now_iso()
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

    return normalized_payload


def main():
    parser = argparse.ArgumentParser(description="External intelligence registry bootstrap")
    parser.add_argument("--ingest-stub", action="store_true")
    parser.add_argument("--source-id")
    parser.add_argument("--summary")
    parser.add_argument("--category")
    parser.add_argument("--asset", action="append", default=[])
    parser.add_argument("--importance", default="medium")
    parser.add_argument("--tag", action="append", default=[])
    args = parser.parse_args()

    ensure_dirs()
    sources = load_sources()
    bootstrap_index(sources)
    bootstrap_state(sources)

    if args.ingest_stub:
        if not args.source_id or not args.summary or not args.category:
            raise SystemExit("--source-id, --summary, and --category are required with --ingest-stub")
        result = ingest_stub(args.source_id, args.summary, args.category, args.asset, args.importance, args.tag)
        print(json.dumps({"status": "ok", "item": result}, indent=2))
        return

    print(json.dumps({
        "status": "ok",
        "index_path": str(INDEX_PATH),
        "state_path": str(STATE_PATH),
        "source_count": len(sources.get("sources", []))
    }, indent=2))


if __name__ == "__main__":
    main()
