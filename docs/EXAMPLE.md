# Worked example — a compact family hall

`projects/compact-hall/` is a complete job, kept in the repo as a reference for how a real one
looks. Its sources are committed; its inputs and outputs are not (see below).

## The job

The front hall of a modest suburban family house. **3.12 × 6.25 m** — a 2:1 tunnel with
a 0.75 m alcove, five openings, no mechanical cooling, damp on one long wall, and a household that
would not part with its inherited carved teak furniture or its shrine.

## What it produced

| | |
|---|---|
| Design directions | 20, each differing on ≥4 of 7 axes, across budget tiers A/B/C |
| Justified changes | **291** — each with specification, design reason and validation |
| Measured drawings | 168 — 8 per direction |
| Photoreal views | 120 — 6 per direction, covering all four walls |
| Report | 165 pages |
| Render cost | $5.30 of 120 images; the rest on the free backend |

## What it cost to get right

Kept here because the same mistakes are waiting in every job:

- **A missed opening.** The hall has two windows. The first survey found one. Nothing caught it —
  no check can test for an opening nobody modelled — until a render looked wrong. This is why the
  surveyor now states the opening count out loud before writing anything.
- **A mirrored model.** The curio wall and the damp were assigned to the wrong flank, inverting all
  20 specs. Fixed by asking the client one precise question with the plan in hand.
- **Overlapping openings.** The entrance elevation showed the front door and window occupying the
  same 75 mm. Invisible in the config; obvious in the drawing.
- **An impossible design.** One direction's own scale check needed 3.67 m in a 3.12 m room. Caught
  by arithmetic, not by eye.
- **Furniture through walls**, and three curio cabinets silently shrunk to a third of their size by
  an automatic relocation. Caught by `design check`.
- **Batching.** The first 40 images were generated before anyone looked. Every one carried the same
  defect. The `pilot` gate exists because of this.
- **Bare renders.** Nothing was wrong with the model — the prompt simply never asked for the
  density a lived-in home has. Hence the richness rules.

## Rebuilding it

Sources are committed; images are not. To regenerate, restore the client photographs to
`projects/compact-hall/refs/` (`entrance.jpg`, `from-entrance.jpg`, `left-side-of-entrance.jpg`,
`right-side-of-entrance.jpg`, `hall-dimensions.jpg`) and:

```bash
./bin/design drawings --shell --project compact-hall
for d in projects/compact-hall/directions/[0-9][0-9]-*.json; do
  ./bin/design drawings "$(basename "$d" .json)" --project compact-hall
done
./bin/design render --project compact-hall --wait
./bin/design report --project compact-hall
```

Drawings regenerate exactly — they are deterministic. Renders will not be pixel-identical, since
image generation is not.

## Reading it as a template

- `project.json` — how a real brief, room model and view set are expressed. Note `key_dimensions`,
  the per-view `drawings` anchors, and `must_appear`.
- `directions/01-*.json` — the shape of a good direction: a spatial thesis, `axes` proving it is
  not a duplicate, an `items` table where every row is validated, and a `layout` of real rectangles.
- `brief/site-survey.md` — a survey that records what was *observed* and marks what was *inferred*.
