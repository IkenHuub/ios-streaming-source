#!/usr/bin/env python3
"""Dependency-free structural and optional remote validation of Classic sources.

This checks this repository's contract, not every client-specific installation rule.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_APP_KEYS = {
    "name", "bundleIdentifier", "developerName", "subtitle", "localizedDescription",
    "iconURL", "tintColor", "versions", "appPermissions",
}
REQUIRED_VERSION_KEYS = {
    "version", "buildVersion", "date", "localizedDescription", "downloadURL", "size", "minOSVersion",
}


def https_url(value, ipa: bool = False) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urllib.parse.urlparse(value)
        return (parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username
                and not parsed.password and (not ipa or parsed.path.lower().endswith(".ipa")))
    except ValueError:
        return False


def remote_error(url: str, image: bool = False) -> str | None:
    request = urllib.request.Request(url, headers={
        "Range": "bytes=0-7", "User-Agent": "ios-streaming-source-validator/2.0",
    })
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            signature = response.read(8)
            content_type = response.headers.get("Content-Type", "").split(";", 1)[0]
            if urllib.parse.urlparse(response.url).scheme != "https":
                return "download redirected away from HTTPS"
        if image:
            if not content_type.startswith("image/") or not signature:
                return "icon response is not an image"
        elif signature[:4] != b"PK\x03\x04":
            return "remote file does not begin with an IPA/ZIP local file header"
    except Exception as error:
        return f"remote URL check failed: {error}"
    return None


def validate_data(source, check_remote: bool = False, allow_duplicate_bundles: bool = False) -> list[str]:
    errors: list[str] = []
    if not isinstance(source, dict):
        return ["source: root must be an object"]
    for key in ("name", "identifier", "subtitle"):
        if not isinstance(source.get(key), str) or not source[key]:
            errors.append(f"source: {key} must be a non-empty string")
    if not isinstance(source.get("apps"), list) or not source["apps"]:
        return errors + ["source: apps must be a non-empty array"]
    if not https_url(source.get("sourceURL")):
        errors.append("source: sourceURL must be absolute HTTPS")
    bundles = set()
    checked_urls = {}
    for index, app in enumerate(source["apps"]):
        label = f"apps[{index}]"
        if not isinstance(app, dict):
            errors.append(f"{label}: app must be an object")
            continue
        missing = REQUIRED_APP_KEYS - app.keys()
        if missing:
            errors.append(f"{label}: missing {', '.join(sorted(missing))}")
        for key in REQUIRED_APP_KEYS - {"versions", "appPermissions"}:
            if not isinstance(app.get(key), str) or not app[key]:
                errors.append(f"{label}: {key} must be a non-empty string")
        bundle = app.get("bundleIdentifier")
        if isinstance(bundle, str):
            if bundle in bundles and not allow_duplicate_bundles:
                errors.append(f"{label}: duplicate bundleIdentifier {bundle}")
            bundles.add(bundle)
        if not re.fullmatch(r"#?[0-9a-fA-F]{6}", str(app.get("tintColor", ""))):
            errors.append(f"{label}: tintColor must be a six-digit hex color")
        permissions = app.get("appPermissions")
        if (not isinstance(permissions, dict) or not isinstance(permissions.get("entitlements"), list)
                or not isinstance(permissions.get("privacy"), dict)):
            errors.append(f"{label}: invalid appPermissions")
        icon = app.get("iconURL")
        if not https_url(icon):
            errors.append(f"{label}: iconURL must be absolute HTTPS")
        elif check_remote:
            if icon not in checked_urls:
                checked_urls[icon] = remote_error(icon, image=True)
            if checked_urls[icon]:
                errors.append(f"{label}: {checked_urls[icon]}")
        if not isinstance(app.get("versions"), list) or not app["versions"]:
            errors.append(f"{label}: versions must be a non-empty array")
            continue
        identities = set()
        previous_date = None
        for version_index, version in enumerate(app["versions"]):
            vl = f"{label}.versions[{version_index}]"
            if not isinstance(version, dict):
                errors.append(f"{vl}: version must be an object")
                continue
            missing = REQUIRED_VERSION_KEYS - version.keys()
            if missing:
                errors.append(f"{vl}: missing {', '.join(sorted(missing))}")
            for key in ("version", "buildVersion", "minOSVersion"):
                if not isinstance(version.get(key), str) or not version[key]:
                    errors.append(f"{vl}: {key} must be a non-empty string")
            identity = (str(version.get("version", "")), str(version.get("buildVersion", "")))
            if identity in identities:
                errors.append(f"{vl}: duplicate version/build {identity}")
            identities.add(identity)
            url = version.get("downloadURL")
            if not https_url(url, ipa=True):
                errors.append(f"{vl}: downloadURL must be an absolute HTTPS .ipa URL")
            if type(version.get("size")) is not int or version["size"] <= 0:
                errors.append(f"{vl}: size must be a positive byte count")
            if "sha256" in version and not re.fullmatch(r"[0-9a-f]{64}", str(version["sha256"])):
                errors.append(f"{vl}: invalid SHA-256 digest")
            try:
                date = datetime.fromisoformat(version["date"].replace("Z", "+00:00"))
                if date.tzinfo is None:
                    date = date.replace(tzinfo=timezone.utc)
                if previous_date is not None and date > previous_date:
                    errors.append(f"{vl}: versions must be newest first")
                previous_date = date
            except (KeyError, ValueError, TypeError, AttributeError):
                errors.append(f"{vl}: date is not ISO 8601")
            if check_remote and https_url(url, ipa=True):
                if url not in checked_urls:
                    checked_urls[url] = remote_error(url)
                if checked_urls[url]:
                    errors.append(f"{vl}: {checked_urls[url]}")
    return errors


def validate(path: Path, check_remote: bool = False, allow_duplicate_bundles: bool = False) -> list[str]:
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:
        return [f"JSON parse failure: {error}"]
    return validate_data(source, check_remote, allow_duplicate_bundles)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", type=Path, default=ROOT / "public" / "apps.json")
    parser.add_argument("--remote", action="store_true", help="Check icon responses and every IPA's ZIP header (not full archive integrity)")
    parser.add_argument("--allow-duplicate-bundles", action="store_true")
    args = parser.parse_args()
    errors = validate(args.path, args.remote, args.allow_duplicate_bundles)
    alias = ROOT / "public" / "repo.json"
    if args.path.resolve() == (ROOT / "public" / "apps.json").resolve() and alias.exists() and not errors:
        if json.loads(alias.read_text(encoding="utf-8")) != json.loads(args.path.read_text(encoding="utf-8")):
            errors.append("repo.json alias differs from apps.json")
    if errors:
        print("INVALID\n" + "\n".join(f"- {error}" for error in errors))
        return 1
    print("VALID: JSON and repository source structure passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
