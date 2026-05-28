#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet"
RUN_DIR="${1:-$PROJECT_DIR/runs/luka-codex}"

if [[ ! -f "$RUN_DIR/imagegen-jobs.json" ]]; then
  echo "Missing imagegen-jobs.json in $RUN_DIR" >&2
  exit 1
fi

PENDING_COUNT="$(jq '[.jobs[] | select(.status != "complete")] | length' "$RUN_DIR/imagegen-jobs.json")"
if [[ "$PENDING_COUNT" != "0" ]]; then
  echo "Cannot process yet: $PENDING_COUNT image job(s) are not complete." >&2
  jq -r '.jobs[] | select(.status != "complete") | "- " + .id + " (" + .status + ")"' "$RUN_DIR/imagegen-jobs.json" >&2
  exit 1
fi

mkdir -p "$RUN_DIR/final" "$RUN_DIR/qa"

python "$SKILL_DIR/scripts/extract_strip_frames.py" \
  --decoded-dir "$RUN_DIR/decoded" \
  --output-dir "$RUN_DIR/frames" \
  --states all \
  --method auto

python "$SKILL_DIR/scripts/inspect_frames.py" \
  --frames-root "$RUN_DIR/frames" \
  --json-out "$RUN_DIR/qa/review.json" \
  --require-components

python "$SKILL_DIR/scripts/compose_atlas.py" \
  --frames-root "$RUN_DIR/frames" \
  --output "$RUN_DIR/final/spritesheet.png" \
  --webp-output "$RUN_DIR/final/spritesheet.webp"

python "$SKILL_DIR/scripts/validate_atlas.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --json-out "$RUN_DIR/final/validation.json"

python "$SKILL_DIR/scripts/make_contact_sheet.py" \
  "$RUN_DIR/final/spritesheet.webp" \
  --output "$RUN_DIR/qa/contact-sheet.png"

python "$SKILL_DIR/scripts/render_animation_previews.py" \
  --frames-root "$RUN_DIR/frames" \
  --output-dir "$RUN_DIR/qa/previews"

PET_ID="$(jq -r '.pet_id' "$RUN_DIR/pet_request.json")"
DISPLAY_NAME="$(jq -r '.display_name' "$RUN_DIR/pet_request.json")"
DESCRIPTION="$(jq -r '.description' "$RUN_DIR/pet_request.json")"
PET_DIR="${CODEX_HOME:-$HOME/.codex}/pets/$PET_ID"

mkdir -p "$PET_DIR" "$PROJECT_DIR/package"
cp "$RUN_DIR/final/spritesheet.webp" "$PET_DIR/spritesheet.webp"
jq -n \
  --arg id "$PET_ID" \
  --arg displayName "$DISPLAY_NAME" \
  --arg description "$DESCRIPTION" \
  '{id: $id, displayName: $displayName, description: $description, spritesheetPath: "spritesheet.webp"}' \
  > "$PET_DIR/pet.json"

jq -n \
  --arg id "$PET_ID" \
  --arg displayName "$DISPLAY_NAME" \
  --arg description "$DESCRIPTION" \
  '{id: $id, displayName: $displayName, description: $description, spritesheetPath: "spritesheet.webp", name: $displayName, spritesheet: "spritesheet.webp"}' \
  > "$PET_DIR/avatar.json"

cp "$PET_DIR/pet.json" "$PROJECT_DIR/package/pet.json"
cp "$PET_DIR/spritesheet.webp" "$PROJECT_DIR/package/spritesheet.webp"
cp "$PET_DIR/avatar.json" "$PROJECT_DIR/package/avatar.json"

jq -n \
  --arg run_dir "$RUN_DIR" \
  --arg spritesheet "$RUN_DIR/final/spritesheet.webp" \
  --arg validation "$RUN_DIR/final/validation.json" \
  --arg contact_sheet "$RUN_DIR/qa/contact-sheet.png" \
  --arg review "$RUN_DIR/qa/review.json" \
  --arg package "$PET_DIR" \
  '{ok: true, run_dir: $run_dir, spritesheet: $spritesheet, validation: $validation, contact_sheet: $contact_sheet, review: $review, package: $package}' \
  > "$RUN_DIR/qa/run-summary.json"

echo "Packaged Codex pet: $PET_DIR"
echo "Project package copy: $PROJECT_DIR/package"
