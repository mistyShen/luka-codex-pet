#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent


PATCHES: tuple[dict[str, str], ...] = (
    {
        "file": "webview/assets/codex-avatar-5rBVLDei.js",
        "label": "custom 8-frame running playback for custom spritesheets",
        "old": (
            "function M(e){let t=(0,p.c)(6),{avatarRef:n,isAnimationEnabled:r,"
            "prefersReducedMotion:i,state:a}=e,o=r===void 0?!0:r,s=a===void 0?"
            "`idle`:a,c,l;t[0]!==n||t[1]!==o||t[2]!==i||t[3]!==s?(c=()=>{let e="
            "n.current;if(e==null)return;let t=N(s,i||!o),r=t.frames,a=0,c=null;"
            "if(e.style.backgroundPosition=F(r[a]),r.length===1)return;let l="
            "()=>{c=window.setTimeout(()=>{let n=a+1;if(n>=r.length){if(t."
            "loopStartIndex!=null){a=t.loopStartIndex,e.style.backgroundPosition="
            "F(r[a]),l();return}c=null;return}a=n,e.style.backgroundPosition=F("
            "r[a]),l()},r[a].frameDurationMs)};return l(),()=>{c!=null&&window."
            "clearTimeout(c)}},l=[n,o,i,s],t[0]=n,t[1]=o,t[2]=i,t[3]=s,t[4]=c,"
            "t[5]=l):(c=t[4],l=t[5]),(0,T.useEffect)(c,l)}"
        ),
        "new": (
            "function M(e){let t=(0,p.c)(8),{avatarRef:n,isAnimationEnabled:r,"
            "isCustomSpritesheet:i,prefersReducedMotion:a,state:o}=e,s=r===void "
            "0?!0:r,c=i===void 0?!1:i,l=o===void 0?`idle`:o,u,d;t[0]!==n||t[1]!==" 
            "s||t[2]!==a||t[3]!==l||t[4]!==c?(u=()=>{let e=n.current;if(e==null)"
            "return;let t=N(l,a||!s,c),r=t.frames,i=0,o=null;if(e.style."
            "backgroundPosition=F(r[i]),r.length===1)return;let c=()=>{o=window."
            "setTimeout(()=>{let n=i+1;if(n>=r.length){if(t.loopStartIndex!=null)"
            "{i=t.loopStartIndex,e.style.backgroundPosition=F(r[i]),c();return}"
            "o=null;return}i=n,e.style.backgroundPosition=F(r[i]),c()},r[i]."
            "frameDurationMs)};return c(),()=>{o!=null&&window.clearTimeout(o)}},"
            "d=[n,s,a,l,c],t[0]=n,t[1]=s,t[2]=a,t[3]=l,t[4]=c,t[5]=u,t[6]=d):("
            "u=t[5],d=t[6]),(0,T.useEffect)(u,d)}"
        ),
        "marker": "isCustomSpritesheet",
    },
    {
        "file": "webview/assets/codex-avatar-5rBVLDei.js",
        "label": "custom running row uses 8 frames",
        "old": (
            "function N(e,t){let n=j[e];if(t)return{frames:[n[0]],loopStartIndex:"
            "null};if(e===`idle`)return{frames:A,loopStartIndex:0};let r=[...n,"
            "...n,...n];return{frames:[...r,...A],loopStartIndex:r.length}}"
        ),
        "new": (
            "function N(e,t,n){let r=n&&e===`running`?P(7,8,120,220):j[e];if(t)"
            "return{frames:[r[0]],loopStartIndex:null};if(e===`idle`)return{"
            "frames:A,loopStartIndex:0};let i=[...r,...r,...r];return{frames:[..."
            "i,...A],loopStartIndex:i.length}}"
        ),
        "marker": "P(7,8,120,220)",
    },
    {
        "file": "webview/assets/codex-avatar-5rBVLDei.js",
        "label": "custom spritesheet flag passed to avatar animator",
        "old": (
            "let f=d,m;t[2]!==l||t[3]!==s?(m={avatarRef:c,prefersReducedMotion:l,"
            "state:s},t[2]=l,t[3]=s,t[4]=m):m=t[4],M(m);let h;"
        ),
        "new": (
            "let f=d;M({avatarRef:c,isCustomSpritesheet:!!a,prefersReducedMotion:"
            "l,state:s});let h;"
        ),
        "marker": "isCustomSpritesheet:!!a",
    },
    {
        "file": "webview/assets/avatar-overlay-page-rDiP16E4.js",
        "label": "closed tray can wave and open tray can review",
        "old": "state:T.mascotState,style:s,transientState:c",
        "new": (
            "state:!E&&re&&(T.mascotState===`idle`||T.mascotState===`review`)?"
            "`waving`:E&&re&&T.mascotState===`idle`?`review`:T.mascotState,style:"
            "s,transientState:c"
        ),
        "marker": "T.mascotState===`review`)?`waving`",
    },
)


def default_backup_dir() -> Path:
    return PROJECT_DIR / "app_runtime_backup"


def candidate_asar_paths() -> list[Path]:
    candidates: list[Path] = []
    home = Path.home()

    if sys.platform == "darwin":
        candidates.extend(
            [
                Path("/Applications/Codex.app/Contents/Resources/app.asar"),
                home / "Applications" / "Codex.app" / "Contents" / "Resources" / "app.asar",
            ]
        )
    elif os.name == "nt":
        env_paths = (
            ("LOCALAPPDATA", ("Programs", "Codex", "resources", "app.asar")),
            ("LOCALAPPDATA", ("Programs", "codex", "resources", "app.asar")),
            ("ProgramFiles", ("Codex", "resources", "app.asar")),
            ("ProgramFiles(x86)", ("Codex", "resources", "app.asar")),
        )
        for env_name, suffix in env_paths:
            base = os.environ.get(env_name)
            if base:
                candidates.append(Path(base).joinpath(*suffix))

    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in candidates:
        expanded = path.expanduser()
        if expanded not in seen:
            deduped.append(expanded)
            seen.add(expanded)
    return deduped


def resolve_default_asar_path() -> Path:
    candidates = candidate_asar_paths()
    for path in candidates:
        if path.is_file():
            return path.resolve()

    checked = "\n".join(f"  - {path}" for path in candidates) or "  - none"
    raise SystemExit(
        "Could not locate Codex app.asar automatically. Pass --asar with the full path.\n"
        f"Checked:\n{checked}"
    )


def ensure_npx() -> None:
    if shutil.which("npx") is None:
        raise SystemExit("Missing npx. Install Node.js first, then rerun this script.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def apply_patch_once(text: str, old: str, new: str, marker: str, label: str) -> tuple[str, bool]:
    if marker in text or new in text:
        return text, False
    if old not in text:
        raise RuntimeError(f"Patch target not found for {label}")
    return text.replace(old, new, 1), True


def patch_extracted_tree(root: Path) -> dict[str, list[str]]:
    applied: dict[str, list[str]] = {}
    for patch in PATCHES:
        file_path = root / patch["file"]
        text = file_path.read_text(encoding="utf-8")
        new_text, changed = apply_patch_once(
            text,
            patch["old"],
            patch["new"],
            patch["marker"],
            patch["label"],
        )
        if changed:
            file_path.write_text(new_text, encoding="utf-8")
            applied.setdefault(patch["file"], []).append(patch["label"])
    return applied


def write_status(
    status_path: Path,
    *,
    asar_path: Path,
    backup_path: Path,
    before_hash: str,
    after_hash: str,
    applied: dict[str, list[str]],
) -> None:
    payload = {
        "target_asar": str(asar_path),
        "backup_asar": str(backup_path),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "before_sha256": before_hash,
        "after_sha256": after_hash,
        "changed": before_hash != after_hash,
        "patched_files": applied,
        "features": [
            "custom spritesheet running row supports 8 frames",
            "custom sprite animation receives explicit custom spritesheet flag",
            "closed notification state can show waving",
            "open notification tray can show review more often",
        ],
    }
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Patch the installed Codex desktop app so custom pets can use 8-frame "
            "running rows and surface review or waving states more reliably."
        )
    )
    parser.add_argument("--asar")
    parser.add_argument("--backup-dir", default=str(default_backup_dir()))
    args = parser.parse_args()

    ensure_npx()

    asar_path = (
        Path(args.asar).expanduser().resolve()
        if args.asar
        else resolve_default_asar_path()
    )
    backup_dir = Path(args.backup_dir).expanduser().resolve()
    backup_path = backup_dir / "Codex.app.asar.orig"
    status_path = backup_dir / "codex_runtime_patch_status.json"

    if not asar_path.is_file():
        raise SystemExit(f"Missing app.asar: {asar_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    if not backup_path.exists():
        shutil.copy2(asar_path, backup_path)

    before_hash = sha256(asar_path)

    with tempfile.TemporaryDirectory(prefix="codex-avatar-patch-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        extracted_dir = tmp_dir / "extracted"
        patched_asar = tmp_dir / "patched.asar"
        run(["npx", "--yes", "asar", "extract", str(asar_path), str(extracted_dir)])
        applied = patch_extracted_tree(extracted_dir)
        run(["npx", "--yes", "asar", "pack", str(extracted_dir), str(patched_asar)])
        shutil.copy2(patched_asar, asar_path)

    after_hash = sha256(asar_path)
    write_status(
        status_path,
        asar_path=asar_path,
        backup_path=backup_path,
        before_hash=before_hash,
        after_hash=after_hash,
        applied=applied,
    )

    print(
        json.dumps(
            {
                "asar": str(asar_path),
                "backup": str(backup_path),
                "status": str(status_path),
                "changed": before_hash != after_hash,
                "patched_files": applied,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
