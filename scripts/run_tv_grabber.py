#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(r"C:\Users\Clamps\.openclaw\workspace-oragorn")
TV_WORKER = ROOT / "scripts" / "tv_catalog_worker.py"


def main():
    cmd = [sys.executable, str(TV_WORKER), "--max-new-indicators-per-run", "1"]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT), timeout=300)
        if p.returncode != 0:
            print(json.dumps({"status": "error", "returncode": p.returncode, "stderr": (p.stderr or "")[:1000]}))
            return p.returncode

        out = (p.stdout or "").strip()
        if out:
            try:
                parsed = json.loads(out)
                parsed["status"] = "ok"
                print(json.dumps(parsed))
            except Exception:
                print(json.dumps({"status": "ok", "stdout": out[:2000]}))
        else:
            print(json.dumps({"status": "ok", "stdout": ""}))
        return 0
    except Exception as e:
        print(json.dumps({"status": "error", "error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
