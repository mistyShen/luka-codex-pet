#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from statistics import median

from PIL import Image, ImageDraw, ImageFont

IMAGE_SUFFIXES = {".png", ".webp", ".jpg", ".jpeg"}
LABEL_HEIGHT = 22

DEFAULT_DURATIONS = {
    "idle": [280, 110, 110, 140, 140, 320],
    "running-right": [120, 120, 120, 120, 120, 120, 120, 220],
    "running-left": [120, 120, 120, 120, 120, 120, 120, 220],
    "waving": [140, 140, 140, 280],
    "jumping": [140, 140, 140, 140, 280],
    "failed": [140, 140, 140, 140, 140, 140, 140, 240],
    "waiting": [150, 150, 150, 150, 150, 260],
    "running": [120, 120, 120, 120, 120, 120, 120, 220],
    "review": [150, 150, 150, 150, 150, 280],
}


def frame_files(state_dir: Path) -> list[Path]:
    if not state_dir.is_dir():
        return []
    return sorted(path for path in state_dir.iterdir() if path.suffix.lower() in IMAGE_SUFFIXES)


def load_pet_request(path: Path) -> tuple[dict[str, int], list[dict[str, int | str]]]:
    request = json.loads(path.read_text(encoding="utf-8"))
    atlas = request["atlas"]
    rows = sorted(request["rows"], key=lambda item: item["row"])
    return atlas, rows


def alpha_nonzero_count(image: Image.Image) -> int:
    alpha = image if image.mode == "L" else image.getchannel("A")
    return sum(alpha.histogram()[1:])


def edge_alpha_count(image: Image.Image, margin: int) -> int:
    alpha = image.getchannel("A")
    width, height = alpha.size
    total = 0
    for box in (
        (0, 0, width, margin),
        (0, height - margin, width, height),
        (0, 0, margin, height),
        (width - margin, 0, width, height),
    ):
        total += alpha_nonzero_count(alpha.crop(box))
    return total


def color_distance(left: tuple[int, int, int], right: tuple[int, int, int]) -> float:
    return math.sqrt(sum((left[index] - right[index]) ** 2 for index in range(3)))


def inspect_frames(
    frames_root: Path,
    atlas: dict[str, int],
    rows: list[dict[str, int | str]],
) -> dict[str, object]:
    cell_width = int(atlas["cell_width"])
    cell_height = int(atlas["cell_height"])
    all_errors: list[str] = []
    all_warnings: list[str] = []
    row_reports = []

    for row in rows:
        state = str(row["state"])
        expected = int(row["frames"])
        files = frame_files(frames_root / state)
        row_errors: list[str] = []
        row_warnings: list[str] = []
        frames = []
        areas: list[int] = []

        if len(files) != expected:
            row_errors.append(f"expected {expected} frame files for {state}, found {len(files)}")

        for index, frame_path in enumerate(files[:expected]):
            with Image.open(frame_path) as opened:
                frame = opened.convert("RGBA")
            nontransparent = alpha_nonzero_count(frame)
            bbox = frame.getbbox()
            edge_pixels = edge_alpha_count(frame, 2)
            info = {
                "index": index,
                "file": str(frame_path),
                "width": frame.width,
                "height": frame.height,
                "nontransparent_pixels": nontransparent,
                "bbox": list(bbox) if bbox else None,
                "edge_pixels": edge_pixels,
            }
            frames.append(info)
            areas.append(nontransparent)

            if frame.size != (cell_width, cell_height):
                row_errors.append(
                    f"{state} frame {index:02d} is {frame.width}x{frame.height}; "
                    f"expected {cell_width}x{cell_height}"
                )
            if nontransparent < 400:
                row_errors.append(
                    f"{state} frame {index:02d} is empty or too sparse ({nontransparent} pixels)"
                )
            if edge_pixels > 24:
                row_warnings.append(
                    f"{state} frame {index:02d} has {edge_pixels} non-transparent pixels near the cell edge"
                )

        if areas:
            row_median = median(areas)
            for index, area in enumerate(areas[:expected]):
                if row_median > 0 and area < row_median * 0.35:
                    row_warnings.append(
                        f"{state} frame {index:02d} is much smaller than the row median "
                        f"({area} vs {row_median:.0f})"
                    )
                if row_median > 0 and area > row_median * 2.75:
                    row_warnings.append(
                        f"{state} frame {index:02d} is much larger than the row median "
                        f"({area} vs {row_median:.0f})"
                    )

        all_errors.extend(row_errors)
        all_warnings.extend(row_warnings)
        row_reports.append(
            {
                "state": state,
                "expected_frames": expected,
                "actual_frames": len(files),
                "ok": not row_errors,
                "errors": row_errors,
                "warnings": row_warnings,
                "frames": frames,
            }
        )

    return {
        "ok": not all_errors,
        "frames_root": str(frames_root),
        "errors": all_errors,
        "warnings": all_warnings,
        "rows": row_reports,
    }


def paste_centered(
    atlas: Image.Image,
    source: Image.Image,
    row: int,
    column: int,
    cell_width: int,
    cell_height: int,
) -> None:
    frame = source.convert("RGBA")
    if frame.size != (cell_width, cell_height):
        frame.thumbnail((cell_width, cell_height), Image.Resampling.LANCZOS)
    left = column * cell_width + (cell_width - frame.width) // 2
    top = row * cell_height + (cell_height - frame.height) // 2
    atlas.alpha_composite(frame, (left, top))


def clear_transparent_rgb(image: Image.Image) -> Image.Image:
    rgba = image.convert("RGBA")
    data = bytearray(rgba.tobytes())
    for index in range(0, len(data), 4):
        if data[index + 3] == 0:
            data[index] = 0
            data[index + 1] = 0
            data[index + 2] = 0
    return Image.frombytes("RGBA", rgba.size, bytes(data))


def compose_atlas(
    frames_root: Path,
    atlas_spec: dict[str, int],
    rows: list[dict[str, int | str]],
) -> Image.Image:
    atlas = Image.new(
        "RGBA",
        (int(atlas_spec["width"]), int(atlas_spec["height"])),
        (0, 0, 0, 0),
    )
    for row in rows:
        state = str(row["state"])
        row_index = int(row["row"])
        frame_count = int(row["frames"])
        files = frame_files(frames_root / state)
        if len(files) < frame_count:
            raise SystemExit(
                f"{state} row needs {frame_count} frames, found {len(files)} under {frames_root}"
            )
        for column, frame_path in enumerate(files[:frame_count]):
            with Image.open(frame_path) as frame:
                paste_centered(
                    atlas,
                    frame,
                    row_index,
                    column,
                    int(atlas_spec["cell_width"]),
                    int(atlas_spec["cell_height"]),
                )
    return clear_transparent_rgb(atlas)


def transparent_rgb_residue_count(image: Image.Image) -> int:
    rgba = image.convert("RGBA")
    data = rgba.tobytes()
    count = 0
    for index in range(0, len(data), 4):
        red, green, blue, alpha = data[index : index + 4]
        if alpha == 0 and (red or green or blue):
            count += 1
    return count


def validate_atlas(
    atlas_path: Path,
    atlas_spec: dict[str, int],
    rows: list[dict[str, int | str]],
) -> dict[str, object]:
    errors: list[str] = []
    warnings: list[str] = []

    with Image.open(atlas_path) as opened:
        source_mode = opened.mode
        source_format = opened.format
        image = opened.convert("RGBA")

    if image.size != (int(atlas_spec["width"]), int(atlas_spec["height"])):
        errors.append(
            f"expected {atlas_spec['width']}x{atlas_spec['height']}, got {image.width}x{image.height}"
        )

    if source_format not in {"PNG", "WEBP"}:
        errors.append(f"expected PNG or WebP, got {source_format}")

    columns = int(atlas_spec["columns"])
    cell_width = int(atlas_spec["cell_width"])
    cell_height = int(atlas_spec["cell_height"])
    cells = []
    near_opaque_used_cells: dict[str, list[int]] = {}

    for row in rows:
        state = str(row["state"])
        row_index = int(row["row"])
        frame_count = int(row["frames"])
        for column_index in range(columns):
            left = column_index * cell_width
            top = row_index * cell_height
            cell = image.crop((left, top, left + cell_width, top + cell_height))
            nontransparent = alpha_nonzero_count(cell)
            used = column_index < frame_count
            cells.append(
                {
                    "state": state,
                    "row": row_index,
                    "column": column_index,
                    "used": used,
                    "nontransparent_pixels": nontransparent,
                }
            )
            if used and nontransparent < 50:
                errors.append(
                    f"{state} row {row_index} column {column_index} is empty or too sparse "
                    f"({nontransparent} pixels)"
                )
            if used and nontransparent > cell_width * cell_height * 0.95:
                near_opaque_used_cells.setdefault(f"{state} row {row_index}", []).append(column_index)
            if not used and nontransparent != 0:
                errors.append(
                    f"{state} row {row_index} unused column {column_index} is not transparent "
                    f"({nontransparent} pixels)"
                )

    for row_label, columns_used in near_opaque_used_cells.items():
        errors.append(
            f"{row_label} has {len(columns_used)} nearly opaque used cells; "
            "this usually means the sprite has a non-transparent background"
        )

    if "A" not in source_mode:
        errors.append("atlas does not have an alpha channel")

    alpha_count = alpha_nonzero_count(image)
    if alpha_count == image.width * image.height:
        errors.append("atlas is fully opaque; custom pets require a transparent sprite background")

    transparent_rgb_residue = transparent_rgb_residue_count(image)
    if transparent_rgb_residue:
        errors.append(
            f"atlas has {transparent_rgb_residue} fully transparent pixels with non-zero RGB residue"
        )

    return {
        "ok": not errors,
        "file": str(atlas_path),
        "format": source_format,
        "mode": source_mode,
        "width": image.width,
        "height": image.height,
        "transparent_rgb_residue_pixels": transparent_rgb_residue,
        "errors": errors,
        "warnings": warnings,
        "cells": cells,
    }


def checker(size: tuple[int, int], square: int = 16) -> Image.Image:
    image = Image.new("RGB", size, "#ffffff")
    draw = ImageDraw.Draw(image)
    for y in range(0, size[1], square):
        for x in range(0, size[0], square):
            if (x // square + y // square) % 2:
                draw.rectangle((x, y, x + square - 1, y + square - 1), fill="#e8e8e8")
    return image


def make_contact_sheet(
    atlas_path: Path,
    atlas_spec: dict[str, int],
    rows: list[dict[str, int | str]],
    output: Path,
    scale: float = 0.5,
) -> None:
    with Image.open(atlas_path) as opened:
        atlas = opened.convert("RGBA")

    columns = int(atlas_spec["columns"])
    cell_width = int(atlas_spec["cell_width"])
    cell_height = int(atlas_spec["cell_height"])
    cell_w = max(1, round(cell_width * scale))
    cell_h = max(1, round(cell_height * scale))
    width = columns * cell_w
    height = len(rows) * (cell_h + LABEL_HEIGHT)
    sheet = Image.new("RGB", (width, height), "#f7f7f7")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for row_spec in rows:
        row = int(row_spec["row"])
        state = str(row_spec["state"])
        used_frames = int(row_spec["frames"])
        y = row * (cell_h + LABEL_HEIGHT)
        draw.rectangle((0, y, width, y + LABEL_HEIGHT - 1), fill="#111111")
        draw.text((6, y + 5), f"row {row}: {state}", fill="#ffffff", font=font)
        draw.text((width - 92, y + 5), f"{used_frames} frames", fill="#ffffff", font=font)
        for column in range(columns):
            crop = atlas.crop(
                (
                    column * cell_width,
                    row * cell_height,
                    (column + 1) * cell_width,
                    (row + 1) * cell_height,
                )
            )
            crop = crop.resize((cell_w, cell_h), Image.Resampling.LANCZOS)
            bg = checker((cell_w, cell_h))
            bg.paste(crop, (0, 0), crop)
            x = column * cell_w
            sheet.paste(bg, (x, y + LABEL_HEIGHT))
            outline = "#18a058" if column < used_frames else "#cc3344"
            draw.rectangle(
                (x, y + LABEL_HEIGHT, x + cell_w - 1, y + LABEL_HEIGHT + cell_h - 1),
                outline=outline,
            )
            draw.text((x + 4, y + LABEL_HEIGHT + 4), str(column), fill="#111111", font=font)

    output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output)


def durations_for_state(state: str, frame_count: int) -> list[int]:
    base = DEFAULT_DURATIONS.get(state)
    if base is None:
        if frame_count <= 1:
            return [280]
        return [140] * (frame_count - 1) + [260]
    if len(base) == frame_count:
        return base
    if frame_count == 1:
        return [base[-1]]
    hold = base[-2] if len(base) >= 2 else base[-1]
    return [hold] * (frame_count - 1) + [base[-1]]


def render_previews(
    frames_root: Path,
    rows: list[dict[str, int | str]],
    output_dir: Path,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    previews = []
    for row in rows:
        state = str(row["state"])
        frame_count = int(row["frames"])
        files = frame_files(frames_root / state)
        if len(files) != frame_count:
            raise SystemExit(
                f"{state} preview needs {frame_count} frames, found {len(files)} under {frames_root / state}"
            )
        frames = []
        for path in files:
            with Image.open(path) as opened:
                frames.append(opened.convert("RGBA"))
        output = output_dir / f"{state}.gif"
        frames[0].save(
            output,
            save_all=True,
            append_images=frames[1:],
            duration=durations_for_state(state, frame_count),
            loop=0,
            disposal=2,
            optimize=False,
        )
        previews.append({"state": state, "path": str(output), "frames": len(frames)})
    return {"ok": True, "output_dir": str(output_dir), "previews": previews}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect frames, compose a spritesheet, validate it, and build QA outputs."
    )
    parser.add_argument("--pet-request", required=True)
    parser.add_argument("--frames-root", required=True)
    parser.add_argument("--final-dir", required=True)
    parser.add_argument("--qa-dir", required=True)
    args = parser.parse_args()

    pet_request = Path(args.pet_request).expanduser().resolve()
    frames_root = Path(args.frames_root).expanduser().resolve()
    final_dir = Path(args.final_dir).expanduser().resolve()
    qa_dir = Path(args.qa_dir).expanduser().resolve()

    atlas_spec, rows = load_pet_request(pet_request)

    review = inspect_frames(frames_root, atlas_spec, rows)
    qa_dir.mkdir(parents=True, exist_ok=True)
    review_path = qa_dir / "review.json"
    review_path.write_text(json.dumps(review, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in review.items() if k != "rows"}, indent=2))
    if not review["ok"]:
        raise SystemExit(1)

    final_dir.mkdir(parents=True, exist_ok=True)
    atlas = compose_atlas(frames_root, atlas_spec, rows)
    png_output = final_dir / "spritesheet.png"
    webp_output = final_dir / "spritesheet.webp"
    atlas.save(png_output)
    atlas.save(
        webp_output,
        format="WEBP",
        lossless=True,
        quality=100,
        method=6,
        exact=True,
    )
    print(f"wrote {png_output}")
    print(f"wrote {webp_output}")

    validation = validate_atlas(webp_output, atlas_spec, rows)
    validation_path = final_dir / "validation.json"
    validation_path.write_text(json.dumps(validation, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in validation.items() if k != "cells"}, indent=2))
    if not validation["ok"]:
        raise SystemExit(1)

    contact_sheet = qa_dir / "contact-sheet.png"
    make_contact_sheet(webp_output, atlas_spec, rows, contact_sheet)
    print(f"wrote {contact_sheet}")

    previews = render_previews(frames_root, rows, qa_dir / "previews")
    print(json.dumps(previews, indent=2))


if __name__ == "__main__":
    main()
