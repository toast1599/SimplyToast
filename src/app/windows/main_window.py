import logging
log = logging.getLogger(__name__)

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from ..settings import load_settings, save_settings
from ..theme import apply_theme


try:
    from .pages.startup_page import StartupPage
    from .pages.background_page import BackgroundPage
    from .pages.settings_page import SettingsPage
    from .pages.about_page import AboutPage
except Exception as e:
    log.error("Import error while loading pages")
    import traceback
    traceback.print_exc()
    raise


class ToastWindow(Gtk.Window):
    SIDEBAR_WIDTH = 240

    def refresh_autostart(self):
        try:
            if hasattr(self, "startup_page"):
                self.startup_page.refresh()
        except Exception as e:
            log.exception("Failed to refresh startup page")

    def __init__(self):
        super().__init__(title="SimplyToast")
        self.set_default_size(1100, 700)

        self.settings = load_settings()

        hb = Gtk.HeaderBar()
        hb.set_show_title_buttons(True)
        self.set_titlebar(hb)

        # Left menu (three-dot)
        self.menu_button = Gtk.MenuButton()
        menu_icon = Gtk.Image.new_from_icon_name("open-menu-symbolic")
        menu_icon.set_pixel_size(18)
        self.menu_button.set_child(menu_icon)
        self.menu_button.set_tooltip_text("Application menu")

        pop = Gtk.Popover()
        menu_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=6,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        btn_help = Gtk.Button(label="Help & Support")
        btn_help.set_tooltip_text("Open help and support information")
        btn_help.connect("clicked", self._on_help)
        menu_box.append(btn_help)

        pop.set_child(menu_box)
        self.menu_button.set_popover(pop)
        hb.pack_start(self.menu_button)

        # Search in header
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search…")
        self.search_entry.set_tooltip_text("Filter items on the current page")
        self.search_entry.connect("search-changed", self._on_search_changed)
        hb.pack_start(self.search_entry)

        # Refresh button on right
        self.refresh_btn = Gtk.Button()
        icon_refresh = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        icon_refresh.set_pixel_size(18)
        self.refresh_btn.set_child(icon_refresh)
        self.refresh_btn.set_tooltip_text("Refresh current page")
        self.refresh_btn.connect("clicked", lambda *_: self._on_refresh())
        hb.pack_end(self.refresh_btn)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_margin_top(12)
        sidebar.set_margin_bottom(12)
        sidebar.set_margin_start(12)
        sidebar.set_margin_end(12)
        sidebar.set_size_request(self.SIDEBAR_WIDTH, -1)

        def make_sidebar_button(icon_name, label_text, key, tooltip):
            btn = Gtk.Button()
            btn.set_halign(Gtk.Align.FILL)
            btn.set_hexpand(False)
            btn.set_tooltip_text(tooltip)

            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            img = Gtk.Image.new_from_icon_name(icon_name)
            img.set_pixel_size(18)
            lbl = Gtk.Label(label=label_text, xalign=0.0)

            box.append(img)
            box.append(lbl)
            btn.set_child(box)
            btn.connect("clicked", lambda *_: self._on_sidebar_select(key))
            return btn

        btn_startup = make_sidebar_button(
            "media-playback-start-symbolic",
            "Startup Apps",
            "startup",
            "Manage apps that run when you log in",
        )

        btn_background = make_sidebar_button(
            "system-run-symbolic",
            "Background Apps",
            "background",
            "View and manage running background processes",
        )

        sidebar.append(btn_startup)
        sidebar.append(btn_background)
        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        btn_settings_bottom = make_sidebar_button(
            "emblem-system-symbolic",
            "Settings",
            "settings",
            "Application preferences",
        )

        btn_about = make_sidebar_button(
            "help-about-symbolic",
            "About",
            "about",
            "About SimplyToast",
        )

        sidebar.append(btn_settings_bottom)
        sidebar.append(btn_about)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self.startup_page = StartupPage(self)
        self.background_page = BackgroundPage(self)
        self.settings_page = SettingsPage(self)
        self.about_page = AboutPage(self)

        self.stack.add_named(self.startup_page, "startup")
        self.stack.add_named(self.background_page, "background")
        self.stack.add_named(self.settings_page, "settings")
        self.stack.add_named(self.about_page, "about")

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.set_hexpand(True)
        content_box.set_vexpand(True)
        content_box.append(self.stack)

        root.append(sidebar)
        root.append(content_box)
        self.set_child(root)

        self._on_sidebar_select("startup")

        GLib.idle_add(self._initial_refresh)

        try:
            apply_theme(self, self.settings.get("theme"))
        except Exception as e:
            log.exception("Unhandled exception")

    # -----------------------------------------------------------------

    def _on_sidebar_select(self, key):
        try:
            self.stack.set_visible_child_name(key)
            if hasattr(self.background_page, "_active"):
                pause = self.settings.get("pause_background_when_hidden", True)
                self.background_page._active = (key == "background") or not pause
        except Exception:
            return

        page = {
            "startup": self.startup_page,
            "background": self.background_page,
            "settings": self.settings_page,
            "about": self.about_page,
        }.get(key)

        if page and hasattr(page, "refresh"):
            try:
                page.refresh()
            except Exception as e:
                log.exception("Unhandled exception")

    def _on_search_changed(self, entry):
        text = entry.get_text().strip().lower()
        visible = self.stack.get_visible_child()
        try:
            if hasattr(visible, "on_search"):
                visible.on_search(text)
        except Exception as e:
            log.exception("Unhandled exception")

    def _on_refresh(self):
        for p in (
            self.startup_page,
            self.background_page,
            self.settings_page,
            self.about_page,
        ):
            try:
                if hasattr(p, "refresh"):
                    p.refresh()
            except Exception as e:
                log.exception("Error refreshing page")

    def _on_help(self, _btn):
        try:
            from .help_window import HelpWindow
            HelpWindow(self).present()
        except Exception as e:
            log.exception("Unhandled exception")

    def _initial_refresh(self):
        try:
            self.startup_page.refresh()
            self.background_page.refresh()
        except Exception as e:
            log.exception("Unhandled exception")
        return False
