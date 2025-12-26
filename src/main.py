#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

import sys
from pathlib import Path

from app.utils.fs import atomic_write

# Ensure src/ is on PYTHONPATH when running directly
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.windows.main_window import ToastWindow

class SimplyToastApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="com.toast1599.SimplyToast")

    def do_activate(self):
        existing = self.props.active_window
        if existing is not None:
            existing.present()
            return

        win = ToastWindow()
        win.set_application(self)
        win.present()

def main():
    app = SimplyToastApp()
    app.run()
    
if __name__ == "__main__":
    main()