APP_NAME      = open-gp-client
MAJOR_VERSION = 1
COMMIT_COUNT  = $(shell git rev-list --count HEAD 2>/dev/null || echo 0)
VERSION       = $(MAJOR_VERSION).$(COMMIT_COUNT)
# Dynamic release based on timestamp for local build uniqueness
RELEASE_SUFFIX = $(shell date +%H%M%S)

DESTDIR    ?=
PREFIX     ?= /usr/local
INSTALL_DIR = $(PREFIX)/lib/$(APP_NAME)
BIN_DIR     = $(PREFIX)/bin
DESKTOP_DIR = $(PREFIX)/share/applications
ICON_DIR    = $(PREFIX)/share/icons/hicolor/512x512/apps
PYTHON_SRC  = __init__.py __main__.py app.py window.py client.py config.py
DEP_REPO    = https://github.com/yuezk/GlobalProtect-openconnect
DEP_DIR     = GlobalProtect-openconnect
BIN_DIR_LOCAL = bin
ARCH        = $(shell uname -m)

.PHONY: install uninstall cleanup-legacy rpm deb clean pull-deps

# ─── Dependencies ───────────────────────────────────────────────

pull-deps:
	@echo "Pulling latest dependencies from $(DEP_REPO)..."
	@if [ -d "$(DEP_DIR)" ]; then \
		cd $(DEP_DIR) && git pull; \
	else \
		git clone $(DEP_REPO) $(DEP_DIR); \
	fi

fetch-binaries:
	@echo "Fetching pre-built binaries for $(ARCH)..."
	@mkdir -p $(BIN_DIR_LOCAL)
	@# Find latest version tag
	$(eval LATEST_TAG=$(shell curl -s https://api.github.com/repos/yuezk/GlobalProtect-openconnect/releases/latest | grep tag_name | cut -d '"' -f 4 | sed 's/v//'))
	@echo "Latest version: v$(LATEST_TAG)"
	@if [ ! -f "$(BIN_DIR_LOCAL)/gpclient" ]; then \
		curl -L -o /tmp/gp_bin.tar.xz https://github.com/yuezk/GlobalProtect-openconnect/releases/download/v$(LATEST_TAG)/globalprotect-openconnect_$(LATEST_TAG)_$(ARCH).bin.tar.xz; \
		tar -xJf /tmp/gp_bin.tar.xz -C /tmp; \
		cp /tmp/globalprotect-openconnect_$(LATEST_TAG)/artifacts/usr/bin/gpclient $(BIN_DIR_LOCAL)/; \
		cp /tmp/globalprotect-openconnect_$(LATEST_TAG)/artifacts/usr/bin/gpauth $(BIN_DIR_LOCAL)/; \
		cp /tmp/globalprotect-openconnect_$(LATEST_TAG)/artifacts/usr/bin/gpservice $(BIN_DIR_LOCAL)/; \
		chmod +x $(BIN_DIR_LOCAL)/*; \
		rm /tmp/gp_bin.tar.xz; \
		rm -rf /tmp/globalprotect-openconnect_$(LATEST_TAG); \
	fi

# ─── Install / Uninstall ──────────────────────────────────────────

install: fetch-binaries
	@echo "Installing $(APP_NAME) to $(DESTDIR)$(INSTALL_DIR)..."
	@# Install Python source to private directory
	install -d $(DESTDIR)$(INSTALL_DIR)/open_gp_client
	install -m 644 $(PYTHON_SRC) $(DESTDIR)$(INSTALL_DIR)/open_gp_client/
	@# Install bundled binaries
	install -d $(DESTDIR)$(INSTALL_DIR)/bin
	install -m 755 $(BIN_DIR_LOCAL)/* $(DESTDIR)$(INSTALL_DIR)/bin/
	@# Create wrapper script with explicit PYTHONPATH
	install -d $(DESTDIR)$(BIN_DIR)
	@echo '#!/bin/sh' > $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	@echo 'export PYTHONPATH="$(INSTALL_DIR):$$PYTHONPATH"' >> $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	@echo 'exec python3 -m open_gp_client "$$@"' >> $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	chmod 755 $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	@# Desktop and Icon
	install -Dm 644 open-gp-client.desktop $(DESTDIR)$(DESKTOP_DIR)/com.github.opengp.desktop
	install -Dm 644 open-gp-client.png $(DESTDIR)$(ICON_DIR)/com.github.opengp.png
	@# Fix Exec and Icon lines in installed desktop file
	sed -i 's|Exec=.*|Exec=$(BIN_DIR)/$(APP_NAME)|' $(DESTDIR)$(DESKTOP_DIR)/com.github.opengp.desktop
	sed -i 's|Icon=.*|Icon=com.github.opengp|' $(DESTDIR)$(DESKTOP_DIR)/com.github.opengp.desktop
	@# Database updates (only if absolute install, skip for buildroot)
	[ -z "$(DESTDIR)" ] && update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	[ -z "$(DESTDIR)" ] && gtk-update-icon-cache -f -t $(PREFIX)/share/icons/hicolor 2>/dev/null || true
	@echo "✅ Installed. Launch from GNOME Activities or run: $(APP_NAME)"

uninstall:
	@echo "Removing $(APP_NAME)..."
	rm -rf $(DESTDIR)$(INSTALL_DIR)
	rm -f $(DESTDIR)$(BIN_DIR)/$(APP_NAME)
	rm -f $(DESTDIR)$(DESKTOP_DIR)/$(APP_NAME).desktop
	rm -f $(DESTDIR)$(ICON_DIR)/$(APP_NAME).png
	[ -z "$(DESTDIR)" ] && update-desktop-database $(DESKTOP_DIR) 2>/dev/null || true
	@echo "✅ Uninstalled."

# Deep clean for any old/manual installations
cleanup-legacy:
	@echo "Cleaning up legacy /usr/local or old-style installations (requires sudo for some regions)..."
	rm -rf /usr/local/lib/$(APP_NAME)
	rm -rf /usr/local/lib/python3/dist-packages/open_gp_client
	rm -f /usr/local/bin/$(APP_NAME)
	rm -f /usr/local/share/applications/$(APP_NAME).desktop
	rm -f /usr/local/share/icons/hicolor/512x512/apps/$(APP_NAME).png
	@# Clean up user-local legacy entries
	rm -f $(HOME)/.local/share/applications/open-gp.desktop
	rm -f $(HOME)/.local/share/applications/$(APP_NAME).desktop
	@# Refresh databases
	update-desktop-database /usr/local/share/applications 2>/dev/null || true
	update-desktop-database $(HOME)/.local/share/applications 2>/dev/null || true
	@echo "✅ Legacy cleanup complete. Now run 'make rpm' and reinstall if needed."

# ─── RPM Build (Fedora) ──────────────────────────────────────────

rpm: pull-deps fetch-binaries
	@echo "Building RPM..."
	mkdir -p ~/rpmbuild/{SPECS,SOURCES,BUILD,RPMS,SRPMS}
	@# Create tarball
	mkdir -p /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)
	cp $(PYTHON_SRC) open-gp-client.desktop open-gp-client.png Makefile README.md /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)/
	mkdir -p /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)/$(BIN_DIR_LOCAL)
	cp $(BIN_DIR_LOCAL)/* /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)/$(BIN_DIR_LOCAL)/
	sed -i 's/__version__ = .*/__version__ = "$(VERSION)-1.$(RELEASE_SUFFIX)"/' /tmp/$(APP_NAME)-$(VERSION)/$(APP_NAME)/__init__.py
	tar czf ~/rpmbuild/SOURCES/$(APP_NAME)-$(VERSION).tar.gz -C /tmp $(APP_NAME)-$(VERSION)
	rm -rf /tmp/$(APP_NAME)-$(VERSION)
	@# Generate spec
	@echo 'Name:           $(APP_NAME)' > ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%define debug_package %{nil}' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Version:        $(VERSION)' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Release:        1.$(RELEASE_SUFFIX)%{?dist}' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Summary:        GTK GlobalProtect VPN Client' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'License:        GPL-3.0' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Requires:       python3-gobject gtk4 openconnect webkit2gtk4.1 libsecret' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'Source0:        %{name}-%{version}.tar.gz' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '%description' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo 'A lightweight GTK desktop client for GlobalProtect VPN.' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
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
	@echo '/usr/bin/$(APP_NAME)' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/share/applications/com.github.opengp.desktop' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo '/usr/share/icons/hicolor/512x512/apps/com.github.opengp.png' >> ~/rpmbuild/SPECS/$(APP_NAME).spec
	rpmbuild -bb ~/rpmbuild/SPECS/$(APP_NAME).spec
	@echo "✅ RPM built: ~/rpmbuild/RPMS/noarch/"

# ─── DEB Build (Debian/Ubuntu) ───────────────────────────────────

deb: pull-deps fetch-binaries
	@echo "Building DEB..."
	mkdir -p /tmp/$(APP_NAME)_$(VERSION)/DEBIAN
	@echo 'Package: $(APP_NAME)' > /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Version: $(VERSION)' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Architecture: $(shell dpkg --print-architecture 2>/dev/null || echo "amd64")' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Maintainer: Open GP Client' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Depends: python3, python3-gi, gir1.2-gtk-4.0, openconnect, libwebkit2gtk-4.1-0, libsecret-1-0' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo 'Description: GTK GlobalProtect VPN Client' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
	@echo ' A lightweight GTK desktop client for GlobalProtect VPN.' >> /tmp/$(APP_NAME)_$(VERSION)/DEBIAN/control
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
