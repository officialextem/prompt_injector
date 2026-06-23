# Prompt-Injector

Prompt-Injector ist ein lokales Windows-Desktop-Tool, das Prompt-Ketten aus `.txt`-, `.md`- und `.pdf`-Dateien in einzelne Prompt-Bloecke aufteilen und spaeter kontrolliert in aktive Zielfenster einfuegen soll.

Das Tool bleibt Human-in-the-loop: kein automatisches Absenden, kein blindes Klicken und keine automatische Antwortauswertung.

## Start

```powershell
python -m prompt_injector
```

## Tests

```powershell
python -m pytest
```

## Aktueller Stand

- startbares Tkinter-Hauptfenster
- Datenmodelle fuer `PromptBlock`, `PromptSession` und `InjectorSettings`
- Parser fuer `.txt`-, `.md`- und `.pdf`-Prompt-Ketten
- Datei-Import per Dialog fuer `.txt`, `.md` und `.pdf`
- PDF-Text-Extraktion ueber PyMuPDF ohne OCR
- linke Prompt-Liste mit Status und Fortschritt
- rechte Detailansicht mit Prompt-Nummer, Titel, editierbarem Inhalt, Zeichenanzahl und grober Token-Schaetzung
- lokale Session-Speicherung und Session-Laden als JSON
- automatische Session-Dateinamen nach `sessions/session_YYYY-MM-DD_HH-MM-SS.json`
- Clipboard-Kopieren und kontrolliertes Strg+V-Einfuegen ohne Enter
- optionales Wiederherstellen des urspruenglichen Clipboard-Inhalts nach dem Einfuegen
- persistente Settings fuer letzten Ordner, Clipboard-Restore, Einfuege-Modus, Always-on-top und Fenstergeometrie
- Logging nach `prompt_injector/runs/prompt_injector.log`
- optionale globale Hotkeys F6-F9 ueber `keyboard`
- Settings-Dialog per Zahnrad mit personalisierbaren Hotkeys, Zielfenster-Auswahl und optionalem Auto-Send
- manuelles Antwort-Archiv unter `prompt_injector/runs/`
- Fixing-Prompt fuer unsauber formatierte Prompt-Ketten
- Status-Reset fuer versehentlich erledigte, uebersprungene oder kopierte Prompts
- grobe Token-Schaetzung ueber `len(text) // 4`

## Erkannte Header-Beispiele

```text
PROMPT 0
Prompt 1
# PROMPT 1
## PROMPT 2
### PROMPT 3
### 📦 PROMPT 1: Basis-Architektur
🔍 PROMPT 2: Fenster-Erkennung
🛡️ PROMPT 3: Sicherheit
💥 PROMPT 4: Edge Cases
```

Titel nach einem Doppelpunkt werden als Prompt-Titel uebernommen. Wenn kein Titel vorhanden ist, wird das Label wie `PROMPT 1` als Standardtitel genutzt.

Falls keine Prompt-Header gefunden werden, wird der gesamte Text als einzelner `PromptBlock` mit `PROMPT 0` zurueckgegeben.

## Bedienung

1. In der Header-Iconleiste `Datei laden` auswaehlen und eine `.txt`-, `.md`- oder `.pdf`-Datei oeffnen.
2. Prompt-Injector liest `.txt`/`.md` mit UTF-8-SIG ein oder extrahiert PDF-Text mit PyMuPDF und uebergibt den Inhalt an `parse_prompt_blocks(...)`.
3. Erkannte Prompts erscheinen links mit Label, Titel und Status.
4. Bei Auswahl eines Prompts wird rechts der Titel und Inhalt angezeigt.
5. Aenderungen am Titel oder Inhalt werden vor Auswahlwechsel, Navigation und Session-Speicherung im Datenmodell gesichert.
6. Die untere Aktionsleiste ist einzeilig und nutzt Symbolbuttons; Tooltips erklaeren die jeweilige Aktion beim Darueberfahren.
7. `In Clipboard kopieren` schreibt nur den aktuellen Prompt in die Zwischenablage.
8. `In aktives Fenster einfuegen` fragt vorher nach, minimiert die App kurz und sendet nur `Ctrl+V`.

## Sessions

`Session speichern` schreibt den aktuellen Zustand automatisch nach:

```text
prompt_injector/sessions/session_YYYY-MM-DD_HH-MM-SS.json
```

Gespeichert werden Quelle, Erstellungszeit, Aktualisierungszeit, aktueller Index und alle Prompts mit `index`, `label`, `title`, `content`, `status` und `notes`.

`Session laden` oeffnet einen Dateidialog fuer `.json`-Sessions. Beim Laden werden aktueller Index, editierte Inhalte und Statuswerte wiederhergestellt. Kaputte oder strukturell ungueltige JSON-Dateien werden mit einer verstaendlichen Fehlermeldung abgelehnt.

Statuswerte:

- `pending`: noch nicht benutzt
- `copied`: in Clipboard kopiert
- `inserted`: alter Kompatibilitaetsstatus aus frueheren Sessions
- `done`: vom Nutzer als erledigt markiert
- `skipped`: uebersprungen
- `failed`: fehlgeschlagen

Neue erfolgreiche Einfuegeaktionen werden direkt als `done` gespeichert. `inserted` bleibt gueltig, damit alte Session-Dateien weiter geladen werden koennen.

## Fixing-Prompt Kopieren

Wenn eine Prompt-Kette nicht korrekt erkannt wird:

1. Button `Fixing-Prompt kopieren` klicken.
2. Den kopierten Text in ChatGPT, Gemini oder Grok einfuegen.
3. Danach die unsaubere Prompt-Kette darunter einfuegen.
4. Antwort kopieren und als neue `.md` oder `.txt` speichern.
5. Diese Datei erneut in Prompt-Injector laden.

Der Button kopiert nur Text in die Zwischenablage. Es wird nichts automatisch abgesendet, keine Webseite geoeffnet und keine Browser-Automation ausgefuehrt.

## Status Zuruecksetzen

Wenn ein Prompt versehentlich erledigt, uebersprungen, kopiert oder als fehlgeschlagen markiert wurde:

1. Prompt in der Liste auswaehlen.
2. `Status zuruecksetzen` klicken.
3. Der Prompt steht wieder auf `pending`.

Der neue Status wird beim naechsten Session-Speichern in der JSON-Datei gesichert.

## Clipboard-Restore

Wenn `restore_clipboard` in `prompt_injector/settings.json` auf `true` steht, liest Prompt-Injector den urspruenglichen Clipboard-Inhalt vor dem Einfuegen, haelt ihn nur im Arbeitsspeicher und stellt ihn nach `Ctrl+V` wieder her. Der alte Clipboard-Inhalt wird nicht geloggt und nicht in Dateien gespeichert.

## Settings

Die Datei `prompt_injector/settings.json` speichert:

- `last_directory`: letzter Datei- oder Session-Ordner
- `restore_clipboard`: Clipboard nach dem Einfuegen wiederherstellen
- `paste_mode`: aktuell `clipboard`
- `always_on_top`: Fenster immer im Vordergrund
- `window_geometry`: letzte Fensterposition und -groesse
- `enable_global_hotkeys`: globale Hotkeys aktivieren
- `target_window_title`: optionales Zielfenster fuer das Einfuegen
- `auto_send_after_paste`: nach dem Einfuegen automatisch Enter senden
- `hotkeys`: personalisierte Hotkeys fuer Copy, Paste, Done+Next und Not-Stopp

Die Optionen werden ueber den Zahnrad-Button in der Header-Iconleiste geaendert. Always-on-top wird sofort per Tkinter-Attribut `-topmost` auf das Hauptfenster angewendet.

Der Settings-Dialog enthaelt:

- Clipboard nach Einfuegen wiederherstellen
- Fenster immer im Vordergrund
- Globale Hotkeys aktivieren
- Hotkeys personalisieren
- Zielfenster aus sichtbaren Fenstern auswaehlen
- Automatisch senden nach Einfuegen

`Automatisch senden nach Einfuegen` ist standardmaessig aus. Wenn aktiv, sendet Prompt-Injector nach `Ctrl+V` automatisch `Enter`.

## Globale Hotkeys

Globale Hotkeys sind optional und muessen in den Settings aktiviert werden. Wenn das `keyboard`-Paket fehlt oder Windows/Berechtigungen globale Hooks blockieren, zeigt Prompt-Injector eine verstaendliche Warnung und laeuft ohne Hotkeys weiter.

Standard-Hotkeys:

- `F6`: aktuellen Prompt in Clipboard kopieren
- `F7`: aktuellen Prompt nach Bestaetigung per `Ctrl+V` einfuegen
- `F8`: aktuellen Prompt als erledigt markieren und den naechsten Prompt vorbereiten
- `F9`: Not-Stopp, bricht eine geplante Einfuegeaktion im Countdown ab

Hotkey-Callbacks manipulieren Tkinter nicht direkt aus Fremdthreads, sondern werden ueber `root.after(...)` in den GUI-Thread delegiert. Per Hotkey wird nur dann Enter gesendet, wenn `Automatisch senden nach Einfuegen` explizit aktiviert ist.

Wenn `Automatisch senden nach Einfuegen` aktiv ist, kann `F7` nach dem Einfuegen ebenfalls `Enter` senden.

## Logging

Logs liegen unter:

```text
prompt_injector/runs/prompt_injector.log
```

Geloggte Ereignisse: App gestartet/beendet, Datei geladen, erkannte Prompt-Anzahl, Session gespeichert/geladen, Prompt kopiert/eingefuegt/erledigt/uebersprungen und Fehler mit Exception-Typ und Nachricht. Clipboard-Inhalte und vollstaendige Prompt-Inhalte werden nicht geloggt.

## Antwort-Archiv

Das Antwort-Archiv ist manuell. Prompt-Injector liest keine fremden Fenster, keine Browser und keine Assistentenantworten automatisch aus.

Bedienung:

1. Nach einem externen Codex-/Claude-/Cursor-Lauf die Antwort manuell kopieren.
2. Antwort in das Feld `Antwort-Archiv (manuell einfuegen)` einfuegen.
3. `Antwort speichern` klicken.

Prompt-Injector erzeugt im Ordner `prompt_injector/runs/` einen Run-Ordner. Pro Prompt werden diese Dateien geschrieben:

```text
prompt_XX.md
response_XX.md
summary.json
```

`summary.json` enthaelt Session-Datei, Quelldatei, Prompt-Anzahl, Prompt-Status, Antwort-Dateien und Zeitstempel.

## Abhaengigkeiten

```powershell
pip install -r requirements.txt
```

- `pyperclip` fuer Clipboard-Lesen und -Schreiben
- `pyautogui` fuer `Ctrl+V`
- `PyMuPDF` fuer PDF-Text-Extraktion
- `keyboard` fuer optionale globale Hotkeys
- `pygetwindow` fuer optionale Zielfenster-Auswahl

## Bewusste MVP-Grenzen

- keine OCR fuer gescannte PDFs
- globale Hotkeys sind optional und koennen je nach Windows-Rechten blockiert sein
- automatisches Absenden ist nur als explizite Settings-Option aktivierbar und standardmaessig aus
- kein Klicken auf Senden-Buttons
- keine automatische Antwortauswertung
- keine automatische Antwortauslesung aus fremden Apps

## Manueller v0.1-Testplan

1. App starten: `python -m prompt_injector`.
2. `.txt`-Datei mit mehreren `PROMPT N`-Bloecken laden.
3. `.md`-Datei mit Markdown-Headern wie `## PROMPT 2` laden.
4. `.pdf` mit normalem Text laden und pruefen, ob die Prompts erkannt werden.
5. Gescanntes PDF oder PDF ohne extrahierbaren Text laden und Fehlermeldung pruefen.
6. Datei ohne Prompt-Header laden und pruefen, ob sie als einzelner `PROMPT 0` erscheint.
7. Leere `.txt`-Datei laden und pruefen, dass die App nicht abstuerzt und keine Aktionsbuttons aktiv sind.
8. Prompt-Titel und Prompt-Inhalt bearbeiten, dann Prompt wechseln und zurueckwechseln.
9. `Fixing-Prompt kopieren` klicken, in einen Editor einfuegen und Inhalt pruefen.
10. `In Clipboard kopieren` ausfuehren und pruefen, ob der Status `copied` wird.
11. `In aktives Fenster einfuegen` ausfuehren, bestaetigen und ein Ziel-Textfeld fokussieren; Status muss danach `done` sein.
12. Prompt mit `Als erledigt markieren` auf `done` setzen.
13. `Status zuruecksetzen` klicken und pruefen, ob Status wieder `pending` ist.
14. Prompt mit `Ueberspringen` auf `skipped` setzen.
15. `Status zuruecksetzen` klicken und pruefen, ob Status wieder `pending` ist.
16. `Zurueck` und `Weiter` testen und pruefen, dass Bearbeitungen erhalten bleiben.
17. `Session speichern` ausfuehren und die JSON-Datei unter `prompt_injector/sessions/` pruefen.
18. App neu starten, `Session laden` ausfuehren und Status, Inhalt und aktuellen Index pruefen.
19. Kaputte Session-Datei mit ungueltigem JSON laden und pruefen, ob ein Fehlerdialog erscheint.
20. Alte Session mit Status `inserted` laden, falls vorhanden.
21. Settings `Clipboard nach Einfuegen wiederherstellen` und `Fenster immer im Vordergrund` aendern.
22. App schliessen und neu oeffnen, dann gespeicherte Settings und Fenstergeometrie pruefen.
23. Logdatei `prompt_injector/runs/prompt_injector.log` pruefen: keine Clipboard-Inhalte und keine vollstaendigen Prompt-Inhalte.
