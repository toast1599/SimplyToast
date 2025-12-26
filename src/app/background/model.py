# app/background/model.py

import os
import signal
from pathlib import Path

from app.processes import scan_processes


def load_processes():
    rows = []

    for p in scan_processes():
        try:
            pid = int(p[0])
            comm = str(p[1])
            cpu = float(p[2])
            mem = float(p[3])
            cmd = str(p[4])
        except Exception:
            continue

        # skip kernel threads
        if cmd.startswith("[") and cmd.endswith("]"):
            continue

        name = _display_name(comm, cmd)
        rows.append((pid, name, cpu, mem, cmd))

    # sort by CPU usage (desc)
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows


def kill_process(pid: int):
    try:
        os.kill(pid, signal.SIGTERM)
    except PermissionError:
        log.warning(f"No permission to kill PID {pid}")
    except ProcessLookupError:
        log.info(f"PID {pid} already exited")

def _display_name(comm, cmd):
    if cmd:
        exe = cmd.split()[0]
        if exe.startswith("/"):
            return Path(exe).name
        return exe
    return comm
