#!/usr/bin/env python3
"""Simple verification helper for delegated/background work artifacts."""
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--json-file", action="append", default=[])
    args = parser.parse_args()

    missing = []
    checked = []
    for item in args.file:
        path = Path(item)
        checked.append(str(path))
        if not path.exists():
            missing.append(str(path))
    for item in args.json_file:
        path = Path(item)
        checked.append(str(path))
        if not path.exists():
            missing.append(str(path))
            continue
        try:
            json.loads(path.read_text(encoding='utf-8'))
        except Exception:
            missing.append(str(path) + ' (invalid json)')

    payload = {
        "status": "ok" if not missing else "fail",
        "checked": checked,
        "missing_or_invalid": missing,
    }
    print(json.dumps(payload, indent=2))
    raise SystemExit(0 if not missing else 1)


if __name__ == '__main__':
    main()
