#!/usr/bin/env bash
# Render every direction that is still missing photoreal views, one direction at a time.
# Stops cleanly the moment the codex image_gen quota is exhausted, so it can simply be re-run later.
#
#   scripts/resume_renders.sh
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VIEWS="${VIEWS:-hero-in hero-back seated corner alcove far-wall}"

for f in "$ROOT"/directions/[0-9][0-9]-*.json; do
  KEY="$(basename "$f" .json)"
  MISSING=0
  for v in $VIEWS; do [[ -s "$ROOT/renders/$KEY-$v.png" ]] || MISSING=1; done
  [[ $MISSING -eq 1 ]] || { echo "done   $KEY"; continue; }

  echo "═══ $KEY"
  JOBS="${JOBS:-3}" "$ROOT/scripts/make_pack.sh" "$KEY" >/dev/null 2>&1

  # Did we actually get images, or did codex refuse?
  GOT=0; for v in $VIEWS; do [[ -s "$ROOT/renders/$KEY-$v.png" ]] && GOT=$((GOT+1)); done
  echo "    $GOT/$(echo $VIEWS | wc -w) views"
  if [[ $GOT -eq 0 ]]; then
    if grep -qi "usage limit\|quota\|rate limit" "$ROOT"/renders/"$KEY"-*.log 2>/dev/null; then
      echo
      echo "STOPPED: codex image_gen usage limit reached. Re-run this script when it resets;"
      echo "everything already rendered is skipped."
      exit 2
    fi
    echo "STOPPED: $KEY produced no images and it is not a quota problem - check renders/$KEY-*.log" >&2
    exit 1
  fi
done
echo "all directions have their full set of views"
