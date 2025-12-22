# src/app/windows/pages/startup_page.py
from pathlib import Path
import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango

from ...log import get_logger
from ...autostart import scan_autostart, parse_desktop_file, set_enabled, delete_autostart
from ...config import AUTOSTART_USER
from ...processes import (
    scan_processes,
    group_processes_by_exe,
    compute_startup_impact,
)
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
    def __init__(self, rec, on_toggle, on_edit, on_delete):
        super().__init__()

        (
            self.name,
            self.enabled,
            self.filepath,
            self.source,
            self.icon,
            self.comment,
            self.exec_cmd,
            self.impact_label,
            self.impact_color,
        ) = rec

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
        sw.set_active(self.enabled)
        sw.set_tooltip_text("Enable or disable this app at login")
        sw.connect("state-set", self._on_toggle)
        box.append(sw)

        btn_edit = Gtk.Button()
        btn_edit.set_child(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        btn_edit.set_tooltip_text("Edit command and metadata for this startup entry")
        btn_edit.connect("clicked", lambda *_: self._on_edit_cb(self))
        box.append(btn_edit)

        btn_delete = Gtk.Button()
        btn_delete.set_child(Gtk.Image.new_from_icon_name("user-trash-symbolic"))
        btn_delete.set_tooltip_text("Remove this app from startup")
        btn_delete.connect("clicked", lambda *_: self._on_delete_cb(self))
        box.append(btn_delete)

        if self.source == "system":
            btn_edit.set_sensitive(False)
            btn_delete.set_sensitive(False)

        self.set_child(box)

    def _on_toggle(self, switch, state):
        self._on_toggle_cb(self, bool(state))
        return False


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------

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

    def _impact_level(self, impact, max_impact):
        if max_impact <= 0:
            return None, None

        ratio = impact / max_impact

        if ratio < 0.3:
            return "Low", "green"
        elif ratio < 0.7:
            return "Medium", "orange"
        else:
            return "High", "red"

    def _impact_sort_key(self, impact, max_impact):
        if max_impact <= 0:
            return 3
        ratio = impact / max_impact
        if ratio >= 0.7:
            return 0
        elif ratio >= 0.3:
            return 1
        elif ratio > 0:
            return 2
        else:
            return 3

    def refresh(self):
        self.listbox.remove_all()

        try:
            entries = scan_autostart()
        except Exception as e:
            log.error("Failed to scan autostart entries", exc_info=e)
            return

        processes = scan_processes()
        proc_groups = group_processes_by_exe(processes)

        rows = []
        impacts = []

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
            except Exception:
                pass

            impact = compute_startup_impact(exec_cmd, proc_groups)

            rows.append(
                (name, enabled, str(filepath), source, icon, comment, exec_cmd)
            )
            impacts.append(impact)

        max_impact = max(impacts, default=0.0)

        sorted_items = sorted(
            zip(rows, impacts),
            key=lambda item: self._impact_sort_key(item[1], max_impact),
        )

        for row_data, impact in sorted_items:
            impact_label, impact_color = self._impact_level(impact, max_impact)

            row = AutostartRow(
                rec=[*row_data, impact_label, impact_color],
                on_toggle=self._toggle_entry,
                on_edit=self._edit_entry,
                on_delete=self._delete_entry,
            )

            self.listbox.append(row)

    # --------------------------------------------------------------

    def _toggle_entry(self, row, state):
        path = Path(row.filepath)
        override = AUTOSTART_USER / path.name

        try:
            if row.source == "user":
                set_enabled(row.filepath, state)
            else:
                AUTOSTART_USER.mkdir(parents=True, exist_ok=True)
                if not state:
                    from ...utils.fs import atomic_write
                    atomic_write(override, "[Desktop Entry]\nHidden=true\n")
                else:
                    override.unlink(missing_ok=True)
        except Exception as e:
            log.error("Toggle failed", exc_info=e)

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
        except Exception:
            pass

        EditEntryWindow(
            self.get_root(),
            row.filepath,
            row.name,
            exec_cmd,
            comment,
            row.icon,
        ).present()

    def _delete_entry(self, row):
        if row.source == "system":
            return

        dlg = Gtk.MessageDialog(
            transient_for=self.get_root(),
            modal=True,
            message_type=Gtk.MessageType.QUESTION,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text=f"Delete '{row.name}'?",
        )

        def resp(d, r):
            d.close()
            if r == Gtk.ResponseType.OK:
                delete_autostart(row.filepath)
                self.refresh()

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
                or q in row.name.lower()
                or q in row.exec_cmd.lower()
            )
            row = row.get_next_sibling()
