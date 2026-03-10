#!/usr/bin/env python3
"""Bootstrap and maintain shared intelligence memory buckets."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
SHARED_ROOT = ROOT / "memory" / "shared"
INDEX_PATH = SHARED_ROOT / "INDEX.json"
BUCKETS = [
    "lessons",
    "decisions",
    "known_fixes",
    "regimes",
    "strategy_families",
    "postmortems",
    "handoffs"
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-") or "entry"


def load_index():
    if not INDEX_PATH.exists():
        return {"version": "shared-memory-index-v1", "generated_at": now_iso(), "entries": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def save_index(index_data):
    SHARED_ROOT.mkdir(parents=True, exist_ok=True)
    index_data["generated_at"] = now_iso()
    index_data["entries"] = sorted(
        index_data.get("entries", []),
        key=lambda entry: (entry.get("bucket", ""), entry.get("ts_iso", ""), entry.get("id", "")),
        reverse=True
    )
    INDEX_PATH.write_text(json.dumps(index_data, indent=2), encoding="utf-8")
    return index_data


def ensure_structure():
    SHARED_ROOT.mkdir(parents=True, exist_ok=True)
    for bucket in BUCKETS:
        (SHARED_ROOT / bucket).mkdir(parents=True, exist_ok=True)
    save_index(load_index())


def make_entry_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid4().hex[:4].upper()
    return "MEM-{0}-{1}".format(stamp, suffix)


def write_markdown(bucket, title, body):
    date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
    filename = "{0}-{1}.md".format(date_part, slugify(title))
    path = SHARED_ROOT / bucket / filename
    counter = 2
    while path.exists():
        path = SHARED_ROOT / bucket / "{0}-{1}-{2}.md".format(date_part, slugify(title), counter)
        counter += 1
    path.write_text(body, encoding="utf-8")
    return path


def frontmatter_block(meta):
    lines = ["---"]
    for key, value in meta.items():
        if isinstance(value, list):
            lines.append("{0}: [{1}]".format(key, ", ".join(json.dumps(v) for v in value)))
        else:
            lines.append("{0}: {1}".format(key, json.dumps(value)))
    lines.append("---")
    return "\n".join(lines)


def add_index_entry(index_data, entry_id, bucket, title, path, actor, source, tags, confidence, summary):
    index_data.setdefault("entries", []).append({
        "id": entry_id,
        "bucket": bucket,
        "title": title,
        "path": str(path.relative_to(ROOT)),
        "actor": actor,
        "source": source,
        "tags": tags,
        "confidence": confidence,
        "summary": summary,
        "ts_iso": now_iso()
    })
    return index_data


def cmd_bootstrap(_args):
    ensure_structure()
    readme = SHARED_ROOT / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Shared Intelligence Memory\n\n"
            "This directory holds promoted long-term memory for AutoQuant.\n\n"
            "Buckets:\n"
            "- lessons\n"
            "- decisions\n"
            "- known_fixes\n"
            "- regimes\n"
            "- strategy_families\n"
            "- postmortems\n"
            "- handoffs\n",
            encoding="utf-8"
        )
    print(json.dumps({"status": "ok", "shared_root": str(SHARED_ROOT), "bucket_count": len(BUCKETS)}, indent=2))


def cmd_promote_note(args):
    ensure_structure()
    entry_id = make_entry_id()
    meta = {
        "id": entry_id,
        "bucket": args.bucket,
        "title": args.title,
        "actor": args.actor,
        "source": args.source,
        "confidence": args.confidence,
        "tags": args.tag,
        "ts_iso": now_iso()
    }
    body = "\n\n".join([
        frontmatter_block(meta),
        "# {0}".format(args.title),
        "## Summary\n{0}".format(args.summary),
        "## Details\n{0}".format(args.details or "No extra details provided."),
        "## Source\n{0}".format(args.source)
    ])
    path = write_markdown(args.bucket, args.title, body)
    index_data = load_index()
    add_index_entry(index_data, entry_id, args.bucket, args.title, path, args.actor, args.source, args.tag, args.confidence, args.summary)
    save_index(index_data)
    print(json.dumps({"status": "ok", "entry_id": entry_id, "path": str(path)}, indent=2))


def cmd_promote_known_fix(args):
    ensure_structure()
    entry_id = make_entry_id()
    title = args.title or args.symptom
    meta = {
        "id": entry_id,
        "bucket": "known_fixes",
        "title": title,
        "actor": args.actor,
        "source": args.source,
        "confidence": args.confidence,
        "tags": args.tag,
        "ts_iso": now_iso()
    }
    summary = "Symptom: {0} | Fix: {1}".format(args.symptom, args.fix)
    body = "\n\n".join([
        frontmatter_block(meta),
        "# {0}".format(title),
        "## Symptom\n{0}".format(args.symptom),
        "## Root Cause\n{0}".format(args.root_cause),
        "## Fix\n{0}".format(args.fix),
        "## Prevention\n{0}".format(args.prevention),
        "## Source\n{0}".format(args.source)
    ])
    path = write_markdown("known_fixes", title, body)
    index_data = load_index()
    add_index_entry(index_data, entry_id, "known_fixes", title, path, args.actor, args.source, args.tag, args.confidence, summary)
    save_index(index_data)
    print(json.dumps({"status": "ok", "entry_id": entry_id, "path": str(path)}, indent=2))


def cmd_list(args):
    index_data = load_index()
    entries = index_data.get("entries", [])
    if args.bucket:
        entries = [entry for entry in entries if entry.get("bucket") == args.bucket]
    print(json.dumps({"count": len(entries), "entries": entries[: args.limit]}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Memory governor for AutoQuant shared intelligence")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bootstrap")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("promote-note")
    p.add_argument("--bucket", required=True, choices=BUCKETS)
    p.add_argument("--title", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--details")
    p.add_argument("--actor", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--confidence", default="medium", choices=["low", "medium", "high"])
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(func=cmd_promote_note)

    p = sub.add_parser("promote-known-fix")
    p.add_argument("--title")
    p.add_argument("--symptom", required=True)
    p.add_argument("--root-cause", dest="root_cause", required=True)
    p.add_argument("--fix", required=True)
    p.add_argument("--prevention", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--source", required=True)
    p.add_argument("--confidence", default="high", choices=["low", "medium", "high"])
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(func=cmd_promote_known_fix)

    p = sub.add_parser("list")
    p.add_argument("--bucket", choices=BUCKETS)
    p.add_argument("--limit", type=int, default=20)
    p.set_defaults(func=cmd_list)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
