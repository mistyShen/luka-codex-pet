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


def copy_payload(source_dir: Path, destination_dir: Path) -> None:
    destination_dir.mkdir(parents=True, exist_ok=True)
    for name in ("pet.json", "avatar.json", "spritesheet.webp"):
        shutil.copy2(source_dir / name, destination_dir / name)


def apply_runtime_patch(project_dir: Path, asar: str | None) -> None:
    cmd = [sys.executable, str(project_dir / "scripts" / "patch_codex_avatar_runtime.py")]
    if asar:
        cmd.extend(["--asar", asar])
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Install the prebuilt Luka Codex pet package into the local Codex pets directory."
    )
    parser.add_argument("--project-dir", default=str(PROJECT_DIR))
    parser.add_argument("--source-dir")
    parser.add_argument("--codex-home")
    parser.add_argument("--patch-runtime", action="store_true")
    parser.add_argument("--asar")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    source_dir = Path(args.source_dir or project_dir / "package").expanduser().resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"Missing package dir: {source_dir}")

    required = [source_dir / name for name in ("pet.json", "avatar.json", "spritesheet.webp")]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise SystemExit("Package is incomplete:\n" + "\n".join(missing))

    pet_payload = load_json(source_dir / "pet.json")
    pet_id = str(pet_payload["id"])
    install_dir = codex_home_path(args.codex_home) / "pets" / pet_id
    copy_payload(source_dir, install_dir)

    if args.patch_runtime:
        apply_runtime_patch(project_dir, args.asar)

    summary = {
        "ok": True,
        "pet_id": pet_id,
        "source_dir": str(source_dir),
        "install_dir": str(install_dir),
        "runtime_patch_applied": bool(args.patch_runtime),
    }
    write_json(project_dir / "package" / "install-summary.json", summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
