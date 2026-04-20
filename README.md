# Open GP Client

[![Build and Release](https://github.com/arinadi/Open-GP-Client/actions/workflows/build.yml/badge.svg)](https://github.com/arinadi/Open-GP-Client/actions/workflows/build.yml)

A lightweight GTK4 desktop client for **GlobalProtect VPN**, compatible with GNOME, KDE, and other desktop environments.  
Wraps the open-source [`gpclient`/`gpauth`](https://github.com/yuezk/GlobalProtect-openconnect) CLI tools.

## Features

- 🖱️ **One-click connect** — Click Connect, authenticate via built-in browser SSO, done
- 🔐 **Polkit integration** — GUI password prompt (no terminal sudo needed for connect/disconnect)
- 🌐 **Auto gateway selection** — Automatically picks the first available gateway
- 🎨 **Minimalist GTK look** — Clean UI, respects system dark/light theme
- 📋 **Connection log** — Expandable log panel for troubleshooting
- 📦 **Self-contained** — Bundles core `gpclient`/`gpauth` engine binaries
- 🛡️ **Embedded Browser** — Uses WebKitGTK for SSO to prevent GlobalProtect URL scheme hijacking

## Prerequisites

- Python 3.10+
- GTK4, WebKitGTK 4.1, libsecret
- Core engine binaries (automatically bundled via `make rpm`/`make deb`)

On **Fedora**:
```bash
sudo dnf install python3-gobject gtk4 openconnect webkit2gtk4.1 libsecret
```

On **Ubuntu/Debian**:
```bash
sudo apt install python3-gi gir1.2-gtk-4.0 openconnect libwebkit2gtk-4.1-0 libsecret-1-0
```

## Usage

### Run directly
```bash
cd /path/to/Open-GP-Client
export PYTHONPATH=".:$PYTHONPATH"
python3 -m open_gp_client
```

### Install system-wide
```bash
sudo make install
```

Then search **"Open GP Client"** in your application menu and click the icon.

### Uninstall
```bash
sudo make uninstall
```

## How It Works

1. **Authenticate** — Runs `gpauth <portal>`, opening an embedded secure browser for SSO authentication.
2. **Connect** — Pipes auth cookie to `gpclient connect --cookie-on-stdin` via pseudo-TTY.
3. **Auto-select gateway** — Detects gateway prompt, selects first option automatically.
4. **Graceful Disconnect** — Sends a virtual `Ctrl+C` (`SIGINT`) to cleanly tear down the VPN tunnel without requesting root passwords repeatedly.

## Build Packages

The project uses dynamic versioning: `v1.[commit-count]-[timestamp]`.

### Fedora RPM
```bash
make rpm
# Output: ~/rpmbuild/RPMS/x86_64/open-gp-client-1.*.x86_64.rpm
sudo dnf install ~/rpmbuild/RPMS/x86_64/open-gp-client-*.rpm
```

### Debian/Ubuntu DEB
```bash
make deb
# Output: ./open-gp-client_1.*_all.deb
sudo dpkg -i open-gp-client_*.deb
```

## GitHub Releases
Every commit to `main` automatically triggers a build and creates/updates a [Release](https://github.com/arinadi/Open-GP-Client/releases) with `.deb` and `.rpm` artifacts.

## License

GPL-3.0 — Same as [GlobalProtect-openconnect](https://github.com/yuezk/GlobalProtect-openconnect).
