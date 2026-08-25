#!/usr/bin/env bash
# Render one view of one direction via codex exec (image_gen tool).
#
#   scripts/render.sh 01-tropical-modernist-pavilion hero-in
#
# The measured floor plan drawn by scripts/drawings.py is passed as a reference image alongside the
# owner's photographs, so the generated room inherits the real proportions and the real openings
# rather than inventing them.
#
# Resumable: exits early if the output already exists. FORCE=1 to re-render.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${1:?usage: render.sh <NN-slug> <view>}"
VIEW="${2:?usage: render.sh <NN-slug> <view>}"

OUT="$ROOT/renders/${KEY}-${VIEW}.png"
if [[ -s "$OUT" && "${FORCE:-0}" != "1" ]]; then
  echo "skip  ${KEY}-${VIEW} (exists)"
  exit 0
fi

# Photographic anchors: whichever of the owner's photographs was taken nearest this standpoint.
case "$VIEW" in
  hero-in)    PHOTOS="$ROOT/refs/from-entrance.jpg $ROOT/refs/right-side-of-entrance.jpg" ;;
  hero-back)  PHOTOS="$ROOT/refs/entrance.jpg $ROOT/refs/left-side-of-entrance.jpg" ;;
  seated)     PHOTOS="$ROOT/refs/right-side-of-entrance.jpg $ROOT/refs/from-entrance.jpg" ;;
  corner)     PHOTOS="$ROOT/refs/entrance.jpg $ROOT/refs/from-entrance.jpg" ;;
  alcove)     PHOTOS="$ROOT/refs/left-side-of-entrance.jpg $ROOT/refs/entrance.jpg" ;;
  far-wall)   PHOTOS="$ROOT/refs/from-entrance.jpg $ROOT/refs/left-side-of-entrance.jpg" ;;
  *)          PHOTOS="$ROOT/refs/from-entrance.jpg $ROOT/refs/entrance.jpg" ;;
esac

# Measured drawings of this direction, as dimensional references.
PLAN="$ROOT/drawings/${KEY}-plan.png"
ISO="$ROOT/drawings/${KEY}-iso.png"
[[ -s "$PLAN" ]] || PLAN="$ROOT/drawings/_shell-plan.png"
[[ -s "$ISO"  ]] || ISO="$ROOT/drawings/_shell-iso.png"

REFS="$PLAN $ISO $PHOTOS"
PROMPT="$(python3 "$ROOT/scripts/build_prompts.py" "$KEY" "$VIEW")"

IMG_ARGS=(); REF_LIST=""
for r in $REFS; do
  IMG_ARGS+=(-i "$r")
  REF_LIST="$REF_LIST$r"$'\n'
done

WORK="$(mktemp -d)"; trap 'rm -rf "$WORK"' EXIT
LOG="$ROOT/renders/${KEY}-${VIEW}.log"

INSTRUCTION=$(cat <<EOF
Generate exactly one image with the image_gen tool, then save it and stop.

Pass these as referenced_image_paths:
$REF_LIST
The FIRST image is a measured floor plan of this exact room, and the SECOND is a measured isometric
cutaway of it. Use them to get the room's proportion, its narrowness, the position of every opening
and the placement of the furniture correct. The remaining images are BEFORE photographs of the same
room taken from roughly this camera position - use them for the architectural shell only: the
finishes, furniture, ceiling treatment and colours in them are the condition being replaced.

The plan is authoritative on geometry. If the photographs and the plan disagree about where an
opening is, follow the plan.

After the tool returns, copy the generated PNG to exactly this path:
$OUT
Then reply with only that path. Do not generate a second image. Do not edit any other file.

--- IMAGE PROMPT ---
$PROMPT
EOF
)

echo "render ${KEY}-${VIEW} ..."
printf '%s' "$INSTRUCTION" | codex exec \
  --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check \
  -C "$WORK" --add-dir "$ROOT" "${IMG_ARGS[@]}" - >"$LOG" 2>&1 || true

if [[ -s "$OUT" ]]; then
  echo "ok    ${KEY}-${VIEW}"
else
  LATEST="$(grep -oE "$HOME/\.codex/generated_images/[A-Za-z0-9./_-]+\.png" "$LOG" 2>/dev/null | tail -1)"
  if [[ -n "$LATEST" && -s "$LATEST" ]]; then
    cp "$LATEST" "$OUT"; echo "ok    ${KEY}-${VIEW} (recovered)"
  else
    echo "FAIL  ${KEY}-${VIEW} - see $LOG" >&2; exit 1
  fi
fi
