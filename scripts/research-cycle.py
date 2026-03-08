#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
PY = sys.executable
SKILLS_DIR = Path.home() / ".openclaw" / "skills"
BRIEFING_PATH = ROOT / "agents" / "quandalf" / "memory" / "briefing_packet.json"
THROTTLE_STATE_PATH = ROOT / "data" / "state" / "throttle_state.json"
STRATEGY_SPECS_DIR = ROOT / "artifacts" / "strategy_specs"
BACKTESTER_PATH = Path(r"C:\Users\Clamps\.openclaw\skills\autoquant-backtester\engine.py")


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


def _load_throttle_mode() -> str:
    try:
        if not THROTTLE_STATE_PATH.exists():
            return "normal"
        obj = json.loads(THROTTLE_STATE_PATH.read_text(encoding="utf-8-sig"))
        return str(obj.get("mode") or "normal").strip().lower()
    except Exception:
        return "normal"


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


def _safe_first(items):
    if isinstance(items, list) and items:
        return items[0]
    return None


def _build_briefing_summary(packet: dict) -> str:
    lb = packet.get("leaderboard", {})
    lessons = packet.get("recent_lessons", {})
    digest = packet.get("research_digest", {})
    scan = packet.get("market_scan", {})
    funding = packet.get("funding_rates", {})

    lb_count = _count_items(lb, ["strategies", "items", "rows", "data"])
    lesson_count = _count_items(lessons, ["lessons", "items", "rows", "data"])
    research_count = _count_items(digest, ["items", "entries", "results", "data"])
    scan_count = _count_items(scan, ["top_opportunities", "opportunities", "items", "data"])
    funding_count = _count_items(funding, ["funding", "items", "rows", "data"])

    top_opportunity = None
    if isinstance(scan, dict):
        top = _safe_first(scan.get("top_opportunities"))
        if isinstance(top, dict):
            top_opportunity = top.get("asset") or top.get("symbol") or top.get("name")

    top_leader = None
    if isinstance(lb, dict):
        lead = _safe_first(lb.get("strategies"))
        if isinstance(lead, dict):
            top_leader = lead.get("spec_id") or lead.get("id") or lead.get("name")

    parts = [
        f"Cycle: {packet.get('cycle_id', 'unknown')}",
        f"Leaderboard entries: {lb_count}",
        f"Top leaderboard strategy: {top_leader or 'n/a'}",
        f"Recent lessons: {lesson_count}",
        f"Unprocessed research items: {research_count}",
        f"Market scan opportunities: {scan_count}",
        f"Top market opportunity: {top_opportunity or 'n/a'}",
        f"Funding rows: {funding_count}",
    ]
    return "\n".join(parts)


def _build_quandalf_prompt(packet: dict) -> str:
    schema_template = {
        "schema_version": "1.0",
        "id": "strategy_name_YYYYMMDD",
        "ts_iso": "...",
        "thesis_id": "...",
        "name": "...",
        "version": "1.0",
        "asset": "ETH",
        "timeframe": "4h",
        "indicators": ["EMA_9", "EMA_21", "RSI_14"],
        "entry_rules": {"long": ["..."], "short": ["..."]},
        "exit_rules": {"long": ["..."], "short": ["..."]},
        "position_sizing": {"risk_per_trade_pct": 0.01},
        "regime_filter": None,
        "variants": [
            {
                "name": "variant_name",
                "template_name": "ema_crossover",
                "parameters": [],
                "risk_policy": {
                    "stop_type": "atr",
                    "stop_atr_mult": 2.0,
                    "tp_type": "atr",
                    "tp_atr_mult": 3.0,
                    "risk_per_trade_pct": 0.01,
                },
                "execution_policy": {
                    "entry_fill": "bar_close",
                    "tie_break": "worst_case",
                    "allow_reverse": True,
                },
                "risk_rules": [],
            }
        ],
        "complexity_score": 1.0,
        "status": "draft",
        "source": "claude-advisor",
    }

    briefing_summary = _build_briefing_summary(packet)

    return (
        "Read this briefing. Design ONE new strategy or refine an existing one. "
        "Return a complete strategy_spec JSON only.\n\n"
        "Briefing summary:\n"
        f"{briefing_summary}\n\n"
        "Required strategy_spec format:\n"
        f"{json.dumps(schema_template, indent=2)}\n\n"
        "Requirements:\n"
        "- Return valid JSON object\n"
        "- Include at least one variant\n"
        "- Set source = claude-advisor\n"
        "- Prefer one asset/timeframe supported by current market scan\n"
    )


def _extract_json_from_text(text: str):
    if not text:
        return None

    # 1) whole output is JSON
    try:
        obj = json.loads(text.strip())
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # 2) fenced blocks
    for m in re.finditer(r"```(?:json)?\s*([\s\S]*?)```", text, flags=re.IGNORECASE):
        chunk = m.group(1).strip()
        try:
            obj = json.loads(chunk)
            if isinstance(obj, dict):
                return obj
        except Exception:
            continue

    # 3) balanced braces scan
    s = text
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        depth = 0
        in_str = False
        esc = False
        for j in range(i, len(s)):
            c = s[j]
            if esc:
                esc = False
                continue
            if c == "\\":
                esc = True
                continue
            if c == '"':
                in_str = not in_str
                continue
            if in_str:
                continue
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    chunk = s[i : j + 1]
                    try:
                        obj = json.loads(chunk)
                        if isinstance(obj, dict):
                            return obj
                    except Exception:
                        break
    return None


def _valid_spec(spec: dict) -> bool:
    if not isinstance(spec, dict):
        return False
    for k in ("name", "asset", "timeframe", "variants"):
        if k not in spec:
            return False
    if not isinstance(spec.get("variants"), list) or not spec.get("variants"):
        return False
    first = spec["variants"][0]
    if not isinstance(first, dict) or not first.get("name"):
        return False
    return True


def _save_spec(spec: dict) -> Path:
    STRATEGY_SPECS_DIR.mkdir(parents=True, exist_ok=True)
    sid = str(spec.get("id") or f"generated_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}")
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", sid)
    path = STRATEGY_SPECS_DIR / f"{safe}.strategy_spec.json"
    path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return path


def _run_backtest(spec: dict, spec_path: Path):
    try:
        first_variant = spec.get("variants", [])[0]
        variant_name = str(first_variant.get("name"))
        asset = str(spec.get("asset"))
        timeframe = str(spec.get("timeframe"))
        cmd = [
            PY,
            str(BACKTESTER_PATH),
            "--asset",
            asset,
            "--tf",
            timeframe,
            "--strategy-spec",
            str(spec_path),
            "--variant",
            variant_name,
        ]
        p = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = (p.stdout or "").strip()
        parsed = _extract_json_from_text(out)
        backtest_result_id = None
        if isinstance(parsed, dict):
            bt_path = parsed.get("backtest_result")
            if isinstance(bt_path, str) and bt_path:
                backtest_result_id = Path(bt_path).name.replace(".backtest_result.json", "")
        return {
            "ok": True,
            "stdout": out,
            "stderr": (p.stderr or "").strip(),
            "backtest_result_id": backtest_result_id,
        }
    except subprocess.CalledProcessError as e:
        return {
            "ok": False,
            "stdout": (e.stdout or "").strip(),
            "stderr": (e.stderr or "").strip(),
            "backtest_result_id": None,
        }
    except Exception as e:
        return {"ok": False, "stdout": "", "stderr": str(e), "backtest_result_id": None}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--briefing-only", action="store_true", help="Run only Phase 1 briefing build")
    ap.add_argument("--full-cycle", action="store_true", help="Run Phase 1 + Phase 2 (default)")
    args = ap.parse_args()

    run_full_cycle = True
    if args.briefing_only:
        run_full_cycle = False
    elif args.full_cycle:
        run_full_cycle = True

    mode = _load_throttle_mode()

    # Phase 1: Build briefing packet
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

    phase1_summary = {
        "status": "briefing_ready",
        "cycle_id": cycle_id,
        "briefing_path": str(BRIEFING_PATH),
        "leaderboard_count": _count_items(leaderboard, ["strategies", "items", "rows", "data"]),
        "lesson_count": _count_items(lessons, ["lessons", "items", "rows", "data"]),
        "research_count": _count_items(digest, ["items", "entries", "results", "data"]),
        "scan_count": _count_items(scan, ["top_opportunities", "opportunities", "items", "data"]),
        "top_opportunity": top_opportunity,
    }

    if not run_full_cycle:
        print(json.dumps(phase1_summary, indent=2))
        return 0

    if mode == "paused":
        print(json.dumps({
            "status": "paused",
            "reason": "throttle_paused",
            "cycle_id": cycle_id,
            "briefing_path": str(BRIEFING_PATH),
        }, indent=2))
        return 0

    # Phase 2: Deliver briefing to Quandalf, parse strategy, run backtest
    briefing_delivered = False
    strategy_received = False
    strategy_name = None
    backtest_ran = False
    backtest_result_id = None

    try:
        packet_loaded = json.loads(BRIEFING_PATH.read_text(encoding="utf-8-sig"))
        prompt_text = _build_quandalf_prompt(packet_loaded)

        send_cmd = ["openclaw", "agent-send", "quandalf", "--message", prompt_text]
        send_res = subprocess.run(send_cmd, capture_output=True, text=True)
        briefing_delivered = send_res.returncode == 0

        response_text = (send_res.stdout or "")
        response_json = _extract_json_from_text(response_text)
        if _valid_spec(response_json or {}):
            strategy_received = True
            strategy_name = str(response_json.get("name") or "")
            spec_path = _save_spec(response_json)

            bt = _run_backtest(response_json, spec_path)
            backtest_ran = bool(bt.get("ok"))
            backtest_result_id = bt.get("backtest_result_id")

    except Exception:
        # keep briefing packet as durable output regardless of phase 2 failure
        pass

    final_summary = {
        "status": "cycle_complete",
        "cycle_id": cycle_id,
        "briefing_delivered": briefing_delivered,
        "strategy_received": strategy_received,
        "strategy_name": strategy_name,
        "backtest_ran": backtest_ran,
        "backtest_result_id": backtest_result_id,
    }
    print(json.dumps(final_summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
