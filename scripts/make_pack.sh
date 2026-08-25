#!/usr/bin/env bash
# Build the COMPLETE interior pack for ONE direction, then stop.
#
#   scripts/make_pack.sh 01-tropical-modernist-pavilion
#   FORCE=1 scripts/make_pack.sh 01-...          # re-render even if images exist
#   VIEWS="hero-in seated" scripts/make_pack.sh 01-...   # re-do only some views
#
# One direction at a time is deliberate. Each pack is inspected and corrected before the next
# direction starts, so a defect found in direction 01 is fixed for 02..20 instead of being
# reproduced twenty times.
#
# The pack:
#   drawings/  plan, blueprint, isometric dollhouse, four wall elevations   (drawn by code, exact)
#   renders/   six photoreal views covering all four walls                  (image_gen)
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEY="${1:?usage: make_pack.sh <NN-slug>}"
JOBS="${JOBS:-3}"
VIEWS="${VIEWS:-hero-in hero-back seated corner alcove far-wall}"

# Resolve a partial key such as "01" to the full directory stem.
FULL="$(ls "$ROOT"/directions/[0-9][0-9]-*.json | xargs -n1 basename | sed 's/\.json$//' \
        | grep -E "^${KEY}" | head -1)"
[[ -n "$FULL" ]] || { echo "no direction matching '$KEY'" >&2; exit 1; }

echo "═══ PACK  $FULL"
echo "--- measured drawings (code-drawn, exact geometry)"
python3 "$ROOT/scripts/drawings.py" "$FULL" | sed 's/^/    /'

echo "--- photoreal views"
printf '%s\n' $VIEWS | xargs -P "$JOBS" -I{} "$ROOT/scripts/render.sh" "$FULL" {}

echo
echo "--- pack contents"
MISSING=0
for f in plan blueprint iso elev-entrance elev-right elev-far elev-left; do
  p="$ROOT/drawings/$FULL-$f.png"
  if [[ -s "$p" ]]; then printf '    ✓ drawing  %s\n' "$f"; else printf '    ✗ drawing  %s\n' "$f"; MISSING=1; fi
done
for v in $VIEWS; do
  p="$ROOT/renders/$FULL-$v.png"
  if [[ -s "$p" ]]; then printf '    ✓ render   %s\n' "$v"; else printf '    ✗ render   %s\n' "$v"; MISSING=1; fi
done

cat <<'EOF'

--- QA CHECKLIST — inspect every render against this before moving to the next direction
    1  OPENINGS. Exactly four: front door D1 and window W1 on the entrance wall; curtained
       doorway D2 inside the alcove on the entering-RIGHT flank; arch A1 at the far end of the
       entering-RIGHT flank. Any extra door, window, pass-through or opening in the entering-LEFT
       wall or the far wall is a FAIL.
    2  SCALE. Room must read ~3.1 m wide. The settee must span more than half the width. If the
       floor looks generous or the far wall looks distant, it is a FAIL.
    3  FURNITURE. Carved teak settee, two carved armchairs, curio cabinet, a low table and an
       eating table must all be present.
    4  SHRINE. Crucifix or statue with a lit votive lamp, present and reachable.
    5  ALCOVE. The entering-RIGHT wall must show the step-out, not run flat.
    6  CONSISTENCY. All six views must be the same room - same finishes, same layout, same
       furniture positions as the plan.
EOF
exit $MISSING
