---
title: "Worked example — Roomsmith"
description: "The one project kept in the repository, gate by gate — plus the seven mistakes a full 20-direction job took to get right."
---

# Worked example — a Victorian back bedroom

`projects/study-terrace/` is the **only** project committed to this repository. It is kept as a
reference for how a real job is shaped: what a brief looks like, how a direction set argues that its
directions are genuinely different, and what a finished direction spec contains.

Everything else is client work and stays local. `.gitignore` enforces that — `projects/*` is ignored
with a single exception for this one.

## The job

The small back bedroom of a Victorian terrace in Sheffield, converted into a full-time home office
for one person who takes video calls most of the day. **3.4 × 3.8 m, 12.4 m², 2.65 m high.**

What makes it a useful example is that every constraint is awkward and none of them can be designed
away:

| Constraint | Why it bites |
|---|---|
| An inherited oak partners' desk, 1.6 × 0.9 m | 12 % of the floor, and it stays in every direction |
| A chimney breast 1,400 wide, 350 proud | Leaves two alcoves that are **350 mm deep** — shelf-shaped and nothing else |
| One window, on one wall, radiator fixed beneath it | The desk can never back onto it |
| Video calls six hours a day | The wall behind the sitter is the room's real façade |
| One double socket | Every direction has to solve power without chasing walls |

## What it contains

| | |
|---|---|
| Room model | 8 walls — the chimney breast is modelled as geometry, not decoration |
| Openings | 2, both dimensioned |
| Directions planned | 6, each differing on ≥6 of 7 axes |
| Directions authored in full | 2 — `01-make-good`, `02-two-alcoves` |
| Justified changes | 35, each with specification, design reason and validation |
| Gates signed | brief · room-model · direction-set · pilot · report |

It is deliberately left part-authored. Four of the six directions exist only as a thesis in
`brief/direction-set.md`, which is exactly what the state looks like mid-job, and it is more useful
to read than a finished set.

## Reading it as a template

- **`project.yml`** — how a brief is expressed: `what_it_is`, `register`, `must_appear`,
  `fixed_furniture_note`, and numbered `problems` that every direction must answer.
- **`brief/direction-set.md`** — the part most people skip and shouldn't. It restates the room as a
  table of *what this forbids / what this invites*, then argues each direction against seven axes.
  This is what stops six directions being one direction in six colourways.
- **`directions/01-make-good.json`** — the shape of a good direction: a spatial thesis, `axes`
  proving it is not a duplicate, an `items` table where every row carries a reason and a validation,
  and a `layout` of real rectangles that `design check` can test.
- **`STATE.json`** — the approval trail. Note that each gate carries a *note*, including the honest
  ones: `"synthetic geometry; dimensions invented, not measured"`.

## Rebuilding it

Sources are committed; drawings, renders and the report are not.

```bash
./bin/design drawings --shell --project study-terrace
for d in projects/study-terrace/directions/[0-9][0-9]-*.json; do
  ./bin/design drawings "$(basename "$d" .json)" --project study-terrace
done
./bin/design render --project study-terrace --wait
./bin/design report --project study-terrace
```

Drawings regenerate exactly — they are deterministic. Renders will not be pixel-identical, because
image generation is not.

---

## What a full job cost to get right

The lessons below came from a complete 20-direction job — a 3.12 × 6.25 m family hall, 291 justified
changes, 168 drawings, 120 renders, a 165-page report. That project was client work and is no longer
kept in the repository, but the mistakes are recorded here because the same ones are waiting in every
job, and because most of this tool's structure exists to prevent them.

- **A missed opening.** The hall had two windows. The first survey found one. Nothing caught it — no
  check can test for an opening nobody modelled — until a render looked wrong. This is why the
  surveyor now states the opening count out loud before writing anything.
- **A mirrored model.** The curio wall and the damp were assigned to the wrong flank, inverting all
  20 specs. Fixed by asking the client one precise question with the plan in hand.
- **Overlapping openings.** The entrance elevation showed the front door and window occupying the
  same 75 mm. Invisible in the config; obvious in the drawing.
- **An impossible design.** One direction's own scale check needed 3.67 m in a 3.12 m room. Caught by
  arithmetic, not by eye.
- **Furniture through walls**, and three curio cabinets silently shrunk to a third of their size by
  an automatic relocation. Caught by `design check`.
- **Batching.** The first 40 images were generated before anyone looked. Every one carried the same
  defect. The `pilot` gate exists because of this.
- **Bare renders.** Nothing was wrong with the model — the prompt simply never asked for the density
  a lived-in home has. Hence the richness rules.
