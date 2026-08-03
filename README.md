# iOS Source

Een generieke AltStore-compatible source voor officiële iOS-appdistributies. De source werkt met AltStore Classic en apps die hetzelfde source-formaat ondersteunen, waaronder FlareStore, Feather en SideStore.

## Source-URL

```text
https://ikenhuub.github.io/ios-source/apps.json
```

De identieke compatibiliteitsalias is `https://ikenhuub.github.io/ios-source/repo.json`.

## Toevoegen aan FlareStore

1. Open FlareStore en ga naar **Sources**.
2. Kies **Add Source** of het plusteken.
3. Plak `https://ikenhuub.github.io/ios-source/apps.json`.
4. Bevestig het toevoegen van de source.

## APEX

APEX wordt niet door de beheerder van deze repository ontwikkeld. De IPA wordt niet opnieuw gehost of gewijzigd. De download-URL verwijst rechtstreeks naar de officiële Catbox-download die de APEX-ontwikkelaar zelf in de officiële [GitHub Release](https://github.com/lowiqentity/APEX/releases) heeft gepubliceerd.

Bundle identifier, appversie, buildversie, minimum iOS-versie, privacyteksten, bestandsgrootte en SHA-256 worden rechtstreeks uit de gedownloade IPA bepaald.

## Later apps toevoegen

Elke app heeft een eigen item in [`config/apps.json`](config/apps.json). De generieke updater doorloopt die configuratie, controleert de nieuwste officiële GitHub Release, downloadt de IPA alleen voor inspectie en voegt uitsluitend een versie toe wanneer `CFBundleShortVersionString` of `CFBundleVersion` nieuw is. De IPA zelf wordt nooit in deze repository opgeslagen.

De updater draait elke zes uur en kan ook handmatig via GitHub Actions worden gestart.
