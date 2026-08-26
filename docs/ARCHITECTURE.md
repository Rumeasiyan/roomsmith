# Architecture

## One source of truth

```
project.yml
   │
   ├── engine/room.py ──── Room: walls, openings, features
   │        │
   │        ├── engine/drawings.py ── plan · blueprint · elevations · isometric
   │        │                              │
   │        │                              └── passed to the renderer as references
   │        ├── engine/prompts.py ──── opening inventory · solid-wall clause · scale rules
   │        └── engine/report.py ───── the deliverable
   │
   └── engine/render.py ── codex | openrouter
```

A dimension is written down **once**. Change `project.yml` and every drawing, prompt and figure
regenerates. There is no second place where the room's size lives.

## Why the drawings are authoritative

An image model cannot be trusted with geometry — it will helpfully add a window. So geometry never
comes from it:

1. Plans, elevations and the isometric are **drawn by code** from the room model.
2. Those drawings are handed to the image model as reference images.
3. The prompt states the opening inventory and which walls are solid, both **generated** from the
   same model.

The image model is left to do what it is good at — light, material, atmosphere — and is given no
latitude on what the room *is*.

The `drawings` field on each view decides which drawing constrains that camera. A square-on view of
one wall must get **that wall's elevation** first, or the model reverts to a long axial view. This
was learned the hard way.

## Elevations derive from the plan

`Room.nearest_wall()` projects each furniture rectangle onto the nearest wall segment, at any
angle. So an elevation is computed from the same layout as the plan and the two cannot disagree —
there is no second list to keep in sync.

## Room shapes

`shape` supports `rectangle`, `rectangle_with_alcove` and arbitrary `polygon`; walls are generated
anticlockwise as `w1, w2, …`. Or declare `walls` explicitly for any shape at all. Openings are
positioned **along the wall they belong to**, measured from that wall's start, so they stay correct
whatever the shape.

`key_dimensions` exists because a bounding box lies about a room with an alcove: a 3.12 m hall with
a 0.75 m bay has a 3.87 m bbox, and describing it that way to a renderer produces a room that is
too wide.

## Validation

`design check` is an independent auditor, not a formatter. It finds:

- openings running past the end of their wall, or overlapping each other
- openings taller than the ceiling
- furniture outside the room
- furniture colliding with other furniture
- specs missing a thesis, items or a scale check
- items with an empty justification

Run it constantly. It has caught real errors in real work — including a design whose own arithmetic
was impossible.

## Gates

`STATE.json` records approvals. `Project.require(gate)` exits with an explanation rather than
prompting, so an automated run cannot proceed past a decision nobody made. Gates are revocable when
the basis for one changes.

## Backends

Both take the same prompt and the same references. `codex` shells out to the codex CLI's
`image_gen`; `openrouter` posts to its image API. Both default to **gpt-image-2**, so a set
rendered partly on each is still visually one document. Both stop cleanly on quota or on the spend
ceiling and resume by skipping finished views.

## Who does what

| Layer | Runs | Does |
|---|---|---|
| Agents | Claude Code | Interviews, surveys, authors specs, critiques renders, writes the report |
| `design` CLI | Python, locally | Room model, scaled drawings, prompt assembly, report build. **No AI** |
| Image backend | Codex CLI or OpenRouter | Photoreal renders only |

The separation is the point. Anything that must be *correct* — dimensions, openings, layouts,
arithmetic — is computed. Anything that benefits from *judgement* — the brief, the design, the
critique — is an agent. Anything that needs *imagination* — light, material, atmosphere — is the
image model, and it is given no say in the geometry.

## Testing

`tests/run.sh` is the whole suite: engine imports, unit tests, the example project, both templates
and drawing rasterisation. It needs no network, no key and no browser beyond the one already
required.

There is deliberately **no CI**. The suite runs in seconds locally, and a failing build emailing
the maintainer on every push is noise for a project this size.

## Dependencies

Python 3 standard library only. PyYAML is used if installed; otherwise a small YAML parser in
`engine/project.py` handles the project file. Chrome or Chromium rasterises SVG and prints the PDF.
