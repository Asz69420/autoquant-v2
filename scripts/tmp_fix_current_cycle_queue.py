import json
import os
import sqlite3

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
SPEC_IDS = [
    "QD-20260311-C020-SOL-RANGE-FAILURE-REACCEPTANCE-v1",
    "QD-20260311-C020-ETH-TREND-RESET-CONTINUATION-v1",
    "QD-20260311-C020-TAO-COMPRESSION-FAKEOUT-REEXPANSION-v1",
]

conn = sqlite3.connect(DB)
requeued = 0
for spec_id in SPEC_IDS:
    cur = conn.execute(
        """
        UPDATE research_funnel_queue
        SET status='queued', completed_at=NULL, notes=?
        WHERE strategy_spec_id=?
          AND status='done'
          AND result_id IS NULL
          AND lower(COALESCE(notes,'')) LIKE '%orphan_discarded%'
        """,
        (json.dumps({"status": "requeued_after_false_orphan_cleanup", "requeued_by": "oragorn_fix"}), spec_id),
    )
    requeued += cur.rowcount
conn.commit()
conn.close()
print(json.dumps({"status": "ok", "requeued": requeued, "spec_ids": SPEC_IDS}, indent=2))
