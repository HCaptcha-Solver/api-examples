// Copyable Node.js example client. No automatic POST retries or external packages.
const API_URL = "https://api.hcaptchasolver.org";
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

export class ApiError extends Error {
  constructor(status, body, retryAfter) {
    super(`HTTP ${status}: ${body?.error ?? "http_error"}`);
    this.status = status;
    this.body = body;
    this.retryAfter = retryAfter;
  }
}

function taskPath(id) {
  if (!uuid.test(id)) throw new Error("Use the server operation UUID, not challenge_id");
  return `/v2/tasks/${id}`;
}

export class Client {
  #apiKey;
  #fetch;

  constructor(apiKey, { fetchImpl = globalThis.fetch } = {}) {
    if (!apiKey || /\s/.test(apiKey)) throw new Error("Set HCAPTCHA_API_KEY to your private API key");
    this.#apiKey = apiKey;
    this.#fetch = fetchImpl;
  }

  async request(method, path, body, { idempotencyKey, timeoutMs = 45000 } = {}) {
    if (!path.startsWith("/v2/") || path.includes("..")) throw new Error("Invalid API path");
    const headers = { Authorization: `Bearer ${this.#apiKey}`, Accept: "application/json" };
    if (idempotencyKey !== undefined) {
      if (!/^[A-Za-z0-9._:-]{8,128}$/.test(idempotencyKey)) throw new Error("Use an 8–128 character request ID, such as a UUID");
      headers["Idempotency-Key"] = idempotencyKey;
    }
    if (body !== undefined) headers["Content-Type"] = "application/json";
    const response = await this.#fetch(API_URL + path, {
      method, headers, body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.timeout(Math.max(1, Math.ceil(timeoutMs))), redirect: "error",
    });
    let result;
    try { result = await response.json(); }
    catch { throw new ApiError(response.status, { error: "non_json_response" }, response.headers.get("Retry-After")); }
    if (!response.ok) throw new ApiError(response.status, result, response.headers.get("Retry-After"));
    if (!result || typeof result !== "object" || Array.isArray(result)) throw new Error("Expected a JSON object from the API");
    return result;
  }

  balance() { return this.request("GET", "/v2/balance"); }
  createBrowserTask(url, sitekey, idempotencyKey) {
    if (!idempotencyKey) throw new Error("An idempotency key is required for a paid request");
    return this.request("POST", "/v2/tasks", { url, sitekey }, { idempotencyKey });
  }
  solveImage(body, idempotencyKey) {
    if (!idempotencyKey) throw new Error("An idempotency key is required for a paid request");
    return this.request("POST", "/v2/solutions", body, { idempotencyKey });
  }
  getTask(id, timeoutMs) { return this.request("GET", taskPath(id), undefined, { timeoutMs }); }
  cancel(id) { return this.request("DELETE", taskPath(id)); }
  feedback(id, success) {
    if (typeof success !== "boolean") throw new Error("success must be a boolean");
    return this.request("POST", taskPath(id) + "/feedback", { success });
  }

  async wait(task, { maxWaitMs = 120000, pollMs = 2000 } = {}) {
    if (!(maxWaitMs > 0) || !(pollMs > 0)) throw new Error("Timeout and polling interval must be positive");
    const deadline = performance.now() + maxWaitMs;
    while (["queued", "running"].includes(task.status)) {
      let remaining = deadline - performance.now();
      if (remaining <= 0) throw new Error(`Polling stopped; resume GET for task ${task.id}`);
      await new Promise(resolve => setTimeout(resolve, Math.min(pollMs, remaining)));
      remaining = deadline - performance.now();
      if (remaining <= 0) throw new Error(`Polling stopped; resume GET for task ${task.id}`);
      task = await this.getTask(task.id, Math.min(45000, remaining));
    }
    if (!["ready", "failed", "cancelled"].includes(task.status)) throw new Error("Unknown task status");
    return task;
  }
}

export function requireResult(task, challengeId) {
  if (task.status !== "ready") throw new Error(`Task ended with status ${task.status}: ${task.error}`);
  if (task.result_expired || !task.result || typeof task.result !== "object" || Array.isArray(task.result)) throw new Error("The task result has expired or is missing");
  if (challengeId !== undefined) {
    if (task.result.challenge_id !== challengeId) throw new Error("Result belongs to a different capture");
    if (task.result.coordinate_space !== "full_challenge_image_0_1000") throw new Error("Unsupported coordinate space");
  }
  return task.result;
}
