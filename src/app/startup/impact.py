# src/app/startup/impact.py

import json
import subprocess
from pathlib import Path

from ..processes import (
    scan_processes,
    group_processes_by_exe,
)
from .model import AutostartEntry


from shutil import which

_IMPACT_BIN = (
    which("simplytoast-core")
    or str(
        Path(__file__).resolve()
        .parents[3]
        / "tools"
        / "simplytoast-core"
        / "target"
        / "debug"
        / "simplytoast-core"
    )
)

def _run_impact_engine(payload: dict) -> dict:
    proc = subprocess.run(
        [_IMPACT_BIN, "impact"],
            input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=True,
    )

    if proc.stderr:
        print("RUST STDERR:", proc.stderr, flush=True)

    if proc.returncode != 0:
        return {}

    return json.loads(proc.stdout)

def compute_impacts(entries: list[AutostartEntry]) -> dict[AutostartEntry, float]:
    processes = scan_processes()
    proc_groups = group_processes_by_exe(processes)

    payload = {
        "process_groups": proc_groups,
        "autostart": [
            {
                "id": str(entry.filepath.name),
                "exec": entry.exec_cmd,
            }
            for entry in entries
        ],
    }

    results = _run_impact_engine(payload)

    impacts: dict[AutostartEntry, float] = {}

    for entry in entries:
        key = str(entry.filepath.name)
        data = results.get(key)
        impacts[entry] = data["impact"] if data else 0.0

    # cache full results for helpers
    _CACHE.clear()
    _CACHE.update(results)

    return impacts


# --------------------------------------------------
# Compatibility helpers (logic-free)
# --------------------------------------------------

_CACHE: dict[str, dict] = {}

def impact_level(impact: float, max_impact: float, entry=None):
    if entry:
        data = _CACHE.get(entry.filepath.name)
        if data:
            return data["label"], data["color"]
    return None, None


def impact_sort_key(impact: float, max_impact: float, entry=None) -> int:
    if entry:
        data = _CACHE.get(entry.filepath.name)
        if data:
            return data["sort_key"]
    return 3
