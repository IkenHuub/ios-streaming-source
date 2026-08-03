# iOS Streaming Source

A generic AltStore-compatible source for (un)official iOS streaming apps. The source works with AltStore Classic and apps that support the same source format, including FlareStore, Feather, and SideStore.

## Source URL

```text
https://ikenhuub.github.io/ios-streaming-source/apps.json
```

An identical FlareStore alias is available at `https://ikenhuub.github.io/ios-streaming-source/repo.json`.

The main `apps.json` catalog shows both Nuvio variants so FlareStore users can choose which one to install. Both variants use `com.nuvio.media`, so installing one replaces the other.

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
- `https://ikenhuub.github.io/ios-streaming-source/youtube-lowiqentity.json`
- `https://ikenhuub.github.io/ios-streaming-source/stremio.json`
- `https://ikenhuub.github.io/ios-streaming-source/nuvio-enhanced.json`
- `https://ikenhuub.github.io/ios-streaming-source/nuvio-full.json`

## Add to FlareStore

1. Open FlareStore and go to **Sources**.
2. Select **Add Source** or tap the plus button.
3. Paste `https://ikenhuub.github.io/ios-streaming-source/apps.json`.
4. Confirm that you want to add the source.

## APEX

APEX is not developed by the maintainer of this repository. The IPA is neither rehosted nor modified. Its download URL points directly to the official Catbox download published by the APEX developer in the official [GitHub Release](https://github.com/lowiqentity/APEX/releases).

The bundle identifier, app version, build version, minimum iOS version, privacy descriptions, file size, and SHA-256 digest are determined directly from the downloaded IPA.

## YouTube by lowiqentity

The legacy-style YouTube build is linked directly and unmodified from [`lowiqentity/releases`](https://github.com/lowiqentity/releases/releases). The developer explicitly marks this IPA as supporting installation only through Feather and LiveContainer. It is included in the main catalog with that warning, but excluded from the AltStore Classic catalogs. Future releases are not guaranteed now that the developer is also working on APEX.

## Stremio

The full-featured Stremio iOS app follows the unofficial [`gorlev/stremio-altstore`](https://github.com/gorlev/stremio-altstore) source published at `https://repo.omix4.one/stremio-ios.json`. The IPA itself is downloaded directly and unmodified from Stremio's public `dl.strem.io` CDN. The updater verifies its bundle identifier, version, build, minimum iOS version, byte size, and SHA-256 digest before publishing it.

## Nuvio

Official Nuvio is monitored through [`NuvioMedia/NuvioMobile`](https://github.com/NuvioMedia/NuvioMobile). Its current releases do not provide an iOS IPA, so it is intentionally kept out of the published source until a directly downloadable official IPA becomes available.

## Nuvio Enhanced

Nuvio Enhanced is an actively maintained unofficial build from [`luqmanfadlli/NuvioMobile-iOS`](https://github.com/luqmanfadlli/NuvioMobile-iOS). This repository maintains its own source metadata and links directly to the latest unmodified `-Enhanced.ipa` published in that project's GitHub Releases; the upstream raw source JSON is not used for distribution. It uses Nuvio's `com.nuvio.media` bundle identifier, so it may replace or conflict with another Nuvio installation rather than install alongside it.

## Nuvio Full

Nuvio Full is the alternative Full build from [`luqmanfadlli/NuvioMobile-iOS`](https://github.com/luqmanfadlli/NuvioMobile-iOS). This repository links directly to the latest unmodified `-Full.ipa` from its GitHub Releases. Full and Enhanced intentionally appear as separate choices in this source, but both use `com.nuvio.media`; installing one therefore replaces the other.

Both Nuvio variants appear in the main FlareStore catalog. Their individual JSON files remain available for clients that enforce AltStore's unique-bundle-identifier rule.

## Adding more apps later

Each app has its own entry in [`config/apps.json`](config/apps.json). The generic updater processes that configuration, checks the latest official GitHub Release, downloads the IPA for inspection only, and adds a version only when `CFBundleShortVersionString` or `CFBundleVersion` is new. The IPA itself is never stored in this repository.

The updater runs every six hours and can also be started manually through GitHub Actions.
