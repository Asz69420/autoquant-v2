from __future__ import annotations

from pathlib import Path

BEST_EFFORT_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


def read_text_best_effort(path: str | Path, default: str = "") -> str:
    target = Path(path)
    for encoding in BEST_EFFORT_ENCODINGS:
        try:
            return target.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception:
            break
    try:
        return target.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return default
