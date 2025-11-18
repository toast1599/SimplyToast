#!/usr/bin/env python3

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import GLib
import json
import subprocess
from pathlib import Path
import os

CONFIG_DIR = Path.home() / ".config" / "simplytoast"
SETTINGS_FILE = CONFIG_DIR / "settings.json"

current_provider = None


# ===========================
# SETTINGS
# ===========================

def load_settings():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not SETTINGS_FILE.exists():
        save_settings({"theme": "dark"})
        return {"theme": "dark"}

    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except:
        return {"theme": "dark"}


def save_settings(settings):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


# ===========================
# THEME
# ===========================

def apply_theme(window, theme_name):
    global current_provider

    css_path = (
        Path(__file__).resolve().parent.parent
        / "data" / "css" / f"{theme_name}.css"
    )

    if not css_path.exists():
        return

    screen = Gdk.Screen.get_default()

    if current_provider is not None:
        Gtk.StyleContext.remove_provider_for_screen(screen, current_provider)

    provider = Gtk.CssProvider()
    provider.load_from_path(str(css_path))

    Gtk.StyleContext.add_provider_for_screen(
        screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    current_provider = provider


# ===========================
# AUTOSTART HANDLING
# ===========================

def scan_autostart():
    entries = []

    user_dir = Path.home() / ".config" / "autostart"
    system_dir = Path("/etc/xdg/autostart")

    if user_dir.exists():
        for f in user_dir.glob("*.desktop"):
            entries.append((f, "user"))

    if system_dir.exists():
        for f in system_dir.glob("*.desktop"):
            entries.append((f, "system"))

    return entries


def parse_desktop_file(filepath):
    name = filepath.stem
    comment = ""
    icon = ""
    enabled = True

    try:
        with open(filepath, "r") as f:
            for line in f:
                if line.startswith("Name="):
                    name = line.split("=", 1)[1].strip()
                elif line.startswith("Comment="):
                    comment = line.split("=", 1)[1].strip()
                elif line.startswith("Icon="):
                    icon = line.split("=", 1)[1].strip()
                elif line.startswith("Hidden="):
                    enabled = not ("true" in line.lower())
    except:
        pass

    return name, comment, icon, enabled


def set_enabled(filepath, enabled):
    try:
        lines = []
        found = False
        with open(filepath, "r") as f:
            for line in f:
                if line.startswith("Hidden="):
                    found = True
                    line = "Hidden=false\n" if enabled else "Hidden=true\n"
                lines.append(line)

        if not found:
            lines.append("Hidden=false\n" if enabled else "Hidden=true\n")

        with open(filepath, "w") as f:
            f.writelines(lines)
    except:
        pass


def delete_autostart(filepath):
    try:
        Path(filepath).unlink(missing_ok=True)
    except:
        pass


# ===========================
# NEW ENTRY WINDOW
# ===========================

class NewEntryWindow(Gtk.Window):
    def __init__(self, parent):
        super().__init__(title="New Autostart Entry")
        self.parent = parent

        self.set_default_size(350, 300)
        self.set_modal(True)
        self.set_transient_for(parent)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(15)
        box.set_margin_bottom(15)
        box.set_margin_left(20)
        box.set_margin_right(20)
        self.add(box)

        # Name
        lbl_name = Gtk.Label(label="Name:")
        lbl_name.set_xalign(0)
        self.entry_name = Gtk.Entry()

        # Command
        lbl_cmd = Gtk.Label(label="Command:")
        lbl_cmd.set_xalign(0)
        self.entry_cmd = Gtk.Entry()

        # Comment
        lbl_comment = Gtk.Label(label="Comment:")
        lbl_comment.set_xalign(0)
        self.entry_comment = Gtk.Entry()

        # Icon
        lbl_icon = Gtk.Label(label="Icon (name or path):")
        lbl_icon.set_xalign(0)
        self.entry_icon = Gtk.Entry()

        for widget in [
            lbl_name, self.entry_name,
            lbl_cmd, self.entry_cmd,
            lbl_comment, self.entry_comment,
            lbl_icon, self.entry_icon
        ]:
            box.pack_start(widget, False, False, 0)

        btn_box = Gtk.Box(spacing=10)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_create = Gtk.Button(label="Create")

        btn_cancel.connect("clicked", lambda x: self.destroy())
        btn_create.connect("clicked", self.on_create)

        btn_box.pack_end(btn_create, False, False, 0)
        btn_box.pack_end(btn_cancel, False, False, 0)

        box.pack_end(btn_box, False, False, 0)

    def on_create(self, button):
        name = self.entry_name.get_text().strip()
        cmd = self.entry_cmd.get_text().strip()
        comment = self.entry_comment.get_text().strip()
        icon = self.entry_icon.get_text().strip()

        if not name or not cmd:
            self.destroy()
            return

        autostart_dir = Path.home() / ".config" / "autostart"
        autostart_dir.mkdir(parents=True, exist_ok=True)

        filename = autostart_dir / f"{name.replace(' ', '_')}.desktop"

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
        self.destroy()


# ===========================
# EDIT ENTRY WINDOW
# ===========================

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
        box.set_margin_left(20)
        box.set_margin_right(20)
        self.add(box)

        widgets = []

        # Name
        lbl_name = Gtk.Label(label="Name:")
        lbl_name.set_xalign(0)
        self.entry_name = Gtk.Entry()
        self.entry_name.set_text(name)
        widgets += [lbl_name, self.entry_name]

        # Command
        lbl_cmd = Gtk.Label(label="Command:")
        lbl_cmd.set_xalign(0)
        self.entry_cmd = Gtk.Entry()
        self.entry_cmd.set_text(cmd)
        widgets += [lbl_cmd, self.entry_cmd]

        # Comment
        lbl_comment = Gtk.Label(label="Comment:")
        lbl_comment.set_xalign(0)
        self.entry_comment = Gtk.Entry()
        self.entry_comment.set_text(comment)
        widgets += [lbl_comment, self.entry_comment]

        # Icon
        lbl_icon = Gtk.Label(label="Icon:")
        lbl_icon.set_xalign(0)
        self.entry_icon = Gtk.Entry()
        self.entry_icon.set_text(icon)
        widgets += [lbl_icon, self.entry_icon]

        for w in widgets:
            box.pack_start(w, False, False, 0)

        btn_box = Gtk.Box(spacing=10)
        btn_cancel = Gtk.Button(label="Cancel")
        btn_save = Gtk.Button(label="Save")

        btn_cancel.connect("clicked", lambda x: self.destroy())
        btn_save.connect("clicked", self.on_save)

        btn_box.pack_end(btn_save, False, False, 0)
        btn_box.pack_end(btn_cancel, False, False, 0)

        box.pack_end(btn_box, False, False, 0)

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

        with open(self.filepath, "w") as f:
            f.writelines(lines)

        self.parent.refresh_autostart()
        self.destroy()


# ===========================
# BACKGROUND PROCESSES
# ===========================

def scan_processes():
    user = os.environ.get("USER") or os.getlogin()

    try:
        cmd = f"ps -u {user} -o pid=,comm=,%cpu=,%mem=,args="
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.DEVNULL).decode(errors="ignore")

        rows = []

        for line in out.splitlines():
            parts = line.strip().split(None, 4)
            if len(parts) >= 5:
                pid, comm, cpu, mem, args = parts
            elif len(parts) == 4:
                pid, comm, cpu, mem = parts
                args = comm
            else:
                continue

            try:
                cpu_f = float(cpu)
                mem_f = float(mem)
            except:
                cpu_f = 0.0
                mem_f = 0.0

            rows.append((pid, comm, cpu, mem, args, cpu_f, mem_f))

        rows.sort(key=lambda x: (-x[5], -x[6]))

        return rows

    except:
        return []


# ===========================
# FILTERING
# ===========================

def toast_filter(data, text, columns):
    text = text.lower()
    result = []
    for row in data:
        for col in columns:
            if text in str(row[col]).lower():
                result.append(row)
                break
    return result


# ===========================
# MAIN WINDOW
# ===========================

class ToastWindow(Gtk.Window):
    def __init__(self):
        super().__init__(title="SimplyToast")
        self.set_default_size(1100, 630)

        self.settings = load_settings()

        # HEADER BAR
        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "SimplyToast"
        self.set_titlebar(hb)

        # Hamburger Menu
        self.menu_button = Gtk.MenuButton()
        icon = Gtk.Image.new_from_icon_name("open-menu-symbolic", Gtk.IconSize.BUTTON)
        self.menu_button.add(icon)

        menu = Gtk.Menu()

        item_new = Gtk.MenuItem(label="New Autostart Entry")
        item_delete = Gtk.MenuItem(label="Delete Selected")
        item_edit = Gtk.MenuItem(label="Edit Selected")

        item_new.connect("activate", self.on_new_entry)
        item_delete.connect("activate", self.on_delete_selected)
        item_edit.connect("activate", self.on_edit_selected)

        menu.append(item_new)
        menu.append(item_delete)
        menu.append(item_edit)
        menu.show_all()

        self.menu_button.set_popup(menu)
        hb.pack_start(self.menu_button)

        # Search Box
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search…")
        self.search_entry.connect("search-changed", self.on_search)
        hb.pack_start(self.search_entry)

        # Theme toggle
        btn_theme = Gtk.Button(label="Theme")
        btn_theme.connect("clicked", self.on_toggle_theme)
        hb.pack_end(btn_theme)

        # ===== TOP ROW (Startup | Refresh Button | Background) =====
        top_grid = Gtk.Grid()
        top_grid.set_column_homogeneous(True)
        top_grid.set_row_spacing(5)
        top_grid.set_column_spacing(5)
        top_grid.set_margin_top(12)
        top_grid.set_margin_bottom(12)

        lbl_left = Gtk.Label(label="Startup Apps")
        lbl_left.set_xalign(0.5)

        lbl_right = Gtk.Label(label="Background Apps")
        lbl_right.set_xalign(0.5)

        # Refresh button in middle
        self.center_refresh_btn = Gtk.Button()
        self.center_refresh_btn.set_size_request(40, 40)
        icon2 = Gtk.Image.new_from_icon_name("view-refresh-symbolic", Gtk.IconSize.BUTTON)
        self.center_refresh_btn.add(icon2)
        self.center_refresh_btn.connect("clicked", self.on_refresh)

        top_grid.attach(lbl_left, 0, 0, 1, 1)
        top_grid.attach(self.center_refresh_btn, 1, 0, 1, 1)
        top_grid.attach(lbl_right, 2, 0, 1, 1)

        # MAIN PANED
        self.paned = Gtk.Paned.new(Gtk.Orientation.HORIZONTAL)
        self.paned.set_wide_handle(True)       # thicker border

        # LEFT (AUTOSTART)
        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Columns: name, enabled, filepath, source, icon, comment, score_float, score_percent
        self.autostart_list = Gtk.ListStore(str, bool, str, str, str, str, float, float)
        self.autostart_view = Gtk.TreeView(model=self.autostart_list)

        # Toggle column (index 1)
        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_toggle_autostart)
        col_toggle = Gtk.TreeViewColumn("On", renderer_toggle, active=1)
        col_toggle.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_toggle.set_fixed_width(48)
        self.autostart_view.append_column(col_toggle)

        # Icon column (index 4)
        renderer_icon = Gtk.CellRendererPixbuf()
        col_icon = Gtk.TreeViewColumn("", renderer_icon, icon_name=4)
        col_icon.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_icon.set_fixed_width(36)
        self.autostart_view.append_column(col_icon)

        # App name (index 0)
        renderer_name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn("App", renderer_name, text=0)

        col_name.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_name.set_fixed_width(260)   # hard cap so Impact stays visible
        col_name.set_expand(True)

        self.autostart_view.append_column(col_name)


        # Impact % (index 7)
        renderer_impact = Gtk.CellRendererText()
        renderer_impact.set_property("xalign", 1.0)
        col_impact = Gtk.TreeViewColumn("Impact %", renderer_impact)

        col_impact.set_cell_data_func(
            renderer_impact,
            lambda column, cell, model, iter, data: cell.set_property(
                "text",
                f"{model.get_value(iter, 7):.2f}"
            )
        )

        col_impact.set_sizing(Gtk.TreeViewColumnSizing.FIXED)
        col_impact.set_fixed_width(90)
        col_impact.set_alignment(1.0)
        self.autostart_view.append_column(col_impact)

        # Tooltip = comment (index 5)
        self.autostart_view.set_tooltip_column(5)

        sc_left = Gtk.ScrolledWindow()
        sc_left.add(self.autostart_view)
        left_box.pack_start(sc_left, True, True, 0)

        # RIGHT (BACKGROUND PROCESSES)
        right_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.process_list = Gtk.ListStore(str, str, str, str, str, str)
        # pid name cpu mem args ico-name

        self.process_view = Gtk.TreeView(model=self.process_list)
        renderer_picon = Gtk.CellRendererPixbuf()
        col_picon = Gtk.TreeViewColumn("", renderer_picon, icon_name=5)
        self.process_view.append_column(col_picon)

        col_pid = Gtk.TreeViewColumn("PID", Gtk.CellRendererText(), text=0)
        col_comm = Gtk.TreeViewColumn("App", Gtk.CellRendererText(), text=1)
        col_cpu = Gtk.TreeViewColumn("CPU%", Gtk.CellRendererText(), text=2)
        col_mem = Gtk.TreeViewColumn("MEM%", Gtk.CellRendererText(), text=3)
        col_args = Gtk.TreeViewColumn("Command", Gtk.CellRendererText(), text=4)

        col_comm.set_expand(True)
        col_args.set_expand(True)

        for col in [col_pid, col_comm, col_cpu, col_mem, col_args]:
            self.process_view.append_column(col)

        sc_right = Gtk.ScrolledWindow()
        sc_right.add(self.process_view)
        right_box.pack_start(sc_right, True, True, 0)

        # Attach to paned
        self.paned.add1(left_box)
        self.paned.add2(right_box)


        # MAIN OUTER BOX
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.pack_start(top_grid, False, False, 0)
        outer.pack_start(self.paned, True, True, 0)
        self.add(outer)
        self.connect("size-allocate", self.on_resize_keep_split)         

        # Load everything
        
        self.refresh_autostart()
        self.refresh_processes()
        apply_theme(self, self.settings["theme"])

        # Auto-refresh processes
        self.auto_refresh_id = GLib.timeout_add(3000, self.auto_refresh_processes)

    # ===========================
    # AUTO REFRESH
    # ===========================
    def auto_refresh_processes(self):
        self.refresh_processes()
        return True

    # ===========================
    # DATA LOADERS
    # ===========================
    def refresh_autostart(self):
        self.autostart_list.clear()
        # Build process usage map {name: resource_score}
        proc_usage = {}
        for pid, comm, cpu, mem, args, _, _ in scan_processes():
            try:
                score = float(cpu) + float(mem)
            except:
                score = 0.0
            proc_usage[comm.lower()] = score

        entries = scan_autostart()
        self._autostart_original = []

        if not entries:
            self.autostart_list.append(["(empty)", False, "", "", "", ""])
            return
        
        rows_temp = []

        # total score to calculate percentages
        total_score = sum(proc_usage.values()) or 1.0


        for filepath, source in entries:
            name, comment, icon, enabled = parse_desktop_file(filepath)

            if not icon:
                icon = "application-x-executable"

            # Get resource usage score
            score = proc_usage.get(name.lower(), 0.0)

            impact_percent = round((score / total_score) * 100, 1)

            row = [
                name,
                enabled,
                str(filepath),
                source,
                icon,
                comment or "No description available",
                score,
                float(f"{impact_percent:.2f}")
            ]


            rows_temp.append(row)

        # Sort by resource usage (highest to lowest)
        rows_temp.sort(key=lambda x: -x[6])

        # Append sorted items into the ListStore
        for row in rows_temp:
            self.autostart_list.append(row)


    def refresh_processes(self):
        self.process_list.clear()
        rows = scan_processes()

        for pid, comm, cpu, mem, args, _, _ in rows:

            # Determine icon name safely
            icon_name = comm.lower()

            try:
                theme = Gtk.IconTheme.get_default()
                if not theme.has_icon(icon_name):
                    icon_name = "application-x-executable"
            except:
                icon_name = "application-x-executable"

            # Add the row WITHIN the loop
            self.process_list.append([pid, comm, cpu, mem, args, icon_name])



    def on_refresh(self, button):
        self.search_entry.set_text("")
        self.refresh_autostart()
        self.refresh_processes()

    def on_toggle_theme(self, button):
        themes = ["light", "mid", "dark"]
        current = self.settings.get("theme", "light")

        try:
            idx = themes.index(current)
        except ValueError:
            idx = 0

        new_theme = themes[(idx + 1) % len(themes)]

        self.settings["theme"] = new_theme
        save_settings(self.settings)
        apply_theme(self, new_theme)


    def on_new_entry(self, menuitem):
        win = NewEntryWindow(self)
        win.show_all()

    def on_edit_selected(self, menuitem):
        if self.search_entry.get_text().strip():
            return

        selection = self.autostart_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return

        name, enabled, filepath, source, icon, comment = model[treeiter]

        if source == "system":
            return
        if name == "(empty)":
            return

        cmd = ""
        try:
            with open(filepath, "r") as f:
                for line in f:
                    if line.startswith("Exec="):
                        cmd = line.split("=", 1)[1].strip()
        except:
            pass

        win = EditEntryWindow(
            self, filepath, name, cmd, comment, icon)
        win.show_all()

    def on_delete_selected(self, menuitem):
        if self.search_entry.get_text().strip():
            return

        selection = self.autostart_view.get_selection()
        model, treeiter = selection.get_selected()
        if not treeiter:
            return

        name, enabled, filepath, source, icon, comment = model[treeiter]

        if source == "system":
            return
        if name == "(empty)":
            return

        delete_autostart(filepath)
        self.refresh_autostart()

    def on_toggle_autostart(self, widget, path):
        iter = self.autostart_list.get_iter(path)
        name, enabled, filepath, source, icon, comment = self.autostart_list[iter]

        if source == "system":
            return

        new_val = not enabled
        self.autostart_list[iter][1] = new_val
        set_enabled(filepath, new_val)

    def on_search(self, entry):
        text = entry.get_text().lower()

        # Autostart filter
        self.autostart_list.clear()
        for row in toast_filter(self._autostart_original, text, [0]):
           self.autostart_list.append(row)

        # Background process filter
        self.process_list.clear()

        rows = scan_processes()
        for pid, comm, cpu, mem, args, _, _ in rows:
            if text in pid.lower() or text in comm.lower() or text in args.lower():

                icon_name = comm.lower()
                try:
                    theme = Gtk.IconTheme.get_default()
                    if not theme.has_icon(icon_name):
                        icon_name = "application-x-executable"
                except:
                    icon_name = "application-x-executable"

            # Append INSIDE the IF and INSIDE THE LOOP
            self.process_list.append([pid, comm, cpu, mem, args, icon_name])


    def on_resize_keep_split(self, widget, allocation):
        width = self.paned.get_allocated_width()
        self.paned.set_position(width // 2)



# ===========================
# ENTRY POINT
# ===========================

def main():
    win = ToastWindow()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
