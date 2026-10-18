"""Prepare a /v2/solutions JSON request from local PNG/JPEG files. No network calls.

Install: python3 -m pip install Pillow
Example (rectangles are in pixels of challenge.png):
  python3 prepare_image_request.py challenge.png \
    --question "Click the object matching the example" \
    --canvas 30 80 540 280 --reference reference.png --output request.json
"""

import argparse
import base64
import json
import re
from pathlib import Path
from uuid import uuid4

from PIL import Image


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("--question", required=True, help="Exact visible instruction")
    parser.add_argument("--reference", action="append", default=[], type=Path,
                        help="Optional example image; repeat for multiple references")
    parser.add_argument("--canvas", action="append", default=[], type=float, nargs=4,
                        metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="Interaction rectangle in pixels of the main image")
    parser.add_argument("--tile", action="append", default=[], type=float, nargs=4,
                        metavar=("X", "Y", "WIDTH", "HEIGHT"),
                        help="For a nine-cell DOM grid: repeat exactly nine times in reading order")
    parser.add_argument("--challenge-id", default=str(uuid4()))
    parser.add_argument("--output", type=Path, help="Write UTF-8 JSON to a file (also safe on Windows)")
    args = parser.parse_args()
    if not 1 <= len(args.question) <= 2000:
        parser.error("question must contain 1 to 2000 characters")
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", args.challenge_id):
        parser.error("challenge-id must contain 8 to 128 letters, digits, underscores or hyphens")
    if len(args.reference) > 9 or len(args.canvas) > 8:
        parser.error("maximum nine reference images and eight canvas rectangles")
    if len(args.tile) not in (0, 9) or (not args.canvas and not args.tile):
        parser.error("provide at least one canvas, or exactly nine tiles for a DOM grid")
    if args.tile and len({tuple(box[:2]) for box in args.tile}) != 9:
        parser.error("each tile must have a different position")

    encoded, sizes = [], []
    try:
        for path in [args.image, *args.reference]:
            with Image.open(path) as image:
                if image.format not in {"PNG", "JPEG"} or getattr(image, "n_frames", 1) != 1:
                    parser.error("use static PNG or JPEG files")
                if min(image.size) < 8:
                    parser.error("every image must be at least 8 by 8 pixels")
                sizes.append(image.size)
                if sum(w * h for w, h in sizes) > 8_000_000:
                    parser.error("images exceed eight million pixels in total")
                image.verify()
            encoded.append(base64.b64encode(path.read_bytes()).decode("ascii"))
    except (OSError, Image.DecompressionBombError) as exc:
        parser.error(str(exc))

    width, height = sizes[0]

    def normalize(box):
        x, y, w, h = box
        if not (0 <= x < width and 0 <= y < height and w > 0 and h > 0
                and x + w <= width and y + h <= height):
            parser.error("rectangles must fit entirely inside the main image")
        return dict(zip(("x", "y", "width", "height"),
                        (round(x / width * 1000, 6), round(y / height * 1000, 6),
                         round(w / width * 1000, 6), round(h / height * 1000, 6))))

    body = {
        "protocol": "1",
        "challenge_id": args.challenge_id,
        "question": args.question,
        "image": encoded[0],
        "references": encoded[1:],
        "canvases": [normalize(box) for box in args.canvas],
        "tiles": [normalize(box) for box in args.tile],
    }
    serialized = json.dumps(body, ensure_ascii=True, indent=2, allow_nan=False)
    if len(serialized.encode("utf-8")) > 10 * 1024 * 1024:
        parser.error("JSON exceeds 10 MiB")
    if args.output:
        args.output.write_text(serialized + "\n", encoding="utf-8")
    else:
        print(serialized)


if __name__ == "__main__":
    main()
