#!/usr/bin/env bash
# Render every direction, both views, in parallel. Resumable - already-rendered views are
# skipped, so a partial or failed run is re-run rather than restarted.
#
#   scripts/render_all.sh          # all directions, 4 concurrent
#   JOBS=6 scripts/render_all.sh   # more concurrency
#   scripts/render_all.sh 03 07    # only these direction ids
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JOBS="${JOBS:-4}"

mapfile -t SPECS < <(ls "$ROOT"/directions/[0-9][0-9]-*.json | xargs -n1 basename | sed 's/\.json$//')

if [[ $# -gt 0 ]]; then
  FILTER=("$@")
  KEEP=()
  for s in "${SPECS[@]}"; do
    for f in "${FILTER[@]}"; do [[ "$s" == "$f"* ]] && KEEP+=("$s"); done
  done
  SPECS=("${KEEP[@]}")
fi

printf '%s\n' "${SPECS[@]}" \
  | awk '{print $0" a"; print $0" b"}' \
  | xargs -P "$JOBS" -n 2 "$ROOT/scripts/render.sh"

echo
echo "rendered: $(ls "$ROOT"/renders/*.png 2>/dev/null | wc -l) / $(( ${#SPECS[@]} * 2 ))"
for s in "${SPECS[@]}"; do
  for v in a b; do
    [[ -s "$ROOT/renders/${s}-${v}.png" ]] || echo "MISSING ${s}-${v}"
  done
done
