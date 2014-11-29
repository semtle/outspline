# Maintainer: Dario Giovannetti <dev at dariogiovannetti dot net>

pkgname='outspline'
pkgver='0.8.1'
pkgrel=1
pkgdesc="Outliner and personal time organizer to manage todo lists, schedule tasks, remind events."
arch=('any')
url="https://kynikos.github.io/outspline/"
license=('GPL3')
depends=('wxpython<3.1')
optdepends=('python2-dbus: prevent opening multiple instances with the same configuration file'
            'dbus-glib: prevent opening multiple instances with the same configuration file'
            'libnotify: for desktop notifications (notify plugin)'
            'python2-gobject: for desktop notifications (notify plugin)'
            'outspline-extra: extra addons'
            'outspline-experimental: experimental addons'
            'outspline-development: development tools for beta testers')
conflicts=('organism' 'organism-organizer')
replaces=('organism' 'organism-organizer')
install=outspline.install
source=("http://downloads.sourceforge.net/project/outspline/main/$pkgname-$pkgver.tar.bz2")
sha256sums=('4a2bdd5ba373c3e08c660741cd50c73a9ac570142a124ef704797bad4915c378')

package() {
    cd "$srcdir/$pkgname-$pkgver"
    python2 setup.py install --root="$pkgdir" --optimize=1
}
