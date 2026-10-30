# HeidiSQL Flatpak

Unofficial Flatpak packages of [HeidiSQL](https://github.com/HeidiSQL/HeidiSQL), the graphical client for
MariaDB, MySQL, PostgreSQL, SQLite and other databases.

This repository is **not affiliated with or endorsed by the HeidiSQL project**. It repackages the Linux
binaries that upstream publishes with each release; it does not compile HeidiSQL itself.

> **AI notice:** the build tooling in this repository (GitHub Actions workflow, Flatpak manifests and
> render script) and this README were written with the help of an AI assistant (Claude). The generated
> packaging has been test-built, but review it before relying on it.

## Which one do I install?

Upstream ships one Linux build per UI toolkit, so there is one Flatpak per toolkit. They have different app
IDs and can be installed side by side.

| Toolkit | App ID | Architectures | Runtime |
| ------- | ------ | ------------- | ------- |
| GTK2 | `com.heidisql.HeidiSQL.GTK2` | x86_64 | `org.freedesktop.Platform` 25.08 |
| Qt5 | `com.heidisql.HeidiSQL.Qt5` | x86_64 | `org.kde.Platform` 5.15-25.08 |
| Qt6 | `com.heidisql.HeidiSQL.Qt6` | x86_64, aarch64 | `org.kde.Platform` 6.10 |

Qt6 is the best default. GTK2 and Qt5 are for people who prefer them or want upstream's most-tested
widgetset on their desktop.

## Installing

Download the `.flatpak` bundle for your toolkit and architecture from the
[Releases](../../releases) page, then:

```sh
flatpak install --user HeidiSQL-qt6-v12.22-x86_64.flatpak
flatpak run com.heidisql.HeidiSQL.Qt6
```

The bundle pulls its runtime from Flathub, so Flathub must be configured as a remote.

## How releases are made

A scheduled GitHub Actions workflow (`.github/workflows/build.yml`) runs once a day, at 03:17 UTC:

1. It asks the GitHub API for the latest HeidiSQL release.
2. If this repository already has a release with the same tag, it stops.
3. Otherwise it builds every Flatpak in parallel, using the upstream tarballs for that tag.
4. When all builds succeeded it creates a release with the **same tag, title and notes as the upstream
   release** and attaches the bundles. If any build fails, no release is created and the next daily run
   retries.

You can also run the workflow by hand from the Actions tab, optionally giving an upstream tag (for
example `v12.21`) to build an older or rebuilt release. An existing release for that tag is replaced.

GitHub disables scheduled workflows in repositories with no activity for 60 days. If the daily check stops
running, re-enable it from the Actions tab.

## What is in the package

- The upstream `heidisql` binary, locale files and `functions-*.ini` for the chosen toolkit.
- The toolkit bindings the binary links against, which the runtimes lack: `libQt6Pas` / `libQt5Pas`
  (built from [davidbannon/libqt6pas](https://github.com/davidbannon/libqt6pas) and
  [libqt5pas](https://github.com/davidbannon/libqt5pas)), or GTK 2.24 plus ATK for the GTK2 build.
- Database client libraries that HeidiSQL loads at run time: MariaDB Connector/C (MySQL and MariaDB) and
  libpq (PostgreSQL). SQLite comes from the runtime.

Not included: the Firebird and FreeTDS/Sybase client libraries, so those connection types are unavailable.

## Permissions and known limits

- Network access, X11 and GPU access, and read/write access to your home folder, so you can open and save
  SQL files and exports.
- The upstream binary is X11-only. On Wayland it runs through XWayland, and the Qt builds are forced to
  the `xcb` platform plugin for that reason.
- Settings are stored under `~/.var/app/<app id>/`.

## Repository layout

| Path | Purpose |
| ---- | ------- |
| `.github/workflows/build.yml` | Daily check, build matrix and release publishing |
| `scripts/render.py` | Looks up the upstream asset and its checksum, writes a manifest for one toolkit and architecture |
| `modules/` | Flatpak modules for the libraries upstream does not bundle |
| `data/` | Desktop entry and AppStream metadata templates |

To build locally:

```sh
python3 -I scripts/render.py --tag v12.22 --toolkit qt6 --out /tmp/heidisql-qt6
cd /tmp/heidisql-qt6
flatpak-builder --user --install --install-deps-from=flathub --force-clean build com.heidisql.HeidiSQL.Qt6.json
```

## License

HeidiSQL is licensed under the GPL-2.0. This repository only contains packaging files; see the upstream
project for the application's license and sources.
