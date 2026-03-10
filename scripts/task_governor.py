#!/usr/bin/env python3
"""Deterministic task board + roadmap sync for AutoQuant."""
import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent.parent
BOARD_PATH = ROOT / "data" / "state" / "task_board.json"
ROADMAP_PATH = ROOT / "ROADMAP.md"
COMPLETIONS_DIR = ROOT / "artifacts" / "completions"

STATUS_ORDER = {"active": 0, "blocked": 1, "queued": 2, "done": 3, "dropped": 4}
PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

SEED_TASKS = [
    {
        "title": "Bootstrap memory governance spine",
        "type": "governance",
        "status": "active",
        "priority": "critical",
        "owner": "oragorn",
        "shared": True,
        "depends_on": [],
        "acceptance": [
            "memory governance config exists",
            "task board exists",
            "completion records exist",
            "roadmap sync exists"
        ],
        "tags": ["memory-v2", "governance", "bootstrap"],
        "notes": "Foundation for shared/private memory, task governance, and completion-driven updates."
    },
    {
        "title": "Bootstrap shared intelligence memory buckets",
        "type": "migration",
        "status": "queued",
        "priority": "high",
        "owner": "logron",
        "shared": True,
        "depends_on": ["TASK-0001"],
        "acceptance": [
            "shared memory directories exist",
            "shared index exists",
            "promotion script is working"
        ],
        "tags": ["memory-v2", "shared-memory"],
        "notes": "Create shared long-term memory buckets and promotion entry points."
    },
    {
        "title": "Backfill Quandalf lessons into shared intelligence",
        "type": "migration",
        "status": "queued",
        "priority": "high",
        "owner": "quandalf",
        "shared": True,
        "depends_on": ["TASK-0002"],
        "acceptance": [
            "pilot lessons promoted from journals",
            "shared lesson index is populated",
            "no raw journal bloat in active context"
        ],
        "tags": ["memory-v2", "quandalf", "lessons"],
        "notes": "Start with strategy lessons, regime insights, and reusable thesis patterns."
    },
    {
        "title": "Integrate completion records into recurring pipelines",
        "type": "feature",
        "status": "queued",
        "priority": "high",
        "owner": "frodex",
        "shared": True,
        "depends_on": ["TASK-0001"],
        "acceptance": [
            "significant pipeline steps emit completion records",
            "task board updates after meaningful milestones",
            "roadmap sync can run unattended"
        ],
        "tags": ["memory-v2", "pipelines", "automation"],
        "notes": "Wire the new governance spine into the live automation loop."
    },
    {
        "title": "Design external market intelligence ingestion for Quandalf",
        "type": "research",
        "status": "queued",
        "priority": "medium",
        "owner": "quandalf",
        "shared": True,
        "depends_on": ["TASK-0002"],
        "acceptance": [
            "ingestion sources are categorized",
            "promotion policy is defined",
            "noise filtering rules exist"
        ],
        "tags": ["market-intel", "quandalf", "future"],
        "notes": "Plan liquidation, positioning, news, events, and research ingestion without flooding active memory."
    }
]


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def load_board():
    if not BOARD_PATH.exists():
        return {
            "version": "task-board-v1",
            "generated_at": now_iso(),
            "summary": {"queued": 0, "active": 0, "blocked": 0, "done": 0, "dropped": 0, "total": 0},
            "tasks": []
        }
    return json.loads(BOARD_PATH.read_text(encoding="utf-8"))


def next_task_id(board):
    max_id = 0
    for task in board.get("tasks", []):
        match = re.match(r"^TASK-(\d{4})$", task.get("id", ""))
        if match:
            max_id = max(max_id, int(match.group(1)))
    return "TASK-{0:04d}".format(max_id + 1)


def ensure_task_shape(task):
    task.setdefault("depends_on", [])
    task.setdefault("acceptance", [])
    task.setdefault("evidence", [])
    task.setdefault("tags", [])
    task.setdefault("notes", None)
    task.setdefault("completed_at", None)
    return task


def recalc_summary(board):
    summary = {"queued": 0, "active": 0, "blocked": 0, "done": 0, "dropped": 0, "total": 0}
    for task in board.get("tasks", []):
        status = task.get("status", "queued")
        if status in summary:
            summary[status] += 1
        summary["total"] += 1
    board["summary"] = summary
    board["generated_at"] = now_iso()
    board["tasks"] = sorted(
        board.get("tasks", []),
        key=lambda t: (
            STATUS_ORDER.get(t.get("status", "queued"), 99),
            PRIORITY_ORDER.get(t.get("priority", "medium"), 99),
            t.get("id", "")
        )
    )
    return board


def save_board(board):
    BOARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    board = recalc_summary(board)
    BOARD_PATH.write_text(json.dumps(board, indent=2), encoding="utf-8")
    return board


def find_task(board, task_id):
    for task in board.get("tasks", []):
        if task.get("id") == task_id:
            return task
    raise SystemExit("Task not found: {0}".format(task_id))


def render_roadmap_summary(board):
    summary = board["summary"]
    active = [t for t in board["tasks"] if t["status"] == "active"]
    blocked = [t for t in board["tasks"] if t["status"] == "blocked"]
    queued = [t for t in board["tasks"] if t["status"] == "queued"]
    done = [t for t in board["tasks"] if t["status"] == "done"][:5]

    lines = []
    lines.append("_Last synced: {0}_".format(board["generated_at"]))
    lines.append("")
    lines.append("- Queued: **{0}**".format(summary["queued"]))
    lines.append("- Active: **{0}**".format(summary["active"]))
    lines.append("- Blocked: **{0}**".format(summary["blocked"]))
    lines.append("- Done: **{0}**".format(summary["done"]))
    lines.append("")

    lines.append("### Active")
    if active:
        for task in active:
            lines.append("- `{0}` **{1}** — owner: {2}".format(task["id"], task["title"], task["owner"]))
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### Blocked")
    if blocked:
        for task in blocked:
            lines.append("- `{0}` **{1}** — {2}".format(task["id"], task["title"], task.get("notes") or "blocked"))
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### Next Up")
    if queued:
        for task in queued[:5]:
            lines.append("- `{0}` **{1}** — owner: {2}".format(task["id"], task["title"], task["owner"]))
    else:
        lines.append("- None")

    lines.append("")
    lines.append("### Recently Done")
    if done:
        for task in done:
            lines.append("- `{0}` **{1}**".format(task["id"], task["title"]))
    else:
        lines.append("- None")

    return "\n".join(lines)


def sync_roadmap(board):
    if not ROADMAP_PATH.exists():
        return None
    text = ROADMAP_PATH.read_text(encoding="utf-8")
    start = "<!-- TASK_SUMMARY_START -->"
    end = "<!-- TASK_SUMMARY_END -->"
    if start not in text or end not in text:
        return None
    replacement = start + "\n" + render_roadmap_summary(board) + "\n" + end
    text = re.sub(start + r".*?" + end, replacement, text, flags=re.S)
    ROADMAP_PATH.write_text(text, encoding="utf-8")
    return str(ROADMAP_PATH)


def create_task(board, title, task_type, priority, owner, shared, depends_on=None, acceptance=None, tags=None, notes=None, status="queued"):
    timestamp = now_iso()
    task = {
        "id": next_task_id(board),
        "title": title,
        "type": task_type,
        "status": status,
        "priority": priority,
        "owner": owner,
        "shared": bool(shared),
        "depends_on": list(depends_on or []),
        "acceptance": list(acceptance or []),
        "evidence": [],
        "tags": list(tags or []),
        "notes": notes,
        "created_at": timestamp,
        "updated_at": timestamp,
        "completed_at": None
    }
    ensure_task_shape(task)
    board["tasks"].append(task)
    return task


def make_completion_id():
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    suffix = uuid4().hex[:4].upper()
    return "COMP-{0}-{1}".format(stamp, suffix)


def write_generic_completion_record(record_prefix, actor, summary, outcome, significance, files_touched, evidence, follow_up_titles, notes=None, tasks_completed=None):
    completion_id = make_completion_id()
    date_dir = COMPLETIONS_DIR / datetime.now(timezone.utc).strftime("%Y%m%d")
    date_dir.mkdir(parents=True, exist_ok=True)
    path = date_dir / ("{0}--{1}.completion_record.json".format(record_prefix, completion_id))
    record = {
        "version": "completion-record-v1",
        "id": completion_id,
        "ts_iso": now_iso(),
        "actor": actor,
        "summary": summary,
        "outcome": outcome,
        "significance": significance,
        "tasks_completed": list(tasks_completed or []),
        "files_touched": files_touched,
        "evidence": evidence,
        "follow_up_titles": follow_up_titles,
        "notes": notes,
        "memory_candidates": []
    }
    path.write_text(json.dumps(record, indent=2), encoding="utf-8")
    return str(path)



def write_completion_record(task, actor, summary, outcome, significance, files_touched, evidence, follow_up_titles, notes=None):
    return write_generic_completion_record(
        record_prefix=task["id"],
        actor=actor,
        summary=summary,
        outcome=outcome,
        significance=significance,
        files_touched=files_touched,
        evidence=evidence,
        follow_up_titles=follow_up_titles,
        notes=notes,
        tasks_completed=[task["id"]],
    )


def cmd_bootstrap(_args):
    board = load_board()
    if board.get("tasks"):
        board = save_board(board)
        roadmap_path = sync_roadmap(board)
        print(json.dumps({"status": "exists", "task_count": len(board["tasks"]), "roadmap_synced": bool(roadmap_path)}, indent=2))
        return

    for seed in SEED_TASKS:
        create_task(
            board,
            title=seed["title"],
            task_type=seed["type"],
            priority=seed["priority"],
            owner=seed["owner"],
            shared=seed["shared"],
            depends_on=seed.get("depends_on"),
            acceptance=seed.get("acceptance"),
            tags=seed.get("tags"),
            notes=seed.get("notes"),
            status=seed.get("status", "queued")
        )

    board = save_board(board)
    roadmap_path = sync_roadmap(board)
    print(json.dumps({
        "status": "bootstrapped",
        "task_count": len(board["tasks"]),
        "board_path": str(BOARD_PATH),
        "roadmap_synced": bool(roadmap_path)
    }, indent=2))


def cmd_add(args):
    board = load_board()
    task = create_task(
        board,
        title=args.title,
        task_type=args.type,
        priority=args.priority,
        owner=args.owner,
        shared=args.shared,
        depends_on=args.depends_on,
        acceptance=args.acceptance,
        tags=args.tag,
        notes=args.notes,
        status=args.status
    )
    board = save_board(board)
    sync_roadmap(board)
    print(json.dumps({"status": "ok", "task": task}, indent=2))


def cmd_update(args):
    board = load_board()
    task = find_task(board, args.task_id)
    if args.status:
        task["status"] = args.status
        if args.status != "done":
            task["completed_at"] = None
    if args.priority:
        task["priority"] = args.priority
    if args.owner:
        task["owner"] = args.owner
    if args.notes is not None:
        task["notes"] = args.notes
    if args.evidence:
        task["evidence"].extend(args.evidence)
    if args.tag:
        existing = set(task.get("tags", []))
        for tag in args.tag:
            if tag not in existing:
                task.setdefault("tags", []).append(tag)
    task["updated_at"] = now_iso()
    board = save_board(board)
    sync_roadmap(board)
    print(json.dumps({"status": "ok", "task": task}, indent=2))


def cmd_complete(args):
    board = load_board()
    task = find_task(board, args.task_id)
    task["status"] = "done"
    task["completed_at"] = now_iso()
    task["updated_at"] = now_iso()
    if args.notes is not None:
        task["notes"] = args.notes
    if args.evidence:
        task["evidence"].extend(args.evidence)

    follow_up_ids = []
    for title in args.follow_up:
        new_task = create_task(
            board,
            title=title,
            task_type="feature",
            priority="medium",
            owner=args.actor,
            shared=True,
            depends_on=[task["id"]],
            acceptance=[],
            tags=["follow-up"],
            notes="Auto-created from completion record for {0}.".format(task["id"]),
            status="queued"
        )
        follow_up_ids.append(new_task["id"])

    completion_path = write_completion_record(
        task=task,
        actor=args.actor,
        summary=args.summary,
        outcome=args.outcome,
        significance=args.significance,
        files_touched=args.file,
        evidence=args.evidence,
        follow_up_titles=args.follow_up,
        notes=args.notes
    )
    if completion_path not in task["evidence"]:
        task["evidence"].append(completion_path)

    board = save_board(board)
    sync_roadmap(board)
    print(json.dumps({
        "status": "ok",
        "task_id": task["id"],
        "completion_record": completion_path,
        "follow_up_ids": follow_up_ids
    }, indent=2))


def cmd_record(args):
    board = load_board()
    completion_path = write_generic_completion_record(
        record_prefix=args.record_prefix,
        actor=args.actor,
        summary=args.summary,
        outcome=args.outcome,
        significance=args.significance,
        files_touched=args.file,
        evidence=args.evidence,
        follow_up_titles=args.follow_up,
        notes=args.notes,
        tasks_completed=args.task_id,
    )
    board = save_board(board)
    sync_roadmap(board)
    print(json.dumps({"status": "ok", "completion_record": completion_path, "linked_tasks": args.task_id}, indent=2))



def cmd_list(args):
    board = load_board()
    tasks = board.get("tasks", [])
    if args.status:
        tasks = [t for t in tasks if t.get("status") == args.status]
    if args.owner:
        tasks = [t for t in tasks if t.get("owner") == args.owner]
    print(json.dumps({"summary": board.get("summary", {}), "tasks": tasks}, indent=2))


def cmd_sync_roadmap(_args):
    board = save_board(load_board())
    path = sync_roadmap(board)
    print(json.dumps({"status": "ok", "roadmap_path": path, "board_path": str(BOARD_PATH)}, indent=2))


def build_parser():
    parser = argparse.ArgumentParser(description="Task governor for AutoQuant")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("bootstrap")
    p.set_defaults(func=cmd_bootstrap)

    p = sub.add_parser("add")
    p.add_argument("--title", required=True)
    p.add_argument("--type", required=True, choices=["milestone", "feature", "infra", "research", "migration", "maintenance", "governance"])
    p.add_argument("--status", default="queued", choices=["queued", "active", "blocked", "done", "dropped"])
    p.add_argument("--priority", default="medium", choices=["low", "medium", "high", "critical"])
    p.add_argument("--owner", required=True)
    p.add_argument("--shared", action="store_true")
    p.add_argument("--depends-on", action="append", default=[])
    p.add_argument("--acceptance", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.add_argument("--notes")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("update")
    p.add_argument("--task-id", required=True)
    p.add_argument("--status", choices=["queued", "active", "blocked", "done", "dropped"])
    p.add_argument("--priority", choices=["low", "medium", "high", "critical"])
    p.add_argument("--owner")
    p.add_argument("--notes")
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--tag", action="append", default=[])
    p.set_defaults(func=cmd_update)

    p = sub.add_parser("complete")
    p.add_argument("--task-id", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--outcome", default="success", choices=["success", "partial", "fail", "info"])
    p.add_argument("--significance", default="medium", choices=["low", "medium", "high", "critical"])
    p.add_argument("--file", action="append", default=[])
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--follow-up", action="append", default=[])
    p.add_argument("--notes")
    p.set_defaults(func=cmd_complete)

    p = sub.add_parser("record")
    p.add_argument("--record-prefix", required=True)
    p.add_argument("--actor", required=True)
    p.add_argument("--summary", required=True)
    p.add_argument("--outcome", default="success", choices=["success", "partial", "fail", "info"])
    p.add_argument("--significance", default="medium", choices=["low", "medium", "high", "critical"])
    p.add_argument("--task-id", action="append", default=[])
    p.add_argument("--file", action="append", default=[])
    p.add_argument("--evidence", action="append", default=[])
    p.add_argument("--follow-up", action="append", default=[])
    p.add_argument("--notes")
    p.set_defaults(func=cmd_record)

    p = sub.add_parser("list")
    p.add_argument("--status", choices=["queued", "active", "blocked", "done", "dropped"])
    p.add_argument("--owner")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("sync-roadmap")
    p.set_defaults(func=cmd_sync_roadmap)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
