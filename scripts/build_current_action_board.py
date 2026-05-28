#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


@dataclass(frozen=True)
class TileSpec:
    state: str
    source: str
    note: str = ""
    mirror: bool = False


TILES = [
    TileSpec("idle", "references/idle.png", "latest screenshot"),
    TileSpec("running-right", "references/run_left.png", "provisional mirror", mirror=True),
    TileSpec("running-left", "references/run_left.png", "clean crop"),
    TileSpec("waving", "references/waving.png", "latest screenshot"),
    TileSpec("jumping", "references/jumping.png", "latest screenshot"),
    TileSpec("failed", "references/failed.png", "clean crop"),
    TileSpec("waiting", "references/waiting.png", "latest screenshot"),
    TileSpec("running", "references/working.png", "working pose proxy"),
    TileSpec("review", "references/review.png", "clean crop"),
    TileSpec("complete", "references/complete.png", "clean crop"),
]


def load_font(size: int) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    for name in ("Arial Unicode.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def trim_white(image: Image.Image, tolerance: int = 250) -> Image.Image:
    rgb = image.convert("RGB")
    inv = Image.eval(rgb, lambda px: 255 if px < tolerance else 0)
    bbox = inv.getbbox()
    if bbox is None:
        return image
    return image.crop(bbox)


def open_tile(path: Path, mirror: bool) -> Image.Image:
    image = Image.open(path).convert("RGBA")
    alpha_bbox = image.getchannel("A").getbbox()
    if alpha_bbox is None:
        image = trim_white(image)
    if mirror:
        image = ImageOps.mirror(image)
    return image


def fit(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    fitted = image.copy()
    fitted.thumbnail(max_size, Image.Resampling.LANCZOS)
    return fitted


def make_placeholder(size: tuple[int, int], label: str) -> Image.Image:
    image = Image.new("RGBA", size, (245, 245, 245, 255))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, size[0] - 1, size[1] - 1), outline=(210, 210, 210), width=2)
    font = load_font(18)
    text_box = draw.textbbox((0, 0), label, font=font)
    x = (size[0] - (text_box[2] - text_box[0])) // 2
    y = (size[1] - (text_box[3] - text_box[1])) // 2
    draw.text((x, y), label, fill=(120, 120, 120), font=font)
    return image


def build_board(project_dir: Path, output_path: Path) -> None:
    tile_width = 260
    tile_height = 250
    label_height = 48
    note_height = 22
    columns = 5
    padding = 18
    header_height = 56
    rows = (len(TILES) + columns - 1) // columns

    board_width = columns * tile_width + (columns + 1) * padding
    board_height = header_height + rows * (tile_height + label_height + note_height) + (rows + 1) * padding
    board = Image.new("RGB", (board_width, board_height), "white")
    draw = ImageDraw.Draw(board)
    title_font = load_font(28)
    label_font = load_font(18)
    note_font = load_font(14)

    title = "Luka Codex Current Action Board"
    title_box = draw.textbbox((0, 0), title, font=title_font)
    title_x = (board_width - (title_box[2] - title_box[0])) // 2
    draw.text((title_x, 14), title, fill="black", font=title_font)

    image_top = header_height
    for index, tile in enumerate(TILES):
        col = index % columns
        row = index // columns
        cell_x = padding + col * tile_width
        cell_y = image_top + padding + row * (tile_height + label_height + note_height)

        source_path = project_dir / tile.source
        if source_path.exists():
            tile_image = open_tile(source_path, tile.mirror)
            tile_image = fit(tile_image, (tile_width - 16, tile_height - 16))
        else:
            tile_image = make_placeholder((tile_width - 16, tile_height - 16), "missing")

        if tile_image.mode != "RGBA":
            tile_image = tile_image.convert("RGBA")
        tile_bg = Image.new("RGBA", (tile_width, tile_height), (250, 250, 250, 255))
        image_x = (tile_width - tile_image.width) // 2
        image_y = (tile_height - tile_image.height) // 2
        tile_bg.alpha_composite(tile_image, (image_x, image_y))
        board.paste(tile_bg.convert("RGB"), (cell_x, cell_y))

        draw.rectangle(
            (cell_x, cell_y, cell_x + tile_width - 1, cell_y + tile_height - 1),
            outline=(228, 228, 228),
            width=1,
        )

        label = tile.state
        label_box = draw.textbbox((0, 0), label, font=label_font)
        label_x = cell_x + (tile_width - (label_box[2] - label_box[0])) // 2
        label_y = cell_y + tile_height + 10
        draw.text((label_x, label_y), label, fill="black", font=label_font)

        if tile.note:
            note_box = draw.textbbox((0, 0), tile.note, font=note_font)
            note_x = cell_x + (tile_width - (note_box[2] - note_box[0])) // 2
            note_y = label_y + 22
            draw.text((note_x, note_y), tile.note, fill=(110, 110, 110), font=note_font)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    board.save(output_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the current Luka action board.")
    parser.add_argument("--project-dir", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()
    build_board(project_dir, output_path)


if __name__ == "__main__":
    main()
