#!/usr/bin/env python3
"""Hard OS-level subprocess timeout wrapper.

Usage: python run_with_timeout.py <seconds> <command> [args...]

Runs <command> with a hard timeout. If the process exceeds <seconds>,
it is killed and this script exits with code 124 (matching GNU timeout).
"""
import subprocess
import sys

if len(sys.argv) < 3:
    print("Usage: run_with_timeout.py <seconds> <command> [args...]", file=sys.stderr)
    sys.exit(2)

timeout_s = int(sys.argv[1])
cmd = sys.argv[2:]

try:
    result = subprocess.run(cmd, timeout=timeout_s)
    sys.exit(result.returncode)
except subprocess.TimeoutExpired:
    print(f"[run_with_timeout] KILLED after {timeout_s}s: {' '.join(cmd[:3])}...", file=sys.stderr)
    sys.exit(124)
except FileNotFoundError:
    print(f"[run_with_timeout] command not found: {cmd[0]}", file=sys.stderr)
    sys.exit(127)
