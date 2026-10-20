Name:       rd_client
Version:    1.5.0
Release:    0
Summary:    RPM package
License:    GPL-3.0
URL:        https://rustdesk.com
Vendor:     ZavierCloud <dev@spidercloude.com>
Requires:   gtk3 libxcb1 libXfixes3 alsa-utils libXtst6 libva2 gstreamer-plugins-base gstreamer-plugin-pipewire
Recommends: libayatana-appindicator3-1 xdotool
Provides:   libdesktop_drop_plugin.so()(64bit), libdesktop_multi_window_plugin.so()(64bit), libfile_selector_linux_plugin.so()(64bit), libflutter_custom_cursor_plugin.so()(64bit), libflutter_linux_gtk.so()(64bit), libscreen_retriever_plugin.so()(64bit), libtray_manager_plugin.so()(64bit), liburl_launcher_linux_plugin.so()(64bit), libwindow_manager_plugin.so()(64bit), libwindow_size_plugin.so()(64bit), libtexture_rgba_renderer_plugin.so()(64bit)

# https://docs.fedoraproject.org/en-US/packaging-guidelines/Scriptlets/

%description
The best open-source remote desktop client software, written in Rust.

%prep
# we have no source, so nothing here

%build
# we have no source, so nothing here

# %global __python %{__python3}

%install

mkdir -p "%{buildroot}/usr/share/rd_client" && cp -r ${HBB}/flutter/build/linux/x64/release/bundle/* -t "%{buildroot}/usr/share/rd_client"
mkdir -p "%{buildroot}/usr/bin"
install -Dm 644 $HBB/res/rd_client.service -t "%{buildroot}/usr/share/rd_client/files"
install -Dm 644 $HBB/res/rd_client.desktop -t "%{buildroot}/usr/share/rd_client/files"
install -Dm 644 $HBB/res/rd_client-link.desktop -t "%{buildroot}/usr/share/rd_client/files"
install -Dm 644 $HBB/res/128x128@2x.png "%{buildroot}/usr/share/icons/hicolor/256x256/apps/rd_client.png"
install -Dm 644 $HBB/res/scalable.svg "%{buildroot}/usr/share/icons/hicolor/scalable/apps/rd_client.svg"

%files
/usr/share/rd_client/*
/usr/share/rd_client/files/rd_client.service
/usr/share/icons/hicolor/256x256/apps/rd_client.png
/usr/share/icons/hicolor/scalable/apps/rd_client.svg
/usr/share/rd_client/files/rd_client.desktop
/usr/share/rd_client/files/rd_client-link.desktop

%changelog
# let's skip this for now

%pre
# can do something for centos7
case "$1" in
  1)
    # for install
  ;;
  2)
    # for upgrade
    systemctl stop rd_client || true
  ;;
esac

%post
cp /usr/share/rd_client/files/rd_client.service /etc/systemd/system/rd_client.service
cp /usr/share/rd_client/files/rd_client.desktop /usr/share/applications/
cp /usr/share/rd_client/files/rd_client-link.desktop /usr/share/applications/
ln -sf /usr/share/rd_client/rd_client /usr/bin/rd_client
systemctl daemon-reload
systemctl enable rd_client
systemctl start rd_client
update-desktop-database

%preun
case "$1" in
  0)
    # for uninstall
    systemctl stop rd_client || true
    systemctl disable rd_client || true
    rm /etc/systemd/system/rd_client.service || true
  ;;
  1)
    # for upgrade
  ;;
esac

%postun
case "$1" in
  0)
    # for uninstall
    rm /usr/bin/rd_client || true
    rmdir /usr/lib/rd_client || true
    rmdir /usr/local/rd_client || true
    rmdir /usr/share/rd_client || true
    rm /usr/share/applications/rd_client.desktop || true
    rm /usr/share/applications/rd_client-link.desktop || true
    update-desktop-database
  ;;
  1)
    # for upgrade
    rmdir /usr/lib/rd_client || true
    rmdir /usr/local/rd_client || true
  ;;
esac
