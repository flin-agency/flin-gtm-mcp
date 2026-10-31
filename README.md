# flin Google Tag Manager MCP

Read-only MCP für Google Tag Manager von flin.

Repository: https://github.com/flin-agency/flin-gtm-mcp

## Status

Projektgrundlage und Funktionsumfang sind vorbereitet. Die Python-Implementierung
wird separat ergänzt. Aktuell gibt es noch keinen ausführbaren MCP-Server,
keine OAuth-Anmeldung und keine installierte MCP-Verbindung.

## Geplanter Umfang

- Accounts, Container und Workspaces auflisten und lesen.
- Tags, Trigger, Variablen und Ordner eines Workspaces auflisten und lesen.
- Aktivierte integrierte Variablen auflisten.
- Container-Versionen und die veröffentlichte Version lesen.
- Konfigurationen analysieren und Unterschiede erklären.

Änderungen, Löschen, Importieren, Synchronisieren, Versionserstellung,
Preview-Erstellung und Veröffentlichen sind nicht Bestandteil dieser Version.

## Google-Zugriff

Google Tag Manager API v2 aktivieren und ausschließlich diesen OAuth-Scope verwenden:

```text
https://www.googleapis.com/auth/tagmanager.readonly
```

Der angemeldete Google-Nutzer benötigt Zugriff auf die betreffenden GTM-Container.
Die konkrete OAuth- und Server-Konfiguration folgt mit der Python-Implementierung.
Zugangsdaten und Tokens gehören nicht ins Repository.

## Umsetzung

Die Vorgaben für die Python-Implementierung stehen in
[docs/read-only-contract.md](docs/read-only-contract.md).
Startbefehl, Installation, Transport und Deployment werden ergänzt, sobald die
Implementierung vorhanden ist.

## Referenzen

- [Google: Autorisierung und Scopes](https://developers.google.com/tag-platform/tag-manager/api/v2/authorization)
- [Google: Tag Manager API v2](https://developers.google.com/tag-platform/tag-manager/api/reference/rest/v2/accounts)
