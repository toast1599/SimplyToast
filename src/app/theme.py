from gi.repository import Gtk, Gdk
from .config import CSS_DIR

current_provider = None

def apply_theme(window, theme_name):
    global current_provider

    css_path = CSS_DIR / f"{theme_name}.css"
    if not css_path.exists():
        # optional debug
        # print("Theme CSS NOT FOUND:", css_path)
        return

    display = Gdk.Display.get_default()
    if display is None:
        # print("ERROR: No Gdk.Display available")
        return

    if current_provider is not None:
        try:
            Gtk.StyleContext.remove_provider_for_display(display, current_provider)
        except Exception:
            pass

    provider = Gtk.CssProvider()
    provider.load_from_path(str(css_path))

    Gtk.StyleContext.add_provider_for_display(
        display,
        provider,
        Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )

    current_provider = provider
