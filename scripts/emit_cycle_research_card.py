#!/usr/bin/env python3
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = r"C:\Users\Clamps\.openclaw\workspace-oragorn"
RUN_STATE = os.path.join(ROOT, "data", "state", "research_cycle_started_at.json")
STATUS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "current_cycle_status.json")
ORDERS_PATH = os.path.join(ROOT, "agents", "quandalf", "memory", "cycle_orders.json")
CURRENT_METRICS_PATH = os.path.join(ROOT, "data", "state", "current_cycle_metrics.json")
CARD_STATE_PATH = os.path.join(ROOT, "data", "state", "cycle_postprocess_card_state.json")
TG_SCRIPT = os.path.join(ROOT, "scripts", "tg_notify.py")
BANNER_PATH = os.path.join(ROOT, "assets", "banners", "cooking.jpg")


def format_elapsed(seconds):
    total = max(0, int(seconds or 0))
    mins, secs = divmod(total, 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m {secs}s"


def load_json(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def load_card_state():
    state = load_json(CARD_STATE_PATH, {})
    cards = state.get("cards") if isinstance(state, dict) else None
    if not isinstance(cards, dict):
        cards = {}
    return {"cards": cards}


def should_send_card(cycle_id, card_kind, card_text):
    fingerprint = hashlib.sha256(card_text.encode("utf-8")).hexdigest()
    cards = load_card_state().get("cards") or {}
    key = f"{int(cycle_id)}:{card_kind}"
    last = cards.get(key)
    if not isinstance(last, dict):
        return True, fingerprint
    if last.get("fingerprint") == fingerprint:
        return False, fingerprint
    return True, fingerprint


def remember_card_send(cycle_id, card_kind, card_text, fingerprint):
    os.makedirs(os.path.dirname(CARD_STATE_PATH), exist_ok=True)
    state = load_card_state()
    cards = state.get("cards") or {}
    cards[f"{int(cycle_id)}:{card_kind}"] = {
        "cycle_id": int(cycle_id),
        "kind": card_kind,
        "fingerprint": fingerprint,
        "sent_at_iso": datetime.now(timezone.utc).isoformat(),
        "preview": card_text.splitlines(),
    }
    with open(CARD_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump({"cards": cards}, f, indent=2)


def send_card(card_text):
    payload = f"<pre>{card_text}</pre>"
    cmd = [sys.executable, TG_SCRIPT, "--message", payload, "--channel", "log", "--bot", "logron"]
    if os.path.exists(BANNER_PATH):
        cmd.extend(["--photo", BANNER_PATH])
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    return proc.returncode == 0 and '"status": "sent"' in (proc.stdout or "")


def main():
    run_state = load_json(RUN_STATE, {})
    status = load_json(STATUS_PATH, {})
    orders = load_json(ORDERS_PATH, {})
    current_metrics = load_json(CURRENT_METRICS_PATH, {})

    cycle_id = int(run_state.get("cycle_id", 0) or orders.get("cycle_id", 0) or status.get("cycle_id", 0) or 0)
    if cycle_id <= 0:
        print(json.dumps({"status": "error", "reason": "missing_cycle_id"}))
        return 1

    mode = str(orders.get("mode") or status.get("mode") or current_metrics.get("mode") or "pending")
    direction = str(orders.get("research_direction") or status.get("research_direction") or current_metrics.get("research_direction") or "pending")
    target_asset = str(orders.get("target_asset") or status.get("target_asset") or current_metrics.get("target_asset") or "?")
    started_at_epoch = float(run_state.get("started_at_epoch", 0) or 0)
    elapsed_seconds = max(0.0, datetime.now(timezone.utc).timestamp() - started_at_epoch) if started_at_epoch > 0 else 0.0
    target_tf = str(orders.get("target_timeframe") or status.get("target_timeframe") or current_metrics.get("target_timeframe") or "?")
    min_specs = int(orders.get("minimum_spec_count", status.get("minimum_spec_count", current_metrics.get("minimum_spec_count", 0))) or 0)
    max_specs = int(orders.get("maximum_spec_count", status.get("maximum_spec_count", current_metrics.get("maximum_spec_count", 0))) or 0)
    concepts = (orders.get("exploration_targets") or status.get("exploration_targets") or current_metrics.get("exploration_targets") or {}).get("concepts") or []
    concept_preview = "; ".join(str(x) for x in concepts[:2]) if concepts else "Designing fresh batch from current orders."

    specs_written = int(current_metrics.get("specs_written", current_metrics.get("specs_produced", status.get("specs_produced", 0))) or 0)
    stage_kpis = current_metrics.get("stage_kpis") or {}
    train_runs = int(stage_kpis.get("train_runs", 0) or 0)
    test_runs = int(stage_kpis.get("test_runs", 0) or 0)
    integrity_skips = int(current_metrics.get("queue_integrity_skips", 0) or 0)
    train_failed = integrity_skips if integrity_skips > 0 else max(0, train_runs - test_runs)

    if train_runs == 0 and test_runs == 0 and specs_written == 0:
        note = f"This {mode} cycle has started on {target_asset}/{target_tf} and is still gathering fresh specs before any train/test executions complete."
    elif train_runs == 0 and test_runs == 0 and specs_written > 0:
        note = f"This {mode} cycle generated fresh work but no train/test executions have completed yet, so the batch is still gathering evidence before any strategy gets advanced or cut."
    else:
        note = f"This {mode} cycle is still in progress. Evidence collection is ahead of decision closure, so final pass / refine / abort counts are intentionally withheld until Quandalf finishes judging the batch."

    lines = [
        "🧪 Research",
        f"▶️ | {format_elapsed(elapsed_seconds)} | 🆔 {cycle_id}",
        "○────────────activity────────────",
        f"Generated: {specs_written}",
        f"Training: {train_runs}",
        f"Testing: {test_runs}",
        f"Failed: {train_failed}",
        "○─────────────note─────────────",
        note[:350],
    ]
    card_text = "\n".join(lines)
    should_send, fingerprint = should_send_card(cycle_id, "research", card_text)
    if not should_send:
        print(json.dumps({"status": "skipped", "reason": "duplicate", "cycle_id": cycle_id}))
        return 0
    sent = send_card(card_text)
    if not sent:
        print(json.dumps({"status": "error", "reason": "send_failed", "cycle_id": cycle_id}))
        return 1
    remember_card_send(cycle_id, "research", card_text, fingerprint)
    print(json.dumps({"status": "sent", "cycle_id": cycle_id, "kind": "research"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
