from pathlib import Path
import os

# ---------- Constants ----------
CONFIG_DIR = Path.home() / ".config" / "simplytoast"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
CSS_DIR = Path(__file__).resolve().parent.parent / "data" / "css"
AUTOSTART_USER = Path.home() / ".config" / "autostart"
AUTOSTART_SYSTEM = Path("/etc/xdg/autostart")
REFRESH_INTERVAL_MS = 3000
DEFAULT_THEME = "dark"
