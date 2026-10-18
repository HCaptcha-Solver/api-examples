import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class PreparationTests(unittest.TestCase):
    def run_helper(self, *extra):
        return subprocess.run([sys.executable, str(ROOT / "python/prepare_image_request.py"),
                               str(ROOT / "fixtures/challenge.png"), "--question", "Click the matching object",
                               "--challenge-id", "capture_test_001", *extra],
                              text=True, capture_output=True, timeout=10)

    def test_reference_and_canvas_are_different_types(self):
        result = self.run_helper("--canvas", "30", "80", "540", "280", "--reference", str(ROOT / "fixtures/reference.png"))
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["canvases"], [{"x": 50, "y": 200, "width": 900, "height": 700}])
        self.assertEqual(base64.b64decode(data["image"]), (ROOT / "fixtures/challenge.png").read_bytes())
        self.assertEqual(base64.b64decode(data["references"][0]), (ROOT / "fixtures/reference.png").read_bytes())
        self.assertNotIn("reference", data)

    def test_no_reference_is_allowed(self):
        result = self.run_helper("--canvas", "30", "80", "540", "280")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["references"], [])

    def test_output_file_is_utf8_and_has_no_bom(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "request.json"
            result = self.run_helper("--canvas", "30", "80", "540", "280", "--output", str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertTrue(path.read_bytes().startswith(b"{"))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["challenge_id"], "capture_test_001")

    def test_bad_rectangle_and_nan_are_rejected(self):
        for x in ["590", "nan", "-1"]:
            with self.subTest(x=x):
                self.assertNotEqual(self.run_helper("--canvas", x, "80", "540", "280").returncode, 0)

    def test_grid_requires_nine_distinct_cells(self):
        tiles = []
        for row in range(3):
            for column in range(3):
                tiles.extend(["--tile", str(30 + column * 180), str(80 + row * 90), "180", "90"])
        result = self.run_helper(*tiles)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(json.loads(result.stdout)["tiles"]), 9)
        self.assertNotEqual(self.run_helper(*tiles[:5]).returncode, 0)
        self.assertNotEqual(self.run_helper(*(tiles[:5] * 9)).returncode, 0)


if __name__ == "__main__":
    unittest.main()
