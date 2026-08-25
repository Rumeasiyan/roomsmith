---
name: interior-design
description: Produce a full set of distinct interior design directions for a real room from photographs and dimensions - survey, spec, photoreal renders via codex image_gen, and a validated PDF report. Use when the user asks to redesign a room, wants multiple design directions or concepts, wants renders of their space, or wants a design report. Triggers - "interior design", "redesign my hall/room", "design directions", "room concepts", "render my room".
---

# Interior Design Direction Set

Turns owner photographs into a contractor-grade set of design directions with renders and
a justified PDF report.

## When to use

Any request of the form "here are photos of my room, design it", "give me N design
directions", "render my living room", "make me a design report".

## Prerequisites

| Requirement | Check |
|---|---|
| `codex` CLI with the `image_gen` tool | `codex --version` — image generation is used through `codex exec` |
| Chrome / Chromium for PDF printing | `command -v google-chrome \|\| command -v chromium` |
| Python 3 | `python3 --version` |

If `codex` is missing, stop and say so — renders are not optional to the deliverable.

## Layout

```
refs/                     owner photographs + dimension sketch (inputs)
brief/site-survey.md      surveyed ground truth; every direction obeys it
directions/_schema.json   the shape of a direction spec
directions/NN-slug.json   one authored spec per direction
scripts/build_prompts.py  spec -> render prompt (single source of truth)
scripts/render.sh         one render via codex exec
scripts/render_all.sh     all renders, parallel, resumable
scripts/build_report.py   spec + renders -> HTML -> PDF
renders/                  generated images
report/                   report.html, report.pdf
```

## Procedure

1. **Survey.** Read every file in `refs/` with the Read tool — actually look at them. Write
   `brief/site-survey.md`: geometry table, openings table, existing fabric, contents and
   their verdicts, observed use patterns, numbered problem list (P1, P2 …), non-negotiable
   constraints, budget tiers. Mark inferred numbers as inferred.

2. **Plan the direction set.** Before writing any spec, list all N theses in one place and
   check the difference rule: two directions are distinct only if they differ on **four or
   more** of {plan/zoning, ceiling, floor, seating typology, storage, lighting architecture,
   programme}. Kill and replace any near-duplicate. Spread the set across budget tiers A/B/C
   and across cultural registers, so the client is choosing between real alternatives.

3. **Write the specs.** One `directions/NN-slug.json` each, to `_schema.json`. The `items`
   array is the heart of the deliverable: every physical change gets `change`, `reason` and
   `validation`, where validation cites this room's constraints — climate, proportion,
   circulation, damp, devotional objects, budget. Also fill `risks` and `not_for`.

4. **Build one pack at a time.** `scripts/make_pack.sh <NN-slug>` produces the seven measured
   drawings and the six photoreal views for ONE direction, then stops. Inspect every image against
   the QA checklist it prints. Fix defects in `brief/room.json`, `scripts/drawings.py` or
   `scripts/build_prompts.py` so the correction carries into every later direction, then move on.
   Do not start the next direction until the current one passes.

   Common failures, all of which must be fixed at the source: an invented door or window; a wall
   that should be solid showing daylight; the room drawn wider than it is; furniture missing;
   views that disagree with each other; **a MISSED opening** - re-read every photograph and count the
   windows before trusting the model, because an opening you never modelled is invisible until a
   render looks wrong; and images that read **bare** - a real home has layered textiles, objects in
   use, plants, a full display cabinet and three or four lamps actually switched on. Bareness is a
   prompt failure, not a style.

5. **Render (batch, only once every spec is settled).** `scripts/render_all.sh` — two views per direction, each anchored to a real
   reference photograph so the client compares like with like. Resumable: existing outputs
   are skipped, so a failed run is re-run, not restarted.

5. **Report.** `scripts/build_report.py` then Chrome headless → `report/report.pdf`.
   Contents: survey, problem list, constraints, comparison matrix, then one full spread per
   direction (renders, thesis, story, per-item justification table, palette, materials,
   risks, cost tier).

## Rules that make the output good

- **Spec first, image second.** The render illustrates a written specification. Never the
  reverse.
- **No cosmetic directions.** If the difference between two directions could be achieved
  with a paint tin and new cushions, they are the same direction.
- **Honour what the household holds sacred.** Devotional objects, heirlooms and inherited
  furniture are design anchors, not obstacles. Say in each direction how they are handled.
- **Inherited furniture stays in the room.** Strip it, re-polish it, cut it down,
  re-upholster it, re-position it — but never design it out, and never "relocate it
  elsewhere in the house", which is deletion by another name. Fill `teak_treatment` (or the
  equivalent) in every spec. A direction that needs the family's furniture gone is not
  finished.
- **Prove the scale.** Every spec carries `scale_check`: the widths added across the narrow
  dimension and the clear circulation lane that survives. Push the same discipline into the
  render prompt — small rooms are drawn spacious by default, and a render wider than the
  client's actual house is worthless. Say the width in metres, say the furniture nearly
  touches the walls, and explicitly rule out the gallery / loft / lobby / showroom look.
- **Keep the regional and domestic register.** Design the room the household actually lives
  in — shoes at the door, a shrine in use, photographs on the wall, a fan turning, a
  through-route to the rest of the house.
- **Design for the climate you are in.** Tropical, humid, non-air-conditioned rooms rule
  out wall-to-wall carpet, sealed joinery on damp walls and blocked ventilation openings.
- **Repair before finish.** Never specify a finish over an unrepaired defect; call out the
  substrate work first.
- **State the downside.** Every direction lists its risks and who it is wrong for.

## Reuse on a new room

1. `refs/` ← new photographs and dimension sketch. Clear `directions/`, `renders/`, `report/`.
2. Re-run the procedure from step 1. The scripts are project-agnostic and read only the
   JSON specs and `refs/`.
3. `scripts/render.sh` takes `REF_A` / `REF_B` overrides if the new room's camera anchors
   have different filenames.
