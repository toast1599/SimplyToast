# src/app/windows/pages/background_page.py

import os
import signal
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Pango, GLib, Gdk

from ...processes import scan_processes

FALLBACK_ICON = "application-x-executable"
CPU_COL_WIDTH = 6
MEM_COL_WIDTH = 6


def display_name(comm, cmd):
    if cmd:
        exe = cmd.split()[0]
        if exe.startswith("/"):
            return Path(exe).name
        return exe
    return comm


def resolve_icon(name):
    theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())

    candidates = [
        name,
        name.lower(),
        f"{name.lower()}-symbolic",
        "application-x-executable",
    ]

    for c in candidates:
        if theme.has_icon(c):
            return c

    return "application-x-executable"


def short(text, n=90):
    if not text:
        return ""
    return text if len(text) <= n else text[: n - 1] + "…"


# ---------------------------------------------------------------------
# Row
# ---------------------------------------------------------------------

class ProcessRow(Gtk.ListBoxRow):
    def __init__(self, pid, name, cpu, mem, cmd, on_kill):
        super().__init__()

        self.pid = pid
        self.name = name
        self.cmd = cmd
        self.on_kill = on_kill

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.set_margin_top(6)
        box.set_margin_bottom(6)
        box.set_margin_start(8)
        box.set_margin_end(8)

        # icon
        icon = Gtk.Image.new_from_icon_name(resolve_icon(name))
        icon.set_pixel_size(20)
        box.append(icon)

        # name + cmd
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)

        lbl_name = Gtk.Label(label=name, xalign=0)
        lbl_name.set_ellipsize(Pango.EllipsizeMode.END)

        lbl_cmd = Gtk.Label(label=short(cmd), xalign=0)
        lbl_cmd.get_style_context().add_class("dim-label")
        lbl_cmd.set_ellipsize(Pango.EllipsizeMode.END)

        vbox.append(lbl_name)
        vbox.append(lbl_cmd)
        box.append(vbox)

        # spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        box.append(spacer)

        # kill button
        btn_kill = Gtk.Button()
        btn_kill.set_child(Gtk.Image.new_from_icon_name("process-stop-symbolic"))
        btn_kill.set_tooltip_text("Terminate this process (SIGTERM)")
        btn_kill.connect("clicked", lambda *_: self.on_kill(self))
        box.append(btn_kill)

        # cpu / mem
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

        header.append(Gtk.Label(label="", xalign=0))  # icon column

        lbl_process = Gtk.Label(label="Process", xalign=0)
        lbl_process.set_hexpand(True)
        header.append(lbl_process)

        lbl_kill = Gtk.Label(label="KILL", xalign=1)
        lbl_kill.set_width_chars(4)
        lbl_kill.set_tooltip_text("Terminate the process")
        header.append(lbl_kill)

        lbl_cpu_h = Gtk.Label(label="CPU %", xalign=1)
        lbl_cpu_h.set_width_chars(6)
        header.append(lbl_cpu_h)

        lbl_mem_h = Gtk.Label(label="RAM %", xalign=1)
        lbl_mem_h.set_width_chars(6)
        header.append(lbl_mem_h)

        self.append(header)

        sc = Gtk.ScrolledWindow()
        sc.set_hexpand(True)
        sc.set_vexpand(True)

        self.listbox = Gtk.ListBox()
        sc.set_child(self.listbox)
        self.append(sc)

        self._rows_by_pid = {}
        self._active = True

        GLib.idle_add(self.refresh)
        self._refresh_source = None
        self._start_timer()

    # -----------------------------------------------------------------

    def _start_timer(self):
        self._stop_timer()

        interval_ms = self.parent.settings.get("refresh_interval_ms", 3000)

        self._refresh_source = GLib.timeout_add(interval_ms, self._tick)

    def _stop_timer(self):
        if self._refresh_source is not None:
            GLib.source_remove(self._refresh_source)
            self._refresh_source = None

    def _tick(self):
        if not self._active:
            return True

        if not self.parent.search_entry.get_text().strip():
            self.refresh()

        return True

    def refresh(self):
        try:
            processes = scan_processes()
        except Exception as e:
            print("Process scan failed:", e)
            return

        rows = []

        for p in processes:
            try:
                pid = int(p[0])
                comm = str(p[1])
                cpu = float(p[2])
                mem = float(p[3])
                cmd = str(p[4])
            except Exception:
                continue

            if cmd.startswith("[") and cmd.endswith("]"):
                continue

            name = display_name(comm, cmd)
            rows.append((pid, name, cpu, mem, cmd))

        rows.sort(key=lambda r: r[2], reverse=True)

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

    def _kill_process(self, row):
        try:
            os.kill(row.pid, signal.SIGTERM)
        except Exception as e:
            print("Kill failed:", e)

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
