import { readFile } from "node:fs/promises";
import { parseArgs } from "node:util";
import { ApiError, Client, requireResult } from "./client.mjs";

async function main() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: { url: { type: "string" }, sitekey: { type: "string" }, "idempotency-key": { type: "string" } },
  });
  const [command, argument] = positionals;
  if (!["balance", "browser", "image", "get"].includes(command)) throw new Error("Usage: node javascript/example.mjs balance|browser|image| get (see README)");
  if (command === "browser" && (!values.url || !values.sitekey)) throw new Error("browser requires --url and --sitekey");
  if (["image", "get"].includes(command) && !argument) throw new Error("Provide request.json for image, or the server operation ID for get");
  const client = new Client(process.env.HCAPTCHA_API_KEY);
  if (command === "balance") { console.log(JSON.stringify(await client.balance(), null, 2)); return; }
  let task, captureId;
  if (command === "browser") task = await client.createBrowserTask(values.url, values.sitekey, values["idempotency-key"]);
  else if (command === "image") {
    const body = JSON.parse((await readFile(argument, "utf8")).replace(/^\uFEFF/, ""));
    if (!body.challenge_id) throw new Error("request.json must include challenge_id");
    captureId = body.challenge_id;
    task = await client.solveImage(body, values["idempotency-key"]);
  } else task = await client.getTask(argument);
  console.error(`Operation: ${task.id}`);
  task = await client.wait(task);
  console.log(JSON.stringify(task, null, 2));
  requireResult(task, captureId);
}

main().catch(error => {
  console.error(error.message);
  if (error instanceof ApiError && error.retryAfter) console.error(`Retry-After: ${error.retryAfter} seconds`);
  console.error("If a paid call was interrupted, keep its original JSON and Idempotency-Key.");
  process.exitCode = 1;
});
