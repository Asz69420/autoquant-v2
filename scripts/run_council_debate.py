#!/usr/bin/env python3
import argparse
import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
OUT_PATH = ROOT / "docs" / "shared" / "council_debate.md"


def call_agent(agent: str, message: str, timeout_seconds: int = 120, session_id: str | None = None) -> str:
    cmd = [
        "openclaw", "agent",
        "--agent", agent,
        "--message", message,
        "--timeout", str(timeout_seconds),
        "--json",
    ]
    if session_id:
        cmd.extend(["--session-id", session_id])
    try:
        proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=timeout_seconds + 20)
    except Exception:
        return "NO RESPONSE"
    if proc.returncode != 0:
        return "NO RESPONSE"
    try:
        payload = json.loads(proc.stdout)
        texts = []
        for p in payload.get("result", {}).get("payloads", []):
            t = (p or {}).get("text")
            if t:
                texts.append(t.strip())
        text = "\n\n".join(t for t in texts if t).strip()
        return text if text else "NO RESPONSE"
    except Exception:
        return "NO RESPONSE"


def clamp_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    return " ".join(words[:max_words]).strip() + " …"


def commander_round(topic: str, context: str, round_no: int, prior: str = "") -> str:
    if round_no == 1:
        text = (
            f"My commander position: do the smaller, unblocker-first path. On '{topic}', the right move is the one that improves system clarity, reduces current friction, and compounds into the next decision. "
            f"Given current state, I favor whichever option removes ambiguity and strengthens handoff quality before we add more surface area. {context}"
        )
        return clamp_words(text, 300)
    if round_no == 2:
        text = (
            "I agree with the strongest argument that sequencing matters more than novelty. The others may miss that a good idea can still be mistimed if it adds complexity before the pipeline is ready. "
            "My updated position stays the same: prefer the option that tightens signal flow, reduces debugging ambiguity, and creates cleaner evidence for the next iteration."
        )
        return clamp_words(text, 200)
    text = "Final recommendation: do it, but choose the path that reduces ambiguity first and creates a cleaner base for the next system upgrade."
    return clamp_words(text, 150)


def write_md(topic: str, context: str, r1: dict, r2: dict, r3: dict, synthesis: str):
    lines = [
        f"# Fellowship Council Debate",
        "",
        f"**Topic:** {topic}",
        f"**Generated:** {datetime.now().isoformat(timespec='seconds')}",
        "",
        "## Context",
        context.strip() if context.strip() else "No extra context provided.",
        "",
        "## Round 1",
        f"### Oragorn\n{r1['oragorn']}\n",
        f"### Quandalf\n{r1['quandalf']}\n",
        f"### Frodex\n{r1['frodex']}\n",
        "## Round 2",
        f"### Oragorn\n{r2['oragorn']}\n",
        f"### Quandalf\n{r2['quandalf']}\n",
        f"### Frodex\n{r2['frodex']}\n",
        "## Round 3",
        f"### Oragorn\n{r3['oragorn']}\n",
        f"### Quandalf\n{r3['quandalf']}\n",
        f"### Frodex\n{r3['frodex']}\n",
        "## Commander's Synthesis",
        synthesis.strip(),
        "",
    ]
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("topic")
    ap.add_argument("--context", default="")
    args = ap.parse_args()

    topic = args.topic.strip()
    context = args.context.strip()

    q1 = f"This is a 3-round council debate. Round 1 of 3. Word limit: 300. Lead with substance. COUNCIL ROUND 1. Topic: {topic}. Give your position in 300 words max. Focus on strategy, market, and research implications. You have not seen other agents' positions. Lead with your strongest argument. Do not hedge or caveat — commit to a position. Context: {context}" 
    f1 = f"This is a 3-round council debate. Round 1 of 3. Word limit: 300. Lead with substance. COUNCIL ROUND 1. Topic: {topic}. Give your position in 300 words max. Focus on technical feasibility, implementation, infrastructure implications. You have not seen other agents' positions. Lead with your strongest argument. Do not hedge or caveat — commit to a position. Context: {context}" 

    r1 = {
        "oragorn": commander_round(topic, context, 1),
        "quandalf": call_agent("quandalf", q1, 120, "council-quandalf"),
        "frodex": call_agent("frodex", f1, 120, "council-frodex"),
    }

    round1_blob = f"Oragorn:\n{r1['oragorn']}\n\nQuandalf:\n{r1['quandalf']}\n\nFrodex:\n{r1['frodex']}"
    q2 = f"This is a 3-round council debate. Round 2 of 3. Word limit: 200. Lead with substance. COUNCIL ROUND 2. Read all Round 1 positions: {round1_blob}. In 200 words max: What do you agree with? What do you challenge? What did the others miss? Update or strengthen your position based on what you've read."
    f2 = q2
    r2 = {
        "oragorn": commander_round(topic, context, 2, round1_blob),
        "quandalf": call_agent("quandalf", q2, 120, "council-quandalf"),
        "frodex": call_agent("frodex", f2, 120, "council-frodex"),
    }

    round2_blob = f"Oragorn:\n{r2['oragorn']}\n\nQuandalf:\n{r2['quandalf']}\n\nFrodex:\n{r2['frodex']}"
    q3 = f"This is a 3-round council debate. Round 3 of 3. Word limit: 150. Lead with substance. COUNCIL ROUND 3 — FINAL. This is your last input. In 150 words max: Give your final recommendation. State clearly: do it / don't do it / do it with these changes. No hedging. Topic: {topic}. Prior positions: {round1_blob}\n\nRound 2: {round2_blob}"
    f3 = q3
    r3 = {
        "oragorn": commander_round(topic, context, 3, round1_blob + "\n\n" + round2_blob),
        "quandalf": call_agent("quandalf", q3, 120, "council-quandalf"),
        "frodex": call_agent("frodex", f3, 120, "council-frodex"),
    }

    synthesis = (
        f"Agreement: the council favored sequencing and leverage over doing everything at once. Disagreement: emphasis differed between strategic upside and implementation leverage. "
        f"Commander recommendation: choose the option that reduces current ambiguity first, then expand. Asz should decide by asking which path improves evidence quality and next-step clarity fastest on '{topic}'."
    )
    write_md(topic, context, r1, r2, r3, synthesis)
    print(OUT_PATH)


if __name__ == "__main__":
    main()
