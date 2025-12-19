from pathlib import Path
from .config import AUTOSTART_USER, AUTOSTART_SYSTEM

def scan_autostart():
    entries = []
    if AUTOSTART_USER.exists():
        for f in sorted(AUTOSTART_USER.glob("*.desktop")):
            entries.append((f, "user"))
    if AUTOSTART_SYSTEM.exists():
        for f in sorted(AUTOSTART_SYSTEM.glob("*.desktop")):
            entries.append((f, "system"))
    return entries


def parse_desktop_file(filepath):
    name = filepath.stem
    comment = ""
    icon = ""
    enabled = True

    try:
        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                if line.startswith("Name="):
                    name = line.split("=", 1)[1].strip()
                elif line.startswith("Comment="):
                    comment = line.split("=", 1)[1].strip()
                elif line.startswith("Icon="):
                    icon = line.split("=", 1)[1].strip()
                elif line.startswith("Hidden="):
                    enabled = not ("true" in line.lower())
    except Exception:
        pass

    return name, comment, icon, enabled


def set_enabled(filepath, enabled):
    try:
        lines = []
        found = False
        with open(filepath, "r", errors="ignore") as f:
            for line in f:
                if line.startswith("Hidden="):
                    found = True
                    line = "Hidden=false\n" if enabled else "Hidden=true\n"
                lines.append(line)
        if not found:
            lines.append("Hidden=false\n" if enabled else "Hidden=true\n")
        with open(filepath, "w") as f:
            f.writelines(lines)
    except Exception:
        pass


def delete_autostart(filepath):
    try:
        Path(filepath).unlink(missing_ok=True)
    except Exception:
        pass
