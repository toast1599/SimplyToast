import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk
from ..config import AUTOSTART_USER

class NewEntryWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="New Autostart Entry")
        self.parent = parent
        self.set_default_size(350, 300)
        self.set_modal(True)
        self.set_transient_for(parent)

        # Root container
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(20)
        box.set_margin_end(20)
        self.set_child(box)

        # Entries
        self.entry_name = self._labeled_entry(box, "Name:")
        self.entry_cmd = self._labeled_entry(box, "Command:")
        self.entry_comment = self._labeled_entry(box, "Comment:")
        self.entry_icon = self._labeled_entry(box, "Icon (name or path):")

        # Buttons
        btn_box = Gtk.Box(spacing=10)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_create = Gtk.Button(label="Create")

        btn_cancel.connect("clicked", lambda *_: self.close())
        btn_create.connect("clicked", self.on_create)

        btn_box.append(btn_cancel)
        btn_box.append(btn_create)

        box.append(btn_box)

        self.present()

    def _labeled_entry(self, parent, label_text):
        lbl = Gtk.Label(label=label_text, xalign=0.0)
        entry = Gtk.Entry()

        parent.append(lbl)
        parent.append(entry)
        return entry

    def on_create(self, button):
        from ..autostart import AUTOSTART_USER  # avoid circular import

        name = self.entry_name.get_text().strip()
        cmd = self.entry_cmd.get_text().strip()
        comment = self.entry_comment.get_text().strip()
        icon = self.entry_icon.get_text().strip()

        if not name or not cmd:
            self.close()
            return

        AUTOSTART_USER.mkdir(parents=True, exist_ok=True)
        filename = AUTOSTART_USER / f"{name.replace(' ', '_')}.desktop"

        text = [
            "[Desktop Entry]\n",
            "Type=Application\n",
            f"Name={name}\n",
            f"Exec={cmd}\n",
        ]
        if comment:
            text.append(f"Comment={comment}\n")
        if icon:
            text.append(f"Icon={icon}\n")

        text.append("Hidden=false\n")
        text.append("X-GNOME-Autostart-enabled=true\n")

        with open(filename, "w") as f:
            f.writelines(text)

        self.parent.refresh_autostart()
        self.close()
