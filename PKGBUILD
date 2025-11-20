pkgname=simplytoast
pkgver=0.9.9
pkgrel=1
pkgdesc="A lightweight toast notification tool written in Python + GTK4"
arch=('any')
url="https://github.com/toast1599/SimplyToast"
license=('GPL3')
depends=('python' 'python-gobject' 'gtk4')
source=()
sha256sums=()

package() {
    mkdir -p "$pkgdir/usr/bin"
    mkdir -p "$pkgdir/usr/share/simplytoast"
    mkdir -p "$pkgdir/usr/share/applications"
    mkdir -p "$pkgdir/usr/share/icons/hicolor/512x512/apps"

    install -Dm755 src/main.py "$pkgdir/usr/bin/simplytoast"

    cp -r assets data "$pkgdir/usr/share/simplytoast/"

    install -Dm644 data/com.toast1599.SimplyToast.desktop \
        "$pkgdir/usr/share/applications/com.toast1599.SimplyToast.desktop"

    install -Dm644 data/com.toast1599.SimplyToast.png \
        "$pkgdir/usr/share/icons/hicolor/512x512/apps/com.toast1599.SimplyToast.png"
}
