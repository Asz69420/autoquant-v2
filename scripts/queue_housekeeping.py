#!/usr/bin/env python3
import json
import os
import sqlite3
from datetime import datetime, timezone, timedelta

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def main():
    conn = sqlite3.connect(DB)
    stale_cutoff = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()

    stale = conn.execute(
        "SELECT id, cycle_id, stage, strategy_spec_id, variant_id FROM research_funnel_queue WHERE status='running' AND started_at < ?",
        (stale_cutoff,),
    ).fetchall()
    for row in stale:
        conn.execute(
            "UPDATE research_funnel_queue SET status='queued', started_at=NULL, notes=? WHERE id=?",
            (json.dumps({"status":"reset_stale_running","reason":"stale_running_timeout","reset_at":now_iso()}), row[0]),
        )

    max_cycle = conn.execute("SELECT COALESCE(MAX(cycle_id),0) FROM research_funnel_queue WHERE cycle_id < 90000").fetchone()[0] or 0
    orphan = conn.execute(
        "SELECT id, cycle_id, stage, strategy_spec_id, variant_id FROM research_funnel_queue WHERE status='queued' AND (cycle_id >= 90000 OR cycle_id < ?)",
        (max(0, int(max_cycle) - 20),),
    ).fetchall()
    for row in orphan:
        conn.execute(
            "UPDATE research_funnel_queue SET status='done', completed_at=?, notes=? WHERE id=?",
            (now_iso(), json.dumps({"status":"orphan_discarded","reason":"orphan_or_legacy_cycle","discarded_at":now_iso()}), row[0]),
        )

    conn.commit()
    remaining = conn.execute("SELECT status, COUNT(*) FROM research_funnel_queue GROUP BY status ORDER BY status").fetchall()
    conn.close()
    print(json.dumps({
        "status":"ok",
        "stale_reset": len(stale),
        "orphan_discarded": len(orphan),
        "remaining": [{"status": r[0], "count": r[1]} for r in remaining]
    }, indent=2))


if __name__ == "__main__":
    main()
