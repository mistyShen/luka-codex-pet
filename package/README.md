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

Codex reads the installed copy from:

```text
${CODEX_HOME:-$HOME/.codex}/pets/luka-codex/
  pet.json
  avatar.json
  spritesheet.webp
```
