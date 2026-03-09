#!/usr/bin/env python3
import html
import json
import subprocess
import sys
from pathlib import Path

from text_io import read_text_best_effort

ROOT = Path(__file__).resolve().parents[1]
TG_NOTIFY = ROOT / "scripts" / "tg_notify.py"
DAILY_JOURNAL = ROOT / "agents" / "quandalf" / "memory" / "daily_journal.md"
LATEST_JOURNAL = ROOT / "agents" / "quandalf" / "memory" / "latest_journal.md"
MAX_MESSAGE_CHARS = 4000
TITLE = "🧠 <b>Quandalf Daily Journal</b>\n\n"


def pick_journal_path() -> Path:
    if DAILY_JOURNAL.exists() and DAILY_JOURNAL.stat().st_size > 0:
        return DAILY_JOURNAL
    return DAILY_JOURNAL


def send_message(message: str) -> tuple[bool, str]:
    cmd = [
        sys.executable,
        str(TG_NOTIFY),
        "--message",
        message,
        "--bot",
        "quandalf",
        "--channel",
        "dm",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    ok = proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")
    detail = (proc.stdout or proc.stderr or "").strip()
    return ok, detail


def main() -> int:
    path = pick_journal_path()
    if not path.exists() or path.stat().st_size == 0:
        fallback_note = (
            f"{TITLE}"
            "Daily journal not found.\n"
            "Policy: DM only sends the dedicated daily journal entry (single message, max 4000 chars).\n"
            "Raw latest_journal dumps are blocked."
        )
        ok, detail = send_message(fallback_note)
        print(json.dumps({"status": "sent" if ok else "failed", "journal": str(path), "detail": detail}))
        return 0 if ok else 1

    raw = read_text_best_effort(path).strip()
    safe = html.escape(raw)
    message = TITLE + safe

    if len(message) > MAX_MESSAGE_CHARS:
        detail_message = (
            f"{TITLE}"
            "Daily journal exceeded the one-message limit and was not sent.\n"
            "Please rewrite it to 4000 characters or less."
        )
        ok, detail = send_message(detail_message)
        print(json.dumps({
            "status": "oversize_blocked" if ok else "failed",
            "journal": str(path),
            "chars": len(message),
            "detail": detail,
        }))
        return 0 if ok else 1

    ok, detail = send_message(message)
    print(json.dumps({"status": "sent" if ok else "failed", "chars": len(message), "journal": str(path), "detail": detail}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
