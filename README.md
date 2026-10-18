# HCaptcha Solver API examples

[![Examples](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml/badge.svg)](https://github.com/HCaptcha-Solver/api-examples/actions/workflows/test.yml)
[Português](README.pt-BR.md) · [Website](https://hcaptchasolver.org/) · [Interactive documentation](https://hcaptchasolver.org/?lang=en#/docs) · [OpenAPI](https://api.hcaptchasolver.org/v2/openapi.json)

Copyable **Python, Node.js and cURL** examples for the HCaptcha Solver service. This repository contains API clients, an image preparation helper and synthetic teaching fixtures. The examples call the hosted API; they do not run a local solver.

| Mode | You send | You receive |
| --- | --- | --- |
| Managed Chrome | Public page URL and its hCaptcha `sitekey` | An operation ID; poll until the widget emits a token or the task fails |
| Images | Challenge screenshot, instruction, optional reference images and interaction rectangles | Clicks, grid selections or drag movements for your integration to apply |

The code is released under [MIT](LICENSE). Use the service on sites and workflows you are authorized to automate. HCaptcha Solver is an independent service and is not affiliated with the hCaptcha provider.

## 1. Set up

Create an account at [hcaptchasolver.org](https://hcaptchasolver.org/), verify your email, add credit and create an API key. Enable `images` and/or `browser`; add `balance` to query credit and `feedback` to report an outcome.

```bash
git clone https://github.com/HCaptcha-Solver/api-examples.git
cd api-examples
export HCAPTCHA_API_KEY='YOUR_API_KEY'
```

The Python HTTP client uses only the standard library (**Python 3.11+**). Node examples require **Node.js 22+** with built-in `fetch`; no `npm install` is needed. The image preparation helper additionally uses Pillow:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python python/example.py balance
# Or: node javascript/example.mjs balance
```

On Windows PowerShell, set `$env:HCAPTCHA_API_KEY = 'YOUR_API_KEY'`, create the virtual environment with `py -m venv .venv`, and run `.\.venv\Scripts\python.exe` instead of `python`. The examples read environment variables, not `.env` files automatically.

Keep keys on your backend or in your own trusted tools. Do not embed an account key in a public webpage. Monetary values are integer millionths of USD: divide by `1_000_000`. `available` excludes credit reserved by running operations.

## 2. Prepare an image request locally

Read the [image and coordinate guide](docs/image-mode.md) first. In particular:

- **`image`** is the full challenge capture, as raw Base64 PNG/JPEG.
- **`references`**, in the plural, contains separate example images for visual comparison. It may be empty.
- **`canvases`** contains rectangles marking clickable or draggable areas **inside the main image**. These are coordinates, not image files.
- **`tiles`** contains nine cell rectangles for a DOM grid. A grid drawn inside one canvas uses `canvases` instead.

This command prepares a JSON file using our synthetic 600 × 400 illustration. It makes **no network requests**:

```bash
python python/prepare_image_request.py fixtures/challenge.png \
  --question 'Click the object matching the example' \
  --canvas 30 80 540 280 \
  --reference fixtures/reference.png --output request.json
```

`--output` saves UTF-8 JSON consistently on Linux, macOS and Windows. The multiline commands use Bash/zsh syntax; on PowerShell, put the helper command on one line. `--canvas` accepts pixels of the main image; the helper converts them to the API's 0–1000 scale. Here the result is `{ "x": 50, "y": 200, "width": 900, "height": 700 }`. Omit `--reference` if there is no example image. Repeat it for multiple references. For a DOM grid, use nine `--tile X Y WIDTH HEIGHT` arguments in reading order.

For a real task, replace the fixture files, instruction and rectangles with your current capture. The fixtures illustrate the format; they are not a live CAPTCHA and cannot issue a token. Keep real captures in `captures/`, which is ignored by Git.

## 3. Send the image — choose one client

The following POST operations use your account credit. Generate one request ID for each **new** operation:

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py image request.json --idempotency-key "$REQUEST_ID"
# Or, using the same prepared JSON:
# node javascript/example.mjs image request.json --idempotency-key "$REQUEST_ID"
```

PowerShell equivalent: `$requestId = [guid]::NewGuid().ToString()`, then pass `--idempotency-key $requestId` to your chosen client.

If a connection fails and you do not know whether the API accepted the request, **reuse both the same JSON and the same request ID**. Do not rerun the helper or generate another ID for that retry. A new ID can create another paid operation. Our clients do not automatically retry POST requests.

The client waits when the operation is still `queued` or `running`. It prints the complete final JSON and exits with an error for failed or expired results. Keep the operation ID if polling times out; resume with:

```bash
python python/example.py get SERVER_OPERATION_ID
# Or: node javascript/example.mjs get SERVER_OPERATION_ID
```

**Read `result.action`, not a top-level `action`.** An abbreviated response looks like:

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

`id` identifies the server operation. `result.challenge_id` identifies your capture. Before applying an action, ensure the challenge still matches that capture. See [clicks, drags and grid indices](docs/image-mode.md#apply-the-answer) for coordinate conversion. The examples return instructions; they do not click your browser for you.

An image response may be billed even if the widget later rejects it. A new visual round needs a new capture and request and may incur another charge. Client feedback does not automatically refund credit.

## 4. Managed Chrome

Send the public URL containing the widget and its public `sitekey`. The sitekey is **not** your HCaptcha Solver API key. This mode starts a fresh session; it does not import your browser cookies or perform a custom login flow.

```bash
REQUEST_ID=$(python -c 'import uuid; print(uuid.uuid4())')
python python/example.py browser \
  --url 'https://your-site.example/form' \
  --sitekey 'YOUR_PUBLIC_SITEKEY' \
  --idempotency-key "$REQUEST_ID"
# Or: node javascript/example.mjs browser --url ... --sitekey ... --idempotency-key "$REQUEST_ID"
```

POST returns `202`; the client polls `GET /v2/tasks/{id}`. Only read `result.token` when `status` is `ready`, `result_expired` is false and `result` exists. Token issuance by the widget does not prove acceptance by the target backend. Retrieve results promptly: the API retains them for five minutes, which is separate from the token's own validity.

## cURL

These commands use Bash/zsh and the JSON and `REQUEST_ID` prepared above. The first one is a **paid** request:

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

HTTP 200 is not enough: inspect the operation's `status` and `error`. Unlike the Python/Node examples, these cURL commands do not automatically poll or validate task status.

## Errors and limits

| Response | What to do |
| --- | --- |
| `401` / `403` | Check the API key and the required scopes. |
| `402` | Add credit or wait for another operation's reservation to be released. |
| `409` | A request ID was reused with different content. Restore the original content, or use a new ID for a genuinely new task. |
| `413` / `422` | Check JSON size, raw Base64, field names and rectangle bounds. `reference` is not an alias for `references`. |
| `429` | Wait for the `Retry-After` interval and reduce concurrency. Keep the same content and ID when retrying the same operation. |
| `5xx` / network timeout | Keep the original content and request ID; if you already have an operation ID, query it first. |
| HTTP 200 with `failed` / `cancelled` | Inspect `error`. Do not apply `result`. |

Images must be static PNG/JPEG, at least 8 × 8 pixels each. The full JSON may be at most 10 MiB; decoded images together may use at most 8,000,000 pixels. Limits: nine references, eight canvases, nine grid tiles. The current operation budgets are 30 seconds for images and 90 seconds for managed Chrome, including queue time. Client polling defaults to 120 seconds; its timeout does not cancel the server task.

## Reuse the client

Both [Python](python/client.py) and [JavaScript](javascript/client.mjs) expose balance, image solving, browser tasks, status polling, cancellation and feedback. Copy the files into your backend, or import them from this checkout. They are example clients, not packages published on PyPI or npm.

| Endpoint | Purpose |
| --- | --- |
| `GET /v2/balance` | Credit totals (`balance` scope) |
| `POST /v2/solutions` | Analyze one image request (`images`) |
| `POST /v2/tasks` | Start managed Chrome (`browser`) |
| `GET /v2/tasks/{id}` | Retrieve an operation (matching `images` or `browser` scope) |
| `DELETE /v2/tasks/{id}` | Cancel an unfinished operation |
| `POST /v2/tasks/{id}/feedback` | Report `{ "success": true }` or `{ "success": false }` (`feedback`) |

## Run tests without spending credit

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
node --test tests/*.test.mjs
```

Tests use fake HTTP responses and synthetic images. No API key or live CAPTCHA is needed. CI runs the same tests. For changes and bug reports, see [CONTRIBUTING.md](CONTRIBUTING.md).

Documentation: [English](https://hcaptchasolver.org/?lang=en#/docs) · [Português](https://hcaptchasolver.org/?lang=pt-BR#/docs) · [Deutsch](https://hcaptchasolver.org/?lang=de#/docs) · [Español](https://hcaptchasolver.org/?lang=es#/docs).
