# src/app/startup/impact.py

from ..processes import (
    scan_processes,
    group_processes_by_exe,
    compute_startup_impact,
)
from .model import AutostartEntry


def compute_impacts(entries: list[AutostartEntry]) -> dict[AutostartEntry, float]:
    processes = scan_processes()
    proc_groups = group_processes_by_exe(processes)

    impacts: dict[AutostartEntry, float] = {}
    for entry in entries:
        impacts[entry] = compute_startup_impact(entry.exec_cmd, proc_groups)

    return impacts


def impact_level(impact: float, max_impact: float):
    if max_impact <= 0:
        return None, None

    ratio = impact / max_impact

    if ratio < 0.3:
        return "Low", "green"
    elif ratio < 0.7:
        return "Medium", "orange"
    else:
        return "High", "red"


def impact_sort_key(impact: float, max_impact: float) -> int:
    if max_impact <= 0:
        return 3

    ratio = impact / max_impact

    if ratio >= 0.7:
        return 0
    elif ratio >= 0.3:
        return 1
    elif ratio > 0:
        return 2
    else:
        return 3
