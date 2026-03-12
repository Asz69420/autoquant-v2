#!/usr/bin/env python3
import argparse
import json
import os
import sys
import urllib.request
import urllib.parse

ENV_PATH = r"C:\Users\Clamps\.openclaw\workspace-oragorn\.env"
OPENCLAW_CONFIG = r"C:\Users\Clamps\.openclaw\openclaw.json"
BANNERS_DIR = r"C:\Users\Clamps\.openclaw\workspace-oragorn\assets\banners"


BOT_TOKENS = {
    "oragorn": "ORAGORN_BOT_TOKEN",
    "quandalf": "QUANDALF_BOT_TOKEN",
    "frodex": "FRODEX_BOT_TOKEN",
    "logron": "LOGRON_BOT_TOKEN",
}


def load_env():
    env = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"')
    return env


def load_openclaw_config():
    try:
        with open(OPENCLAW_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def get_token(bot_name, env, cfg):
    accounts = (((cfg or {}).get("channels") or {}).get("telegram") or {}).get("accounts") or {}
    acct = accounts.get(bot_name) or accounts.get("default") or {}
    token = str(acct.get("botToken") or "").strip()
    if token:
        return token
    key = BOT_TOKENS.get(bot_name, "ORAGORN_BOT_TOKEN")
    token = env.get(key, "")
    if not token:
        token = env.get("ORAGORN_BOT_TOKEN", "")
    return token


def get_chat_id(channel_name, env, cfg):
    if channel_name == "log":
        return env.get("LOG_CHANNEL_ID", "-5038734156")
    if channel_name == "hades":
        return env.get("HADES_CHANNEL_ID", "-5133891354")
    return env.get("ASZ_CHAT_ID", "1801759510")


def send_message(text, chat_id, bot_token, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
    }).encode()
    try:
        req = urllib.request.Request(url, data=data)
        resp = urllib.request.urlopen(req, timeout=15)
        payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("ok", False), payload
    except Exception as e:
        print(f"Send failed: {e}", file=sys.stderr)
        return False, {"error": str(e)}


def send_photo(photo_path, caption, chat_id, bot_token, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    boundary = "----AutoQuantBoundary"
    body_parts = []
    for name, value in [("chat_id", chat_id), ("parse_mode", parse_mode), ("caption", caption)]:
        body_parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{value}".encode())
    with open(photo_path, "rb") as f:
        photo_data = f.read()
    body_parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{os.path.basename(photo_path)}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode() + photo_data
    )
    body_parts.append(f"--{boundary}--\r\n".encode())
    body = b"\r\n".join(body_parts)
    try:
        req = urllib.request.Request(url, data=body)
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        resp = urllib.request.urlopen(req, timeout=15)
        payload = json.loads(resp.read().decode("utf-8"))
        return payload.get("ok", False), payload
    except Exception as e:
        print(f"Photo send failed: {e}", file=sys.stderr)
        return False, {"error": str(e)}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--message", required=True)
    p.add_argument("--channel", choices=["dm", "log", "hades"], default="dm")
    p.add_argument("--bot", choices=["oragorn", "quandalf", "frodex", "logron"], default="oragorn")
    p.add_argument("--chat-id", default=None)
    p.add_argument("--photo", default=None)
    p.add_argument("--parse-mode", default="HTML")
    a = p.parse_args()

    env = load_env()
    cfg = load_openclaw_config()
    token = get_token(a.bot, env, cfg)
    if not token:
        print(json.dumps({"status": "error", "message": "No bot token found", "bot": a.bot}))
        return

    chat_id = a.chat_id or get_chat_id(a.channel, env, cfg)

    if a.photo and os.path.exists(a.photo):
        ok, payload = send_photo(a.photo, a.message, chat_id, token, a.parse_mode)
    else:
        ok, payload = send_message(a.message, chat_id, token, a.parse_mode)

    print(json.dumps({
        "status": "sent" if ok else "failed",
        "bot": a.bot,
        "channel": a.channel,
        "chat_id": str(chat_id),
        "ok": bool(ok),
        "telegram_result": payload,
    }))


if __name__ == "__main__":
    main()
