# src/app/processes.py
import subprocess
from pathlib import Path
import shlex
import json

from .log import get_logger

log = get_logger(__name__)

from pathlib import Path
import ctypes

ROOT = Path(__file__).resolve().parent.parent
LIB_PATH = ROOT / "libsimplytoast_processes.so"

if not LIB_PATH.exists():
    raise RuntimeError(f"Missing native library: {LIB_PATH}")
import os
_lib = ctypes.CDLL(str(LIB_PATH), mode=os.RTLD_NOW)

def scan_processes():
    """
    Returns processes as:
    (pid:int, name:str, cpu:float, mem:float, cmd:str)
    """
    try:
        out = subprocess.check_output(
            ["simplytoast-processes", "scan"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        log.error("Failed to execute simplytoast-processes", exc_info=e)
        return []

    try:
        rows = json.loads(out)
    except Exception as e:
        log.error("Failed to parse process JSON", exc_info=e)
        return []

    return [
        (int(pid), str(name), float(cpu), float(mem), str(cmd))
        for pid, name, cpu, mem, cmd in rows
    ]


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
