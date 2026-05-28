#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import deque
from pathlib import Path

from PIL import Image, ImageOps

CELL_W = 192
CELL_H = 208
SAFE_X = 18
SAFE_Y = 16
CHROMA = (0, 255, 0, 255)


ROW_SPECS = {
    "idle": {
        "source": "idle.png",
        "frames": 6,
        "mirror": False,
        "transforms": [
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 0.998, 1.004, 0.0),
            (0, -2, 0.996, 1.008, 0.0),
            (0, -1, 0.998, 1.004, 0.0),
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 0.999, 1.003, 0.0),
        ],
    },
    "running-right": {
        "source": "run_left.png",
        "frames": 8,
        "mirror": True,
        "transforms": [
            (0, 0, 1.00, 1.00, 0.0),
            (2, -3, 1.02, 0.98, 1.0),
            (4, -6, 1.04, 0.96, 2.0),
            (2, -3, 1.02, 0.98, 1.0),
            (0, 0, 1.00, 1.00, 0.0),
            (-2, -3, 0.99, 1.01, -1.0),
            (-4, -6, 0.97, 1.03, -2.0),
            (-2, -3, 0.99, 1.01, -1.0),
        ],
    },
    "running-left": {
        "source": "run_left.png",
        "frames": 8,
        "mirror": False,
        "transforms": [
            (0, 0, 1.00, 1.00, 0.0),
            (-2, -3, 1.02, 0.98, -1.0),
            (-4, -6, 1.04, 0.96, -2.0),
            (-2, -3, 1.02, 0.98, -1.0),
            (0, 0, 1.00, 1.00, 0.0),
            (2, -3, 0.99, 1.01, 1.0),
            (4, -6, 0.97, 1.03, 2.0),
            (2, -3, 0.99, 1.01, 1.0),
        ],
    },
    "waving": {
        "source": "waving.png",
        "frames": 4,
        "mirror": False,
        "transforms": [
            (0, 0, 1.000, 1.000, -1.0),
            (1, -1, 1.010, 0.995, 1.0),
            (0, 0, 1.000, 1.000, -1.0),
            (-1, -1, 1.010, 0.995, 1.0),
        ],
    },
    "jumping": {
        "source": "jumping.png",
        "frames": 5,
        "mirror": False,
        "transforms": [
            (0, 8, 1.040, 0.960, 0.0),
            (0, 2, 1.010, 1.000, 0.0),
            (0, -8, 0.960, 1.060, 0.0),
            (0, 2, 1.010, 1.000, 0.0),
            (0, 8, 1.040, 0.960, 0.0),
        ],
    },
    "failed": {
        "source": "failed.png",
        "frames": 8,
        "mirror": False,
        "transforms": [
            (0, 1, 1.000, 1.000, -1.0),
            (0, 2, 0.995, 1.005, -2.0),
            (0, 3, 0.990, 1.010, -2.0),
            (0, 2, 0.995, 1.005, -1.0),
            (0, 1, 1.000, 1.000, 0.0),
            (0, 2, 0.995, 1.005, -1.0),
            (0, 3, 0.990, 1.010, -2.0),
            (0, 2, 0.995, 1.005, -1.0),
        ],
    },
    "waiting": {
        "source": "waiting.png",
        "frames": 6,
        "mirror": False,
        "transforms": [
            (0, 0, 1.000, 1.000, 0.0),
            (0, 1, 0.998, 1.002, 0.0),
            (0, 2, 0.996, 1.004, 0.0),
            (0, 1, 0.998, 1.002, 0.0),
            (0, 0, 1.000, 1.000, 0.0),
            (0, 1, 0.998, 1.002, 0.0),
        ],
    },
    "running": {
        "source": "working.png",
        "frames": 8,
        "mirror": False,
        "transforms": [
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 1.002, 0.999, 0.0),
            (0, -2, 1.004, 0.998, 0.0),
            (0, -1, 1.002, 0.999, 0.0),
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 1.002, 0.999, 0.0),
            (0, -2, 1.003, 0.998, 0.0),
            (0, -1, 1.001, 0.999, 0.0),
        ],
        "note_offsets": [
            (0, 0),
            (2, -1),
            (0, -4),
            (-2, -1),
            (0, 0),
            (2, -2),
            (0, -5),
            (-2, -2),
        ],
    },
    "review": {
        "source": "review.png",
        "frames": 6,
        "mirror": False,
        "transforms": [
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 1.005, 0.998, 1.0),
            (0, -2, 1.010, 0.996, 0.0),
            (0, -1, 1.005, 0.998, -1.0),
            (0, 0, 1.000, 1.000, 0.0),
            (0, -1, 1.005, 0.998, 1.0),
        ],
    },
}


def near_light_bg(
    rgba: tuple[int, int, int, int],
    ref: tuple[int, int, int],
    tol: int = 38,
) -> bool:
    r, g, b, a = rgba
    if a == 0:
        return False
    return abs(r - ref[0]) <= tol and abs(g - ref[1]) <= tol and abs(b - ref[2]) <= tol


def remove_border_light_bg(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    corners = [px[0, 0], px[w - 1, 0], px[0, h - 1], px[w - 1, h - 1]]
    ref = tuple(sum(c[i] for c in corners) // len(corners) for i in range(3))
    q = deque()
    seen = [[False] * h for _ in range(w)]
    for x in range(w):
        q.append((x, 0))
        q.append((x, h - 1))
    for y in range(h):
        q.append((0, y))
        q.append((w - 1, y))
    while q:
        x, y = q.popleft()
        if x < 0 or x >= w or y < 0 or y >= h or seen[x][y]:
            continue
        seen[x][y] = True
        if not near_light_bg(px[x, y], ref):
            continue
        r, g, b, _ = px[x, y]
        px[x, y] = (r, g, b, 0)
        q.extend(((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)))
    return rgba


def visible_bbox(image: Image.Image) -> tuple[int, int, int, int] | None:
    return image.getbbox()


def prepare_source(image: Image.Image) -> Image.Image:
    return remove_border_light_bg(image)


def transform_sprite(
    sprite: Image.Image,
    scale_x: float,
    scale_y: float,
    rotation: float,
    mirror: bool,
) -> Image.Image:
    image = sprite
    if mirror:
        image = ImageOps.mirror(image)
    if scale_x != 1.0 or scale_y != 1.0:
        image = image.resize(
            (
                max(1, round(image.width * scale_x)),
                max(1, round(image.height * scale_y)),
            ),
            Image.Resampling.LANCZOS,
        )
    if rotation:
        image = image.rotate(rotation, resample=Image.Resampling.BICUBIC, expand=True)
    return image


def fit_base_scale(sprite: Image.Image) -> float:
    bbox = visible_bbox(sprite)
    if bbox is None:
        return 1.0
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]
    max_w = CELL_W - SAFE_X * 2
    max_h = CELL_H - SAFE_Y * 2
    return min(max_w / bbox_width, max_h / bbox_height, 1.0)


def alpha_components(
    image: Image.Image,
) -> list[dict[str, object]]:
    rgba = image.convert("RGBA")
    w, h = rgba.size
    px = rgba.load()
    seen = [[False] * h for _ in range(w)]
    components = []

    for y in range(h):
        for x in range(w):
            if seen[x][y] or px[x, y][3] == 0:
                continue
            q = deque([(x, y)])
            seen[x][y] = True
            pixels = []
            min_x = max_x = x
            min_y = max_y = y
            while q:
                cx, cy = q.popleft()
                pixels.append((cx, cy))
                min_x = min(min_x, cx)
                max_x = max(max_x, cx)
                min_y = min(min_y, cy)
                max_y = max(max_y, cy)
                for nx, ny in ((cx - 1, cy), (cx + 1, cy), (cx, cy - 1), (cx, cy + 1)):
                    if nx < 0 or nx >= w or ny < 0 or ny >= h or seen[nx][ny]:
                        continue
                    if px[nx, ny][3] == 0:
                        continue
                    seen[nx][ny] = True
                    q.append((nx, ny))
            components.append(
                {
                    "area": len(pixels),
                    "bbox": (min_x, min_y, max_x + 1, max_y + 1),
                    "pixels": pixels,
                }
            )
    return components


def split_running_layers(source: Image.Image) -> tuple[Image.Image, Image.Image]:
    body = source.copy()
    notes = Image.new("RGBA", source.size, (0, 0, 0, 0))
    source_px = source.load()
    body_px = body.load()
    notes_px = notes.load()

    for component in alpha_components(source):
        area = int(component["area"])
        x0, y0, x1, y1 = component["bbox"]
        if 20 <= area <= 250 and y1 <= 150:
            for x, y in component["pixels"]:
                notes_px[x, y] = source_px[x, y]
                body_px[x, y] = (0, 0, 0, 0)

    return body, notes


def translate_image(image: Image.Image, dx: int, dy: int) -> Image.Image:
    shifted = Image.new("RGBA", image.size, (0, 0, 0, 0))
    width = image.width - abs(dx)
    height = image.height - abs(dy)
    if width <= 0 or height <= 0:
        return shifted

    src_x0 = max(0, -dx)
    src_y0 = max(0, -dy)
    dst_x0 = max(0, dx)
    dst_y0 = max(0, dy)

    region = image.crop((src_x0, src_y0, src_x0 + width, src_y0 + height))
    shifted.alpha_composite(region, (dst_x0, dst_y0))
    return shifted


def render_cell(
    sprite: Image.Image,
    dx: int,
    dy: int,
    scale_x: float,
    scale_y: float,
    rotation: float,
    mirror: bool,
    anchor_sprite: Image.Image | None = None,
) -> Image.Image:
    canvas = Image.new("RGBA", (CELL_W, CELL_H), (0, 0, 0, 0))
    transformed = transform_sprite(sprite, scale_x, scale_y, rotation, mirror)
    if anchor_sprite is None:
        anchor = transformed
    else:
        anchor = transform_sprite(anchor_sprite, scale_x, scale_y, rotation, mirror)
    bbox = visible_bbox(anchor)
    if bbox is None:
        return canvas
    bbox_width = bbox[2] - bbox[0]
    bbox_height = bbox[3] - bbox[1]
    target_left = (CELL_W - bbox_width) // 2 + dx
    target_top = CELL_H - SAFE_Y - bbox_height + dy
    paste_left = target_left - bbox[0]
    paste_top = target_top - bbox[1]
    canvas.alpha_composite(transformed, (paste_left, paste_top))
    return canvas


def build_frames_for_state(state: str, references_dir: Path) -> list[Image.Image]:
    spec = ROW_SPECS[state]
    source = prepare_source(Image.open(references_dir / spec["source"]))
    base_scale = fit_base_scale(source)

    if state == "running":
        body_source, note_source = split_running_layers(source)
        frames = []
        transforms = spec["transforms"]
        note_offsets = spec["note_offsets"]
        if len(transforms) != len(note_offsets):
            raise ValueError(
                f"running transform count {len(transforms)} does not match "
                f"note offset count {len(note_offsets)}"
            )
        for transform, note_offset in zip(transforms, note_offsets):
            dx, dy, extra_scale_x, extra_scale_y, rotation = transform
            body_frame = render_cell(
                body_source,
                dx,
                dy,
                base_scale * extra_scale_x,
                base_scale * extra_scale_y,
                rotation,
                spec["mirror"],
                anchor_sprite=source,
            )
            note_frame = render_cell(
                note_source,
                dx,
                dy,
                base_scale * extra_scale_x,
                base_scale * extra_scale_y,
                rotation,
                spec["mirror"],
                anchor_sprite=source,
            )
            frame = body_frame.copy()
            frame.alpha_composite(translate_image(note_frame, note_offset[0], note_offset[1]), (0, 0))
            frames.append(frame)
        return frames

    frames = []
    for dx, dy, extra_scale_x, extra_scale_y, rotation in spec["transforms"]:
        frames.append(
            render_cell(
                source,
                dx,
                dy,
                base_scale * extra_scale_x,
                base_scale * extra_scale_y,
                rotation,
                spec["mirror"],
            )
        )
    return frames


def save_state_outputs(
    state: str,
    frames: list[Image.Image],
    rows_dir: Path,
    frames_dir: Path | None,
) -> Path:
    strip = Image.new("RGBA", (CELL_W * len(frames), CELL_H), CHROMA)
    for index, frame in enumerate(frames):
        cell_bg = Image.new("RGBA", (CELL_W, CELL_H), CHROMA)
        cell_bg.alpha_composite(frame, (0, 0))
        strip.alpha_composite(cell_bg, (index * CELL_W, 0))

    rows_dir.mkdir(parents=True, exist_ok=True)
    row_path = rows_dir / f"{state}.png"
    strip.save(row_path)

    if frames_dir is not None:
        state_dir = frames_dir / state
        state_dir.mkdir(parents=True, exist_ok=True)
        for index, frame in enumerate(frames):
            frame.save(state_dir / f"{index:02d}.png")

    return row_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build transform-only Luka row strips and optional transparent frame directories."
    )
    parser.add_argument("--references-dir", required=True)
    parser.add_argument("--output-dir", required=True, help="Directory for chroma-key row strips.")
    parser.add_argument(
        "--frames-dir",
        help="Optional directory for transparent 192x208 frame folders, one folder per state.",
    )
    args = parser.parse_args()

    references_dir = Path(args.references_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    frames_dir = Path(args.frames_dir).expanduser().resolve() if args.frames_dir else None

    for state in ROW_SPECS:
        frames = build_frames_for_state(state, references_dir)
        out = save_state_outputs(state, frames, output_dir, frames_dir)
        print(out)


if __name__ == "__main__":
    main()
