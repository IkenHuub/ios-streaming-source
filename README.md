# iOS Streaming Source

A generic AltStore-compatible source for (un)official iOS streaming apps. The source works with AltStore Classic and apps that support the same source format, including FlareStore, Feather, and SideStore.

## Source URL

```text
https://ikenhuub.github.io/ios-streaming-source/apps.json
```

An identical full-catalog alias is available at `https://ikenhuub.github.io/ios-streaming-source/repo.json`.

The main `apps.json` catalog shows every available app and variant so users can choose what to install. Nuvio Enhanced and Nuvio Full share `com.nuvio.media`, so installing one variant replaces the other.

## AltStore-compatible source URLs

AltStore Classic, SideStore, and other clients that enforce unique bundle identifiers can use one of these complete catalogs:

- Enhanced catalog: `https://ikenhuub.github.io/ios-streaming-source/altstore-enhanced.json`
- Full catalog: `https://ikenhuub.github.io/ios-streaming-source/altstore-full.json`

Both contain APEX and Stremio. Choose which Nuvio variant you want included. These catalogs pass strict AltStore source validation.

The individual Nuvio Full source is:

```text
https://ikenhuub.github.io/ios-streaming-source/nuvio-full.json
```

Every published app also has an individual source hosted by this repository:

- `https://ikenhuub.github.io/ios-streaming-source/apex.json`
- `https://ikenhuub.github.io/ios-streaming-source/stremio.json`
- `https://ikenhuub.github.io/ios-streaming-source/nuvio-enhanced.json`
- `https://ikenhuub.github.io/ios-streaming-source/nuvio-full.json`

## Add to a sideloading store

1. Open your sideloading store and go to **Sources**, **Repos**, or the equivalent section.
2. Select **Add Source**, **Add Repo**, or tap the plus button.
3. Paste the source URL appropriate for your client:
   - use `apps.json` for the complete catalog with every variant;
   - use `altstore-enhanced.json` or `altstore-full.json` when your client enforces unique bundle identifiers;
   - use an individual app source when you only want one app.
4. Confirm the addition and refresh the source.

The JSON format is intended for compatible sideloading stores including FlareStore, Feather, SideStore, and AltStore Classic. Exact menus and support for multiple entries sharing a bundle identifier depend on the client.

## APEX

APEX is not developed by the maintainer of this repository. The IPA is neither rehosted nor modified. Its download URL points directly to the official Catbox download published by the APEX developer in the official [GitHub Release](https://github.com/lowiqentity/APEX/releases).

The bundle identifier, app version, build version, minimum iOS version, privacy descriptions, file size, and SHA-256 digest are determined directly from the downloaded IPA.

## Stremio

The full-featured Stremio iOS app follows the unofficial [`gorlev/stremio-altstore`](https://github.com/gorlev/stremio-altstore) source published at `https://repo.omix4.one/stremio-ios.json`. The IPA itself is downloaded directly and unmodified from Stremio's public `dl.strem.io` CDN. The updater verifies its bundle identifier, version, build, minimum iOS version, byte size, and SHA-256 digest before publishing it.

## Nuvio Enhanced

Nuvio Enhanced is an actively maintained unofficial build from [`luqmanfadlli/NuvioMobile-Enhanced`](https://github.com/luqmanfadlli/NuvioMobile-Enhanced). This repository maintains its own source metadata and links directly to the latest unmodified `-Enhanced.ipa` published in that project's GitHub Releases. It uses Nuvio's `com.nuvio.media` bundle identifier, so it may replace or conflict with another Nuvio installation rather than install alongside it.

## Nuvio Full

Nuvio Full is the official full build from [`NuvioMedia/NuvioMobile`](https://github.com/NuvioMedia/NuvioMobile). This repository links directly to the latest unmodified `full-release.ipa` from the official GitHub Releases. Full and Enhanced intentionally appear as separate choices in this source, but both use `com.nuvio.media`; installing one therefore replaces the other.

Both Nuvio variants appear in the complete catalog. Their individual JSON files remain available for clients that enforce AltStore's unique-bundle-identifier rule.

## Adding more apps later

Each app has its own entry in [`config/apps.json`](config/apps.json). The generic updater processes that configuration, checks the latest official GitHub Release, downloads the IPA for inspection only, and adds a version only when `CFBundleShortVersionString` or `CFBundleVersion` is new. The IPA itself is never stored in this repository.

The updater runs every six hours and can also be started manually through GitHub Actions.
