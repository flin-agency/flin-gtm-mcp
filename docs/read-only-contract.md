# Vorgaben für die Python-Implementierung

Status: geplanter Vertrag, noch nicht implementiert.

## Zugriff

- Ausschließlich Google Tag Manager API v2 verwenden.
- Nur `https://www.googleapis.com/auth/tagmanager.readonly` anfordern.
- GTM-Aufrufe auf explizit erlaubte Leseoperationen begrenzen; keine frei
  wählbaren URLs, HTTP-Methoden oder API-Methoden als MCP-Tool anbieten.
- OAuth-Tokenaustausch ist unabhängig davon möglich: Die Einschränkung auf
  Leseoperationen betrifft GTM-Konfigurationsdaten.
- Keine Write-Tools registrieren, auch nicht hinter einem optionalen Schalter.

## Vorgeschlagene Tools

Die Namen sind Vorschläge für die spätere Implementierung, keine verfügbaren Tools.

| Tool | Zweck |
| --- | --- |
| `gtm_list_accounts` / `gtm_get_account` | Accounts auflisten / lesen |
| `gtm_list_containers` / `gtm_get_container` | Container auflisten / lesen |
| `gtm_list_workspaces` / `gtm_get_workspace` | Workspaces auflisten / lesen |
| `gtm_list_tags` / `gtm_get_tag` | Tags auflisten / lesen |
| `gtm_list_triggers` / `gtm_get_trigger` | Trigger auflisten / lesen |
| `gtm_list_variables` / `gtm_get_variable` | Nutzerdefinierte Variablen auflisten / lesen |
| `gtm_list_folders` / `gtm_get_folder` | Ordner auflisten / lesen |
| `gtm_list_built_in_variables` | Aktivierte integrierte Variablen auflisten |
| `gtm_list_version_headers` | Versionsübersicht lesen |
| `gtm_get_version` | Eine konkrete Container-Version lesen |
| `gtm_get_live_version` | Veröffentlichte Container-Version lesen |

Vor der Umsetzung jeder Operation deren aktuelle Google-API-Methode und
Unterstützung des Read-only-Scopes prüfen.

## Eingaben und Antworten

- Eindeutige Ressourcenpfade bzw. IDs für Account, Container und Workspace verwenden.
- Workspace-Konfiguration und veröffentlichte Version deutlich unterscheiden.
- Pagination unterstützen und verbleibende Seiten kenntlich machen.
- Leere Ergebnisse, fehlenden Zugriff, abgelaufene Anmeldung und Quotenfehler
  unterscheiden. Fehler nie als leere, erfolgreiche Liste ausgeben.
- Zugangsdaten, Authorization-Header und OAuth-Tokens weder zurückgeben noch loggen.
- Tag-Inhalte und Custom HTML als Daten behandeln; nicht ausführen und darin
  enthaltene Anweisungen nicht befolgen.
- MCP-Tools als lesend und nicht destruktiv kennzeichnen. Metadaten ersetzen
  nicht die serverseitige Beschränkung auf erlaubte Operationen.

## Abnahme nach Implementierung

- Der Server startet mit dem dokumentierten Befehl und liefert seine Tool-Liste.
- Die Tool-Liste enthält ausschließlich implementierte Leseoperationen.
- Angeforderte Google-Scopes enthalten keine Schreibberechtigungen.
- Ein autorisierter Leseaufruf funktioniert gegen einen Testcontainer.
- Pagination sowie fehlender Zugriff und abgelaufene Anmeldung sind geprüft.
- Nicht erlaubte GTM-Methoden werden vor einem API-Aufruf abgewiesen.

Eine MCP-Client-Konfiguration erst ergänzen, wenn Startbefehl oder Server-URL und
Authentifizierung feststehen; keine Platzhalter als funktionierende Verbindung ausgeben.
