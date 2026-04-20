"""Main window for Open GP Client — Generic GTK GlobalProtect VPN Client."""

import threading

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, GLib, Gtk, Pango  # noqa: E402

from .client import GPClient, VPNState
import logging

logger = logging.getLogger("open-gp-client.window")
  # noqa: E402
from .config import Config  # noqa: E402


class OpenGPWindow(Gtk.ApplicationWindow):
    """Main application window mimicking the GP Connect GUI style."""

    def __init__(self, **kwargs):
        logger.debug("Initializing OpenGPWindow")
        super().__init__(**kwargs)
        self.set_title("Open GP Client")
        self.set_default_size(500, 400)

        logger.debug("Loading config")
        self.config = Config()
        logger.debug("Initializing GPClient")
        self.client = GPClient()
        self._vpn_thread: threading.Thread | None = None

        self.set_title("Open GP Client")
        self.set_default_size(300, 420)
        self.set_resizable(False)

        self._build_ui()
        self._sync_ui_to_state()
        logger.debug("OpenGPWindow initialization complete. No auto-connect should happen.")
        
        # Prevent accidental clicks from leaked Enter keypresses when launching via terminal
        GLib.timeout_add(500, self._set_ready)

    def _set_ready(self):
        self._is_ready = True
        return False

    def _build_ui(self):
        """Construct the full widget tree."""

        # --- Header Bar ---
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        self.set_titlebar(header)

        # --- Main Content ---
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        main_box.set_margin_start(24)
        main_box.set_margin_end(24)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(24)

        # Shield icon area
        self.shield_icon = Gtk.Image()
        self.shield_icon.set_from_icon_name("security-medium-symbolic")
        self.shield_icon.set_pixel_size(80)
        self.shield_icon.add_css_class("shield-icon")
        self.shield_icon.set_margin_top(16)
        self.shield_icon.set_margin_bottom(8)
        main_box.append(self.shield_icon)

        # Portal name label
        self.portal_label = Gtk.Label()
        self.portal_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.portal_label.set_max_width_chars(25)
        self.portal_label.add_css_class("title-3")
        self.portal_label.set_margin_bottom(4)
        main_box.append(self.portal_label)

        # Status label
        self.status_label = Gtk.Label(label="Not Connected")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_bottom(24)
        main_box.append(self.status_label)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sep.set_margin_bottom(16)
        main_box.append(sep)

        # Portal address field
        portal_frame_label = Gtk.Label(label="Portal address")
        portal_frame_label.set_halign(Gtk.Align.START)
        portal_frame_label.add_css_class("dim-label")
        portal_frame_label.add_css_class("caption")
        portal_frame_label.set_margin_bottom(6)
        main_box.append(portal_frame_label)

        # Entry row with globe icon
        entry_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        entry_box.add_css_class("card")
        entry_box.set_margin_bottom(16)

        globe_icon = Gtk.Image.new_from_icon_name("network-workgroup-symbolic")
        globe_icon.set_margin_start(12)
        globe_icon.set_margin_top(8)
        globe_icon.set_margin_bottom(8)
        globe_icon.add_css_class("accent")
        entry_box.append(globe_icon)

        self.portal_entry = Gtk.Entry()
        self.portal_entry.set_text(self.config.portal)
        self.portal_entry.set_hexpand(True)
        self.portal_entry.set_has_frame(False)
        self.portal_entry.set_margin_top(4)
        self.portal_entry.set_margin_bottom(4)
        self.portal_entry.set_margin_end(8)
        entry_box.append(self.portal_entry)

        main_box.append(entry_box)

        # Connect/Disconnect button
        self.action_button = Gtk.Button(label="Connect")
        self.action_button.add_css_class("suggested-action")
        self.action_button.add_css_class("pill")
        self.action_button.set_margin_bottom(16)
        self.action_button.connect("clicked", self._on_action_clicked)
        main_box.append(self.action_button)

        # Log area (expandable)
        log_expander = Gtk.Expander(label="Connection Log")
        log_expander.set_margin_top(8)

        log_scroll = Gtk.ScrolledWindow()
        log_scroll.set_min_content_height(100)
        log_scroll.set_max_content_height(150)
        log_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_cursor_visible(False)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.log_view.add_css_class("monospace")
        self.log_view.set_top_margin(8)
        self.log_view.set_bottom_margin(8)
        self.log_view.set_left_margin(8)
        self.log_view.set_right_margin(8)
        self.log_buffer = self.log_view.get_buffer()
        log_scroll.set_child(self.log_view)
        log_expander.set_child(log_scroll)
        main_box.append(log_expander)

        # Spacer to push content up
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        main_box.append(spacer)

        # Version label at bottom
        import open_gp_client
        version_label = Gtk.Label(label=f"v{open_gp_client.__version__}")
        version_label.set_halign(Gtk.Align.START)
        version_label.add_css_class("dim-label")
        version_label.add_css_class("caption")
        main_box.append(version_label)

        # --- Assemble ---
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        content_box.append(main_box)
        self.set_child(content_box)

        # --- CSS ---
        css_provider = Gtk.CssProvider()
        css_provider.load_from_string("""
            .title { font-weight: bold; }
            .title-3 { font-size: 1.2rem; font-weight: bold; }
            .dim-label { opacity: 0.55; }
            .caption { font-size: 0.85rem; }
            .card {
                background-color: alpha(currentColor, 0.05);
                border-radius: 8px;
                border: 1px solid alpha(currentColor, 0.1);
            }
            .pill { border-radius: 9999px; }
            .suggested-action {
                background-color: @accent_bg_color;
                color: @accent_fg_color;
            }
            .destructive-action {
                background-color: @error_bg_color;
                color: @error_fg_color;
            }
            @keyframes pulse {
                0% { opacity: 1.0; }
                50% { opacity: 0.4; }
                100% { opacity: 1.0; }
            }
            .shield-icon {
                color: @accent_color;
            }
            .shield-icon.disconnected {
                color: alpha(currentColor, 0.4);
            }
            .shield-icon.connected {
                color: @success_color;
            }
            .shield-icon.connecting {
                color: @warning_color;
                animation: pulse 1.5s ease-in-out infinite;
            }
            .shield-icon.error {
                color: @error_color;
            }
        """)
        Gtk.StyleContext.add_provider_for_display(
            self.get_display(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def _sync_ui_to_state(self):
        """Update all UI elements to match current VPN state."""
        state = self.client.state
        portal = self.portal_entry.get_text().strip()

        # Portal label
        if portal:
            # Show a short name derived from the portal
            short_name = portal.split(".")[0].replace("net", "").replace("portal", "").title()
            if not short_name:
                short_name = portal.split(".")[0].title()
            self.portal_label.set_text(short_name)
        else:
            self.portal_label.set_text("")

        # Shield icon classes
        for cls in ("disconnected", "connected", "connecting", "error"):
            self.shield_icon.remove_css_class(cls)

        # State-specific UI
        match state:
            case VPNState.DISCONNECTED:
                self.status_label.set_text("Not Connected")
                self.shield_icon.set_from_icon_name("security-medium-symbolic")
                self.shield_icon.add_css_class("disconnected")
                self.action_button.set_label("Connect")
                self.action_button.remove_css_class("destructive-action")
                self.action_button.add_css_class("suggested-action")
                self.action_button.set_sensitive(True)
                self.portal_entry.set_sensitive(True)

            case VPNState.AUTHENTICATING:
                self.status_label.set_text("Authenticating...")
                self.shield_icon.set_from_icon_name("dialog-password-symbolic")
                self.shield_icon.add_css_class("connecting")
                self.action_button.set_label("Cancel")
                self.action_button.remove_css_class("suggested-action")
                self.action_button.add_css_class("destructive-action")
                self.portal_entry.set_sensitive(False)

            case VPNState.CONNECTING:
                self.status_label.set_text("Connecting...")
                self.shield_icon.set_from_icon_name("security-medium-symbolic")
                self.shield_icon.add_css_class("connecting")
                self.action_button.set_label("Cancel")
                self.action_button.remove_css_class("suggested-action")
                self.action_button.add_css_class("destructive-action")
                self.portal_entry.set_sensitive(False)

            case VPNState.CONNECTED:
                self.status_label.set_text("Connected")
                self.shield_icon.set_from_icon_name("security-high-symbolic")
                self.shield_icon.add_css_class("connected")
                self.action_button.set_label("Disconnect")
                self.action_button.remove_css_class("suggested-action")
                self.action_button.add_css_class("destructive-action")
                self.action_button.set_sensitive(True)
                self.portal_entry.set_sensitive(False)
                # Auto-minimize when connected
                self.minimize()

            case VPNState.DISCONNECTING:
                self.status_label.set_text("Disconnecting...")
                self.shield_icon.set_from_icon_name("security-medium-symbolic")
                self.shield_icon.add_css_class("connecting")
                self.action_button.set_sensitive(False)
                self.portal_entry.set_sensitive(False)

            case VPNState.ERROR:
                self.status_label.set_text("Connection Failed")
                self.shield_icon.set_from_icon_name("dialog-error-symbolic")
                self.shield_icon.add_css_class("error")
                self.action_button.set_label("Retry")
                self.action_button.remove_css_class("destructive-action")
                self.action_button.add_css_class("suggested-action")
                self.action_button.set_sensitive(True)
                self.portal_entry.set_sensitive(True)

    def _on_action_clicked(self, button):
        """Handle Connect/Disconnect/Cancel button click."""
        if not getattr(self, "_is_ready", False):
            logger.debug("Action button clicked but window is not ready yet. Ignoring.")
            return

        state = self.client.state
        logger.debug(f"Action button clicked. Current state: {state}")

        if state in (VPNState.DISCONNECTED, VPNState.ERROR):
            self._start_connect()
        elif state in (VPNState.AUTHENTICATING, VPNState.CONNECTING, VPNState.CONNECTED):
            self._start_disconnect()

    def _start_connect(self):
        """Begin the connect flow in a background thread."""
        import traceback
        logger.debug("Starting connection flow. Traceback:\n%s", "".join(traceback.format_stack()))
        portal = self.portal_entry.get_text().strip()
        if not portal:
            self._append_log("Error: Portal address is empty.")
            return

        # Save portal to config
        self.config.portal = portal

        # Clear log
        self.log_buffer.set_text("")

        def _on_state_change(state: VPNState):
            GLib.idle_add(self._sync_ui_to_state)

        def _on_output(line: str):
            GLib.idle_add(self._append_log, line)

        def _worker():
            self.client.connect_with_auth(
                server=portal,
                browser=self.config.browser,
                fix_openssl=self.config.fix_openssl,
                ignore_tls_errors=self.config.ignore_tls_errors,
                on_state_change=_on_state_change,
                on_output=_on_output,
            )
            GLib.idle_add(self._sync_ui_to_state)

        self._vpn_thread = threading.Thread(target=_worker, daemon=True)
        self._vpn_thread.start()

    def _start_disconnect(self):
        """Disconnect in a background thread."""
        self.client._state = VPNState.DISCONNECTING
        self._sync_ui_to_state()

        def _on_output(line: str):
            GLib.idle_add(self._append_log, line)

        def _worker():
            self.client.disconnect(on_output=_on_output)
            GLib.idle_add(self._sync_ui_to_state)

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def _append_log(self, text: str):
        """Append a line to the log view."""
        end_iter = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end_iter, text + "\n")
        # Auto-scroll to bottom
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_mark_onscreen(mark)
        self.log_buffer.delete_mark(mark)
