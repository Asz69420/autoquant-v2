#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = WORKSPACE_ROOT / "artifacts"
LOGS_DIR = WORKSPACE_ROOT / "logs"
ARCHIVE_DIR = WORKSPACE_ROOT / "data" / "archive"
DB_PATH = WORKSPACE_ROOT / "db" / "autoquant.db"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def file_age_days(path: Path, now: datetime) -> float:
    ts = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    return (now - ts).total_seconds() / 86400.0


def workspace_size_bytes(root: Path) -> int:
    total = 0
    for p in root.rglob("*"):
        if p.is_file():
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def normalize_key(v: str) -> str:
    return str(v).strip().lower()


def load_promoted_keys(db_path: Path) -> set[str]:
    promoted: set[str] = set()
    if not db_path.exists():
        return promoted

    try:
        conn = sqlite3.connect(str(db_path))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='backtest_results'")
        if not cur.fetchone():
            conn.close()
            return promoted

        cur.execute("PRAGMA table_info(backtest_results)")
        cols = [r[1] for r in cur.fetchall()]

        id_candidates = ["strategy_id", "spec_id", "strategy_name", "name", "id", "strategy_key"]
        q_candidates = ["qscore", "q_score", "qscore_final", "q_score_final"]

        id_cols = [c for c in id_candidates if c in cols]
        q_cols = [c for c in q_candidates if c in cols]
        if not q_cols:
            conn.close()
            return promoted

        sel_cols = id_cols + q_cols
        cur.execute(f"SELECT {', '.join(sel_cols)} FROM backtest_results")
        rows = cur.fetchall()
        conn.close()

        for row in rows:
            values = dict(zip(sel_cols, row))
            q_best = None
            for q in q_cols:
                try:
                    qv = float(values.get(q))
                    q_best = qv if q_best is None else max(q_best, qv)
                except (TypeError, ValueError):
                    continue
            if q_best is None or q_best < 3.0:
                continue
            for c in id_cols:
                v = values.get(c)
                if v is None:
                    continue
                nk = normalize_key(v)
                if nk:
                    promoted.add(nk)
    except Exception:
        return promoted

    return promoted


def extract_strategy_keys(spec_path: Path) -> set[str]:
    keys: set[str] = set()
    stem = spec_path.name.replace(".strategy_spec.json", "")
    keys.add(normalize_key(stem))

    try:
        obj = json.loads(spec_path.read_text(encoding="utf-8-sig"))
        for k in ("strategy_id", "id", "spec_id", "name", "strategy_name", "title", "strategy_key"):
            v = obj.get(k) if isinstance(obj, dict) else None
            if v is not None:
                nk = normalize_key(v)
                if nk:
                    keys.add(nk)
    except Exception:
        pass

    return keys


@dataclass
class CleanupSummary:
    dry_run: bool
    before_bytes: int
    after_bytes: int = 0
    deleted_files: int = 0
    deleted_bytes: int = 0
    archived_logs: int = 0
    archived_bytes: int = 0
    deleted_empty_dirs: int = 0
    kept_promoted_strategy_specs: int = 0
    kept_recent_files: int = 0
    kept_other: int = 0
    deleted_samples: list[str] = None
    kept_samples: list[str] = None

    def __post_init__(self):
        if self.deleted_samples is None:
            self.deleted_samples = []
        if self.kept_samples is None:
            self.kept_samples = []


def add_sample(bucket: list[str], value: str, limit: int = 50) -> None:
    if len(bucket) < limit:
        bucket.append(value)


def delete_file(path: Path, summary: CleanupSummary, reason: str) -> None:
    size = 0
    try:
        size = path.stat().st_size
    except OSError:
        pass

    if not summary.dry_run:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            return

    summary.deleted_files += 1
    summary.deleted_bytes += size
    add_sample(summary.deleted_samples, f"{reason}: {path.as_posix()}")


def mark_kept(summary: CleanupSummary, reason: str, path: Path) -> None:
    if reason == "promoted":
        summary.kept_promoted_strategy_specs += 1
    elif reason == "recent":
        summary.kept_recent_files += 1
    else:
        summary.kept_other += 1
    add_sample(summary.kept_samples, f"{reason}: {path.as_posix()}")


def cleanup_artifacts(summary: CleanupSummary, now: datetime, promoted_keys: set[str]) -> None:
    # batches: delete *.batch_backtest.json older than 7d
    batches = ARTIFACTS_DIR / "batches"
    if batches.exists():
        for p in batches.rglob("*.batch_backtest.json"):
            age = file_age_days(p, now)
            if age > 7:
                delete_file(p, summary, "batches>7d")
            else:
                mark_kept(summary, "recent", p)

    # strategy_specs: delete *.strategy_spec.json older than 7d unless promoted (QScore >=3)
    specs = ARTIFACTS_DIR / "strategy_specs"
    if specs.exists():
        for p in specs.rglob("*.strategy_spec.json"):
            age = file_age_days(p, now)
            if age <= 7:
                mark_kept(summary, "recent", p)
                continue

            keys = extract_strategy_keys(p)
            if any(k in promoted_keys for k in keys):
                mark_kept(summary, "promoted", p)
                continue

            delete_file(p, summary, "strategy_specs>7d_nonpromoted")

    # outcomes: delete all files older than 7d
    outcomes = ARTIFACTS_DIR / "outcomes"
    if outcomes.exists():
        for p in outcomes.rglob("*"):
            if not p.is_file():
                continue
            age = file_age_days(p, now)
            if age > 7:
                delete_file(p, summary, "outcomes>7d")
            else:
                mark_kept(summary, "recent", p)

    # bundles: older than 14d
    bundles = ARTIFACTS_DIR / "bundles"
    if bundles.exists():
        for p in bundles.rglob("*"):
            if not p.is_file():
                continue
            age = file_age_days(p, now)
            if age > 14:
                delete_file(p, summary, "bundles>14d")
            else:
                mark_kept(summary, "recent", p)

    # promotions: older than 14d
    promotions = ARTIFACTS_DIR / "promotions"
    if promotions.exists():
        for p in promotions.rglob("*"):
            if not p.is_file():
                continue
            age = file_age_days(p, now)
            if age > 14:
                delete_file(p, summary, "promotions>14d")
            else:
                mark_kept(summary, "recent", p)


def archive_old_logs(summary: CleanupSummary, now: datetime) -> None:
    if not LOGS_DIR.exists():
        return

    old_logs: dict[str, list[Path]] = defaultdict(list)
    for p in LOGS_DIR.rglob("*.ndjson"):
        if not p.is_file():
            continue
        if file_age_days(p, now) <= 30:
            mark_kept(summary, "recent", p)
            continue
        dt = datetime.fromtimestamp(p.stat().st_mtime, tz=timezone.utc)
        old_logs[dt.strftime("%Y-%m")].append(p)

    for ym, files in old_logs.items():
        zip_path = ARCHIVE_DIR / f"{ym}.zip"
        if not summary.dry_run:
            ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

        existing = set()
        if not summary.dry_run and zip_path.exists():
            try:
                with zipfile.ZipFile(zip_path, "r") as zf:
                    existing = set(zf.namelist())
            except Exception:
                existing = set()

        if not summary.dry_run:
            with zipfile.ZipFile(zip_path, "a", compression=zipfile.ZIP_DEFLATED) as zf:
                for p in files:
                    arcname = p.relative_to(LOGS_DIR).as_posix()
                    if arcname not in existing:
                        zf.write(p, arcname=arcname)

        for p in files:
            try:
                sz = p.stat().st_size
            except OSError:
                sz = 0
            summary.archived_logs += 1
            summary.archived_bytes += sz
            add_sample(summary.deleted_samples, f"logs>30d_archived: {p.as_posix()}")
            if not summary.dry_run:
                try:
                    p.unlink(missing_ok=True)
                    summary.deleted_files += 1
                    summary.deleted_bytes += sz
                except Exception:
                    pass


def delete_empty_artifact_dirs(summary: CleanupSummary) -> None:
    if not ARTIFACTS_DIR.exists():
        return

    dirs = sorted([d for d in ARTIFACTS_DIR.rglob("*") if d.is_dir()], key=lambda p: len(p.parts), reverse=True)
    for d in dirs:
        try:
            if any(d.iterdir()):
                continue
        except OSError:
            continue

        if not summary.dry_run:
            try:
                d.rmdir()
            except Exception:
                continue

        summary.deleted_empty_dirs += 1


def human_mb(nbytes: int) -> float:
    return round(nbytes / (1024 * 1024), 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="AutoQuant V2 data hygiene cleanup")
    ap.add_argument("--dry-run", action="store_true", help="Preview deletions without modifying files")
    args = ap.parse_args()

    now = utc_now()
    before = workspace_size_bytes(WORKSPACE_ROOT)
    promoted_keys = load_promoted_keys(DB_PATH)

    summary = CleanupSummary(dry_run=args.dry_run, before_bytes=before)

    cleanup_artifacts(summary, now, promoted_keys)
    archive_old_logs(summary, now)
    delete_empty_artifact_dirs(summary)

    after = workspace_size_bytes(WORKSPACE_ROOT)
    summary.after_bytes = after

    output = {
        "dry_run": summary.dry_run,
        "workspace": {
            "before_mb": human_mb(summary.before_bytes),
            "after_mb": human_mb(summary.after_bytes),
            "reclaimed_mb": human_mb(max(0, summary.before_bytes - summary.after_bytes)),
        },
        "deleted": {
            "files": summary.deleted_files,
            "mb": human_mb(summary.deleted_bytes),
            "empty_dirs": summary.deleted_empty_dirs,
        },
        "archived_logs": {
            "files": summary.archived_logs,
            "mb": human_mb(summary.archived_bytes),
            "archive_dir": ARCHIVE_DIR.as_posix(),
        },
        "kept": {
            "promoted_strategy_specs": summary.kept_promoted_strategy_specs,
            "recent_files": summary.kept_recent_files,
            "other": summary.kept_other,
        },
        "samples": {
            "deleted": summary.deleted_samples,
            "kept": summary.kept_samples,
        },
        "promoted_keys_loaded": len(promoted_keys),
    }

    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
