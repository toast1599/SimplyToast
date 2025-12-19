import json
from .config import CONFIG_DIR, SETTINGS_FILE, DEFAULT_THEME

def load_settings():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        save_settings({"theme": DEFAULT_THEME})
        return {"theme": DEFAULT_THEME}

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"theme": DEFAULT_THEME}


def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)
