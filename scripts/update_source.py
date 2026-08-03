#!/usr/bin/env python3
"""Update an AltStore source from configured official GitHub releases."""

from __future__ import annotations

import hashlib
import json
import os
import plistlib
import re
import shutil
import sys
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "apps.json"
PUBLIC_DIR = ROOT / "public"
SOURCE_PATH = PUBLIC_DIR / "apps.json"
ALIAS_PATH = PUBLIC_DIR / "repo.json"
STATE_PATH = ROOT / "state" / "releases.json"
USER_AGENT = "IkenHuub-ios-source-updater/1.0"
IPA_URL_RE = re.compile(r"https://[^\s<>\"')]+?\.ipa(?:\?[^\s<>\"')]+)?", re.IGNORECASE)


def request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token and urllib.parse.urlparse(url).hostname == "api.github.com":
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def fetch_json(url: str):
    with urllib.request.urlopen(request(url), timeout=60) as response:
        return json.load(response)


def latest_release(repository: str) -> dict:
    releases = fetch_json(f"https://api.github.com/repos/{repository}/releases?per_page=30")
    for release in releases:
        if not release.get("draft") and not release.get("prerelease"):
            return release
    raise RuntimeError(f"No published stable release found for {repository}")


def select_ipa_url(release: dict, allow_body: bool) -> str:
    for asset in release.get("assets", []):
        url = asset.get("browser_download_url", "")
        if urllib.parse.urlparse(url).path.lower().endswith(".ipa"):
            return url
    if allow_body:
        match = IPA_URL_RE.search(release.get("body") or "")
        if match:
            return match.group(0).rstrip(".,;:")
    raise RuntimeError(f"Release {release.get('tag_name')} contains no permitted IPA URL")


def download_ipa(url: str) -> Path:
    if urllib.parse.urlparse(url).scheme != "https" or not urllib.parse.urlparse(url).path.lower().endswith(".ipa"):
        raise RuntimeError(f"IPA URL is not an absolute HTTPS .ipa URL: {url}")
    handle = tempfile.NamedTemporaryFile(prefix="ios-source-", suffix=".ipa", delete=False)
    path = Path(handle.name)
    try:
        local_ipa = os.environ.get("IOS_SOURCE_IPA_PATH")
        with handle:
            if local_ipa:
                with Path(local_ipa).open("rb") as source:
                    shutil.copyfileobj(source, handle)
            else:
                with urllib.request.urlopen(request(url), timeout=180) as response:
                    while chunk := response.read(1024 * 1024):
                        handle.write(chunk)
        if not zipfile.is_zipfile(path):
            raise RuntimeError(f"Downloaded file is not a valid IPA/ZIP: {url}")
        return path
    except Exception:
        path.unlink(missing_ok=True)
        raise


def ipa_metadata(path: Path) -> dict:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)

    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        main_plists = [
            name
            for name in names
            if re.fullmatch(r"Payload/[^/]+\.app/Info\.plist", name)
        ]
        if len(main_plists) != 1:
            raise RuntimeError(f"Expected one main app Info.plist, found {len(main_plists)}")
        info = plistlib.loads(archive.read(main_plists[0]))
        privacy: dict[str, str] = {}
        related_plists = [main_plists[0]] + [
            name
            for name in names
            if re.fullmatch(r"Payload/[^/]+\.app/PlugIns/[^/]+\.appex/Info\.plist", name)
        ]
        for plist_name in related_plists:
            plist = plistlib.loads(archive.read(plist_name))
            for key, value in plist.items():
                if key.startswith("NS") and key.endswith("UsageDescription") and isinstance(value, str):
                    privacy[key] = value

    required = {
        "bundleIdentifier": info.get("CFBundleIdentifier"),
        "version": info.get("CFBundleShortVersionString"),
        "buildVersion": info.get("CFBundleVersion"),
        "minOSVersion": info.get("MinimumOSVersion"),
    }
    missing = [key for key, value in required.items() if not isinstance(value, str) or not value]
    if missing:
        raise RuntimeError(f"IPA Info.plist is missing required metadata: {', '.join(missing)}")
    return {
        **required,
        "size": path.stat().st_size,
        "sha256": digest.hexdigest(),
        "privacy": dict(sorted(privacy.items())),
    }


def release_description(app: dict, release: dict) -> str:
    body = release.get("body") or ""
    without_urls = IPA_URL_RE.sub("", body)
    without_label = re.sub(r"^\s*(release|download)\s*:\s*", "", without_urls, flags=re.IGNORECASE).strip()
    return without_label or f"Officiële {app['name']}-release {release['tag_name']}."


def base_source(config: dict) -> dict:
    source = dict(config["source"])
    source["featuredApps"] = []
    source["apps"] = []
    source["news"] = []
    return source


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def write_json_if_changed(path: Path, value) -> bool:
    rendered = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    current = path.read_text(encoding="utf-8") if path.exists() else None
    if current == rendered:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return True


def update() -> bool:
    config = load_json(CONFIG_PATH, {})
    existing = load_json(SOURCE_PATH, base_source(config))
    state = load_json(STATE_PATH, {})
    existing_by_bundle = {app["bundleIdentifier"]: app for app in existing.get("apps", [])}
    existing_by_name = {app["name"]: app for app in existing.get("apps", [])}
    generated_apps = []
    changed = False

    for app in config["apps"]:
        release = latest_release(app["githubRepository"])
        release_key = f"{release['id']}:{release.get('updated_at', '')}"
        previous = existing_by_name.get(app["name"])
        if state.get(app["id"], {}).get("releaseKey") == release_key and previous:
            generated_apps.append(previous)
            continue

        ipa_url = select_ipa_url(release, app.get("allowReleaseBodyIPA", False))
        ipa_path = download_ipa(ipa_url)
        try:
            metadata = ipa_metadata(ipa_path)
        finally:
            ipa_path.unlink(missing_ok=True)

        previous = existing_by_bundle.get(metadata["bundleIdentifier"], previous)
        versions = list(previous.get("versions", [])) if previous else []
        version_identity = (metadata["version"], metadata["buildVersion"])
        known_identities = {(item["version"], item.get("buildVersion", "")) for item in versions}
        if version_identity not in known_identities:
            versions.insert(
                0,
                {
                    "version": metadata["version"],
                    "buildVersion": metadata["buildVersion"],
                    "marketingVersion": f"{app['name']} {release['tag_name']} (YouTube {metadata['version']})",
                    "date": release["published_at"],
                    "localizedDescription": release_description(app, release),
                    "downloadURL": ipa_url,
                    "size": metadata["size"],
                    "sha256": metadata["sha256"],
                    "minOSVersion": metadata["minOSVersion"],
                },
            )
            changed = True

        generated_apps.append(
            {
                "name": app["name"],
                "bundleIdentifier": metadata["bundleIdentifier"],
                "developerName": app["developerName"],
                "subtitle": app["subtitle"],
                "localizedDescription": app["localizedDescription"],
                "iconURL": app["iconURL"],
                "tintColor": app["tintColor"],
                "category": app.get("category", "other"),
                "versions": versions,
                "appPermissions": {
                    "entitlements": sorted(set(app.get("entitlements", []))),
                    "privacy": metadata["privacy"],
                },
            }
        )
        if version_identity in known_identities:
            print(f"{app['name']}: release changed, but IPA version/build is unchanged; source not updated")
        else:
            state[app["id"]] = {
                "releaseKey": release_key,
                "releaseTag": release["tag_name"],
                "downloadURL": ipa_url,
                "version": metadata["version"],
                "buildVersion": metadata["buildVersion"],
                "sha256": metadata["sha256"],
            }

    output = base_source(config)
    output["apps"] = generated_apps
    output["featuredApps"] = [app["bundleIdentifier"] for app in generated_apps[:5]]
    if not changed and SOURCE_PATH.exists():
        print("No new IPA version found; apps.json remains unchanged")
        return False
    wrote = write_json_if_changed(SOURCE_PATH, output)
    wrote |= write_json_if_changed(ALIAS_PATH, output)
    wrote |= write_json_if_changed(STATE_PATH, state)
    print("Source updated" if wrote else "Source already current")
    return wrote


if __name__ == "__main__":
    try:
        update()
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise
