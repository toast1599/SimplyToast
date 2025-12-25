# src/app/startup/model.py

from pathlib import Path

from ..autostart import (
    scan_autostart,
    parse_desktop_file,
    set_enabled,
    delete_autostart,
)
from ..config import AUTOSTART_USER
from ..utils.fs import atomic_write


class AutostartEntry:
    def __init__(
        self,
        name: str,
        enabled: bool,
        filepath: Path,
        source: str,
        icon: str,
        comment: str,
        exec_cmd: str,
    ):
        self.name = name
        self.enabled = enabled
        self.filepath = Path(filepath)
        self.source = source  # "user" | "system"
        self.icon = icon
        self.comment = comment
        self.exec_cmd = exec_cmd


def _read_exec(filepath: Path) -> str:
    try:
        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                if line.startswith("Exec="):
                    return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return ""


def load_entries() -> list[AutostartEntry]:
    entries: list[AutostartEntry] = []

    for filepath, source in scan_autostart():
        try:
            name, comment, icon, enabled = parse_desktop_file(filepath)
        except Exception:
            name = Path(filepath).stem
            comment = ""
            icon = "application-x-executable"
            enabled = True

        exec_cmd = _read_exec(filepath)

        entries.append(
            AutostartEntry(
                name=name,
                enabled=enabled,
                filepath=filepath,
                source=source,
                icon=icon,
                comment=comment,
                exec_cmd=exec_cmd,
            )
        )

    return entries


def toggle_entry(entry: AutostartEntry, enabled: bool) -> None:
    if entry.source == "user":
        set_enabled(entry.filepath, enabled)
    else:
        AUTOSTART_USER.mkdir(parents=True, exist_ok=True)
        override = AUTOSTART_USER / entry.filepath.name

        if not enabled:
            atomic_write(override, "[Desktop Entry]\nHidden=true\n")
        else:
            override.unlink(missing_ok=True)

    entry.enabled = enabled


def delete_entry(entry: AutostartEntry) -> None:
    if entry.source == "system":
        return
    delete_autostart(entry.filepath)
