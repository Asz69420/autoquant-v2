#!/usr/bin/env python3
import html
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TG_NOTIFY = ROOT / "scripts" / "tg_notify.py"
DAILY_JOURNAL = ROOT / "agents" / "quandalf" / "memory" / "daily_journal.md"
LATEST_JOURNAL = ROOT / "agents" / "quandalf" / "memory" / "latest_journal.md"


def pick_journal_path() -> Path:
    if DAILY_JOURNAL.exists() and DAILY_JOURNAL.stat().st_size > 0:
        return DAILY_JOURNAL
    if LATEST_JOURNAL.exists() and LATEST_JOURNAL.stat().st_size > 0:
        return LATEST_JOURNAL
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


def chunk_text(text: str, max_len: int = 2800) -> list[str]:
    chunks = []
    buf = []
    size = 0
    for line in text.splitlines():
        add = len(line) + 1
        if size + add > max_len and buf:
            chunks.append("\n".join(buf))
            buf = [line]
            size = add
        else:
            buf.append(line)
            size += add
    if buf:
        chunks.append("\n".join(buf))
    return chunks or [""]


def main() -> int:
    path = pick_journal_path()
    if not path.exists() or path.stat().st_size == 0:
        ok, detail = send_message("🧠 <b>Quandalf Daily Journal</b>\n\nJournal not found yet.")
        print(json.dumps({"status": "sent" if ok else "failed", "journal": str(path), "detail": detail}))
        return 0 if ok else 1

    raw = path.read_text(encoding="utf-8", errors="replace").strip()
    safe = html.escape(raw)
    parts = chunk_text(safe)

    for i, part in enumerate(parts, start=1):
        prefix = f"🧠 <b>Quandalf Daily Journal</b>\n<b>Part {i}/{len(parts)}</b>\n\n"
        message = prefix + f"<pre>{part}</pre>"
        ok, detail = send_message(message)
        if not ok:
            print(json.dumps({"status": "failed", "part": i, "detail": detail}))
            return 1

    print(json.dumps({"status": "sent", "parts": len(parts), "journal": str(path)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
