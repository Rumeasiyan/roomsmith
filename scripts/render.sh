#!/usr/bin/env bash
# Render one direction view via codex exec (image_gen tool).
#
#   scripts/render.sh 01-tropical-modernist-pavilion a
#
# Resumable: exits early if renders/<id>-<slug>-<view>.png already exists.
# Override camera anchor photos with REF_A / REF_B when reusing on another room.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${1:?usage: render.sh <NN-slug> <a|b>}"
VIEW="${2:?usage: render.sh <NN-slug> <a|b>}"

OUT="$ROOT/renders/${KEY}-${VIEW}.png"
if [[ -s "$OUT" ]]; then
  echo "skip  ${KEY}-${VIEW} (exists)"
  exit 0
fi

# Camera anchors: the real photographs taken from the same two standpoints, so the
# generated image is an edit of a known room rather than an invented one.
REF_A="${REF_A:-$ROOT/refs/from-entrance.jpg $ROOT/refs/right-side-of-entrance.jpg}"
REF_B="${REF_B:-$ROOT/refs/entrance.jpg $ROOT/refs/left-side-of-entrance.jpg}"
if [[ "$VIEW" == "a" ]]; then REFS="$REF_A"; else REFS="$REF_B"; fi

PROMPT="$(python3 "$ROOT/scripts/build_prompts.py" "$KEY" "$VIEW")"

IMG_ARGS=()
REF_LIST=""
for r in $REFS; do
  IMG_ARGS+=(-i "$r")
  REF_LIST="$REF_LIST$r"$'\n'
done

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

INSTRUCTION=$(cat <<EOF
Generate exactly one image with the image_gen tool, then save it and stop.

Pass these as referenced_image_paths so the generated room keeps the real geometry,
openings and proportions of the actual space (they are the BEFORE photographs of the same
room, taken from this same camera position):
$REF_LIST
Treat the reference photographs as the architectural shell only. The furniture, finishes,
ceiling treatment, lighting and colours in them are the condition being replaced.

After the tool returns, copy the generated PNG to exactly this path:
$OUT
Then reply with only that path. Do not generate a second image. Do not edit any other file.

--- IMAGE PROMPT ---
$PROMPT
EOF
)

echo "render ${KEY}-${VIEW} ..."
printf '%s' "$INSTRUCTION" | codex exec \
  --dangerously-bypass-approvals-and-sandbox \
  --skip-git-repo-check \
  -C "$WORK" \
  --add-dir "$ROOT" \
  "${IMG_ARGS[@]}" \
  - >"$ROOT/renders/${KEY}-${VIEW}.log" 2>&1 || true

if [[ -s "$OUT" ]]; then
  echo "ok    ${KEY}-${VIEW}"
else
  # Fallback: codex sometimes reports the path instead of copying it. Recover the path it
  # printed in its own transcript - parallel-safe, unlike a newest-file scan.
  LATEST="$(grep -oE "$HOME/\.codex/generated_images/[A-Za-z0-9./_-]+\.png" \
            "$ROOT/renders/${KEY}-${VIEW}.log" 2>/dev/null | tail -1)"
  if [[ -n "$LATEST" && -s "$LATEST" ]]; then
    cp "$LATEST" "$OUT"
    echo "ok    ${KEY}-${VIEW} (recovered)"
  else
    echo "FAIL  ${KEY}-${VIEW} - see renders/${KEY}-${VIEW}.log" >&2
    exit 1
  fi
fi
