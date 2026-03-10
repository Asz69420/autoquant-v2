#!/usr/bin/env python3
"""Promote agent decisions and known-fix style memory into shared intelligence."""
import argparse
import re
from pathlib import Path

from memory_governor import ensure_structure
from subprocess import run
import sys

ROOT = Path(__file__).resolve().parent.parent
MEMORY_GOVERNOR = ROOT / "scripts" / "memory_governor.py"

AGENT_SOURCES = {
    "frodex": ROOT / "agents" / "frodex" / "memory" / "decisions.md",
    "logron": ROOT / "agents" / "logron" / "memory" / "decisions.md",
}

AGENT_EXTRA_SOURCES = {
    "frodex": [
        ROOT / "agents" / "frodex" / "memory" / "goals.md",
        ROOT / "agents" / "frodex" / "memory" / "current_status.md",
    ],
    "logron": [
        ROOT / "agents" / "logron" / "memory" / "goals.md",
        ROOT / "agents" / "logron" / "memory" / "current_status.md",
    ],
}


def parse_table(md_text):
    rows = []
    for line in md_text.splitlines():
        if not line.strip().startswith("|"):
            continue
        if "---" in line:
            continue
        parts = [p.strip() for p in line.strip().strip("|").split("|")]
        if len(parts) == 4 and parts[0] != "Date":
            rows.append({
                "date": parts[0],
                "decision": parts[1],
                "rationale": parts[2],
                "status": parts[3],
            })
    return rows


def slug_title(agent, decision):
    text = re.sub(r"[-_]+", " ", decision).strip()
    return f"{agent.capitalize()} Decision: {text}"


def promote_decision(agent, row, dry_run=False):
    title = slug_title(agent, row['decision'])
    summary = f"{agent.capitalize()} decision '{row['decision']}' remains {row['status'].lower()} because {row['rationale']}."
    details = f"Promoted from {agent} decisions log. Date: {row['date']}. Status: {row['status']}. Rationale: {row['rationale']}."
    if dry_run:
        return title
    cmd = [
        sys.executable,
        str(MEMORY_GOVERNOR),
        "promote-note",
        "--bucket", "decisions",
        "--title", title,
        "--summary", summary,
        "--details", details,
        "--actor", agent,
        "--source", str(AGENT_SOURCES[agent].relative_to(ROOT)),
        "--confidence", "high",
        "--tag", agent,
        "--tag", "decision",
    ]
    run(cmd, check=False, capture_output=True, text=True)
    return title


def maybe_promote_known_fix(agent, row, dry_run=False):
    if agent != "logron":
        return None
    decision = row["decision"].lower()
    if "self-healing" not in decision:
        return None
    title = "Logron Known Fix Policy: Level 1 Self-Healing"
    if dry_run:
        return title
    cmd = [
        sys.executable,
        str(MEMORY_GOVERNOR),
        "promote-known-fix",
        "--title", title,
        "--symptom", "Recurring operational issues detectable from logs and thresholds.",
        "--root-cause", "Known recurring failure patterns were not being codified into a reusable auto-resolution layer.",
        "--fix", "Match recurring errors to known_fixes and auto-resolve at Logron level 1 before escalating.",
        "--prevention", "Keep known_fixes updated whenever a new repeatable issue is solved.",
        "--actor", agent,
        "--source", str(AGENT_SOURCES[agent].relative_to(ROOT)),
        "--confidence", "high",
        "--tag", agent,
        "--tag", "known-fix",
        "--tag", "self-healing",
    ]
    run(cmd, check=False, capture_output=True, text=True)
    return title


def promote_extra_sources(agent, dry_run=False):
    promoted = []
    for src in AGENT_EXTRA_SOURCES.get(agent, []):
        if not src.exists():
            continue
        text = src.read_text(encoding="utf-8-sig").strip()
        if not text:
            continue
        title = f"{agent.capitalize()} Handoff: {src.stem.replace('_', ' ').title()}"
        summary = text.splitlines()[0][:220]
        if dry_run:
            promoted.append(title)
            continue
        cmd = [
            sys.executable,
            str(MEMORY_GOVERNOR),
            "promote-note",
            "--bucket", "handoffs",
            "--title", title,
            "--summary", summary,
            "--details", text,
            "--actor", agent,
            "--source", str(src.relative_to(ROOT)),
            "--confidence", "medium",
            "--tag", agent,
            "--tag", "handoff",
        ]
        run(cmd, check=False, capture_output=True, text=True)
        promoted.append(title)
    return promoted


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["frodex", "logron", "all"], default="all")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_structure()
    agents = ["frodex", "logron"] if args.agent == "all" else [args.agent]
    promoted = []
    for agent in agents:
        src = AGENT_SOURCES[agent]
        if src.exists():
            rows = parse_table(src.read_text(encoding="utf-8-sig"))
            for row in rows:
                promoted.append(promote_decision(agent, row, dry_run=args.dry_run))
                kf = maybe_promote_known_fix(agent, row, dry_run=args.dry_run)
                if kf:
                    promoted.append(kf)
        promoted.extend(promote_extra_sources(agent, dry_run=args.dry_run))
    print({"status": "ok", "count": len([p for p in promoted if p]), "items": [p for p in promoted if p]})


if __name__ == "__main__":
    main()
