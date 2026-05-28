#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def codex_home_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    env_value = os.environ.get("CODEX_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def make_pet_payload(request: dict[str, object]) -> tuple[dict[str, str], dict[str, str]]:
    pet = {
        "id": str(request["pet_id"]),
        "displayName": str(request["display_name"]),
        "description": str(request["description"]),
        "spritesheetPath": "spritesheet.webp",
    }
    avatar = {
        **pet,
        "name": str(request["display_name"]),
        "spritesheet": "spritesheet.webp",
    }
    return pet, avatar


def copy_package_files(package_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for name in ("pet.json", "avatar.json", "spritesheet.webp"):
        shutil.copy2(package_dir / name, destination_dir / name)


def install_runtime_patch(project_dir: Path, asar: str | None) -> None:
    cmd = [sys.executable, str(project_dir / "scripts" / "patch_codex_avatar_runtime.py")]
    if asar:
        cmd.extend(["--asar", asar])
    run(cmd)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the Luka transform-only spritesheet package and optionally install it into Codex."
    )
    parser.add_argument("--project-dir", default=str(PROJECT_DIR))
    parser.add_argument("--pet-request")
    parser.add_argument("--references-dir")
    parser.add_argument("--run-dir")
    parser.add_argument("--package-dir")
    parser.add_argument("--codex-home")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--patch-runtime", action="store_true")
    parser.add_argument("--asar")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    pet_request = Path(args.pet_request or project_dir / "config" / "pet_request.json").expanduser().resolve()
    references_dir = Path(args.references_dir or project_dir / "references").expanduser().resolve()
    run_dir = Path(args.run_dir or project_dir / "runs" / "luka-codex").expanduser().resolve()
    package_dir = Path(args.package_dir or project_dir / "package").expanduser().resolve()

    if not pet_request.is_file():
        raise SystemExit(f"Missing pet request: {pet_request}")
    if not references_dir.is_dir():
        raise SystemExit(f"Missing references dir: {references_dir}")

    rows_dir = run_dir / "generated" / "transform-rows"
    frames_dir = run_dir / "frames"
    final_dir = run_dir / "final"
    qa_dir = run_dir / "qa"

    for path in (rows_dir, frames_dir, final_dir, qa_dir):
        if path.exists():
            shutil.rmtree(path)
        path.mkdir(parents=True, exist_ok=True)

    run(
        [
            sys.executable,
            str(project_dir / "scripts" / "build_filled_rows.py"),
            "--references-dir",
            str(references_dir),
            "--output-dir",
            str(rows_dir),
            "--frames-dir",
            str(frames_dir),
        ]
    )
    run(
        [
            sys.executable,
            str(project_dir / "scripts" / "package_runtime_assets.py"),
            "--pet-request",
            str(pet_request),
            "--frames-root",
            str(frames_dir),
            "--final-dir",
            str(final_dir),
            "--qa-dir",
            str(qa_dir),
        ]
    )

    request = load_json(pet_request)
    pet_payload, avatar_payload = make_pet_payload(request)

    package_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(final_dir / "spritesheet.webp", package_dir / "spritesheet.webp")
    write_json(package_dir / "pet.json", pet_payload)
    write_json(package_dir / "avatar.json", avatar_payload)

    install_dir = None
    if args.install:
        codex_home = codex_home_path(args.codex_home)
        install_dir = codex_home / "pets" / str(request["pet_id"])
        copy_package_files(package_dir, install_dir)

    if args.patch_runtime:
        install_runtime_patch(project_dir, args.asar)

    summary = {
        "ok": True,
        "pet_id": str(request["pet_id"]),
        "run_dir": str(run_dir),
        "rows_dir": str(rows_dir),
        "frames_dir": str(frames_dir),
        "final_dir": str(final_dir),
        "package_dir": str(package_dir),
        "spritesheet": str(final_dir / "spritesheet.webp"),
        "validation": str(final_dir / "validation.json"),
        "contact_sheet": str(qa_dir / "contact-sheet.png"),
        "review": str(qa_dir / "review.json"),
        "installed_to": str(install_dir) if install_dir else None,
        "runtime_patch_applied": bool(args.patch_runtime),
    }
    write_json(qa_dir / "run-summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
