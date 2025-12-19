import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from version import VERSION

class AboutPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=20)

        self.parent = parent

        self.set_margin_top(40)
        self.set_margin_bottom(40)
        self.set_margin_start(40)
        self.set_margin_end(40)

        # App icon placeholder (we will replace this later)
        icon = Gtk.Image.new_from_icon_name("com.toast1599.SimplyToast")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)

        # App name
        title = Gtk.Label()
        title.set_markup("<span size='xx-large'><b>SimplyToast</b></span>")
        title.set_halign(Gtk.Align.CENTER)

        # Version placeholder (replace later with real value)
        version = Gtk.Label(label=f"Version: {VERSION}")
        version.set_halign(Gtk.Align.CENTER)

        # Author / credits
        author = Gtk.Label(label="Created by: toast1599")
        author.set_halign(Gtk.Align.CENTER)

        # Optional description
        desc = Gtk.Label(
            label="A clean and modern utility for managing autostart apps and background tasks."
        )
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_halign(Gtk.Align.CENTER)

        # Append widgets
        self.append(icon)
        self.append(title)
        self.append(version)
        self.append(author)
        self.append(desc)

    def refresh(self):
        pass  # Nothing to refresh right now
