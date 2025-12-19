import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
import webbrowser

class HelpWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="Help & Support")
        self.set_default_size(300, 200)
        self.set_transient_for(parent)
        self.set_modal(True)

        # Main container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        self.set_child(box)

        lbl = Gtk.Label()
        lbl.set_markup("<big><b>SimplyToast Support</b></big>")
        lbl.set_xalign(0.0)
        box.append(lbl)

        btn_discord = Gtk.Button(label="Join Discord Server")
        btn_discord.connect("clicked", self.open_discord)
        box.append(btn_discord)

        btn_github = Gtk.Button(label="Open GitHub Repo")
        btn_github.connect("clicked", self.open_github)
        box.append(btn_github)

        self.present()

    def open_discord(self, _btn):
        webbrowser.open("https://discord.gg/yX92vzqvwd")

    def open_github(self, _btn):
        webbrowser.open("https://github.com/toast1599/SimplyToast")
