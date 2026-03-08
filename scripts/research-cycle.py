#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = sys.executable
SKILLS_DIR = Path.home() / ".openclaw" / "skills"
BRIEFING_PATH = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"


def _run_skill(cmd: list[str]):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, check=True)
        raw = (p.stdout or "").strip()
        if not raw:
            return {"status": "empty", "stdout": "", "stderr": (p.stderr or "").strip()}
        try:
            return json.loads(raw)
        except Exception:
            return {"status": "non_json", "stdout": raw, "stderr": (p.stderr or "").strip()}
    except subprocess.CalledProcessError as e:
        out = (e.stdout or "").strip()
        err = (e.stderr or "").strip()
        try:
            return json.loads(out) if out else {"status": "error", "returncode": e.returncode, "stderr": err}
        except Exception:
            return {"status": "error", "returncode": e.returncode, "stdout": out, "stderr": err}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _count_items(obj, key_hints: list[str]) -> int:
    if isinstance(obj, list):
        return len(obj)
    if isinstance(obj, dict):
        for k in key_hints:
            v = obj.get(k)
            if isinstance(v, list):
                return len(v)
        for v in obj.values():
            if isinstance(v, list):
                return len(v)
    return 0


def main() -> int:
    # Phase 1 only: Build briefing packet
    leaderboard = _run_skill([PY, str(SKILLS_DIR / "autoquant-leaderboard" / "query.py"), "--limit", "5"])
    kpi = _run_skill([PY, str(SKILLS_DIR / "autoquant-kpi" / "query.py"), "--days", "30"])
    lessons = _run_skill([PY, str(SKILLS_DIR / "autoquant-lessons" / "query.py"), "--limit", "5"])
    digest = _run_skill([PY, str(SKILLS_DIR / "autoquant-research-fetch" / "query.py"), "--limit", "5", "--unprocessed"])
    scan = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--scan"])
    funding = _run_skill([PY, str(SKILLS_DIR / "autoquant-market-data" / "market.py"), "--funding"])

    now = datetime.now(timezone.utc)
    cycle_id = f"cycle_{now.strftime('%Y%m%d_%H%M%S')}"

    packet = {
        "ts_iso": now.isoformat(),
        "cycle_id": cycle_id,
        "leaderboard": leaderboard,
        "kpi": kpi,
        "recent_lessons": lessons,
        "research_digest": digest,
        "market_scan": scan,
        "funding_rates": funding,
    }

    BRIEFING_PATH.parent.mkdir(parents=True, exist_ok=True)
    BRIEFING_PATH.write_text(json.dumps(packet, indent=2), encoding="utf-8")

    top_opportunity = None
    if isinstance(scan, dict):
        top = scan.get("top_opportunities")
        if isinstance(top, list) and top:
            first = top[0]
            if isinstance(first, dict):
                top_opportunity = first.get("asset") or first.get("symbol") or first.get("name")

    summary = {
        "status": "briefing_ready",
        "cycle_id": cycle_id,
        "briefing_path": str(BRIEFING_PATH),
        "leaderboard_count": _count_items(leaderboard, ["strategies", "items", "rows", "data"]),
        "lesson_count": _count_items(lessons, ["lessons", "items", "rows", "data"]),
        "research_count": _count_items(digest, ["items", "entries", "results", "data"]),
        "scan_count": _count_items(scan, ["top_opportunities", "opportunities", "items", "data"]),
        "top_opportunity": top_opportunity,
    }

    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
