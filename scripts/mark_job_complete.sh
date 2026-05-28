#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 || $# -gt 3 ]]; then
  echo "Usage: $0 <job-id> <selected-source.png> [run-dir]" >&2
  exit 1
fi

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOB_ID="$1"
SOURCE="$2"
RUN_DIR="${3:-$PROJECT_DIR/runs/luka-codex}"

if [[ ! -f "$SOURCE" ]]; then
  echo "Selected source does not exist: $SOURCE" >&2
  exit 1
fi

if [[ ! -f "$RUN_DIR/imagegen-jobs.json" ]]; then
  echo "Missing imagegen-jobs.json in $RUN_DIR" >&2
  exit 1
fi

OUTPUT_REL="$(jq -r --arg id "$JOB_ID" '.jobs[] | select(.id == $id) | .output_path // empty' "$RUN_DIR/imagegen-jobs.json")"
if [[ -z "$OUTPUT_REL" ]]; then
  echo "Unknown job id: $JOB_ID" >&2
  exit 1
fi

mkdir -p "$(dirname "$RUN_DIR/$OUTPUT_REL")"
cp "$SOURCE" "$RUN_DIR/$OUTPUT_REL"

if [[ "$JOB_ID" == "base" ]]; then
  mkdir -p "$RUN_DIR/references"
  cp "$RUN_DIR/$OUTPUT_REL" "$RUN_DIR/references/canonical-base.png"
fi

UPDATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TMP_MANIFEST="$(mktemp)"
jq \
  --arg id "$JOB_ID" \
  --arg source "$SOURCE" \
  --arg at "$UPDATED_AT" \
  '(.jobs[] | select(.id == $id)) += {status: "complete", source_path: $source, completed_at: $at}' \
  "$RUN_DIR/imagegen-jobs.json" > "$TMP_MANIFEST"
mv "$TMP_MANIFEST" "$RUN_DIR/imagegen-jobs.json"

GENERATED_ROOT="${CODEX_HOME:-$HOME/.codex}/generated_images"
case "$SOURCE" in
  "$GENERATED_ROOT"/*)
    rm -f "$SOURCE"
    rmdir "$(dirname "$SOURCE")" 2>/dev/null || true
    ;;
esac

echo "Marked complete: $JOB_ID -> $RUN_DIR/$OUTPUT_REL"
if [[ "$JOB_ID" == "base" ]]; then
  echo "Canonical base: $RUN_DIR/references/canonical-base.png"
fi
