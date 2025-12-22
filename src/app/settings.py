import json
from .config import CONFIG_DIR, SETTINGS_FILE, DEFAULT_THEME


def load_settings():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if not SETTINGS_FILE.exists():
        defaults = {"theme": DEFAULT_THEME}
        save_settings(defaults)
        return defaults

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        defaults = {"theme": DEFAULT_THEME}
        save_settings(defaults)
        return defaults


def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
