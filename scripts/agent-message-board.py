#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone

BOARD_PATH = r"C:\Users\Clamps\.openclaw\workspace-oragorn\data\state\agent_messages.json"


def load_board():
    if os.path.exists(BOARD_PATH):
        with open(BOARD_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"messages": []}


def save_board(board):
    os.makedirs(os.path.dirname(BOARD_PATH), exist_ok=True)
    with open(BOARD_PATH, "w", encoding="utf-8") as f:
        json.dump(board, f, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--post", action="store_true", help="Post a new message")
    p.add_argument("--read", action="store_true", help="Read recent messages")
    p.add_argument("--from-agent", default="unknown")
    p.add_argument("--to-agent", default="all")
    p.add_argument("--message", default="")
    p.add_argument(
        "--type",
        default="note",
        choices=["note", "suggestion", "complaint", "observation", "request"],
    )
    p.add_argument("--limit", type=int, default=10)
    p.add_argument("--unread-only", action="store_true")
    a = p.parse_args()

    board = load_board()

    if a.post:
        if not a.message:
            print(json.dumps({"status": "error", "message": "No message provided"}))
            return
        entry = {
            "ts_iso": datetime.now(timezone.utc).isoformat(),
            "from": a.from_agent,
            "to": a.to_agent,
            "type": a.type,
            "message": a.message,
            "read_by": [],
        }
        board.setdefault("messages", []).append(entry)
        if len(board["messages"]) > 100:
            board["messages"] = board["messages"][-100:]
        save_board(board)
        print(json.dumps({"status": "posted", "from": a.from_agent, "to": a.to_agent}))
    elif a.read:
        msgs = board.get("messages", [])
        if a.unread_only:
            msgs = [m for m in msgs if a.from_agent not in m.get("read_by", [])]
        if a.to_agent != "all":
            msgs = [m for m in msgs if m.get("to") in [a.to_agent, "all"]]
        msgs = msgs[-a.limit :]
        print(json.dumps({"status": "ok", "count": len(msgs), "messages": msgs}, indent=2))
    else:
        print(json.dumps({"status": "error", "message": "Use --post or --read"}))


if __name__ == "__main__":
    main()
