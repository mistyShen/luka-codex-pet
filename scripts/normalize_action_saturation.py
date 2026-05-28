#!/usr/bin/env python3
from __future__ import annotations

import argparse
import colorsys
from pathlib import Path

from PIL import Image


ACTION_FILES = [
    "idle.png",
    "run_left.png",
    "waving.png",
    "jumping.png",
    "failed.png",
    "waiting.png",
    "working.png",
    "review.png",
    "complete.png",
]


def is_background(r: int, g: int, b: int, a: int) -> bool:
    if a == 0:
        return True
    maximum = max(r, g, b) / 255.0
    minimum = min(r, g, b) / 255.0
    saturation = 0.0 if maximum == 0 else (maximum - minimum) / maximum
    return maximum > 0.93 and saturation < 0.10


def mean_saturation(image: Image.Image) -> float:
    values: list[float] = []
    for r, g, b, a in image.getdata():
        if is_background(r, g, b, a):
            continue
        _h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        if l < 0.98:
            values.append(s)
    return sum(values) / len(values) if values else 0.0


def adjust_image(path: Path, target: float) -> tuple[float, float]:
    image = Image.open(path).convert("RGBA")
    before = mean_saturation(image)
    if before == 0:
        image.save(path)
        return before, before

    factor = target / before
    pixels = []
    for r, g, b, a in image.getdata():
        if is_background(r, g, b, a):
            pixels.append((r, g, b, a))
            continue
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        new_s = max(0.0, min(1.0, s * factor))
        nr, ng, nb = colorsys.hls_to_rgb(h, l, new_s)
        pixels.append((int(round(nr * 255)), int(round(ng * 255)), int(round(nb * 255)), a))

    result = Image.new("RGBA", image.size)
    result.putdata(pixels)
    result.save(path)
    after = mean_saturation(result)
    return before, after


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize saturation across Luka action assets.")
    parser.add_argument("--references-dir", required=True)
    parser.add_argument("--target", type=float, default=0.43)
    args = parser.parse_args()

    references_dir = Path(args.references_dir).expanduser().resolve()
    for name in ACTION_FILES:
        path = references_dir / name
        if not path.exists():
            continue
        before, after = adjust_image(path, args.target)
        print(f"{name}\t{before:.4f}\t{after:.4f}")


if __name__ == "__main__":
    main()
