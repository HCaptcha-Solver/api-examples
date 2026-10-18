import assert from "node:assert/strict";
import test from "node:test";
import { ApiError, Client, requireResult } from "../javascript/client.mjs";

const id = "11111111-1111-4111-8111-111111111111";
const body = { protocol: "1", challenge_id: "capture_test_001" };
const ready = { id, mode: "image", status: "ready", result_expired: false,
  result: { challenge_id: body.challenge_id, coordinate_space: "full_challenge_image_0_1000", action: { type: "point", points: [[250, 450]] } } };

function setup(responses) {
  const requests = [];
  const client = new Client("TEST_API_KEY", { fetchImpl: async (url, options) => {
    requests.push({ url, ...options });
    const value = responses.shift();
    if (value instanceof Error) throw value;
    if (value instanceof Response) return value;
    return Response.json(value);
  } });
  return { client, requests };
}

test("paid request keeps the same body and idempotency key on manual retry", async () => {
  const { client, requests } = setup([ready, ready]);
  await client.solveImage(body, "test-request-0001");
  await client.solveImage(body, "test-request-0001");
  assert.equal(requests[0].url, "https://api.hcaptchasolver.org/v2/solutions");
  assert.equal(requests[0].headers["Idempotency-Key"], "test-request-0001");
  assert.equal(requests[0].body, requests[1].body);
  assert.equal(requests[0].redirect, "error");
});

test("network failure sends only one POST", async () => {
  const { client, requests } = setup([new Error("synthetic network failure")]);
  await assert.rejects(client.solveImage(body, "test-request-0001"), /network failure/);
  assert.equal(requests.length, 1);
});

test("polling uses GET until ready", async () => {
  const { client, requests } = setup([{ id, status: "running" }, ready]);
  assert.deepEqual(await client.wait({ id, status: "queued" }, { pollMs: 1 }), ready);
  assert.equal(requests.length, 2);
  assert.ok(requests.every(request => request.method === "GET"));
});

test("failed, expired and stale answers cannot be applied", () => {
  assert.throws(() => requireResult({ ...ready, status: "failed", error: "example_error" }), /failed/);
  assert.throws(() => requireResult({ ...ready, result_expired: true }), /expired/);
  assert.throws(() => requireResult(ready, "capture_other_001"), /different capture/);
  assert.equal(requireResult(ready, body.challenge_id).action.type, "point");
});

test("rate limit exposes Retry-After without automatic retry", async () => {
  const { client, requests } = setup([Response.json({ error: "rate_limit" }, { status: 429, headers: { "Retry-After": "3" } })]);
  await assert.rejects(client.balance(), error => error instanceof ApiError && error.status === 429 && error.retryAfter === "3");
  assert.equal(requests.length, 1);
});

test("invalid operation IDs and empty idempotency keys never reach fetch", () => {
  const { client, requests } = setup([]);
  assert.throws(() => client.getTask("capture_demo_001"), /operation UUID/);
  assert.throws(() => client.solveImage(body, ""), /required/);
  assert.equal(requests.length, 0);
});

test("polling deadline does not cancel or submit another operation", async () => {
  const { client, requests } = setup([]);
  await assert.rejects(client.wait({ id, status: "running" }, { maxWaitMs: 0.01 }), /Polling stopped/);
  assert.equal(requests.length, 0);
});

test("logging the client does not serialize the API key", () => {
  assert.ok(!JSON.stringify(setup([]).client).includes("TEST_API_KEY"));
});
