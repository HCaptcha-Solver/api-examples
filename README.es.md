# Ejemplos de la API de HCaptcha Solver

[![Ejemplos](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml/badge.svg)](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml)

[🇺🇸 English](README.md) · [🇧🇷 Português](README.pt-BR.md) · [🇩🇪 Deutsch](README.de.md) · [🇪🇸 Español](README.es.md)

[Sitio web](https://hcaptchasolver.org/) · [Documentación interactiva](https://hcaptchasolver.org/?lang=es#/docs) · [OpenAPI](https://api.hcaptchasolver.org/v2/openapi.json)

Ejemplos listos para copiar en **Python, Node.js y cURL** para el servicio HCaptcha Solver. Este repositorio contiene clientes de la API, una herramienta para preparar imágenes e imágenes sintéticas de ejemplo. Los ejemplos llaman a la API alojada; no ejecutan un resolvedor local.

| Modo | Envías | Recibes |
| --- | --- | --- |
| Chrome gestionado | La URL pública de la página y la `sitekey` de su widget hCaptcha | Un ID de operación; consulta su estado hasta que el widget emita un token o la tarea falle |
| Imágenes | Captura del desafío, instrucción, imágenes de referencia opcionales y rectángulos de interacción | Clics, selecciones de celdas o movimientos de arrastre que tu integración debe aplicar |

El código se publica bajo la [licencia MIT](LICENSE). Utiliza el servicio en sitios y procesos que tengas autorización para automatizar. HCaptcha Solver es un servicio independiente y no está afiliado al proveedor de hCaptcha.

## 1. Configuración

Crea una cuenta en [hcaptchasolver.org](https://hcaptchasolver.org/), verifica tu correo electrónico, añade saldo y crea una clave de API. Introduce solo un nombre para tu clave. La misma clave funciona en la extensión Chrome, el modo por imágenes y Chrome gestionado, incluidas las consultas de saldo y el feedback. El administrador fija el límite de nuevas resoluciones por minuto de la cuenta; todas las claves y ambos modos comparten este límite. Crear otra clave no lo aumenta. Las respuestas HTTP 429 incluyen `Retry-After`; también se aplican límites de simultaneidad e infraestructura.

```bash
git clone https://github.com/HCaptcha-Solver/api-examples.git
cd api-examples
export HCAPTCHA_API_KEY='YOUR_API_KEY'
```

El cliente HTTP de Python utiliza únicamente la biblioteca estándar (**Python 3.11+**). Los ejemplos de Node requieren **Node.js 22+** con `fetch` integrado; no necesitas ejecutar `npm install`. La herramienta para preparar imágenes también utiliza Pillow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python python/example.py balance
# O bien: node javascript/example.mjs balance
```

En Windows PowerShell, define `$env:HCAPTCHA_API_KEY = 'YOUR_API_KEY'`, crea el entorno virtual con `py -m venv .venv` y ejecuta `.\.venv\Scripts\python.exe` en lugar de `python`. Los ejemplos leen variables de entorno; no cargan archivos `.env` automáticamente. Sustituye `YOUR_API_KEY` por tu clave privada de API.

Guarda las claves en tu backend o en tus propias herramientas de confianza. No incluyas una clave de cuenta en una página web pública. Los importes son números enteros expresados en millonésimas de USD: divide entre `1_000_000`. `available` no incluye el saldo reservado por operaciones en curso.

## 2. Preparar una solicitud de imágenes localmente

Lee primero la [guía de imágenes y coordenadas](docs/image-mode.md), en inglés, o la [documentación interactiva en español](https://hcaptchasolver.org/?lang=es#/docs). Estos son los campos principales:

- **`image`** es la captura completa del desafío, en PNG/JPEG codificado como una cadena Base64 sin prefijo.
- **`references`**, en plural, contiene imágenes de ejemplo independientes para la comparación visual. Puede estar vacío.
- **`canvases`** contiene rectángulos que delimitan las zonas donde se puede hacer clic o arrastrar **dentro de la imagen principal**. Son coordenadas, no archivos de imagen.
- **`tiles`** contiene los rectángulos de las nueve celdas de una cuadrícula del DOM. Para una cuadrícula dibujada dentro de un único canvas, utiliza `canvases`.

Este comando prepara un archivo JSON con nuestra ilustración sintética de 600 × 400 píxeles. **No realiza solicitudes de red**:

```bash
python python/prepare_image_request.py fixtures/challenge.png \
  --question 'Click the object matching the example' \
  --canvas 30 80 540 280 \
  --reference fixtures/reference.png --output request.json
```

`--output` guarda el JSON en UTF-8 de forma consistente en Linux, macOS y Windows. Los comandos de varias líneas utilizan la sintaxis de Bash/zsh; en PowerShell, escribe el comando de la herramienta en una sola línea. `--canvas` acepta coordenadas en píxeles de la imagen principal; la herramienta las convierte a la escala de 0–1000 de la API. En este ejemplo, el resultado es `{ "x": 50, "y": 200, "width": 900, "height": 700 }`. Omite `--reference` si no hay imagen de ejemplo. Repite el argumento para incluir varias referencias. Para una cuadrícula del DOM, utiliza nueve argumentos `--tile X Y WIDTH HEIGHT` en orden de lectura.

Para una tarea real, sustituye los archivos de ejemplo, la instrucción y los rectángulos por los de tu captura actual. Copia la instrucción en el idioma original que aparece en el desafío. Las imágenes de ejemplo ilustran el formato; no son un CAPTCHA real y no pueden emitir un token. Guarda las capturas reales en `captures/`, que está excluido de Git.

## 3. Enviar la imagen — elige un cliente

Las siguientes operaciones POST consumen saldo de tu cuenta. Genera un ID de solicitud para cada operación **nueva**:

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py image request.json --idempotency-key "$REQUEST_ID"
# O bien, con el mismo JSON preparado:
# node javascript/example.mjs image request.json --idempotency-key "$REQUEST_ID"
```

Equivalente en PowerShell: `$requestId = [guid]::NewGuid().ToString()`. Después, pasa `--idempotency-key $requestId` al cliente que hayas elegido.

Si falla la conexión y no sabes si la API aceptó la solicitud, **reutiliza tanto el mismo JSON como el mismo ID de solicitud**. No vuelvas a ejecutar la herramienta de preparación ni generes otro ID para ese reintento. Un ID nuevo puede crear otra operación de pago. Nuestros clientes no reintentan automáticamente las solicitudes POST.

El cliente espera mientras la operación está en `queued` o `running`. Muestra el JSON final completo y termina con un error si el resultado ha fallado o ha caducado. Conserva el ID de operación si la consulta de estado supera el tiempo de espera; puedes retomarla con:

```bash
python python/example.py get SERVER_OPERATION_ID
# O bien: node javascript/example.mjs get SERVER_OPERATION_ID
```

Sustituye `SERVER_OPERATION_ID` por el ID de operación recibido del servidor.

**Lee `result.action`, no un campo `action` en el nivel principal.** Una respuesta abreviada tiene este aspecto:

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

`id` identifica la operación en el servidor. `result.challenge_id` identifica tu captura. Antes de aplicar una acción, comprueba que el desafío sigue correspondiendo a esa captura. Consulta la sección sobre [clics, arrastres e índices de cuadrícula](docs/image-mode.md#apply-the-answer), en inglés, para convertir las coordenadas. Los ejemplos devuelven instrucciones; no hacen clic en tu navegador por ti.

Una respuesta de imágenes puede cobrarse aunque el widget la rechace después. Una nueva ronda visual necesita una nueva captura y solicitud, y puede generar otro cargo. Los comentarios enviados por el cliente no reembolsan saldo automáticamente.

## 4. Chrome gestionado

Envía la URL pública que contiene el widget y su `sitekey` pública. La sitekey **no es** tu clave de API de HCaptcha Solver. Este modo inicia una sesión nueva; no importa las cookies de tu navegador ni ejecuta un flujo de inicio de sesión personalizado.

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py browser \
  --url 'https://your-site.example/form' \
  --sitekey 'YOUR_PUBLIC_SITEKEY' \
  --idempotency-key "$REQUEST_ID"
# O bien: node javascript/example.mjs browser --url ... --sitekey ... --idempotency-key "$REQUEST_ID"
```

Sustituye la URL de ejemplo y `YOUR_PUBLIC_SITEKEY` por los valores de tu página.

POST devuelve `202`; el cliente consulta periódicamente `GET /v2/tasks/{id}`. Lee `result.token` solo cuando `status` sea `ready`, `result_expired` sea `false` y exista `result`. La emisión de un token por el widget no demuestra que el backend de destino lo acepte. Recupera los resultados cuanto antes: la API los conserva durante cinco minutos, un plazo independiente de la validez del propio token.

## cURL

Estos comandos utilizan Bash/zsh y el JSON y `REQUEST_ID` preparados anteriormente. El primero es una solicitud **de pago**:

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

HTTP 200 no es suficiente: comprueba los campos `status` y `error` de la operación. A diferencia de los ejemplos de Python/Node, estos comandos cURL no consultan periódicamente ni validan el estado de la tarea de forma automática.

## Errores y límites

| Respuesta | Qué hacer |
| --- | --- |
| `401` / `403` | Comprueba que la clave de API esté activa. Las rutas de cuenta y administración requieren una sesión del panel. |
| `402` | Añade saldo o espera a que se libere el saldo reservado por otra operación. |
| `409` | Se reutilizó un ID de solicitud con contenido diferente. Restaura el contenido original o utiliza un ID nuevo para una tarea realmente nueva. |
| `413` / `422` | Comprueba el tamaño del JSON, el Base64 sin prefijo, los nombres de los campos y los límites de los rectángulos. `reference` no es un alias de `references`. |
| `429` | Espera el intervalo indicado en `Retry-After` y reduce la concurrencia. Conserva el mismo contenido e ID al reintentar la misma operación. |
| `5xx` / tiempo de espera de red agotado | Conserva el contenido original y el ID de solicitud; si ya tienes un ID de operación, consúltalo primero. |
| HTTP 200 con `failed` / `cancelled` | Comprueba `error`. No apliques `result`. |

Las imágenes deben ser archivos PNG/JPEG estáticos, de al menos 8 × 8 píxeles cada uno. El JSON completo puede ocupar como máximo 10 MiB; las imágenes decodificadas no pueden superar 8.000.000 de píxeles en total. Límites: nueve referencias, ocho rectángulos de canvas y nueve celdas de cuadrícula. Los límites de tiempo actuales son de 30 segundos para imágenes y 90 segundos para Chrome gestionado, incluido el tiempo en cola. El cliente consulta el estado durante un máximo de 120 segundos de forma predeterminada; agotar ese tiempo de espera no cancela la tarea en el servidor.

## Reutilizar el cliente

Los clientes de [Python](python/client.py) y [JavaScript](javascript/client.mjs) permiten consultar saldo, resolver imágenes, crear tareas de navegador, consultar el estado, cancelar operaciones y enviar comentarios sobre el resultado. Copia los archivos en tu backend o impórtalos desde esta copia del repositorio. Son clientes de ejemplo, no paquetes publicados en PyPI o npm.

| Endpoint | Función |
| --- | --- |
| `GET /v2/balance` | Consultar el saldo |
| `POST /v2/solutions` | Analizar una solicitud de imágenes |
| `POST /v2/tasks` | Iniciar Chrome gestionado |
| `GET /v2/tasks/{id}` | Recuperar una operación de tu cuenta |
| `DELETE /v2/tasks/{id}` | Cancelar una operación que aún no ha terminado |
| `POST /v2/tasks/{id}/feedback` | Comunicar `{ "success": true }` o `{ "success": false }` |

## Ejecutar pruebas sin consumir saldo

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Las pruebas utilizan respuestas HTTP simuladas e imágenes sintéticas. No necesitan una clave de API ni un CAPTCHA real. La integración continua ejecuta las mismas pruebas. Para cambios e informes de errores, consulta [CONTRIBUTING.md](CONTRIBUTING.md), en inglés.

Documentación: [English](https://hcaptchasolver.org/?lang=en#/docs) · [Português](https://hcaptchasolver.org/?lang=pt-BR#/docs) · [Deutsch](https://hcaptchasolver.org/?lang=de#/docs) · [Español](https://hcaptchasolver.org/?lang=es#/docs).
