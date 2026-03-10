#!/usr/bin/env python3
"""Deterministically promote high-value Quandalf lessons from curated markdown sources."""
import argparse
import json
from pathlib import Path

from memory_governor import (
    ensure_structure,
    load_index,
    save_index,
    write_markdown,
    add_index_entry,
    make_entry_id,
    frontmatter_block,
)

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / "agents" / "quandalf" / "memory" / "cycle_summary_20260309.md"


def existing_titles(index_data):
    return {entry.get("title") for entry in index_data.get("entries", [])}


def promote_lesson(index_data, title, summary, details, source, tags, confidence="high", actor="quandalf", dry_run=False):
    if title in existing_titles(index_data):
        return {"status": "skipped_existing", "title": title}

    entry_id = make_entry_id()
    meta = {
        "id": entry_id,
        "bucket": "lessons",
        "title": title,
        "actor": actor,
        "source": source,
        "confidence": confidence,
        "tags": tags,
        "ts_iso": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }
    body = "\n\n".join([
        frontmatter_block(meta),
        "# {0}".format(title),
        "## Summary\n{0}".format(summary),
        "## Details\n{0}".format(details),
        "## Source\n{0}".format(source),
    ])

    if dry_run:
        return {"status": "dry_run", "title": title}

    path = write_markdown("lessons", title, body)
    add_index_entry(index_data, entry_id, "lessons", title, path, actor, source, tags, confidence, summary)
    return {"status": "promoted", "title": title, "path": str(path)}


def candidate_lessons_from_cycle_summary(text, source_label):
    candidates = []

    if "Funding gate non-selective" in text:
        candidates.append({
            "title": "Chronically Extreme Funding Thresholds Become Non-Selective",
            "summary": "A funding threshold loses edge when the asset lives beyond that threshold most of the time; the gate becomes always-on instead of selective.",
            "details": "Promoted from BABY-STOCH deep analysis. The summary explicitly notes that a -0.003 funding gate on an asset chronically near -0.005 becomes non-selective. Future funding-sensitive designs should calibrate thresholds to percentile context or combine them with additional state filters.",
            "source": source_label,
            "tags": ["quandalf", "funding", "selectivity", "entry-filter"],
        })

    if "Exit anchor too fast" in text:
        candidates.append({
            "title": "Fast Exit Anchors Can Destroy Trade Economics",
            "summary": "Overly fast exit anchors can cut winners early and let fees absorb the remaining gross edge.",
            "details": "Promoted from BABY-STOCH deep analysis. Quandalf identified TEMA_8 as too twitchy, leading to premature exits before targets could be realized. The same analysis showed cost drag consuming nearly all gross profit. Future intraday designs should balance responsiveness with hold quality and fee-aware exit logic.",
            "source": source_label,
            "tags": ["quandalf", "exits", "cost-drag", "trade-economics"],
        })

    if "Decision: ABANDON this branch" in text:
        candidates.append({
            "title": "Abandon Branches With Multiple Structural Failures",
            "summary": "When a variant fails on several structural dimensions at once, it should usually be killed rather than iterated blindly.",
            "details": "Promoted from BABY-STOCH deep analysis. Quandalf explicitly abandoned the branch because it required simultaneous fixes for regime exposure, funding selectivity, and exit logic. This becomes a reusable iteration rule: kill multi-failure branches quickly and spend budget where edge already converges.",
            "source": source_label,
            "tags": ["quandalf", "iteration-discipline", "branch-killing", "resource-allocation"],
        })

    if "Recommendation: **Focus iteration budget on AXS + VVV**" in text or "Focus iteration budget on AXS + VVV" in text:
        candidates.append({
            "title": "Iteration Budget Should Favor Converging Families Before Noisy Exploration",
            "summary": "When proven families show improving trajectories, iteration budget should prioritize them before returning to noisier exploratory branches.",
            "details": "Promoted from cycle summary recommendations. The BABY exploration confirmed signal but high execution difficulty, while AXS and VVV were already showing clearer positive trajectories. This becomes a portfolio-level lesson for future cycle planning and budget allocation.",
            "source": source_label,
            "tags": ["quandalf", "portfolio-allocation", "iteration-budget", "family-prioritization"],
        })

    return candidates


def main():
    parser = argparse.ArgumentParser(description="Backfill Quandalf lessons into shared intelligence")
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        raise SystemExit("Source file not found: {0}".format(source_path))

    ensure_structure()
    index_data = load_index()
    text = source_path.read_text(encoding="utf-8")
    source_label = str(source_path.relative_to(ROOT))

    results = []
    for candidate in candidate_lessons_from_cycle_summary(text, source_label):
        results.append(
            promote_lesson(
                index_data=index_data,
                title=candidate["title"],
                summary=candidate["summary"],
                details=candidate["details"],
                source=candidate["source"],
                tags=candidate["tags"],
                dry_run=args.dry_run,
            )
        )

    if not args.dry_run:
        save_index(index_data)

    promoted = [r for r in results if r["status"] == "promoted"]
    skipped = [r for r in results if r["status"] == "skipped_existing"]
    print(json.dumps({
        "status": "ok",
        "source": source_label,
        "promoted": promoted,
        "skipped_existing": skipped,
        "count_promoted": len(promoted),
        "count_skipped": len(skipped),
    }, indent=2))


if __name__ == "__main__":
    main()
