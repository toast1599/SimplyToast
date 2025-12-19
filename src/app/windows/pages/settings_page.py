from gi.repository import Gtk

from ...settings import save_settings
from ...config import REFRESH_INTERVAL_MS


class SettingsPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.parent = parent
        self.settings = parent.settings

        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        self._build_background_section()
        self._build_refresh_section()

    # ---------------- sections ----------------

    def _build_background_section(self):
        frame = Gtk.Frame(label="Background Monitoring")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.set_child(box)

        row = Gtk.Box(spacing=12)

        label = Gtk.Label(
            label="Pause monitoring when page is hidden",
            xalign=0
        )
        label.set_hexpand(True)

        switch = Gtk.Switch()
        switch.set_active(
            self.settings.get("pause_background_when_hidden", True)
        )
        switch.connect("state-set", self._on_pause_toggle)

        row.append(label)
        row.append(switch)
        box.append(row)

        self.append(frame)

    def _build_refresh_section(self):
        frame = Gtk.Frame(label="Performance")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        frame.set_child(box)

        row = Gtk.Box(spacing=12)

        label = Gtk.Label(
            label="Process refresh interval",
            xalign=0
        )
        label.set_hexpand(True)

        combo = Gtk.ComboBoxText()
        options = [2000, 3000, 5000]

        for ms in options:
            combo.append_text(f"{ms // 1000}s")

        current = self.settings.get(
            "refresh_interval_ms",
            REFRESH_INTERVAL_MS
        )

        if current in options:
            combo.set_active(options.index(current))
        else:
            combo.set_active(1)  # default 3s

        combo.connect("changed", self._on_refresh_changed)

        row.append(label)
        row.append(combo)
        box.append(row)

        self.append(frame)

    # ---------------- handlers ----------------

    def _on_pause_toggle(self, switch, state):
        self.settings["pause_background_when_hidden"] = bool(state)
        save_settings(self.settings)
        return False

    def _on_refresh_changed(self, combo):
        text = combo.get_active_text()
        if not text:
            return

        ms = int(text.replace("s", "")) * 1000
        self.settings["refresh_interval_ms"] = ms
        save_settings(self.settings)

    # ---------------- lifecycle ----------------

    def refresh(self):
        # nothing dynamic to refresh yet
        pass
