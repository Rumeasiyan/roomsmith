#!/usr/bin/env bash
# Everything CI used to do, run locally. No network, no API key, no cost.
#   tests/run.sh
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "── engine imports"
python3 -c "import engine.room, engine.project, engine.drawings, engine.prompts, engine.render, engine.cli" \
  && echo "   ok"

echo "── unit tests (fallback YAML parser, room geometry, example project)"
python3 tests/test_config.py | sed 's/^/   /'

echo "── example project validates"
./bin/design check --project compact-hall | sed 's/^/   /'

echo "── templates scaffold and validate"
for t in room kitchen; do
  rm -rf "projects/_t-$t"
  ./bin/design init "_t-$t" --from "$t" >/dev/null
  ./bin/design check --project "_t-$t" | tail -1 | sed "s/^/   $t: /"
  rm -rf "projects/_t-$t"
done

echo "── drawings rasterise"
./bin/design approve room-model --project compact-hall --note "local test" >/dev/null
./bin/design drawings --shell --project compact-hall >/dev/null
test -s projects/compact-hall/drawings/_shell-plan.png && echo "   ok"

echo
echo "all checks passed"
