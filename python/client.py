"""Small standard-library client for https://api.hcaptchasolver.org.

Copyable example code, not a package published on PyPI. No automatic POST retries.
"""

import json
import re
import time
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request, build_opener
from uuid import UUID

API_URL = "https://api.hcaptchasolver.org"


class ApiError(RuntimeError):
    def __init__(self, status, body, retry_after=None):
        self.status = status
        self.body = body
        self.retry_after = retry_after
        code = body.get("error", "http_error") if isinstance(body, dict) else "http_error"
        super().__init__(f"HTTP {status}: {code}")


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class Client:
    def __init__(self, api_key, *, opener=None):
        if not api_key or any(char.isspace() for char in api_key):
            raise ValueError("Set HCAPTCHA_API_KEY to your private API key")
        self._api_key = api_key
        self._opener = opener or build_opener(NoRedirects())

    def _request(self, method, path, body=None, *, idempotency_key=None, timeout=45):
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}
        if idempotency_key is not None:
            if not re.fullmatch(r"[A-Za-z0-9._:-]{8,128}", idempotency_key):
                raise ValueError("Use an 8–128 character request ID, such as a UUID")
            headers["Idempotency-Key"] = idempotency_key
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body, allow_nan=False).encode("utf-8")
        request = Request(API_URL + path, data=data, headers=headers, method=method)
        try:
            with self._opener.open(request, timeout=timeout) as response:
                result = json.load(response)
        except HTTPError as error:
            with error:
                try:
                    detail = json.load(error)
                except (ValueError, UnicodeDecodeError):
                    detail = {"error": "non_json_error"}
            raise ApiError(error.code, detail, error.headers.get("Retry-After")) from None
        if not isinstance(result, dict):
            raise RuntimeError("Expected a JSON object from the API")
        return result

    def balance(self):
        return self._request("GET", "/v2/balance")

    def create_browser_task(self, url, sitekey, *, idempotency_key):
        if not idempotency_key:
            raise ValueError("An idempotency key is required for a paid request")
        return self._request("POST", "/v2/tasks", {"url": url, "sitekey": sitekey},
                             idempotency_key=idempotency_key)

    def solve_image(self, body, *, idempotency_key):
        if not idempotency_key:
            raise ValueError("An idempotency key is required for a paid request")
        return self._request("POST", "/v2/solutions", body, idempotency_key=idempotency_key)

    def get_task(self, task_id, *, timeout=45):
        return self._request("GET", f"/v2/tasks/{UUID(task_id)}", timeout=timeout)

    def cancel(self, task_id):
        return self._request("DELETE", f"/v2/tasks/{UUID(task_id)}")

    def feedback(self, task_id, success):
        if not isinstance(success, bool):
            raise ValueError("success must be a boolean")
        return self._request("POST", f"/v2/tasks/{UUID(task_id)}/feedback", {"success": success})

    def wait(self, task, *, max_wait=120, poll_seconds=2):
        if max_wait <= 0 or poll_seconds <= 0:
            raise ValueError("Timeout and polling interval must be positive")
        deadline = time.monotonic() + max_wait
        while task.get("status") in {"queued", "running"}:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Polling stopped; resume GET for task {task['id']}")
            time.sleep(min(poll_seconds, remaining))
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError(f"Polling stopped; resume GET for task {task['id']}")
            task = self.get_task(task["id"], timeout=min(45, remaining))
        if task.get("status") not in {"ready", "failed", "cancelled"}:
            raise RuntimeError("Unknown task status")
        return task


def require_result(task, *, challenge_id=None):
    """HTTP 200 alone is not success. Reject failed, expired or stale results."""
    if task.get("status") != "ready":
        raise RuntimeError(f"Task ended with status {task.get('status')}: {task.get('error')}")
    result = task.get("result")
    if task.get("result_expired") or not isinstance(result, dict):
        raise RuntimeError("The task result has expired or is missing")
    if challenge_id is not None:
        if result.get("challenge_id") != challenge_id:
            raise RuntimeError("Result belongs to a different capture")
        if result.get("coordinate_space") != "full_challenge_image_0_1000":
            raise RuntimeError("Unsupported coordinate space")
    return result
