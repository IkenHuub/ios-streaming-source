# iOS Streaming Source

A generic AltStore-compatible source for (un)official iOS streaming apps. The source works with AltStore Classic and apps that support the same source format, including FlareStore, Feather, and SideStore.

## Source URL

```text
https://ikenhuub.github.io/ios-streaming-source/apps.json
```

An identical compatibility alias is available at `https://ikenhuub.github.io/ios-streaming-source/repo.json`.

## Add to FlareStore

1. Open FlareStore and go to **Sources**.
2. Select **Add Source** or tap the plus button.
3. Paste `https://ikenhuub.github.io/ios-streaming-source/apps.json`.
4. Confirm that you want to add the source.

## APEX

APEX is not developed by the maintainer of this repository. The IPA is neither rehosted nor modified. Its download URL points directly to the official Catbox download published by the APEX developer in the official [GitHub Release](https://github.com/lowiqentity/APEX/releases).

The bundle identifier, app version, build version, minimum iOS version, privacy descriptions, file size, and SHA-256 digest are determined directly from the downloaded IPA.

## Stremio

The full-featured Stremio iOS app follows the unofficial [`gorlev/stremio-altstore`](https://github.com/gorlev/stremio-altstore) source published at `https://repo.omix4.one/stremio-ios.json`. The IPA itself is downloaded directly and unmodified from Stremio's public `dl.strem.io` CDN. The updater verifies its bundle identifier, version, build, minimum iOS version, byte size, and SHA-256 digest before publishing it.

## Nuvio

Official Nuvio is monitored through [`NuvioMedia/NuvioMobile`](https://github.com/NuvioMedia/NuvioMobile). Its current releases do not provide an iOS IPA, so it is intentionally kept out of the published source until a directly downloadable official IPA becomes available.

## Nuvio Enhanced

Nuvio Enhanced is a community-maintained fork from [`yesnt10/NuvioMobile-Enhanced`](https://github.com/yesnt10/NuvioMobile-Enhanced). Its unsigned IPA is linked directly from the fork maintainer's official GitHub Release and is never rehosted or modified by this repository. Its separate `com.nuvio.enhanced` bundle identifier allows it to be installed alongside official Nuvio.

## Nuvio Full

Nuvio Full is an unofficial, full-featured iOS build from [`luqmanfadlli/NuvioMobile-iOS`](https://github.com/luqmanfadlli/NuvioMobile-iOS), a fork of the official NuvioMobile source code. The IPA is linked directly from that fork's GitHub Release and is never rehosted or modified here. It uses Nuvio's `com.nuvio.media` bundle identifier, so it may replace or conflict with an existing official Nuvio installation rather than install alongside it.

## Adding more apps later

Each app has its own entry in [`config/apps.json`](config/apps.json). The generic updater processes that configuration, checks the latest official GitHub Release, downloads the IPA for inspection only, and adds a version only when `CFBundleShortVersionString` or `CFBundleVersion` is new. The IPA itself is never stored in this repository.

The updater runs every six hours and can also be started manually through GitHub Actions.
