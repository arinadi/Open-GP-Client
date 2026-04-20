import gi

gi.require_version("Gtk", "4.0")

import sys
import logging
from gi.repository import Gio, GLib, Gtk  # noqa: E402

# Configure logging to stdout
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger("open-gp-client")

def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logger.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))

sys.excepthook = handle_exception

from . import __app_id__, __app_name__, __version__  # noqa: E402
from .window import OpenGPWindow  # noqa: E402


class OpenGPApp(Gtk.Application):
    """Main application class — generic GTK version."""

    def __init__(self):
        logger.debug("Initializing OpenGPApp")
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
        logger.debug("Application activated")
        win = self.props.active_window
        if not win:
            logger.debug("Creating new window")
            win = OpenGPWindow(application=self)
        win.present()
        logger.debug("Window presented")

    def _on_about(self, action, param):
        """Show about dialog."""
        about = Gtk.AboutDialog(
            program_name=__app_name__,
            logo_icon_name="open-gp-client",
            version=__version__,
            authors=["Open GP Client Team"],
            comments="A generic GTK client for GlobalProtect VPN.\nWraps gpclient/gpauth CLI tools.",
            website="https://github.com/yuezk/GlobalProtect-openconnect",
            license_type=Gtk.License.GPL_3_0,
        )
        about.set_transient_for(self.props.active_window)
        about.present()
