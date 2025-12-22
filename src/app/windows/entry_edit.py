import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

class EditEntryWindow(Gtk.Window):
    def __init__(self, parent, filepath, name, cmd, comment, icon):
        super().__init__(title="Edit Autostart Entry")
        self.parent = parent
        self.filepath = filepath

        self.set_default_size(350, 300)
        self.set_modal(True)
        self.set_transient_for(parent)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_start(20)
        box.set_margin_end(20)
        self.set_child(box)

        self.entry_name = self._labeled_entry(box, "Name:", name)
        self.entry_cmd = self._labeled_entry(box, "Command:", cmd)
        self.entry_comment = self._labeled_entry(box, "Comment:", comment)
        self.entry_icon = self._labeled_entry(box, "Icon:", icon)

        btn_box = Gtk.Box(spacing=10)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_save = Gtk.Button(label="Save")

        btn_cancel.connect("clicked", lambda *_: self.close())
        btn_save.connect("clicked", self.on_save)

        btn_box.append(btn_cancel)
        btn_box.append(btn_save)
        box.append(btn_box)

        self.present()

    def _labeled_entry(self, parent, label_text, text=""):
        lbl = Gtk.Label(label=label_text, xalign=0.0)
        entry = Gtk.Entry()
        entry.set_text(text)

        parent.append(lbl)
        parent.append(entry)
        return entry

    def on_save(self, button):
        name = self.entry_name.get_text().strip()
        cmd = self.entry_cmd.get_text().strip()
        comment = self.entry_comment.get_text().strip()
        icon = self.entry_icon.get_text().strip()

        lines = [
            "[Desktop Entry]\n",
            "Type=Application\n",
            f"Name={name}\n",
            f"Exec={cmd}\n",
        ]
        if comment:
            lines.append(f"Comment={comment}\n")
        if icon:
            lines.append(f"Icon={icon}\n")
        lines.append("Hidden=false\n")
        lines.append("X-GNOME-Autostart-enabled=true\n")

        from ..utils.fs import atomic_write

        atomic_write(self.filepath, "".join(lines))


        self.parent.refresh_autostart()
        self.close()
