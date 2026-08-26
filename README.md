# Interior Design Agent

A reusable, agent-driven interior design studio. Point it at a room, answer some questions, and it
produces measured drawings, photoreal renders and a client report where **every change is
justified** — with approval gates so nothing expensive or irreversible happens without a decision.

It is generic: any room type, any shape, any country, any brief. The worked example in
`projects/compact-hall/` is a 20-direction job for a 3.12 × 6.25 m family hall —
**291 justified changes, 168 measured drawings, 120 renders, a 165-page report**.

---

## Quick start

```bash
./bin/design init my-room             # scaffold projects/my-room/
cp ~/photos/*.jpg projects/my-room/refs/
```

Then in Claude Code:

```
/interior-design
```

The orchestrator interviews you, surveys the room, plans the directions, and walks the gates.
Or drive it yourself:

```bash
./bin/design status                   # where the job is
./bin/design check                    # validate config, geometry, layouts
./bin/design drawings --shell         # measured drawings of the empty room
./bin/design pack 01                  # ONE direction: drawings + all views, then stop
./bin/design approve pilot            # unlock the rest
./bin/design render                   # everything remaining
./bin/design report                   # the PDF
```

## Why it produces usable work

**Geometry cannot drift.** The room lives in one config block. Plans, blueprints, elevations and
the isometric are *drawn by code* from it, so they cannot invent a door or enlarge a room. Those
drawings are then handed to the image model as references, which is what keeps the renders honest.

**Renders cannot invent openings.** The prompt's opening inventory and its "these walls are solid"
clause are generated from the model. If it is not in the model, the render is told it does not exist.

**Scale is proved, not hoped for.** Every direction carries a `scale_check` with the arithmetic
done across the room's narrow dimension. `design check` independently verifies that no furniture
falls outside the room or collides.

**Directions are genuinely different.** Two count as distinct only if they differ on four or more
of: plan/zoning, ceiling, floor, seating typology, storage, lighting architecture, programme. A
paint change is not a direction.

**What the client refuses to lose, stays.** `must_appear` items are pinned into every prompt and
checked by the critic. "Relocate it elsewhere" is deletion by another name.

**One direction at a time.** The pilot pack is built and reviewed before the rest run. Batch
generation hides a defect in image one and reproduces it a hundred times.

## The agents

| Agent | Does |
|---|---|
| `design-intake` | Interviews the client, resolves ambiguity, writes `project.yml` |
| `design-surveyor` | Reads the photographs, builds the room model, writes the survey |
| `design-strategist` | Plans the direction set and proves they differ |
| `design-author` | Writes one direction: thesis, justified changes, measured layout |
| `design-critic` | Adversarially reviews a rendered pack; reports root causes |
| `design-reporter` | Compiles the report and reads it back |

## Approval gates

Nothing expensive happens without a decision. The tool refuses rather than asking twice.

| Gate | Guards |
|---|---|
| `brief` | writing the room model |
| `room-model` | generating drawings and any renders |
| `direction-set` | authoring the full specs |
| `pilot` | rendering beyond the first direction |
| `spend` | using a paid render backend |
| `report` | marking the job delivered |

```bash
./bin/design approve room-model --note "measured on site 2026-08-26"
./bin/design approve room-model --revoke
```

## Layout

```
bin/design                  the CLI
engine/                     room model · drawings · prompts · render backends · report
config/templates/           project templates (room, kitchen) + direction schema
projects/<slug>/
  project.yml               THE file you edit
  STATE.json                approvals and history, written by the tool
  refs/ brief/ directions/ drawings/ renders/ report/
.claude/agents/             the six agents
.claude/skills/             the orchestrator
docs/                       SETUP.md · WORKFLOW.md · CONFIG.md
```

## Rendering

Two interchangeable backends, same prompts and reference drawings:

| Backend | Cost | Notes |
|---|---|---|
| `codex` | free | via the codex CLI's `image_gen` (gpt-image-2). Quota-limited |
| `openrouter` | ~$0.18/image | `openai/gpt-image-2` by default — the same model, so the set stays visually consistent |

```bash
cp .env.example .env        # then set OPENROUTER_API_KEY
./bin/design render --backend openrouter
```

`render.max_spend_usd` is a hard ceiling enforced against the real per-image cost the API reports.
Both backends stop cleanly on quota or ceiling and resume by skipping finished views.

## Requirements

Python 3 (no required third-party packages; PyYAML used if present), Chrome or Chromium for
rasterising drawings and printing the PDF, and at least one render backend.

## Docs

- `docs/SETUP.md` — install and first run
- `docs/WORKFLOW.md` — the full job, gate by gate
- `docs/CONFIG.md` — every `project.yml` option
