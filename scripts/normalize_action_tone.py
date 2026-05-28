#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
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


def luma(r: int, g: int, b: int) -> float:
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255.0


def tone_stats(image: Image.Image) -> tuple[float, float]:
    values: list[float] = []
    for r, g, b, a in image.getdata():
        if is_background(r, g, b, a):
            continue
        values.append(luma(r, g, b))
    if not values:
        return 0.0, 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return mean, math.sqrt(variance)


def adjust_image(path: Path, target_mean: float, target_std: float) -> tuple[float, float, float, float]:
    image = Image.open(path).convert("RGBA")
    before_mean, before_std = tone_stats(image)
    if before_std == 0:
        image.save(path)
        return before_mean, before_std, before_mean, before_std

    scale = target_std / before_std
    pixels = []
    for r, g, b, a in image.getdata():
        if is_background(r, g, b, a):
            pixels.append((r, g, b, a))
            continue

        old_y = luma(r, g, b)
        new_y = (old_y - before_mean) * scale + target_mean
        new_y = max(0.0, min(1.0, new_y))

        if old_y <= 1e-6:
            ratio = 0.0
        else:
            ratio = new_y / old_y

        nr = max(0, min(255, int(round(r * ratio))))
        ng = max(0, min(255, int(round(g * ratio))))
        nb = max(0, min(255, int(round(b * ratio))))
        pixels.append((nr, ng, nb, a))

    result = Image.new("RGBA", image.size)
    result.putdata(pixels)
    result.save(path)
    after_mean, after_std = tone_stats(result)
    return before_mean, before_std, after_mean, after_std


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize brightness and contrast across Luka action assets.")
    parser.add_argument("--references-dir", required=True)
    parser.add_argument("--target-brightness", type=float, default=0.605)
    parser.add_argument("--target-contrast", type=float, default=0.242)
    args = parser.parse_args()

    references_dir = Path(args.references_dir).expanduser().resolve()
    for name in ACTION_FILES:
        path = references_dir / name
        if not path.exists():
            continue
        b0, c0, b1, c1 = adjust_image(path, args.target_brightness, args.target_contrast)
        print(f"{name}\t{b0:.4f}\t{c0:.4f}\t{b1:.4f}\t{c1:.4f}")


if __name__ == "__main__":
    main()
