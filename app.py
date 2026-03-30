"""Adw.Application subclass for Open GP Client."""


import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib  # noqa: E402

from . import __app_id__, __app_name__, __version__  # noqa: E402
from .window import OpenGPWindow  # noqa: E402


class OpenGPApp(Adw.Application):
    """Main application class — single instance, GNOME integrated."""

    def __init__(self):
        super().__init__(
            application_id=__app_id__,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.set_resource_base_path("/com/github/opengp")

        # Register actions
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

    def do_activate(self):
        """Called when the application is activated."""
        win = self.props.active_window
        if not win:
            win = OpenGPWindow(application=self)
        win.present()

    def _on_about(self, action, param):
        """Show about dialog."""
        about = Adw.AboutDialog(
            application_name=__app_name__,
            application_icon="open-gp-client",
            version=__version__,
            developer_name="Open GP Client",
            comments="A GNOME client for GlobalProtect VPN.\nWraps gpclient/gpauth CLI tools.",
            website="https://github.com/yuezk/GlobalProtect-openconnect",
            license_type=3,  # GPL-3.0
        )
        about.present(self.props.active_window)
