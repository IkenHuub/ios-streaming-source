#!/usr/bin/env python3
"""Strict, dependency-free validation for the generated AltStore source."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_APP_KEYS = {
    "name",
    "bundleIdentifier",
    "developerName",
    "subtitle",
    "localizedDescription",
    "iconURL",
    "tintColor",
    "versions",
    "appPermissions",
}
REQUIRED_VERSION_KEYS = {
    "version",
    "buildVersion",
    "date",
    "localizedDescription",
    "downloadURL",
    "size",
    "minOSVersion",
}


def https_url(value: str, ipa: bool = False) -> bool:
    parsed = urllib.parse.urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and (not ipa or parsed.path.lower().endswith(".ipa"))


def validate(
    path: Path,
    check_remote: bool = False,
    allow_duplicate_bundles: bool = False,
) -> list[str]:
    errors: list[str] = []
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return [f"JSON parse failure: {error}"]

    for key in ("name", "identifier", "subtitle", "apps"):
        if key not in source:
            errors.append(f"source: missing {key}")
    if not isinstance(source.get("apps"), list) or not source.get("apps"):
        errors.append("source: apps must be a non-empty array")
        return errors

    bundles: set[str] = set()
    for index, app in enumerate(source["apps"]):
        label = f"apps[{index}]"
        missing = REQUIRED_APP_KEYS - app.keys()
        if missing:
            errors.append(f"{label}: missing {', '.join(sorted(missing))}")
        bundle = app.get("bundleIdentifier")
        if bundle in bundles and not allow_duplicate_bundles:
            errors.append(f"{label}: duplicate bundleIdentifier {bundle}")
        bundles.add(bundle)
        if not https_url(app.get("iconURL", "")):
            errors.append(f"{label}: iconURL must be absolute HTTPS")
        if not isinstance(app.get("versions"), list) or not app.get("versions"):
            errors.append(f"{label}: versions must be a non-empty array")
            continue
        identities: set[tuple[str, str]] = set()
        for version_index, version in enumerate(app["versions"]):
            version_label = f"{label}.versions[{version_index}]"
            missing = REQUIRED_VERSION_KEYS - version.keys()
            if missing:
                errors.append(f"{version_label}: missing {', '.join(sorted(missing))}")
            identity = (version.get("version", ""), version.get("buildVersion", ""))
            if identity in identities:
                errors.append(f"{version_label}: duplicate version/build {identity}")
            identities.add(identity)
            if not https_url(version.get("downloadURL", ""), ipa=True):
                errors.append(f"{version_label}: downloadURL must be an absolute HTTPS .ipa URL")
            if not isinstance(version.get("size"), int) or version.get("size", 0) <= 0:
                errors.append(f"{version_label}: size must be a positive byte count")
            try:
                datetime.fromisoformat(version.get("date", "").replace("Z", "+00:00"))
            except ValueError:
                errors.append(f"{version_label}: date is not ISO 8601")
            if check_remote and https_url(version.get("downloadURL", ""), ipa=True):
                request = urllib.request.Request(
                    version["downloadURL"],
                    headers={"Range": "bytes=0-3", "User-Agent": "ios-streaming-source-validator/1.0"},
                )
                try:
                    with urllib.request.urlopen(request, timeout=60) as response:
                        signature = response.read(4)
                    if signature[:2] != b"PK":
                        errors.append(f"{version_label}: remote file is not an IPA/ZIP")
                except Exception as error:
                    errors.append(f"{version_label}: remote URL check failed: {error}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "public" / "apps.json")
    parser.add_argument("--remote", action="store_true")
    parser.add_argument("--allow-duplicate-bundles", action="store_true")
    args = parser.parse_args()
    errors = validate(args.path, args.remote, args.allow_duplicate_bundles)
    alias = ROOT / "public" / "repo.json"
    if args.path == ROOT / "public" / "apps.json" and alias.exists():
        if json.loads(alias.read_text(encoding="utf-8")) != json.loads(args.path.read_text(encoding="utf-8")):
            errors.append("repo.json alias differs from apps.json")
    if errors:
        print("INVALID")
        for error in errors:
            print(f"- {error}")
        return 1
    if args.allow_duplicate_bundles:
        print("VALID: JSON syntax and multi-variant catalog structure passed")
    else:
        print("VALID: JSON syntax and AltStore source structure passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
