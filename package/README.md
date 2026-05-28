# Package

This directory contains the ready-to-install Codex pet package:

```text
package/
  pet.json
  avatar.json
  spritesheet.webp
```

Install it with:

```bash
python3 ../scripts/install_pet.py
```

On Windows PowerShell:

```powershell
.\..\scripts\install_pet.ps1
```

Codex reads the installed copy from:

```text
${CODEX_HOME:-$HOME/.codex}/pets/luka-codex/
  pet.json
  avatar.json
  spritesheet.webp
```

The package works without modifying Codex. The runtime patch in `scripts/patch_codex_avatar_runtime.py` is optional.
