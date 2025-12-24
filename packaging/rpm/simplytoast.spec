Name:           simplytoast
Version:        0.0.0
Release:        1%{?dist}
Summary:        Startup & background application manager

License:        GPL-3.0-or-later
URL:            https://github.com/toast1599/SimplyToast
Source0:        artifact.tar.gz

Requires:       python3
Requires:       python3-gobject
Requires:       gtk4

%description
SimplyToast is a GTK 4 utility for managing startup and background
applications on Linux systems.

%prep
%setup -q -c -T
tar -xzf %{SOURCE0}

%install
mkdir -p %{buildroot}/usr/lib/simplytoast
cp -r src data %{buildroot}/usr/lib/simplytoast

# Launcher
mkdir -p %{buildroot}/usr/bin
cat > %{buildroot}/usr/bin/simplytoast <<'EOF'
#!/usr/bin/env bash
export PYTHONPATH="/usr/lib/simplytoast${PYTHONPATH:+:$PYTHONPATH}"
exec python3 /usr/lib/simplytoast/src/main.py "$@"
EOF
chmod 755 %{buildroot}/usr/bin/simplytoast

# Desktop + metadata
mkdir -p %{buildroot}/usr/share/applications
install -m 644 data/com.toast1599.SimplyToast.desktop \
  %{buildroot}/usr/share/applications/com.toast1599.SimplyToast.desktop

mkdir -p %{buildroot}/usr/share/metainfo
install -m 644 data/com.toast1599.SimplyToast.appdata.xml \
  %{buildroot}/usr/share/metainfo/com.toast1599.SimplyToast.appdata.xml

mkdir -p %{buildroot}/usr/share/icons/hicolor/512x512/apps
install -m 644 data/icons/com.toast1599.SimplyToast-512.png \
  %{buildroot}/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png

%files
/usr/bin/simplytoast
/usr/lib/simplytoast
/usr/share/applications/*
/usr/share/metainfo/*
/usr/share/icons/hicolor/512x512/apps/*

%changelog
* Tue Dec 23 2025 toast1599 - 0.0.0-1
- Initial RPM release
