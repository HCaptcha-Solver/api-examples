# API-Beispiele für HCaptcha Solver

[![Beispiele](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml/badge.svg)](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml)

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

[Website](https://hcaptchasolver.org/) · [Interaktive Dokumentation](https://hcaptchasolver.org/?lang=de#/docs) · [OpenAPI](https://api.hcaptchasolver.org/v2/openapi.json)

Beispiele zum Kopieren in **Python, Node.js und cURL** für den Dienst HCaptcha Solver. Dieses Repository enthält API-Clients, ein Hilfsprogramm zur Bildvorbereitung und synthetische Beispielbilder. Die Beispiele rufen die gehostete API auf; sie führen keinen lokalen CAPTCHA-Löser aus.

| Modus | Sie senden | Sie erhalten |
| --- | --- | --- |
| Verwalteter Chrome | Die öffentliche Seiten-URL und die hCaptcha-`sitekey` des Widgets | Eine Vorgangs-ID; fragen Sie den Status ab, bis das Widget ein Token ausstellt oder der Vorgang fehlschlägt |
| Bilder | Screenshot der Aufgabe, Anweisung, optionale Referenzbilder und Interaktionsrechtecke | Klicks, ausgewählte Rasterzellen oder Ziehbewegungen, die Ihre Integration ausführt |

Der Code steht unter der [MIT-Lizenz](LICENSE). Verwenden Sie den Dienst für Websites und Abläufe, deren Automatisierung Ihnen gestattet ist. HCaptcha Solver ist ein unabhängiger Dienst und nicht mit dem hCaptcha-Anbieter verbunden.

## 1. Einrichtung

Erstellen Sie ein Konto auf [hcaptchasolver.org](https://hcaptchasolver.org/), bestätigen Sie Ihre E-Mail-Adresse, laden Sie Guthaben auf und erstellen Sie einen API-Schlüssel. Aktivieren Sie `images` und/oder `browser`; ergänzen Sie `balance` für Guthabenabfragen und `feedback` für Ergebnismeldungen.

```bash
git clone https://github.com/HCaptcha-Solver/api-examples.git
cd api-examples
export HCAPTCHA_API_KEY='YOUR_API_KEY'
```

Der Python-HTTP-Client verwendet ausschliesslich die Standardbibliothek (**Python 3.11+**). Die Node-Beispiele benötigen **Node.js 22+** mit integriertem `fetch`; `npm install` ist nicht erforderlich. Das Hilfsprogramm zur Bildvorbereitung benötigt zusätzlich Pillow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python python/example.py balance
# Oder: node javascript/example.mjs balance
```

Unter Windows PowerShell setzen Sie `$env:HCAPTCHA_API_KEY = 'YOUR_API_KEY'`, erstellen die virtuelle Umgebung mit `py -m venv .venv` und verwenden `.\.venv\Scripts\python.exe` anstelle von `python`. Die Beispiele lesen Umgebungsvariablen; `.env`-Dateien werden nicht automatisch geladen. Ersetzen Sie `YOUR_API_KEY` durch Ihren privaten API-Schlüssel.

Bewahren Sie Schlüssel in Ihrem Backend oder Ihren eigenen vertrauenswürdigen Werkzeugen auf. Betten Sie keinen Kontoschlüssel in eine öffentliche Webseite ein. Geldbeträge sind ganzzahlige Millionstel USD: Teilen Sie durch `1_000_000`. `available` enthält kein Guthaben, das bereits für laufende Vorgänge reserviert ist.

## 2. Eine Bildanfrage lokal vorbereiten

Lesen Sie zuerst die [Anleitung zu Bildern und Koordinaten](docs/image-mode.md) auf Englisch oder die [interaktive Dokumentation auf Deutsch](https://hcaptchasolver.org/?lang=de#/docs). Die wichtigsten Felder:

- **`image`** ist die vollständige Aufnahme der Aufgabe als PNG/JPEG, kodiert als reine Base64-Zeichenfolge ohne Präfix.
- **`references`**, im Plural, enthält separate Beispielbilder zum visuellen Vergleich. Die Liste darf leer sein.
- **`canvases`** enthält Rechtecke, die anklickbare oder verschiebbare Bereiche **innerhalb des Hauptbildes** markieren. Es handelt sich um Koordinaten, nicht um Bilddateien.
- **`tiles`** enthält die neun Zellrechtecke eines DOM-Rasters. Für ein in ein einzelnes Canvas gezeichnetes Raster verwenden Sie stattdessen `canvases`.

Dieser Befehl erzeugt eine JSON-Datei aus unserer synthetischen Illustration mit 600 × 400 Pixeln. Er stellt **keine Netzwerkanfragen**:

```bash
python python/prepare_image_request.py fixtures/challenge.png \
  --question 'Click the object matching the example' \
  --canvas 30 80 540 280 \
  --reference fixtures/reference.png --output request.json
```

`--output` speichert JSON unter Linux, macOS und Windows einheitlich in UTF-8. Die mehrzeiligen Befehle verwenden Bash/zsh-Syntax; schreiben Sie den Befehl für das Hilfsprogramm in PowerShell in eine einzige Zeile. `--canvas` nimmt Pixelwerte des Hauptbildes entgegen und rechnet sie auf die API-Skala von 0–1000 um. Hier ergibt sich `{ "x": 50, "y": 200, "width": 900, "height": 700 }`. Lassen Sie `--reference` weg, wenn es kein Beispielbild gibt. Wiederholen Sie das Argument für mehrere Referenzen. Für ein DOM-Raster geben Sie neun `--tile X Y WIDTH HEIGHT`-Argumente in Leserichtung an.

Für eine echte Aufgabe ersetzen Sie die Beispieldateien, die Anweisung und die Rechtecke durch Ihre aktuelle Aufnahme. Übernehmen Sie die Anweisung in ihrer sichtbaren Originalsprache. Die Beispieldateien veranschaulichen nur das Format; sie sind kein echtes CAPTCHA und können kein Token ausstellen. Speichern Sie echte Aufnahmen in `captures/`; dieser Ordner wird von Git ignoriert.

## 3. Das Bild senden — einen Client auswählen

Die folgenden POST-Aufrufe verbrauchen Kontoguthaben. Erzeugen Sie für jeden **neuen** Vorgang eine Anfrage-ID:

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py image request.json --idempotency-key "$REQUEST_ID"
# Oder mit derselben vorbereiteten JSON-Datei:
# node javascript/example.mjs image request.json --idempotency-key "$REQUEST_ID"
```

In PowerShell: `$requestId = [guid]::NewGuid().ToString()`. Übergeben Sie anschliessend `--idempotency-key $requestId` an den gewählten Client.

Falls die Verbindung abbricht und unklar ist, ob die API die Anfrage angenommen hat, **verwenden Sie dieselbe JSON-Datei und dieselbe Anfrage-ID erneut**. Starten Sie das Hilfsprogramm nicht erneut und erzeugen Sie für diese Wiederholung keine neue ID. Eine neue ID kann einen weiteren kostenpflichtigen Vorgang starten. Unsere Clients wiederholen POST-Anfragen nicht automatisch.

Der Client wartet, solange der Vorgang `queued` oder `running` ist. Er gibt das vollständige abschliessende JSON aus und beendet sich bei fehlgeschlagenen oder abgelaufenen Ergebnissen mit einem Fehler. Bewahren Sie die Vorgangs-ID auf, falls die Statusabfrage ihr Zeitlimit erreicht, und setzen Sie die Abfrage damit fort:

```bash
python python/example.py get SERVER_OPERATION_ID
# Oder: node javascript/example.mjs get SERVER_OPERATION_ID
```

Ersetzen Sie `SERVER_OPERATION_ID` durch die vom Server erhaltene Vorgangs-ID.

**Lesen Sie `result.action`, nicht ein `action`-Feld auf der obersten Ebene.** Eine gekürzte Antwort sieht so aus:

```json
{
  "id": "11111111-1111-4111-8111-111111111111",
  "mode": "image",
  "status": "ready",
  "result_expired": false,
  "result": {
    "protocol": "1",
    "challenge_id": "capture_demo_001",
    "coordinate_space": "full_challenge_image_0_1000",
    "action": { "type": "point", "points": [[250, 450]] },
    "verified_answer": null
  }
}
```

`id` identifiziert den Vorgang auf dem Server. `result.challenge_id` identifiziert Ihre Aufnahme. Prüfen Sie vor dem Ausführen einer Aktion, ob die Aufgabe noch zu dieser Aufnahme passt. Die englische Anleitung zu [Klicks, Ziehbewegungen und Rasterindizes](docs/image-mode.md#apply-the-answer) erklärt die Koordinatenumrechnung. Die Beispiele liefern Anweisungen; sie klicken nicht selbst in Ihrem Browser.

Eine Bildantwort kann kostenpflichtig sein, auch wenn das Widget sie später ablehnt. Jede neue visuelle Runde benötigt eine neue Aufnahme und Anfrage und kann erneut Kosten verursachen. Client-Feedback erstattet Guthaben nicht automatisch.

## 4. Verwalteter Chrome

Senden Sie die öffentliche URL der Seite mit dem Widget und dessen öffentliche `sitekey`. Die sitekey ist **nicht** Ihr HCaptcha-Solver-API-Schlüssel. Dieser Modus startet eine neue Sitzung; er importiert keine Browser-Cookies und führt keinen individuellen Anmeldeablauf aus.

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py browser \
  --url 'https://your-site.example/form' \
  --sitekey 'YOUR_PUBLIC_SITEKEY' \
  --idempotency-key "$REQUEST_ID"
# Oder: node javascript/example.mjs browser --url ... --sitekey ... --idempotency-key "$REQUEST_ID"
```

Ersetzen Sie die Beispiel-URL und `YOUR_PUBLIC_SITEKEY` durch die Werte Ihrer Seite.

POST liefert `202`; der Client fragt anschliessend `GET /v2/tasks/{id}` ab. Lesen Sie `result.token` nur, wenn `status` den Wert `ready` hat, `result_expired` den Wert `false` hat und `result` vorhanden ist. Die Token-Ausstellung durch das Widget beweist keine Annahme durch das Ziel-Backend. Rufen Sie Ergebnisse zeitnah ab: Die API hält sie fünf Minuten vor. Diese Frist ist unabhängig von der Gültigkeit des Tokens selbst.

## cURL

Diese Befehle verwenden Bash/zsh sowie die zuvor vorbereitete JSON-Datei und `REQUEST_ID`. Der erste Befehl ist eine **kostenpflichtige** Anfrage:

```bash
curl --fail-with-body --max-time 45 \
  'https://api.hcaptchasolver.org/v2/solutions' \
  --header "Authorization: Bearer $HCAPTCHA_API_KEY" \
  --header "Idempotency-Key: $REQUEST_ID" \
  --header 'Content-Type: application/json' \
  --data-binary @request.json

curl --fail-with-body \
  'https://api.hcaptchasolver.org/v2/tasks/SERVER_OPERATION_ID' \
  --header "Authorization: Bearer $HCAPTCHA_API_KEY"
```

HTTP 200 allein reicht nicht: Prüfen Sie `status` und `error` des Vorgangs. Anders als die Python-/Node-Beispiele führen diese cURL-Befehle keine automatischen wiederholten Statusabfragen oder Statusprüfungen durch.

## Fehler und Grenzen

| Antwort | Vorgehen |
| --- | --- |
| `401` / `403` | API-Schlüssel und erforderliche Berechtigungsumfänge prüfen. |
| `402` | Guthaben aufladen oder auf die Freigabe einer Reservierung eines anderen Vorgangs warten. |
| `409` | Eine Anfrage-ID wurde mit anderem Inhalt wiederverwendet. Den ursprünglichen Inhalt wiederherstellen oder für eine tatsächlich neue Aufgabe eine neue ID verwenden. |
| `413` / `422` | JSON-Grösse, reines Base64, Feldnamen und Rechteckgrenzen prüfen. `reference` ist kein Alias für `references`. |
| `429` | Die in `Retry-After` angegebene Zeit abwarten und die Parallelität reduzieren. Bei einer Wiederholung desselben Vorgangs Inhalt und ID beibehalten. |
| `5xx` / Netzwerk-Timeout | Ursprünglichen Inhalt und Anfrage-ID beibehalten. Falls bereits eine Vorgangs-ID vorliegt, zuerst deren Status abfragen. |
| HTTP 200 mit `failed` / `cancelled` | `error` prüfen. `result` nicht anwenden. |

Bilder müssen statische PNG/JPEG-Dateien mit jeweils mindestens 8 × 8 Pixeln sein. Das gesamte JSON darf höchstens 10 MiB gross sein; alle dekodierten Bilder zusammen dürfen höchstens 8.000.000 Pixel enthalten. Grenzen: neun Referenzen, acht Canvas-Rechtecke und neun Rasterzellen. Die aktuellen Zeitbudgets betragen 30 Sekunden für Bilder und 90 Sekunden für verwalteten Chrome, einschliesslich Wartezeit in der Warteschlange. Der Client fragt den Status standardmässig bis zu 120 Sekunden lang ab; das Erreichen dieses Zeitlimits bricht den Vorgang auf dem Server nicht ab.

## Den Client weiterverwenden

Die Clients für [Python](python/client.py) und [JavaScript](javascript/client.mjs) unterstützen Guthabenabfragen, Bildlösungen, Browser-Aufgaben, Statusabfragen, Abbruch und Feedback. Kopieren Sie die Dateien in Ihr Backend oder importieren Sie sie aus diesem Checkout. Es handelt sich um Beispiel-Clients, nicht um auf PyPI oder npm veröffentlichte Pakete.

| Endpunkt | Zweck |
| --- | --- |
| `GET /v2/balance` | Guthabenübersicht (Berechtigung `balance`) |
| `POST /v2/solutions` | Eine Bildanfrage analysieren (`images`) |
| `POST /v2/tasks` | Verwalteten Chrome starten (`browser`) |
| `GET /v2/tasks/{id}` | Einen Vorgang abrufen (passende Berechtigung `images` oder `browser`) |
| `DELETE /v2/tasks/{id}` | Einen noch nicht abgeschlossenen Vorgang abbrechen |
| `POST /v2/tasks/{id}/feedback` | `{ "success": true }` oder `{ "success": false }` melden (`feedback`) |

## Tests ohne Guthabenverbrauch ausführen

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Die Tests verwenden simulierte HTTP-Antworten und synthetische Bilder. Sie benötigen weder einen API-Schlüssel noch ein echtes CAPTCHA. In der CI laufen dieselben Tests. Hinweise zu Änderungen und Fehlermeldungen finden Sie in [CONTRIBUTING.md](CONTRIBUTING.md) auf Englisch.

Dokumentation: [English](https://hcaptchasolver.org/?lang=en#/docs) · [Português](https://hcaptchasolver.org/?lang=pt-BR#/docs) · [Deutsch](https://hcaptchasolver.org/?lang=de#/docs) · [Español](https://hcaptchasolver.org/?lang=es#/docs).
