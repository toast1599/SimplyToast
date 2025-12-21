# src/app/windows/pages/startup_page.py
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib

from ...autostart import scan_autostart, parse_desktop_file, set_enabled, delete_autostart
from ...config import AUTOSTART_USER
from ..entry_new import NewEntryWindow
from ..entry_edit import EditEntryWindow


def short_text(text, length=80):
    if not text:
        return ""
    t = str(text)
    return (t[:length - 1] + "…") if len(t) > length else t


class AutostartRow(Gtk.ListBoxRow):
    def __init__(self, rec, on_toggle, on_edit, on_delete):
        super().__init__()

        self.name, self.enabled, self.filepath, self.source, \
        self.icon, self.comment, self.exec_cmd = rec

        self._on_toggle_cb = on_toggle
        self._on_edit_cb = on_edit
        self._on_delete_cb = on_delete

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Gtk.Image.new_from_icon_name(self.icon)
        icon.set_pixel_size(20)
        box.append(icon)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        lbl_name = Gtk.Label(label=self.name, xalign=0)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.END)

        lbl_exec = Gtk.Label(label=short_text(self.exec_cmd, 90), xalign=0)
        lbl_exec.get_style_context().add_class("dim-label")
        lbl_exec.set_ellipsize(Pango.EllipsizeMode.END)

        labels.append(lbl_name)
        labels.append(lbl_exec)
        box.append(labels)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)

        impact = Gtk.Label(label="—", xalign=1.0)
        box.append(impact)

        sw = Gtk.Switch()
        sw.set_active(self.enabled)
        sw.connect("state-set", self._on_toggle)
        box.append(sw)

        btn_edit = Gtk.Button()
        btn_edit.set_child(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        btn_edit.connect("clicked", lambda *_: self._on_edit_cb(self))
        box.append(btn_edit)

        btn_delete = Gtk.Button()
        btn_delete.set_child(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        btn_delete.connect("clicked", lambda *_: self._on_delete_cb(self))
        box.append(btn_delete)

        if self.source == "system":
            btn_edit.set_sensitive(False)
            btn_delete.set_sensitive(False)

        self.set_child(box)

    def _on_toggle(self, switch, state):
        self._on_toggle_cb(self, bool(state))
        return False


class StartupPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        # toolbar
        bar = Gtk.Box(spacing=8)

        btn_new = Gtk.Button(label="New")
        btn_new.connect("clicked", self.on_new)
        bar.append(btn_new)

        btn_edit = Gtk.Button(label="Edit")
        btn_edit.connect("clicked", self.on_edit)
        bar.append(btn_edit)

        btn_delete = Gtk.Button(label="Delete")
        btn_delete.connect("clicked", self.on_delete)
        bar.append(btn_delete)


        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)

        refresh = Gtk.Button()
        refresh.set_child(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        refresh.connect("clicked", lambda *_: self.refresh())
        bar.append(refresh)

        self.append(bar)

        # list
        sc = Gtk.ScrolledWindow()
        sc.set_hexpand(True)
        sc.set_vexpand(True)

        self.listbox = Gtk.ListBox()
        self.listbox.set_hexpand(True)
        self.listbox.set_vexpand(True)

        sc.set_child(self.listbox)
        self.append(sc)

    # ---------------- core ----------------

    def refresh(self):
        self.listbox.remove_all()

        try:
            entries = scan_autostart()
        except Exception:
            entries = []

        for filepath, source in entries:
            try:
                name, comment, icon, enabled = parse_desktop_file(filepath)
            except Exception:
                name = Path(filepath).stem
                comment = ""
                icon = "application-x-executable"
                enabled = True

            exec_cmd = ""
            try:
                with open(filepath, "r", errors="ignore") as f:
                    for line in f:
                        if line.startswith("Exec="):
                            exec_cmd = line.split("=", 1)[1].strip()
                            break
            except Exception as e:
                print('[ERROR] Unhandled exception:', e)

            row = AutostartRow(
                rec=[name, enabled, str(filepath), source, icon, comment, exec_cmd],
                on_toggle=self._toggle_entry,
                on_edit=self._edit_entry,
                on_delete=self._delete_entry,
            )

            row.set_visible(True)   # ← THIS IS THE FIX
            self.listbox.append(row)

    # ---------------- actions ----------------

    def _toggle_entry(self, row, state):
        path = Path(row.filepath)
        override = AUTOSTART_USER / path.name

        try:
            if row.source == "user":
                set_enabled(row.filepath, state)
            else:
                AUTOSTART_USER.mkdir(parents=True, exist_ok=True)
                if not state:
                    override.write_text("[Desktop Entry]\nHidden=true\n")
                else:
                    override.unlink(missing_ok=True)
        except Exception as e:
            print("Toggle failed:", e)

        self.refresh()

    def _edit_entry(self, row):
        if row.source == "system":
            return

        exec_cmd = ""
        comment = ""

        try:
            with open(row.filepath, "r", errors="ignore") as f:
                for line in f:
                    if line.startswith("Exec="):
                        exec_cmd = line.split("=", 1)[1].strip()
                    elif line.startswith("Comment="):
                        comment = line.split("=", 1)[1].strip()
        except Exception as e:
            print('[ERROR] Unhandled exception:', e)

        EditEntryWindow(self.get_root(), row.filepath, row.name, exec_cmd, comment, row.icon).present()

    def _delete_entry(self, row):
        if row.source == "system":
            return

        dlg = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Delete '{row.name}'?"
        )

        def resp(d, r):
            d.close()
            if r == Gtk.ResponseType.OK:
                delete_autostart(row.filepath)
                self.refresh()

        dlg.connect("response", resp)
        dlg.present()

    # ---------------- toolbar ----------------

    def _selected_row(self):
        row = self.listbox.get_selected_row()
        return row if isinstance(row, AutostartRow) else None

    def on_new(self, *_):
        NewEntryWindow(self.get_root()).present()

    def on_edit(self, *_):
        row = self._selected_row()
        if row:
            self._edit_entry(row)

    def on_delete(self, *_):
        row = self._selected_row()
        if row:
            self._delete_entry(row)

    # ---------------- search ----------------

    def on_search(self, text):
        q = (text or "").lower().strip()

        row = self.listbox.get_first_child()
        while row:
            row.set_visible(
                not q
                or q in row.name.lower()
                or q in row.exec_cmd.lower()
            )
            row = row.get_next_sibling()


