#!/usr/bin/env python3
"""Hard OS-level subprocess timeout wrapper.

Usage: python run_with_timeout.py <seconds> <command> [args...]

Runs <command> with a hard timeout. If the process exceeds <seconds>,
it kills the full process tree and exits with code 124 (matching GNU timeout).
"""
import os
import signal
import subprocess
import sys

if len(sys.argv) < 3:
    print("Usage: run_with_timeout.py <seconds> <command> [args...]", file=sys.stderr)
    sys.exit(2)

timeout_s = int(sys.argv[1])
cmd = sys.argv[2:]


def kill_process_tree(proc: subprocess.Popen):
    if proc.poll() is not None:
        return
    try:
        if os.name == 'nt':
            subprocess.run(
                ['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
            )
        else:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


creationflags = 0
popen_kwargs = {}
if os.name == 'nt':
    creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
else:
    popen_kwargs['start_new_session'] = True

try:
    proc = subprocess.Popen(cmd, creationflags=creationflags, **popen_kwargs)
    try:
        result = proc.wait(timeout=timeout_s)
        sys.exit(result)
    except subprocess.TimeoutExpired:
        kill_process_tree(proc)
        print(f"[run_with_timeout] KILLED TREE after {timeout_s}s: {' '.join(cmd[:3])}...", file=sys.stderr)
        sys.exit(124)
except FileNotFoundError:
    print(f"[run_with_timeout] command not found: {cmd[0]}", file=sys.stderr)
    sys.exit(127)
