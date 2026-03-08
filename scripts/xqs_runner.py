#!/usr/bin/env python3
import argparse
import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
DB = os.path.join(ROOT, "db", "autoquant.db")
BACKTESTER = r"C:\Users\Clamps\.openclaw\skills\autoquant-backtester\engine.py"
SPECS_DIR = os.path.join(ROOT, "artifacts", "strategy_specs")
ASSETS = ["ETH", "BTC", "SOL"]


def log_event(conn, event_type, agent, message, severity="info", artifact_id=None, pipeline="xqs", step=None, metadata=None):
    conn.execute(
        """
        INSERT INTO event_log (ts_iso, event_type, agent, pipeline, step, artifact_id, severity, message, metadata)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now(timezone.utc).isoformat(),
            event_type,
            agent,
            pipeline,
            step,
            artifact_id,
            severity,
            message,
            json.dumps(metadata) if metadata is not None else None,
        ),
    )


def geometric_mean(values):
    vals = [max(0.0, float(v)) for v in values if v is not None]
    if not vals:
        return 0.0
    if any(v == 0 for v in vals):
        return 0.0
    p = 1.0
    for v in vals:
        p *= v
    return p ** (1.0 / len(vals))


def find_spec_path(row):
    spec_id = row["strategy_spec_id"] or ""
    candidates = []

    if spec_id:
        candidates.append(os.path.join(SPECS_DIR, f"{spec_id}.strategy_spec.json"))

    # recursive fallback
    if os.path.isdir(SPECS_DIR) and spec_id:
        for dirpath, _, filenames in os.walk(SPECS_DIR):
            for fn in filenames:
                if fn.endswith(".strategy_spec.json") and spec_id.lower() in fn.lower():
                    candidates.append(os.path.join(dirpath, fn))

    for p in candidates:
        if os.path.exists(p):
            return p
    return None


def candidate_rows(conn):
    conn.row_factory = sqlite3.Row
    return conn.execute(
        """
        SELECT id, strategy_spec_id, variant_id, asset, timeframe, score_total, xqscore_total
        FROM backtest_results
        WHERE COALESCE(score_total, 0) >= 1.0
          AND xqscore_total IS NULL
        ORDER BY ts_iso DESC
        """
    ).fetchall()


def run_cross_asset(conn, row, spec_path):
    original_asset = row["asset"]
    timeframe = row["timeframe"]
    variant = row["variant_id"]
    sid = row["id"]

    other_assets = [a for a in ASSETS if a != original_asset]
    qscores = [float(row["score_total"] or 0.0)]
    tested_assets = [original_asset]

    for asset in other_assets:
        start_ts = datetime.now(timezone.utc).isoformat()
        cmd = [
            sys.executable,
            BACKTESTER,
            "--asset",
            asset,
            "--tf",
            timeframe,
            "--strategy-spec",
            spec_path,
            "--variant",
            variant,
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if proc.returncode != 0:
            log_event(
                conn,
                "xqs_backtest_failed",
                "frodex",
                f"xQS cross-asset failed for {sid} on {asset}: rc={proc.returncode}",
                severity="warn",
                artifact_id=sid,
                step="cross_asset",
                metadata={"stderr": (proc.stderr or "")[:500]},
            )
            continue

        bt_row = conn.execute(
            """
            SELECT id, score_total
            FROM backtest_results
            WHERE strategy_spec_id = ? AND variant_id = ? AND asset = ? AND timeframe = ? AND ts_iso >= ?
            ORDER BY ts_iso DESC LIMIT 1
            """,
            (row["strategy_spec_id"], variant, asset, timeframe, start_ts),
        ).fetchone()

        if bt_row and bt_row[1] is not None:
            qscores.append(float(bt_row[1]))
            tested_assets.append(asset)
            log_event(
                conn,
                "xqs_backtest_complete",
                "frodex",
                f"xQS cross-asset {sid}: {asset} QS={float(bt_row[1]):.3f}",
                artifact_id=str(bt_row[0]),
                step="cross_asset",
            )
        else:
            log_event(
                conn,
                "xqs_backtest_missing",
                "frodex",
                f"xQS backtest row missing for {sid} on {asset}",
                severity="warn",
                artifact_id=sid,
                step="cross_asset",
            )

    if len(qscores) <= 1:
        # fallback
        xqs = float(row["score_total"] or 0.0)
        reason = "single_asset_fallback"
    else:
        xqs = geometric_mean(qscores)
        reason = "geometric_mean"

    conn.execute(
        "UPDATE backtest_results SET xqscore_total = ?, xqscore_details = ? WHERE id = ?",
        (
            xqs,
            json.dumps({"method": reason, "assets_tested": tested_assets, "qscores": qscores}),
            sid,
        ),
    )
    log_event(
        conn,
        "xqs_updated",
        "oragorn",
        f"xQS updated for {sid}: {xqs:.3f} ({reason})",
        artifact_id=sid,
        step="update",
    )
    return xqs, tested_assets, reason


def main():
    ap = argparse.ArgumentParser(description="Cross-asset xQS updater")
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--run", action="store_true")
    args = ap.parse_args()

    if not args.preview and not args.run:
        ap.error("Use --preview or --run")

    conn = sqlite3.connect(DB)
    rows = candidate_rows(conn)

    plan = []
    for r in rows:
        spec_path = find_spec_path(r)
        other_assets = [a for a in ASSETS if a != r["asset"]]
        plan.append(
            {
                "id": r["id"],
                "strategy_spec_id": r["strategy_spec_id"],
                "variant_id": r["variant_id"],
                "asset": r["asset"],
                "timeframe": r["timeframe"],
                "qscore": r["score_total"],
                "spec_found": bool(spec_path),
                "spec_path": spec_path,
                "cross_assets": other_assets,
            }
        )

    if args.preview:
        print(json.dumps({"mode": "preview", "candidates": len(plan), "plan": plan}, indent=2))
        conn.close()
        return

    updates = []
    for r in rows:
        sid = r["id"]
        spec_path = find_spec_path(r)
        if not spec_path:
            xqs = float(r["score_total"] or 0.0)
            conn.execute(
                "UPDATE backtest_results SET xqscore_total = ?, xqscore_details = ? WHERE id = ?",
                (xqs, json.dumps({"method": "single_asset_fallback", "reason": "spec_not_found"}), sid),
            )
            log_event(conn, "xqs_fallback", "oragorn", f"xQS fallback for {sid}: spec not found", severity="warn", artifact_id=sid)
            updates.append({"id": sid, "xqscore": xqs, "reason": "spec_not_found"})
            continue

        try:
            xqs, tested_assets, reason = run_cross_asset(conn, r, spec_path)
            updates.append({"id": sid, "xqscore": xqs, "assets_tested": tested_assets, "reason": reason})
        except Exception as e:
            xqs = float(r["score_total"] or 0.0)
            conn.execute(
                "UPDATE backtest_results SET xqscore_total = ?, xqscore_details = ? WHERE id = ?",
                (xqs, json.dumps({"method": "single_asset_fallback", "reason": str(e)}), sid),
            )
            log_event(conn, "xqs_error", "oragorn", f"xQS error for {sid}: {e}", severity="warn", artifact_id=sid)
            updates.append({"id": sid, "xqscore": xqs, "reason": "exception"})

    conn.commit()
    conn.close()

    print(json.dumps({"mode": "run", "updated": len(updates), "results": updates}, indent=2))


if __name__ == "__main__":
    main()
