#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


CROPS = {
    "side_body": (215, 48, 430, 370),
    "back_body": (432, 42, 682, 372),
    "default_face": (720, 48, 860, 188),
    "smile_face": (880, 48, 1020, 188),
    "blink_face": (1042, 48, 1185, 188),
    "think_face": (1204, 48, 1345, 188),
    "confused_face": (720, 238, 860, 378),
    "tired_face": (1042, 238, 1185, 378),
    "warm_face": (1204, 238, 1345, 378),
    "run_left": (536, 436, 796, 652),
    "waving": (790, 436, 1052, 658),
    "failed": (14, 698, 252, 902),
    "waiting": (258, 710, 486, 904),
    "working": (538, 700, 800, 904),
    "review": (802, 700, 1072, 904),
    "complete": (1120, 696, 1382, 904),
}


IDENTITY_ITEMS = [
    "side_body",
    "back_body",
    "default_face",
    "smile_face",
    "blink_face",
    "think_face",
    "confused_face",
    "tired_face",
    "warm_face",
]


ACTION_ITEMS = [
    "run_left",
    "waving",
    "failed",
    "waiting",
    "working",
    "review",
    "complete",
]


FACE_ITEMS = {
    "default_face",
    "smile_face",
    "blink_face",
    "think_face",
    "confused_face",
    "tired_face",
    "warm_face",
}


BODY_ITEMS = {
    "side_body",
    "back_body",
}


def trim_white(image: Image.Image, *, tolerance: int = 250, padding: int = 12) -> Image.Image:
    rgb = image.convert("RGB")
    inv = Image.eval(rgb, lambda px: 255 if px < tolerance else 0)
    bbox = inv.getbbox()
    if bbox is None:
        return image
    left, top, right, bottom = bbox
    left = max(0, left - padding)
    top = max(0, top - padding)
    right = min(image.width, right + padding)
    bottom = min(image.height, bottom + padding)
    return image.crop((left, top, right, bottom))


def border_for(name: str) -> tuple[int, int, int, int]:
    if name in ACTION_ITEMS:
        return (14, 12, 14, 20)
    if name in BODY_ITEMS:
        return (12, 10, 12, 16)
    if name in FACE_ITEMS:
        return (10, 8, 10, 12)
    return (10, 10, 10, 12)


def crop_named(source: Image.Image, name: str, box: tuple[int, int, int, int]) -> Image.Image:
    cropped = source.crop(box)
    trimmed = trim_white(cropped)
    return ImageOps.expand(trimmed, border=border_for(name), fill="white")


def fit(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail(max_size, Image.Resampling.LANCZOS)
    return fitted


def paste_grid(
    source: Image.Image,
    names: list[str],
    *,
    tile_size: tuple[int, int],
    columns: int,
    padding: int,
    background: str = "white",
) -> Image.Image:
    rows = (len(names) + columns - 1) // columns
    width = columns * tile_size[0] + (columns + 1) * padding
    height = rows * tile_size[1] + (rows + 1) * padding
    board = Image.new("RGB", (width, height), background)

    for index, name in enumerate(names):
        crop = crop_named(source, name, CROPS[name]).convert("RGBA")
        crop = fit(crop, (tile_size[0] - 8, tile_size[1] - 8))
        x = padding + (index % columns) * tile_size[0]
        y = padding + (index // columns) * tile_size[1]
        x += (tile_size[0] - crop.width) // 2
        y += (tile_size[1] - crop.height) // 2
        board.paste(crop.convert("RGB"), (x, y))

    return board


def load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype("Arial Unicode.ttf", size)
    except OSError:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except OSError:
            return ImageFont.load_default()


def build_qa_sheet(
    source: Image.Image,
    names: list[str],
    *,
    tile_size: tuple[int, int],
    columns: int,
    padding: int,
    label_height: int = 28,
    background: str = "white",
) -> Image.Image:
    rows = (len(names) + columns - 1) // columns
    cell_width = tile_size[0]
    cell_height = tile_size[1] + label_height
    width = columns * cell_width + (columns + 1) * padding
    height = rows * cell_height + (rows + 1) * padding
    board = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(board)
    font = load_font(16)

    for index, name in enumerate(names):
        crop = crop_named(source, name, CROPS[name]).convert("RGBA")
        crop = fit(crop, (tile_size[0] - 8, tile_size[1] - 8))
        col = index % columns
        row = index // columns
        cell_x = padding + col * cell_width
        cell_y = padding + row * cell_height
        image_x = cell_x + (cell_width - crop.width) // 2
        image_y = cell_y + (tile_size[1] - crop.height) // 2
        board.paste(crop.convert("RGB"), (image_x, image_y))

        label = name.replace("_", "-")
        label_box = draw.textbbox((0, 0), label, font=font)
        label_width = label_box[2] - label_box[0]
        label_x = cell_x + (cell_width - label_width) // 2
        label_y = cell_y + tile_size[1] + max(0, (label_height - (label_box[3] - label_box[1])) // 2 - 2)
        draw.text((label_x, label_y), label, fill="black", font=font)

    return board


def main() -> None:
    parser = argparse.ArgumentParser(description="Build clean Luka reference boards.")
    parser.add_argument("--source", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    source_path = Path(args.source).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(source_path) as opened:
        source = opened.convert("RGB")
        identity = paste_grid(
            source,
            IDENTITY_ITEMS,
            tile_size=(220, 220),
            columns=5,
            padding=18,
        )
        actions = paste_grid(
            source,
            ACTION_ITEMS,
            tile_size=(260, 240),
            columns=3,
            padding=18,
        )
        qa_sheet = build_qa_sheet(
            source,
            ACTION_ITEMS + [
                "side_body",
                "back_body",
                "default_face",
                "smile_face",
                "blink_face",
                "think_face",
                "confused_face",
                "tired_face",
                "warm_face",
            ],
            tile_size=(260, 220),
            columns=3,
            padding=18,
        )

        identity.save(output_dir / "luka_clean_identity_board.png")
        actions.save(output_dir / "luka_clean_action_board.png")
        qa_sheet.save(output_dir / "crop_qa_sheet.png")

        for name, box in CROPS.items():
            crop_named(source, name, box).save(output_dir / f"{name}.png")


if __name__ == "__main__":
    main()
