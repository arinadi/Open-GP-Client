# Open GP Client

[![Build and Release](https://github.com/arinadi/Open-GP-Client/actions/workflows/build.yml/badge.svg)](https://github.com/arinadi/Open-GP-Client/actions/workflows/build.yml)

A lightweight GNOME desktop client for **GlobalProtect VPN**, built with GTK4 + Libadwaita.  
Wraps the open-source [`gpclient`/`gpauth`](https://github.com/yuezk/GlobalProtect-openconnect) CLI tools.

## Features

- 🖱️ **One-click connect** — Click Connect, authenticate via browser SSO, done
- 🔐 **Polkit integration** — GUI password prompt (no terminal sudo needed)
- 🌐 **Auto gateway selection** — Automatically picks the first available gateway
- 🎨 **Native GNOME look** — Libadwaita, respects system dark/light theme
- 📋 **Connection log** — Expandable log panel for troubleshooting
- ⚙️ **Config persistence** — Remembers portal address (`~/.config/open-gp/`)
- 📦 **Zero dependencies** — Only uses Python stdlib + PyGObject (pre-installed on GNOME)

## Prerequisites

- Python 3.10+
- GTK4 + Libadwaita (`python3-gobject`, `gtk4`, `libadwaita`)
- [`gpclient` + `gpauth`](https://github.com/yuezk/GlobalProtect-openconnect) v2.x

On **Fedora**:
```bash
# gpclient/gpauth (see https://github.com/yuezk/GlobalProtect-openconnect#installation)
# PyGObject + GTK4 are pre-installed on GNOME Fedora
```

On **Ubuntu/Debian**:
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 gir1.2-adw-1
```

## Usage

### Run directly
```bash
cd /path/to/parent/folder
python3 -m gp_connect
```

### Install system-wide
```bash
sudo make install
```

Then search **"Open GP"** in GNOME Activities and click the icon.

### Uninstall
```bash
sudo make uninstall
```

## Project Structure

```
Open_GP_Client/
├── __init__.py       # Package metadata
├── __main__.py       # Entry point
├── app.py            # Adw.Application
├── window.py         # Main window UI
├── client.py         # GPClient (gpclient/gpauth wrapper)
├── config.py         # Config persistence
├── open-gp-client.desktop   # Desktop launcher
├── Makefile          # Install/uninstall
└── README.md
```

## How It Works

1. **Authenticate** — Runs `gpauth <portal> --browser default`, opens your browser for SSO
2. **Connect** — Pipes auth cookie to `gpclient connect --cookie-on-stdin` via pseudo-TTY
3. **Auto-select gateway** — Detects gateway prompt, selects first option automatically

## Build Packages

The project uses dynamic versioning: `v1.[commit-count]`.

### Fedora RPM
```bash
make rpm
# Output: ~/rpmbuild/RPMS/noarch/open-gp-client-1.*.noarch.rpm
sudo dnf install ~/rpmbuild/RPMS/noarch/open-gp-client-*.rpm
```

### Debian/Ubuntu DEB
```bash
make deb
# Output: open-gp-client_1.*_all.deb
sudo dpkg -i open-gp-client_*.deb
```

## GitHub Releases
Every commit to `main` automatically triggers a build and creates/updates a [Release](https://github.com/arinadi/Open-GP-Client/releases) with `.deb` and `.rpm` artifacts.

## License

GPL-3.0 — Same as [GlobalProtect-openconnect](https://github.com/yuezk/GlobalProtect-openconnect).
