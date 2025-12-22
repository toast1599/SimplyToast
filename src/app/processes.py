# src/app/processes.py
import subprocess
from pathlib import Path
import shlex

from .log import get_logger

log = get_logger(__name__)


def scan_processes():
    """
    Returns processes as:
    (pid:int, name:str, cpu:float, mem:float, cmd:str)
    """
    try:
        out = subprocess.check_output(
            ["ps", "-eo", "pid,comm,%cpu,%mem,args", "--no-headers"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log.error("Failed to execute ps", exc_info=e)
        return []

    rows = []

    for line in out.splitlines():
        parts = line.strip().split(None, 4)
        if len(parts) < 5:
            continue

        try:
            pid = int(parts[0])
            name = parts[1]
            cpu = float(parts[2])
            mem = float(parts[3])
            cmd = parts[4]
        except Exception:
            # malformed line — ignore safely
            continue

        # Filter kernel threads ONLY (they look like "[kworker/0:1]")
        if cmd.startswith("[") and cmd.endswith("]"):
            continue

        rows.append((pid, name, cpu, mem, cmd))

    return rows


# --------------------------------------------------------------------
# Startup impact helpers
# --------------------------------------------------------------------

def exec_basename(exec_cmd: str) -> str:
    """
    Extract executable basename from Exec= command.
    """
    if not exec_cmd:
        return ""

    try:
        parts = shlex.split(exec_cmd)
    except Exception:
        parts = exec_cmd.split()

    if not parts:
        return ""

    return Path(parts[0]).name


def group_processes_by_exe(processes):
    """
    Groups processes by executable name.

    Returns:
    {
        "firefox": {
            "cpu": float,
            "mem": float,
            "count": int,
        },
        ...
    }
    """
    grouped = {}

    for _pid, _name, cpu, mem, cmd in processes:
        try:
            exe = Path(cmd.split()[0]).name if cmd else ""
        except Exception:
            continue

        if not exe:
            continue

        entry = grouped.setdefault(
            exe,
            {"cpu": 0.0, "mem": 0.0, "count": 0}
        )

        entry["cpu"] += cpu
        entry["mem"] += mem
        entry["count"] += 1

    return grouped


def compute_startup_impact(exec_cmd: str, proc_groups: dict) -> float:
    """
    Computes a raw startup impact score (not percent).

    The score is only meaningful relative to other startup apps.
    """
    exe = exec_basename(exec_cmd)
    if not exe:
        return 0.0

    data = proc_groups.get(exe)
    if not data:
        return 0.0

    cpu = data["cpu"]
    mem = data["mem"]
    count = data["count"]

    # Honest, explainable weighting
    impact = (
        cpu * 2.0 +
        mem * 1.0 +
        min(count, 5) * 1.5
    )

    return impact
