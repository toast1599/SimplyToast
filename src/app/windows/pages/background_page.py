# src/app/windows/pages/background_page.py

import logging
log = logging.getLogger(__name__)

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib, Gdk

from ...background.controller import BackgroundController

CPU_COL_WIDTH = 6
MEM_COL_WIDTH = 6


def short(text, n=90):
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


def resolve_icon(name):
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

    for candidate in (
        name,
        name.lower(),
        f"{name.lower()}-symbolic",
        "application-x-executable",
    ):
        if theme.has_icon(candidate):
            return candidate

    return "application-x-executable"


# ---------------------------------------------------------------------
# Row
# ---------------------------------------------------------------------

class ProcessRow(Gtk.ListBoxRow):
    def __init__(self, pid, name, cpu, mem, cmd, on_kill):
        super().__init__()

        self.pid = pid
        self.name = name
        self.cmd = cmd
        self._on_kill = on_kill

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        icon = Gtk.Image.new_from_icon_name(resolve_icon(name))
        icon.set_pixel_size(20)
        box.append(icon)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_name = Gtk.Label(label=name, xalign=0)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.END)

        lbl_cmd = Gtk.Label(label=short(cmd), xalign=0)
        lbl_cmd.get_style_context().add_class("dim-label")
        lbl_cmd.set_ellipsize(Pango.EllipsizeMode.END)

        vbox.append(lbl_name)
        vbox.append(lbl_cmd)
        box.append(vbox)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)

        btn_kill = Gtk.Button()
        btn_kill.set_child(Gtk.Image.new_from_icon_name("process-stop-symbolic"))
        btn_kill.set_tooltip_text("Terminate this process (SIGTERM)")
        btn_kill.connect("clicked", lambda *_: self._on_kill(self.pid))
        box.append(btn_kill)

        self.lbl_cpu = Gtk.Label(label=f"{cpu:.1f}%", xalign=1)
        self.lbl_mem = Gtk.Label(label=f"{mem:.1f}%", xalign=1)

        self.lbl_cpu.set_width_chars(CPU_COL_WIDTH)
        self.lbl_mem.set_width_chars(MEM_COL_WIDTH)

        box.append(self.lbl_cpu)
        box.append(self.lbl_mem)

        self.set_child(box)

    def update_usage(self, cpu, mem):
        self.lbl_cpu.set_text(f"{cpu:.1f}%")
        self.lbl_mem.set_text(f"{mem:.1f}%")


# ---------------------------------------------------------------------
# Page
# ---------------------------------------------------------------------

class BackgroundPage(Gtk.Box):
    def __init__(self, parent):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        self.parent = parent
        self.controller = BackgroundController(self)

        self.set_margin_top(8)
        self.set_margin_bottom(8)
        self.set_margin_start(8)
        self.set_margin_end(8)

        bar = Gtk.Box(spacing=8)

        refresh = Gtk.Button()
        refresh.set_child(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        refresh.set_tooltip_text("Refresh running process list")
        refresh.connect("clicked", lambda *_: self.refresh())
        bar.append(refresh)

        self.append(bar)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.set_margin_start(8)
        header.set_margin_end(8)

        header.append(Gtk.Label(label="", xalign=0))
        header.append(Gtk.Label(label="Process", xalign=0, hexpand=True))
        header.append(Gtk.Label(label="KILL", xalign=1, width_chars=4))
        header.append(Gtk.Label(label="CPU %", xalign=1, width_chars=6))
        header.append(Gtk.Label(label="RAM %", xalign=1, width_chars=6))

        self.append(header)

        sc = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.listbox = Gtk.ListBox()
        sc.set_child(self.listbox)
        self.append(sc)

        self._rows_by_pid = {}
        self._active = True

        self._refresh_source = None
        self._start_timer()

        GLib.idle_add(self.refresh)

    # --------------------------------------------------------------

    def _start_timer(self):
        self._stop_timer()
        interval_ms = self.parent.settings.get("refresh_interval_ms", 3000)
        self._refresh_source = GLib.timeout_add(interval_ms, self._tick)

    def _stop_timer(self):
        if self._refresh_source:
            GLib.source_remove(self._refresh_source)
            self._refresh_source = None

    def _tick(self):
        if not self._active:
            return True

        if not self.parent.search_entry.get_text().strip():
            self.refresh()

        return True

    # --------------------------------------------------------------

    def refresh(self):
        self.controller.refresh()

    def render(self, rows):
        """
        rows: list[(pid, name, cpu, mem, cmd)]
        """
        seen = set()

        for pid, name, cpu, mem, cmd in rows:
            seen.add(pid)

            if pid in self._rows_by_pid:
                self._rows_by_pid[pid].update_usage(cpu, mem)
            else:
                row = ProcessRow(
                    pid=pid,
                    name=name,
                    cpu=cpu,
                    mem=mem,
                    cmd=cmd,
                    on_kill=self._kill_process,
                )
                self._rows_by_pid[pid] = row
                self.listbox.append(row)

        for pid in list(self._rows_by_pid):
            if pid not in seen:
                self.listbox.remove(self._rows_by_pid.pop(pid))

    def _kill_process(self, pid):
        self.controller.kill(pid)

    def on_search(self, text):
        q = (text or "").lower().strip()
        row = self.listbox.get_first_child()
        while row:
            row.set_visible(
                not q
                or q in row.name.lower()
                or q in row.cmd.lower()
            )
            row = row.get_next_sibling()
