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

        # App icon
        icon = Gtk.Image.new_from_icon_name("com.toast1599.SimplyToast")
        icon.set_pixel_size(96)
        icon.set_halign(Gtk.Align.CENTER)

        # App name
        title = Gtk.Label()
        title.set_markup("<span size='xx-large'><b>SimplyToast</b></span>")
        title.set_halign(Gtk.Align.CENTER)

        # Version
        version = Gtk.Label(label=f"Version: {VERSION}")
        version.set_halign(Gtk.Align.CENTER)

        # Author
        author = Gtk.Label(label="Created by: toast1599")
        author.set_halign(Gtk.Align.CENTER)

        # Description
        desc = Gtk.Label(
            label="A clean and modern utility for managing autostart apps and background tasks."
        )
        desc.set_wrap(True)
        desc.set_justify(Gtk.Justification.CENTER)
        desc.set_halign(Gtk.Align.CENTER)

        # ---------------- NEW: License notice ----------------

        license_notice = Gtk.Label(
            label=(
                "Licensed under the GNU General Public License v3 or later.\n"
                "This program is provided without any warranty, "
                "but the author will try to help on a best-effort basis."
            )
        )
        license_notice.set_wrap(True)
        license_notice.set_justify(Gtk.Justification.CENTER)
        license_notice.set_halign(Gtk.Align.CENTER)
        license_notice.get_style_context().add_class("dim-label")

        license_link = Gtk.LinkButton.new_with_label(
            "https://www.gnu.org/licenses/gpl-3.0.html",
            "View License"
        )
        license_link.set_halign(Gtk.Align.CENTER)

        # ----------------------------------------------------

        # Append widgets
        self.append(icon)
        self.append(title)
        self.append(version)
        self.append(author)
        self.append(desc)
        self.append(license_notice)
        self.append(license_link)

    def refresh(self):
        pass
