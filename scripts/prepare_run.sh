#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/hatch-pet"
RUN_DIR="$PROJECT_DIR/runs/luka-codex"
REFERENCE_BOARD="$PROJECT_DIR/references/luka_reference_board.png"
REFERENCE_ARGS=()
if [[ -f "$REFERENCE_BOARD" ]]; then
  REFERENCE_ARGS+=(--reference "$REFERENCE_BOARD")
fi

python "$SKILL_DIR/scripts/prepare_pet_run.py" \
  --pet-name "巡音流歌 Codex Pet" \
  --pet-id "luka-codex" \
  --display-name "巡音流歌 Codex Pet" \
  --description "一只安静优雅的粉色章鱼歌姬，在屏幕角落陪你写代码、看日志、检查结果" \
  --output-dir "$RUN_DIR" \
  "${REFERENCE_ARGS[@]}" \
  --pet-notes "Chibi anime vocalist girl inspired by the user's attached Luka reference board for private desktop pet use: 2.5 to 3 head tall proportions, long soft pink hair with thick rounded ends and slight curls, violet or blue-violet eyes, black and gold headband/headset with small blue earpad accents, simplified black singer outfit with gold trim and a few orange-gold ornamental lines, calm mature gentle expression, accompanied by a cute rounded small pink octopus helper with black dot eyes and short tentacles. The octopus can hold a tiny blank logbook, keyboard, terminal-shaped board, progress-bar prop, report card, microphone, note prop, check-shaped prop, or blank red error tag. Compact full-body silhouette, elegant and quiet, not childish, no readable text, no logos, no official marks, no lyrics, no UI screenshots, no floating punctuation, no detached particles." \
  --style-preset "sticker" \
  --style-notes "Clean Q-version anime desktop-pet sticker sprite style, crisp visible outlines, clean color blocks, soft minimal highlights, readable at 192x208, mature and gentle, transparent-ready chroma-key source, no background, no shadows, no floating music notes, no neon cyber look, no scary octopus or slime texture." \
  --chroma-key "#00ff00" \
  --force

append_state_note() {
  local state="$1"
  local note="$2"
  for prompt in "$RUN_DIR/prompts/rows/$state.md" "$RUN_DIR/prompts/row-retries/$state.md"; do
    {
      printf '\nUser Luka state preference:\n'
      printf '%s\n' "$note"
    } >> "$prompt"
  done
}

append_state_note "idle" "Follow the attached reference-board notes: Luka sits or stands quietly with calm mature warmth; her long pink hair moves very slightly, and the small rounded pink octopus rests beside her or in her arms with a slow blink. The loop should feel like listening to a soft melody without interrupting the user."
append_state_note "running-right" "Follow the attached reference-board notes: show soft rightward drag movement, not sprinting. Luka takes small gentle steps to the right while hair and skirt lag slightly. The small octopus may follow closely or be held by Luka; keep it round, cute, and stable."
append_state_note "running-left" "Follow the attached reference-board notes: mirror the rightward feeling toward the left. Luka leans slightly left, hair tips follow slowly, and the small octopus remains cute and rounded without exaggerated bouncing."
append_state_note "waving" "Follow the attached reference-board notes: Luka raises one hand in a small elegant wave with a faint smile. The small octopus may lift one tiny tentacle in sync. Do not add wave marks, floating music notes, or punctuation."
append_state_note "jumping" "Follow the attached reference-board notes: use a small gentle hop, not a high jump. Hair tips and skirt lift slightly; the small octopus may bounce a tiny amount. The feeling is quiet task-complete happiness, not excited jumping."
append_state_note "failed" "Follow the attached reference-board notes: Luka calmly looks down at the octopus or at a tiny blank terminal-shaped board, with mild confusion rather than distress. The octopus may hold a small blank red error-colored tag, but no red X, no readable text, and no floating symbols."
append_state_note "waiting" "Follow the attached reference-board notes: Luka holds the small octopus and waits patiently with a slow blink. Express 'waiting for confirmation' through posture and stillness only; do not draw ellipsis text, speech bubbles, or punctuation."
append_state_note "running" "Follow the attached reference-board notes: Codex working state. Luka focuses on a tiny blank terminal-shaped board, gold note microphone, or the octopus with a little keyboard or blank log scroll. This is task processing, not locomotion; no floating code, no progress particles, no readable UI."
append_state_note "review" "Follow the attached reference-board notes: Luka holds a blank result board or small report card with a focused serious expression. The octopus may hold a small check-shaped prop. Keep all props close to the character and without readable text. The attached complete/success pose may inform this row's calm positive finish, but do not create a separate complete row."

echo "Prepared hatch-pet run: $RUN_DIR"
