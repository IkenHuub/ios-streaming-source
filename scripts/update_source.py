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
USER_AGENT = "IkenHuub-ios-streaming-source-updater/1.0"
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


def latest_release(repository: str, tag_prefix: str | None = None) -> dict:
    releases = fetch_json(f"https://api.github.com/repos/{repository}/releases?per_page=30")
    for release in releases:
        if (
            not release.get("draft")
            and not release.get("prerelease")
            and (tag_prefix is None or release.get("tag_name", "").startswith(tag_prefix))
        ):
            return release
    qualifier = f" with tag prefix {tag_prefix}" if tag_prefix else ""
    raise RuntimeError(f"No published stable release found for {repository}{qualifier}")


def select_ipa_url(release: dict, allow_body: bool, asset_pattern: str | None = None) -> str:
    compiled_pattern = re.compile(asset_pattern, re.IGNORECASE) if asset_pattern else None
    for asset in release.get("assets", []):
        url = asset.get("browser_download_url", "")
        name = asset.get("name", "")
        if urllib.parse.urlparse(url).path.lower().endswith(".ipa") and (
            compiled_pattern is None or compiled_pattern.search(name)
        ):
            return url
    if allow_body:
        match = IPA_URL_RE.search(release.get("body") or "")
        if match:
            return match.group(0).rstrip(".,;:")
    raise RuntimeError(f"Release {release.get('tag_name')} contains no permitted IPA URL")


def download_ipa(url: str) -> Path:
    if urllib.parse.urlparse(url).scheme != "https" or not urllib.parse.urlparse(url).path.lower().endswith(".ipa"):
        raise RuntimeError(f"IPA URL is not an absolute HTTPS .ipa URL: {url}")
    handle = tempfile.NamedTemporaryFile(prefix="ios-streaming-source-", suffix=".ipa", delete=False)
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


def release_description(app: dict, release: dict, version: str | None = None) -> str:
    if template := app.get("versionDescriptionTemplate"):
        return template.format(releaseTag=release["tag_name"], version=version or release["tag_name"])
    body = release.get("body") or ""
    without_urls = IPA_URL_RE.sub("", body)
    without_label = re.sub(r"^\s*(release|download)\s*:\s*", "", without_urls, flags=re.IGNORECASE).strip()
    return without_label or f"Official {app['name']} release {release['tag_name']}."


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
    configured_ids = {app["id"] for app in config["apps"]}
    state = {app_id: value for app_id, value in state.items() if app_id in configured_ids}
    existing_by_bundle = {app["bundleIdentifier"]: app for app in existing.get("apps", [])}
    existing_by_name = {app["name"]: app for app in existing.get("apps", [])}
    generated_apps = []
    changed = False

    for app in config["apps"]:
        upstream_version = None
        ipa_url = None
        if upstream_url := app.get("upstreamSourceURL"):
            upstream_source = fetch_json(upstream_url)
            upstream_bundle = app["upstreamBundleIdentifier"]
            upstream_app = next(
                (item for item in upstream_source.get("apps", []) if item.get("bundleIdentifier") == upstream_bundle),
                None,
            )
            if not upstream_app or not upstream_app.get("versions"):
                raise RuntimeError(f"Upstream source has no versions for {upstream_bundle}")
            upstream_version = upstream_app["versions"][0]
            ipa_url = upstream_version["downloadURL"]
            release = {
                "id": f"upstream:{upstream_bundle}:{upstream_version['version']}:{upstream_version.get('buildVersion', '')}",
                "updated_at": upstream_version.get("sha256", ipa_url),
                "tag_name": upstream_version["version"],
                "published_at": upstream_version["date"],
                "body": upstream_version.get("localizedDescription", ""),
            }
        else:
            release = latest_release(app["githubRepository"], app.get("releaseTagPrefix"))
        release_key = f"{release['id']}:{release.get('updated_at', '')}"
        previous = existing_by_name.get(app["name"])
        if state.get(app["id"], {}).get("releaseKey") == release_key and previous:
            current_entry = dict(previous)
            current_entry.update(
                {
                    "name": app["name"],
                    "developerName": app["developerName"],
                    "subtitle": app["subtitle"],
                    "localizedDescription": app["localizedDescription"],
                    "iconURL": app["iconURL"],
                    "tintColor": app["tintColor"],
                    "category": app.get("category", "other"),
                }
            )
            if app.get("versionDescriptionTemplate") and current_entry.get("versions"):
                current_entry["versions"] = [dict(item) for item in current_entry["versions"]]
                current_entry["versions"][0]["localizedDescription"] = release_description(
                    app,
                    release,
                    current_entry["versions"][0]["version"],
                )
            generated_apps.append(current_entry)
            continue

        if ipa_url is None:
            try:
                ipa_url = select_ipa_url(
                    release,
                    app.get("allowReleaseBodyIPA", False),
                    app.get("ipaAssetPattern"),
                )
            except RuntimeError:
                if app.get("allowMissingIPA"):
                    if previous:
                        generated_apps.append(previous)
                    print(f"{app['name']}: latest official release has no IPA; entry remains pending")
                    continue
                raise
        ipa_path = download_ipa(ipa_url)
        try:
            metadata = ipa_metadata(ipa_path)
        finally:
            ipa_path.unlink(missing_ok=True)

        if upstream_version:
            expected_values = {
                "bundleIdentifier": app["upstreamBundleIdentifier"],
                "version": upstream_version.get("version"),
                "buildVersion": upstream_version.get("buildVersion"),
                "minOSVersion": upstream_version.get("minOSVersion"),
                "size": upstream_version.get("size"),
                "sha256": upstream_version.get("sha256"),
            }
            mismatches = [
                key
                for key, expected in expected_values.items()
                if expected is not None and metadata[key] != expected
            ]
            if mismatches:
                raise RuntimeError(
                    f"Upstream metadata does not match downloaded IPA for {app['name']}: "
                    + ", ".join(mismatches)
                )

        if (
            app.get("resetHistoryOnBundleChange")
            and previous
            and previous.get("bundleIdentifier") != metadata["bundleIdentifier"]
        ):
            previous = None
        elif previous is None and not app.get("isolateHistory"):
            previous = existing_by_bundle.get(metadata["bundleIdentifier"])
        versions = list(previous.get("versions", [])) if previous else []
        version_identity = (metadata["version"], metadata["buildVersion"])
        known_identities = {(item["version"], item.get("buildVersion", "")) for item in versions}
        if version_identity not in known_identities:
            new_version = {
                "version": metadata["version"],
                "buildVersion": metadata["buildVersion"],
                "date": release["published_at"],
                "localizedDescription": (
                    upstream_version.get("localizedDescription", "")
                    if upstream_version
                    else release_description(app, release, metadata["version"])
                ),
                "downloadURL": ipa_url,
                "size": metadata["size"],
                "sha256": metadata["sha256"],
                "minOSVersion": metadata["minOSVersion"],
            }
            if template := app.get("marketingVersionTemplate"):
                new_version["marketingVersion"] = template.format(
                    releaseTag=release["tag_name"],
                    version=metadata["version"],
                    buildVersion=metadata["buildVersion"],
                )
            elif upstream_version and upstream_version.get("marketingVersion"):
                new_version["marketingVersion"] = upstream_version["marketingVersion"]
            versions.insert(0, new_version)
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
        state[app["id"]] = {
            "releaseKey": release_key,
            "releaseTag": release["tag_name"],
            "downloadURL": ipa_url,
            "version": metadata["version"],
            "buildVersion": metadata["buildVersion"],
            "sha256": metadata["sha256"],
        }

    config_by_name = {app["name"]: app for app in config["apps"]}
    main_apps = [
        app for app in generated_apps if not config_by_name[app["name"]].get("separateSource")
    ]

    output = base_source(config)
    output["apps"] = main_apps
    output["featuredApps"] = [app["bundleIdentifier"] for app in main_apps[:5]]
    wrote = write_json_if_changed(SOURCE_PATH, output)
    wrote |= write_json_if_changed(ALIAS_PATH, output)
    for app_config in config["apps"]:
        filename = app_config.get("separateSource") or f"{app_config['id']}.json"
        separate_app = next(
            (app for app in generated_apps if app["name"] == app_config["name"]),
            None,
        )
        if not separate_app:
            continue
        separate_output = base_source(config)
        separate_output["name"] = f"{config['source']['name']} — {separate_app['name']}"
        separate_output["identifier"] = (
            f"{config['source']['identifier']}.{Path(filename).stem.replace('-', '.')}"
        )
        separate_output["subtitle"] = f"Optional {separate_app['name']} variant."
        separate_output["apps"] = [separate_app]
        separate_output["featuredApps"] = [separate_app["bundleIdentifier"]]
        wrote |= write_json_if_changed(PUBLIC_DIR / filename, separate_output)
    config_by_id = {app["id"]: app for app in config["apps"]}
    for compatible_config in config.get("compatibleSources", []):
        compatible_apps = []
        for app_id in compatible_config["appIds"]:
            app_config = config_by_id[app_id]
            generated_app = next(
                (app for app in generated_apps if app["name"] == app_config["name"]),
                None,
            )
            if generated_app:
                compatible_apps.append(generated_app)
        compatible_output = base_source(config)
        compatible_output["name"] = compatible_config["name"]
        compatible_output["identifier"] = (
            f"{config['source']['identifier']}."
            f"{Path(compatible_config['filename']).stem.replace('-', '.')}"
        )
        compatible_output["subtitle"] = compatible_config["subtitle"]
        compatible_output["apps"] = compatible_apps
        compatible_output["featuredApps"] = [
            app["bundleIdentifier"] for app in compatible_apps[:5]
        ]
        wrote |= write_json_if_changed(
            PUBLIC_DIR / compatible_config["filename"],
            compatible_output,
        )
    wrote |= write_json_if_changed(STATE_PATH, state)
    if wrote:
        print("Source updated")
    elif changed:
        print("Source already current")
    else:
        print("No new IPA version found; source files remain unchanged")
    return wrote


if __name__ == "__main__":
    try:
        update()
    except Exception as error:
        print(f"error: {error}", file=sys.stderr)
        raise
