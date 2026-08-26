# Usage

Day-to-day commands and recipes. See `WORKFLOW.md` for the gate-by-gate walkthrough and
`CONFIG.md` for every `project.yml` option.

## The command

```
./bin/design <command> [--project <slug>]
```

`--project` works before or after the command. If you omit it, the tool uses the only project
present, or the slug in `config/current`.

| Command | Does |
|---|---|
| `init <slug> [--from room\|kitchen]` | Scaffold a new job |
| `status` | Where the job is: room, directions, views rendered, spend, gates |
| `gates` | Every gate, what it guards, whether it is approved |
| `check` | Validate config, geometry and layouts. **Run this constantly** |
| `drawings [NN\|--shell]` | Measured drawings for one direction, or the empty room |
| `pack <NN>` | ONE direction, end to end, then stop. The unit of review |
| `render [NN] [--backend B] [--wait] [--force]` | Photoreal views |
| `report [--no-pdf]` | Build the client report |
| `approve <gate> [--note "..."] [--revoke]` | Record or withdraw an approval |

## Recipes

**Start a job**

```bash
./bin/design init drawing-room
cp ~/client-photos/*.jpg projects/drawing-room/refs/
./bin/design status
```
Then `/interior-design` in Claude Code, or drive the agents yourself.

**See the empty room before designing anything**

```bash
./bin/design drawings --shell
open projects/drawing-room/drawings/_shell-plan.png
```
Do this early and actually look at it. Drawings expose errors prose hides.

**Review one direction properly**

```bash
./bin/design pack 03
```
Builds its drawings and every camera view, then stops and prints a QA checklist. Run the
`design-critic` agent on the result.

**Render everything**

```bash
./bin/design render                       # free backend, stops on quota
./bin/design render --wait                # free backend, rides out the quota reset
./bin/design render --backend openrouter  # paid, needs the `spend` gate
```
Resumable in every case: finished views are skipped, so re-running costs nothing.

**Re-do one direction after changing its spec**

```bash
./bin/design check
./bin/design drawings 07
./bin/design render 07 --force
```

**Fix a wrong dimension**

Change `project.yml`, then regenerate. Never edit a drawing or retouch an image — the whole point
is that one file is the source of truth.

```bash
$EDITOR projects/drawing-room/project.yml
./bin/design check
./bin/design drawings --shell
```

**Work on several jobs**

```bash
./bin/design status --project kitchen-refit
echo kitchen-refit > config/current      # make it the default
```

**Check what a render will actually be told**

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from engine.project import resolve
from engine import prompts
import json, pathlib
p = resolve(None)
spec = json.loads(pathlib.Path('projects/compact-hall/directions/01-tropical-modernist-pavilion.json').read_text())
print(prompts.build(p, spec, 'hero-in'))"
```
Worth doing when a render keeps coming out wrong — the answer is usually visible in the prompt.

## What gets committed

| Committed | Not committed |
|---|---|
| `project.yml` — the brief and room model | `refs/` — the client's photographs |
| `brief/*.md` — the survey | `drawings/` — generated |
| `directions/*.json` — the authored specs | `renders/` — generated |
| `STATE.json` — the approval record | `report/` — generated |

Everything on the right is reproducible from everything on the left. Photographs of someone's home
are their property and stay out of version control.

To rebuild a job from a fresh clone: restore `refs/`, then

```bash
./bin/design drawings --shell
for d in projects/<slug>/directions/[0-9][0-9]-*.json; do
  ./bin/design drawings "$(basename "$d" .json)"
done
./bin/design render
./bin/design report
```

## Cost control

```yaml
render:
  backend: openrouter
  max_spend_usd: 15
```

The ceiling is enforced against the **real** per-image cost the API returns, not an estimate. The
run stops rather than overspending. Spend to date is in `./bin/design status` and itemised in
`projects/<slug>/renders/_cost.jsonl`.

Measured at **$0.183 per image** on `openai/gpt-image-2` over 29 billed renders.

The free codex backend yields roughly **45–50 images per quota window**, resetting in about 4–5
hours. Both shipped templates fit in one window:

| Job | Images | Codex | OpenRouter |
|---|---|---|---|
| `room` default, 6 × 3 | 18 | one session | ~$3.30 |
| `kitchen` default, 5 × 4 | 20 | one session | ~$3.66 |
| One direction, 6 views | 6 | one session | ~$1.10 |
| 20 × 6 | 120 | ~3 sessions | ~$22 |

`design render` and `design status` both print the forecast before you commit to anything.

The real cost trap is **re-rendering**. Getting the room model wrong and redoing 120 images is
another $22, which is exactly why the `pilot` gate makes you review one 6-image direction first.
