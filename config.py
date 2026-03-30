"""Configuration persistence for Open GP Client."""

import json
import os
from pathlib import Path

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "open-gp"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "portal": "netportal.gameloft.com",
    "browser": "default",
    "fix_openssl": False,
    "ignore_tls_errors": False,
}


class Config:
    """Manages app configuration with JSON persistence."""

    def __init__(self):
        self._data = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        """Load config from disk, falling back to defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    saved = json.load(f)
                self._data.update(saved)
            except (json.JSONDecodeError, OSError):
                pass

    def save(self):
        """Persist current config to disk."""
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self._data, f, indent=2)

    @property
    def portal(self) -> str:
        return self._data.get("portal", DEFAULT_CONFIG["portal"])

    @portal.setter
    def portal(self, value: str):
        self._data["portal"] = value.strip()
        self.save()

    @property
    def browser(self) -> str:
        return self._data.get("browser", DEFAULT_CONFIG["browser"])

    @browser.setter
    def browser(self, value: str):
        self._data["browser"] = value
        self.save()

    @property
    def fix_openssl(self) -> bool:
        return self._data.get("fix_openssl", False)

    @property
    def ignore_tls_errors(self) -> bool:
        return self._data.get("ignore_tls_errors", False)
