#!/usr/bin/env python3
import argparse
import json
import os
import urllib.parse
import urllib.request


def send_telegram(text, chat_id=None, bot_token=None, parse_mode="HTML"):
    if not bot_token:
        env_path = r"C:\Users\Clamps\.openclaw\workspace\.env"
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("TELEGRAM_BOT_TOKEN="):
                        bot_token = line.strip().split("=", 1)[1].strip().strip('"')
                        break

    if not chat_id:
        chat_id = "1801759510"

    if not bot_token:
        print(json.dumps({"status": "error", "message": "No bot token found"}))
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
    ).encode()

    try:
        req = urllib.request.Request(url, data=data)
        resp = urllib.request.urlopen(req, timeout=10)
        result = json.loads(resp.read().decode("utf-8"))
        return result.get("ok", False)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        return False


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--message", required=True)
    p.add_argument("--chat-id", default="1801759510")
    p.add_argument("--channel", choices=["dm", "log"], default="dm")
    p.add_argument("--parse-mode", default="HTML")
    a = p.parse_args()

    cid = a.chat_id
    if a.channel == "log":
        cid = "-5038734156"

    ok = send_telegram(a.message, chat_id=cid, parse_mode=a.parse_mode)
    print(json.dumps({"status": "sent" if ok else "failed"}))


if __name__ == "__main__":
    main()
