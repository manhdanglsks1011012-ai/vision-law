# Third-party software

Vision law is licensed under GPL-3.0-only. Third-party components retain their own notices and licenses.

- PyQt6 6.10.2: GPLv3 edition from Ubuntu. [Riverbank licensing](https://www.riverbankcomputing.com/software/pyqt/intro).
- Qt 6.10.2: components under LGPL/GPL and associated third-party licenses; see distribution copyright notices bundled with the release.
- CPython 3.14.4: Python Software Foundation license and included notices.
- PyInstaller 6.22.3: GPLv2 with bootloader exception and applicable Apache-2.0 components. [Official license](https://pyinstaller.org/en/stable/license.html).

Binary releases contain THIRD-PARTY notices. [BUNDLED-SOURCES.json](docs/BUNDLED-SOURCES.json) identifies every bundled system shared library, its exact Ubuntu source package version, and a corresponding source download page. Corresponding Vision law source and build scripts accompany each release; Ubuntu component versions and notices are provided for locating their corresponding upstream/distribution source. For the exact Ubuntu source packages, use the matching Ubuntu archive source package version (for example `apt source pyqt6` and `apt source qt6-base` with deb-src configured). Do not substitute different-version sources when rebuilding.

The rainbow crystal asset is a project asset. Vision law is independent of Obsidian and does not bundle Obsidian code or trademarks as its application identity.
