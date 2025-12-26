# src/app/windows/pages/startup_page.py

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

from ...log import get_logger
from ...startup.controller import StartupController
from ..entry_new import NewEntryWindow
from ..entry_edit import EditEntryWindow

log = get_logger(__name__)


def short_text(text, length=80):
    if not text:
        return ""
    text = str(text)
    return text if len(text) <= length else text[: length - 1] + "…"


# ---------------------------------------------------------------------
# Row
# ---------------------------------------------------------------------

class AutostartRow(Gtk.ListBoxRow):
    def __init__(self, data, on_toggle, on_edit, on_delete):
        super().__init__()

        self.entry = data["entry"]
        self.impact_label = data["impact_label"]
        self.impact_color = data["impact_color"]

        self._on_toggle_cb = on_toggle
        self._on_edit_cb = on_edit
        self._on_delete_cb = on_delete

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Gtk.Image.new_from_icon_name(self.entry.icon)
        icon.set_pixel_size(20)
        box.append(icon)

        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_name = Gtk.Label(label=self.entry.name, xalign=0)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.END)

        lbl_exec = Gtk.Label(
            label=short_text(self.entry.exec_cmd, 90),
            xalign=0
        )
        lbl_exec.get_style_context().add_class("dim-label")
        lbl_exec.set_ellipsize(Pango.EllipsizeMode.END)

        labels.append(lbl_name)
        labels.append(lbl_exec)
        box.append(labels)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)

        impact = Gtk.Label(xalign=1.0)
        if self.impact_label and self.impact_color:
            impact.set_markup(
                f"<span foreground='{self.impact_color}'><b>{self.impact_label}</b></span>"
            )
        else:
            impact.set_text("—")

        impact.set_tooltip_text(
            "Estimated impact (heuristic, relative — not a boot-time measurement.)"
        )
        box.append(impact)

        sw = Gtk.Switch()
        sw.set_active(self.entry.enabled)
        sw.set_tooltip_text("Enable or disable this app at login")
        sw.connect("state-set", self._on_toggle)
        box.append(sw)

        btn_edit = Gtk.Button()
        btn_edit.set_child(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        btn_edit.set_tooltip_text("Edit this startup entry")
        btn_edit.connect("clicked", lambda *_: self._on_edit_cb(self))
        box.append(btn_edit)

        btn_delete = Gtk.Button()
        btn_delete.set_child(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        btn_delete.set_tooltip_text("Remove this app from startup")
        btn_delete.connect("clicked", lambda *_: self._on_delete_cb(self))
        box.append(btn_delete)

        if self.entry.source == "system":
            btn_edit.set_sensitive(False)
            btn_delete.set_sensitive(False)

        self.set_child(box)

    def _on_toggle(self, switch, state):
        self._on_toggle_cb(self.entry, bool(state))
        return False


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------

class StartupPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.parent = parent
        self.controller = StartupController(self)

        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        # toolbar
        bar = Gtk.Box(spacing=8)

        btn_new = Gtk.Button(label="New")
        btn_new.set_tooltip_text("Create a new startup entry")
        btn_new.connect("clicked", self.on_new)
        bar.append(btn_new)

        btn_edit = Gtk.Button(label="Edit")
        btn_edit.set_tooltip_text("Edit the selected startup entry")
        btn_edit.connect("clicked", self.on_edit)
        bar.append(btn_edit)

        btn_delete = Gtk.Button(label="Delete")
        btn_delete.set_tooltip_text("Remove the selected startup entry")
        btn_delete.connect("clicked", self.on_delete)
        bar.append(btn_delete)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        bar.append(spacer)

        refresh = Gtk.Button()
        refresh.set_child(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        refresh.set_tooltip_text("Refresh startup entries")
        refresh.connect("clicked", lambda *_: self.refresh())
        bar.append(refresh)

        self.append(bar)

        sc = Gtk.ScrolledWindow()
        sc.set_hexpand(True)
        sc.set_vexpand(True)

        self.listbox = Gtk.ListBox()
        sc.set_child(self.listbox)
        self.append(sc)

    # --------------------------------------------------------------

    def refresh(self):
        self.controller.refresh()

    def render(self, rows):
        self.listbox.remove_all()

        for data in rows:
            row = AutostartRow(
                data=data,
                on_toggle=self._toggle_entry,
                on_edit=self._edit_entry,
                on_delete=self._delete_entry,
            )
            self.listbox.append(row)

    # --------------------------------------------------------------

    def _toggle_entry(self, entry, enabled):
        self.controller.toggle(entry, enabled)

    def _edit_entry(self, row):
        entry = row.entry
        if entry.source == "system":
            return

        EditEntryWindow(
            self.get_root(),
            entry.filepath,
            entry.name,
            entry.exec_cmd,
            entry.comment,
            entry.icon,
        ).present()

    def _delete_entry(self, row):
        entry = row.entry
        if entry.source == "system":
            return

        dlg = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Delete '{entry.name}'?",
        )

        def resp(d, r):
            d.close()
            if r == Gtk.ResponseType.OK:
                self.controller.delete(entry)

        dlg.connect("response", resp)
        dlg.present()

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

    def on_search(self, text):
        q = (text or "").lower().strip()
        row = self.listbox.get_first_child()
        while row:
            row.set_visible(
                not q
                or q in row.entry.name.lower()
                or q in row.entry.exec_cmd.lower()
            )
            row = row.get_next_sibling()
