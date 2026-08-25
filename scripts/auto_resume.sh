#!/usr/bin/env bash
# Wait for the codex image_gen quota to come back, then render every direction, one at a time.
# Poll cheaply; do not burn attempts while the limit is still in force.
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG="$ROOT/renders/_auto_resume.log"
mkdir -p "$ROOT/renders"; : > "$LOG"
echo "waiting for codex quota — started $(date)" >> "$LOG"
while true; do
  OUT="$(cd /tmp && timeout 120 codex exec --dangerously-bypass-approvals-and-sandbox \
        --skip-git-repo-check "reply with OK only" 2>&1 | tail -3)"
  if ! grep -qi "usage limit\|quota" <<<"$OUT"; then
    echo "quota available $(date) — starting renders" >> "$LOG"
    "$ROOT/scripts/resume_renders.sh" >> "$LOG" 2>&1
    echo "finished $(date)" >> "$LOG"
    exit 0
  fi
  echo "still limited $(date)" >> "$LOG"
  sleep 600
done
