import io
import json
import sys
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from client import ApiError, Client, NoRedirects, require_result

ID = "11111111-1111-4111-8111-111111111111"
KEY = "test-request-0001"
BODY = {"protocol": "1", "challenge_id": "capture_test_001"}
READY = {
    "id": ID, "mode": "image", "status": "ready", "result_expired": False,
    "result": {"challenge_id": BODY["challenge_id"],
               "coordinate_space": "full_challenge_image_0_1000",
               "action": {"type": "point", "points": [[250, 450]]}},
}


class FakeOpener:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.requests = []

    def open(self, request, timeout):
        self.requests.append((request, timeout))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return io.BytesIO(json.dumps(response).encode())


class ClientTests(unittest.TestCase):
    def test_paid_request_preserves_body_and_idempotency_key(self):
        opener = FakeOpener(READY, READY)
        client = Client("TEST_API_KEY", opener=opener)
        client.solve_image(BODY, idempotency_key=KEY)
        client.solve_image(BODY, idempotency_key=KEY)
        first, second = [item[0] for item in opener.requests]
        self.assertEqual(first.full_url, "https://api.hcaptchasolver.org/v2/solutions")
        self.assertEqual(first.get_header("Authorization"), "Bearer TEST_API_KEY")
        self.assertEqual(first.get_header("Idempotency-key"), KEY)
        self.assertEqual(first.data, second.data)
        self.assertEqual(json.loads(first.data), BODY)

    def test_network_failure_does_not_retry_or_create_a_second_operation(self):
        opener = FakeOpener(URLError("synthetic network failure"))
        with self.assertRaises(URLError):
            Client("TEST_API_KEY", opener=opener).solve_image(BODY, idempotency_key=KEY)
        self.assertEqual(len(opener.requests), 1)

    def test_polling_running_to_ready_uses_only_get(self):
        opener = FakeOpener({"id": ID, "status": "running"}, READY)
        result = Client("TEST_API_KEY", opener=opener).wait({"id": ID, "status": "queued"}, poll_seconds=0.001)
        self.assertEqual(result, READY)
        self.assertTrue(all(req.get_method() == "GET" for req, _ in opener.requests))

    def test_expired_failed_and_stale_results_are_rejected(self):
        for invalid in [{**READY, "result_expired": True}, {**READY, "status": "failed", "error": "example_error"}]:
            with self.assertRaises(RuntimeError):
                require_result(invalid)
        with self.assertRaisesRegex(RuntimeError, "different capture"):
            require_result(READY, challenge_id="capture_other_001")
        self.assertEqual(require_result(READY, challenge_id=BODY["challenge_id"])["action"]["type"], "point")

    def test_rate_limit_is_exposed_without_retry(self):
        error = HTTPError("https://api.hcaptchasolver.org/v2/balance", 429, "Too Many Requests",
                          {"Retry-After": "3"}, io.BytesIO(b'{"error":"rate_limit"}'))
        opener = FakeOpener(error)
        with self.assertRaises(ApiError) as caught:
            Client("TEST_API_KEY", opener=opener).balance()
        self.assertEqual(caught.exception.status, 429)
        self.assertEqual(caught.exception.retry_after, "3")
        self.assertEqual(len(opener.requests), 1)

    def test_invalid_ids_and_empty_keys_fail_before_network(self):
        opener = FakeOpener()
        client = Client("TEST_API_KEY", opener=opener)
        with self.assertRaises(ValueError):
            client.get_task("capture_demo_001")
        with self.assertRaises(ValueError):
            client.solve_image(BODY, idempotency_key="")
        self.assertFalse(opener.requests)

    def test_polling_deadline_does_not_cancel_or_resubmit(self):
        opener = FakeOpener()
        with self.assertRaises(TimeoutError):
            Client("TEST_API_KEY", opener=opener).wait({"id": ID, "status": "running"}, max_wait=0.001)
        self.assertFalse(opener.requests)

    def test_redirects_do_not_forward_authorization(self):
        self.assertIsNone(NoRedirects().redirect_request(None, None, 302, "", {}, "https://example.com"))


if __name__ == "__main__":
    unittest.main()
