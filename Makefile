APP_NAME      = open-gp-client
MAJOR_VERSION = 1
COMMIT_COUNT  = $(shell git rev-list --count HEAD 2>/dev/null || echo 0)
VERSION       = $(MAJOR_VERSION).$(COMMIT_COUNT)

DESTDIR    ?=
PREFIX     ?= /usr/local
INSTALL_DIR = $(PREFIX)/lib/$(APP_NAME)
BIN_DIR     = $(PREFIX)/bin
DESKTOP_DIR = $(PREFIX)/share/applications
ICON_DIR    = $(PREFIX)/share/icons/hicolor/512x512/apps
PYTHON_SRC  = __init__.py __main__.py app.py window.py client.py config.py

.PHONY: install uninstall rpm deb clean

# ─── Install / Uninstall ──────────────────────────────────────────

install:
	@echo "Installing $(APP_NAME) to $(DESTDIR)$(INSTALL_DIR)..."
	install -d $(DESTDIR)$(INSTALL_DIR)
	install -m 644 $(PYTHON_SRC) $(DESTDIR)$(INSTALL_DIR)/
	install -d $(DESTDIR)$(BIN_DIR)
	@echo '#!/bin/sh' > $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	@echo 'exec python3 -m open_gp_client "$$@"' >> $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	chmod 755 $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	@# Python package wrapper logic
	install -d $(DESTDIR)$(PREFIX)/lib/python3/dist-packages/open_gp_client
	install -m 644 $(PYTHON_SRC) $(DESTDIR)$(PREFIX)/lib/python3/dist-packages/open_gp_client/
	@# Desktop and Icon
	install -Dm 644 open-gp-client.desktop $(DESTDIR)$(DESKTOP_DIR)/$(APP_NAME).desktop
	install -Dm 644 open-gp-client.png $(DESTDIR)$(ICON_DIR)/$(APP_NAME).png
	@# Fix Exec and Icon lines in installed desktop file
	sed -i 's|Exec=.*|Exec=$(BIN_DIR)/$(APP_NAME)|' $(DESTDIR)$(DESKTOP_DIR)/$(APP_NAME).desktop
	sed -i 's|Icon=.*|Icon=$(APP_NAME)|' $(DESTDIR)$(DESKTOP_DIR)/$(APP_NAME).desktop
	@# Database updates (only if absolute install, skip for buildroot)
	[ -z "$(DESTDIR)" ] && update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	[ -z "$(DESTDIR)" ] && gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor 2>/dev/null || true
	@echo "✅ Installed. Launch from GNOME Activities or run: $(APP_NAME)"

uninstall:
	@echo "Removing $(APP_NAME)..."
	rm -rf $(DESTDIR)$(INSTALL_DIR)
	rm -rf $(DESTDIR)$(PREFIX)/lib/python3/dist-packages/open_gp_client
	rm -f $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	rm -f $(DESTDIR)$(DESKTOP_DIR)/$(APP_NAME).desktop
	rm -f $(DESTDIR)$(ICON_DIR)/$(APP_NAME).png
	[ -z "$(DESTDIR)" ] && update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@echo "✅ Uninstalled."

# ─── RPM Build (Fedora) ──────────────────────────────────────────

rpm:
	@echo "Building RPM..."
	mkdir -p ~/rpmbuild/{SPECS,SOURCES,BUILD,RPMS,SRPMS}
	@# Create tarball
	mkdir -p /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)
	cp $(PYTHON_SRC) open-gp-client.desktop open-gp-client.png Makefile README.md /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)/
	tar czf ~/rpmbuild/SOURCES/$(APP_NAME)-$(VERSION).tar.gz -C /tmp $(APP_NAME)-$(VERSION)
	rm -rf /tmp/$(APP_NAME)-$(VERSION)
	@# Generate spec
	@echo 'Name:           $(APP_NAME)' > ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Version:        $(VERSION)' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Release:        1%{?dist}' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Summary:        GNOME GlobalProtect VPN Client' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'License:        GPL-3.0' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'BuildArch:      noarch' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Requires:       python3-gobject gtk4 libadwaita globalprotect-openconnect' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Source0:        %{name}-%{version}.tar.gz' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%description' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'A lightweight GNOME desktop client for GlobalProtect VPN.' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%prep' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%setup -q' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%install' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'cd $(APP_NAME) && make install DESTDIR=%{buildroot} PREFIX=/usr' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%post' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'update-desktop-database /usr/share/applications &>/dev/null || :' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || :' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%postun' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'update-desktop-database /usr/share/applications &>/dev/null || :' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || :' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%files' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/lib/$(APP_NAME)/' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/lib/python3/dist-packages/open_gp_client/' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/bin/$(APP_NAME)' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/share/applications/$(APP_NAME).desktop' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/share/icons/hicolor/512x512/apps/$(APP_NAME).png' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	rpmbuild -bb ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo "✅ RPM built: ~/rpmbuild/RPMS/noarch/"

# ─── DEB Build (Debian/Ubuntu) ───────────────────────────────────

deb:
	@echo "Building DEB..."
	mkdir -p /tmp/$(APP_NAME)_$(VERSION)/DEBIAN
	@echo 'Package: $(APP_NAME)' > /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Version: $(VERSION)' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Architecture: all' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Maintainer: Open GP' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Depends: python3, python3-gi, gir1.2-gtk-4.0, gir1.2-adw-1' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Description: GNOME GlobalProtect VPN Client' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo ' A lightweight GNOME desktop client for GlobalProtect VPN.' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@# Postinst/Prerm for DEB
	@echo '#!/bin/sh' > /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/postinst
	@echo 'update-desktop-database /usr/share/applications &>/dev/null || :' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/postinst
	@echo 'gtk-update-icon-cache -f -t /usr/share/icons/hicolor &>/dev/null || :' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/postinst
	chmod 755 /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/postinst
	make install DESTDIR=/tmp/$(APP_NAME)_$(VERSION) PREFIX=/usr
	dpkg-deb --build /tmp/$(APP_NAME)_$(VERSION) ./$(APP_NAME)_$(VERSION)_all.deb
	rm -rf /tmp/$(APP_NAME)_$(VERSION)
	@echo "✅ DEB built: ./$(APP_NAME)_$(VERSION)_all.deb"

clean:
	rm -f *.deb
	rm -rf ~/rpmbuild/SPECS/$(APP_NAME).spec
	rm -rf ~/rpmbuild/SOURCES/$(APP_NAME)-*.tar.gz
