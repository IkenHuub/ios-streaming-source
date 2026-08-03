# iOS Streaming Source

A generic AltStore-compatible source for official iOS app distributions. The source works with AltStore Classic and apps that support the same source format, including FlareStore, Feather, and SideStore.

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

## Adding more apps later

Each app has its own entry in [`config/apps.json`](config/apps.json). The generic updater processes that configuration, checks the latest official GitHub Release, downloads the IPA for inspection only, and adds a version only when `CFBundleShortVersionString` or `CFBundleVersion` is new. The IPA itself is never stored in this repository.

The updater runs every six hours and can also be started manually through GitHub Actions.
