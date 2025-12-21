import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

from ..settings import load_settings, save_settings
from ..theme import apply_theme


# pages are expected to be created under app.windows.pages
try:
    from .pages.startup_page import StartupPage
    from .pages.background_page import BackgroundPage
    from .pages.settings_page import SettingsPage
    from .pages.about_page import AboutPage
except Exception as e:
    print("IMPORT ERROR while loading pages:")
    import traceback
    traceback.print_exc()
    raise

    class BackgroundPage(Gtk.Box):
        def __init__(self, parent):
            super().__init__(orientation=Gtk.Orientation.VERTICAL)
            self.append(Gtk.Label(label="Background page not yet implemented"))
        def refresh(self): pass
        def on_search(self, text): pass

    class SettingsPage(Gtk.Box):
        def __init__(self, parent):
            super().__init__(orientation=Gtk.Orientation.VERTICAL)
            self.append(Gtk.Label(label="Settings page not yet implemented"))
        def refresh(self): pass

    class AboutPage(Gtk.Box):
        def __init__(self, parent):
            super().__init__(orientation=Gtk.Orientation.VERTICAL)
            self.append(Gtk.Label(label="About page not yet implemented"))
        def refresh(self): pass


class ToastWindow(Gtk.Window):
    SIDEBAR_WIDTH = 240

    def refresh_autostart(self):
        try:
            if hasattr(self, "startup_page"):
                self.startup_page.refresh()
        except Exception as e:
            print("Failed to refresh startup page:", e)

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

        pop = Gtk.Popover()
        menu_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                           margin_top=6, margin_bottom=6,
                           margin_start=6, margin_end=6)
        btn_help = Gtk.Button(label="Help & Support")
        btn_help.connect("clicked", self._on_help)
        menu_box.append(btn_help)
        pop.set_child(menu_box)
        self.menu_button.set_popover(pop)
        hb.pack_start(self.menu_button)

        # Search in header
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search…")
        self.search_entry.connect("search-changed", self._on_search_changed)
        hb.pack_start(self.search_entry)

        # Refresh button on right
        self.refresh_btn = Gtk.Button()
        icon_refresh = Gtk.Image.new_from_icon_name("view-refresh-symbolic")
        icon_refresh.set_pixel_size(18)
        self.refresh_btn.set_child(icon_refresh)
        self.refresh_btn.connect("clicked", lambda *_: self._on_refresh())
        hb.pack_end(self.refresh_btn)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)

        # Sidebar (fixed-ish width)
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sidebar.set_margin_top(12)
        sidebar.set_margin_bottom(12)
        sidebar.set_margin_start(12)
        sidebar.set_margin_end(12)
        sidebar.set_size_request(self.SIDEBAR_WIDTH, -1)

        def make_sidebar_button(icon_name, label_text, key):
            btn = Gtk.Button()
            btn.set_halign(Gtk.Align.FILL)
            btn.set_hexpand(False)
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            img = Gtk.Image.new_from_icon_name(icon_name)
            img.set_pixel_size(18)
            lbl = Gtk.Label(label=label_text, xalign=0.0)
            box.append(img)
            box.append(lbl)
            btn.set_child(box)
            btn.connect("clicked", lambda *_: self._on_sidebar_select(key))
            return btn

        # Top buttons
        btn_startup = make_sidebar_button("media-playback-start-symbolic", "Startup Apps", "startup")
        btn_background = make_sidebar_button("system-run-symbolic", "Background Apps", "background")

        sidebar.append(btn_startup)
        sidebar.append(btn_background)
        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Spacer to push bottom buttons down
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        sidebar.append(spacer)

        # Bottom Buttons (Settings + About)
        btn_settings_bottom = make_sidebar_button("emblem-system-symbolic", "Settings", "settings")
        btn_about = make_sidebar_button("help-about-symbolic", "About", "about")

        sidebar.append(btn_settings_bottom)
        sidebar.append(btn_about)

        # Content stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        # create page instances BEFORE selecting anything
        self.startup_page = StartupPage(self)
        self.background_page = BackgroundPage(self)
        self.settings_page = SettingsPage(self)
        self.about_page = AboutPage(self)

        # register pages in the stack
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

        # select default page after pages exist
        self._on_sidebar_select("startup")

        # initial refresh of pages that implement refresh()
        GLib.idle_add(self._initial_refresh)

        # apply theme if applicable (safe no-op if css disabled)
        try:
            apply_theme(self, self.settings.get("theme"))
        except Exception as e:
            print('[ERROR] Unhandled exception:', e)

    def _on_sidebar_select(self, key):
        """Switch visible page and call refresh if available."""
        # attempt to switch the visible child; if the name isn't registered,
        # set_visible_child_name may raise — handle that safely.
        try:
            self.stack.set_visible_child_name(key)
            # pause background refresh unless visible
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
                print('[ERROR] Unhandled exception:', e)

    def _on_search_changed(self, entry):
        text = entry.get_text().strip().lower()
        visible = self.stack.get_visible_child()
        try:
            if hasattr(visible, "on_search"):
                visible.on_search(text)
        except Exception as e:
            print('[ERROR] Unhandled exception:', e)

    def _on_refresh(self):
        """Delegate refresh to all pages that implement `refresh()`."""
        for p in (self.startup_page, self.background_page, self.settings_page, self.about_page):
            try:
                if hasattr(p, "refresh"):
                    p.refresh()
            except Exception as e:
                # keep it visible for debugging during development
                print("Error refreshing page:", getattr(p, '__class__', p), e)

    def _on_help(self, _btn):
        try:
            from .help_window import HelpWindow
            HelpWindow(self).present()
        except Exception as e:
            print('[ERROR] Unhandled exception:', e)

    def _initial_refresh(self):
        try:
            self.startup_page.refresh()
            self.background_page.refresh()
        except Exception as e:
            print('[ERROR] Unhandled exception:', e)
        return False
