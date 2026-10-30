#!/usr/bin/env python3
"""Render a flatpak-builder manifest for one HeidiSQL release / toolkit / arch.

Looks up the upstream Linux tarball for the given tag, takes its sha256 from
the GitHub API (falling back to hashing the download) and writes a ready to
build directory containing the manifest, the shared modules and the desktop
integration files.
"""
import argparse
import hashlib
import json
import os
import shutil
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UPSTREAM = "HeidiSQL/HeidiSQL"

FDO = {"runtime": "org.freedesktop.Platform", "sdk": "org.freedesktop.Sdk", "runtime-version": "25.08"}
KDE5 = {"runtime": "org.kde.Platform", "sdk": "org.kde.Sdk", "runtime-version": "5.15-25.08"}
KDE6 = {"runtime": "org.kde.Platform", "sdk": "org.kde.Sdk", "runtime-version": "6.10"}

# toolkit -> (label, runtime, toolkit modules, upstream asset prefix per arch)
TOOLKITS = {
    "gtk2": ("GTK2", FDO, ["modules/gtk2.yaml"], {"x86_64": "build-gtk2"}),
    "qt5": ("Qt5", KDE5, ["modules/libqt5pas.yaml"], {"x86_64": "build-qt5"}),
    "qt6": ("Qt6", KDE6, ["modules/libqt6pas.yaml"],
            {"x86_64": "build-qt6", "aarch64": "build-qt6-arm64"}),
}
CLIENT_LIBS = ["modules/mariadb-connector-c.yaml", "modules/libpq.yaml"]


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if os.environ.get("GITHUB_TOKEN"):
        req.add_header("Authorization", "Bearer " + os.environ["GITHUB_TOKEN"])
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def sha256_of(url):
    h = hashlib.sha256()
    with urllib.request.urlopen(url) as r:
        while chunk := r.read(1 << 20):
            h.update(chunk)
    return h.hexdigest()


def fill(text, values):
    for key, value in values.items():
        text = text.replace(f"@{key}@", value)
    return text


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True, help="upstream release tag, e.g. v12.22")
    p.add_argument("--toolkit", required=True, choices=TOOLKITS)
    p.add_argument("--arch", default="x86_64")
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()

    label, runtime, toolkit_modules, prefixes = TOOLKITS[a.toolkit]
    if a.arch not in prefixes:
        p.error(f"{a.toolkit} is not built for {a.arch}")
    asset_name = f"{prefixes[a.arch]}-{a.tag}.tgz"

    release = api(f"repos/{UPSTREAM}/releases/tags/{a.tag}")
    asset = next((x for x in release["assets"] if x["name"] == asset_name), None)
    if asset is None:
        raise SystemExit(f"{a.tag} has no asset {asset_name}")
    digest = (asset.get("digest") or "").removeprefix("sha256:")
    sha256 = digest or sha256_of(asset["browser_download_url"])

    app_id = f"com.heidisql.HeidiSQL.{label}"
    values = {
        "APP_ID": app_id,
        "TOOLKIT_LABEL": label,
        "VERSION": a.tag.lstrip("v"),
        "DATE": datetime.fromisoformat(release["published_at"].replace("Z", "+00:00")).date().isoformat(),
    }

    out = a.out
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT / "modules", out / "modules", dirs_exist_ok=True)
    (out / f"{app_id}.desktop").write_text(fill((ROOT / "data/app.desktop.in").read_text(), values))
    (out / f"{app_id}.metainfo.xml").write_text(fill((ROOT / "data/app.metainfo.xml.in").read_text(), values))

    heidisql = {
        "name": "heidisql",
        "buildsystem": "simple",
        "build-commands": [
            "install -d /app/share/heidisql",
            "install -Dm755 heidisql /app/share/heidisql/heidisql",
            "cp -r locale functions-*.ini LICENSE /app/share/heidisql/",
            "install -Dm755 heidisql.sh /app/bin/heidisql",
            f"install -Dm644 heidisql.png /app/share/icons/hicolor/256x256/apps/{app_id}.png",
            f"install -Dm644 {app_id}.desktop /app/share/applications/{app_id}.desktop",
            f"install -Dm644 {app_id}.metainfo.xml /app/share/metainfo/{app_id}.metainfo.xml",
        ],
        "sources": [
            {"type": "archive", "url": asset["browser_download_url"], "sha256": sha256,
             "strip-components": 0},
            {"type": "script", "dest-filename": "heidisql.sh",
             "commands": ["exec /app/share/heidisql/heidisql \"$@\""]},
            {"type": "file", "path": f"{app_id}.desktop"},
            {"type": "file", "path": f"{app_id}.metainfo.xml"},
        ],
    }

    env = {}
    if a.toolkit != "gtk2":
        env["QT_QPA_PLATFORM"] = "xcb"  # the upstream build is X11-only

    manifest = {
        "app-id": app_id,
        **runtime,
        "command": "heidisql",
        "finish-args": [
            "--share=network",
            "--share=ipc",
            "--socket=x11",
            "--device=dri",
            "--filesystem=home",
        ],
        "build-options": {"strip": False, "no-debuginfo": True},
        "modules": [*toolkit_modules, *CLIENT_LIBS, heidisql],
    }
    if env:
        manifest["finish-args"] += [f"--env={k}={v}" for k, v in env.items()]
    (out / f"{app_id}.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(app_id)


if __name__ == "__main__":
    main()
