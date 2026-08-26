---
title: "Configuration reference — Roomsmith"
description: "Every project.yml option: room shapes, openings, camera views, deliverables, render backends and spend ceilings."
---

# project.yml

The only file you edit. Everything else is generated from it. `config/templates/room.yml` is the
annotated template; this is the reference.

## brief

| Key | Purpose |
|---|---|
| `what_it_is` | One or two sentences a stranger could understand the room from |
| `register` | The cultural and social register. Be specific — this is what stops renders drifting into generic hotel styling |
| `must_appear` | Things present in EVERY render, forever. Inherited furniture, religious objects, anything the household will not part with |
| `fixed_furniture_note` | An extra sentence pinned into every prompt about retained items |
| `problems` | `{id, text}`. Directions refer back to these ids |
| `constraints` | Hard limits no direction may break |

## room

| Key | Purpose |
|---|---|
| `shape` | `rectangle` · `rectangle_with_alcove` · `polygon`. Walls are generated as `w1, w2, …` anticlockwise |
| `walls` | Instead of `shape`, give explicit segments `{id, name, from, to, role}` for any shape |
| `wall_names` | Friendly names and roles keyed by wall id |
| `key_dimensions` | `{across, along}`. Use when an alcove or bay makes the bounding box overstate how wide the room feels |
| `openings` | `{tag, type, wall, pos, width, sill, head, desc, extra}`. `pos` is the centre, measured along that wall from its start. **Every opening must be listed** — renders are told anything absent does not exist |
| `features` | Vents, niches, radiators, columns — fixed things that are not openings |
| `shell_notes` | Sentences appended to the shell description in every prompt |
| `existing` | Current floor, ceiling, walls; optional `fan: {x, y, blade_span}` |
| `confirmed` | `false` until a tape has actually been on it |
| `notes` | Anything inferred and still to be verified |

Opening `type` affects how it is drawn: `door` and `doorway` get a swing, `arch` gets a
semicircular head, `window` gets a sill.

## deliverables

| Key | Purpose |
|---|---|
| `directions` | How many distinct directions |
| `aspect_ratio` | Render aspect, default `16:9` |
| `elevations` | Which wall ids get an elevation drawing |
| `iso_hide_walls` | Walls omitted from the dollhouse so you can see in |
| `views` | One render per direction each. See below |

Each view:

```yaml
- id: alcove
  caption: "The alcove bay"
  drawings: [elev-w4, plan]     # which measured drawing constrains this camera
  photos: [right-side.jpg]      # client photo nearest this standpoint
  from:    [2.40, 1.90]         # where the camera stands, in room coordinates
  look_at: [0.00, 1.90]         # what it points at
  camera: >
    CAMERA — ... describe the standpoint, lens, eye level and what must be in frame.
```

**`from` and `look_at` matter more than they look.** From them the engine generates an orientation
block naming which wall lands on the LEFT, the RIGHT, AHEAD and BEHIND for that specific frame, and
which openings can admit daylight in it. Without them the model has world coordinates and prose,
no way to convert one into the other, and will mirror the room roughly half the time and invent
daylight on a wall the model says is solid. This was observed, not theorised.

`drawings` matters more than it looks. A square-on view of one wall needs **that wall's
elevation** as its first reference, or the model defaults to a long axial view. Axial views take
`[plan, iso]`.

## style

`richness` — leave blank to use the built-in rules, which are what stop renders looking bare
(layered textiles, objects in use, planting, several lamps actually lit). Override only to change
the level of dressing.

## render

| Key | Purpose |
|---|---|
| `backend` | `codex` (free, quota-limited) or `openrouter` (paid) |
| `fallback` | Optional. Backend to degrade to when the primary runs out mid-run |
| `max_spend_usd` | Hard ceiling, enforced against the real per-image cost the API reports |

### How the backend is chosen

There is no automatic choice. Precedence, highest first:

1. `--backend openrouter` on the command line
2. `render.backend` in `project.yml`
3. `codex`

A paid backend is refused outright until the **`spend`** gate is approved. This is deliberate: a
tool that decides by itself to start spending money is one you cannot hand an API key to.

`design render` prints which backend it picked and why before it starts.

### Falling back

By default, running out of quota **stops** the run. Finished views are skipped on the next attempt,
so nothing is wasted. Two ways to keep going:

```bash
./bin/design render --wait          # sit out the reset, then continue on the same backend
```

```yaml
render:
  backend: codex          # start free
  fallback: openrouter    # switch to paid when the free quota runs out
  max_spend_usd: 15
```

A fallback is only ever used when **all** of these hold: you set `render.fallback` explicitly; the
`spend` gate is approved if it costs money; and the spend is under the ceiling. Otherwise the run
stops and tells you exactly which condition failed. Every switch is written to `STATE.json`.

Secrets live in `.env`, never here.
