#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet"
RUN_DIR="${1:-$PROJECT_DIR/runs/luka-codex}"

python "$SKILL_DIR/scripts/derive_running_left_from_running_right.py" \
  --run-dir "$RUN_DIR" \
  --confirm-appropriate-mirror \
  --decision-note "The simplified Luka Codex pet uses a mostly symmetric chibi silhouette, non-readable headset details, and pet-safe held props, so framewise mirroring preserves identity while changing drag direction."
