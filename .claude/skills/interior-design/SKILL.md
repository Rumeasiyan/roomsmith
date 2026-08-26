---
name: interior-design
description: Run a complete interior design job for a real room - interview the client, survey the room, plan and author distinct design directions, produce measured drawings and photoreal renders, and compile a client report. Use whenever someone wants a room designed, redesigned, rendered, or wants design options or a design report. Triggers - "design my room", "redesign", "interior design", "design directions", "room concepts", "render my space", "design report".
---

# Interior Design

Orchestrates a team of agents through a gated pipeline. You are the conductor: you decide who runs
next, you never skip a gate, and you stop and ask rather than guess.

## The pipeline

```
 intake  →  survey  →  strategy  →  author  →  pilot pack  →  full render  →  report
    ↓         ↓           ↓                        ↓                            ↓
  GATE     GATE        GATE                      GATE                         GATE
  brief  room-model  direction-set              pilot                        report
```

Each gate is approved by the **client**, never by you:

```bash
./bin/design status                 # where the job is, what is approved, what is left
./bin/design approve <gate> --note "..."
```

## Steps

**0. Set the job up.** `./bin/design init <slug>` scaffolds `projects/<slug>/`. Put the client's
photographs and any dimension sketch in `projects/<slug>/refs/`.

**1. Intake** — spawn `design-intake`. It interviews the client in small batches and writes
`project.yml`. Ask the client to confirm the brief back. → gate `brief`

**2. Survey** — spawn `design-surveyor`. It reads every photograph, counts the openings out loud,
builds the room model, writes the survey and generates the shell drawings. Show the client the
plan and ask them to confirm anything inferred, especially which flank is which. → gate `room-model`

**3. Strategy** — spawn `design-strategist`. It plans the whole set of directions and proves they
differ on four or more of the seven axes, spread across budget tiers. → gate `direction-set`

**4. Author** — spawn `design-author` per direction. Run `./bin/design check` after each.

**5. Pilot pack** — `./bin/design pack 01` builds ONE direction completely: measured drawings, then
every camera view, then stops and prints a QA checklist. Spawn `design-critic` on it. Fix every
defect **at the source** — the room model, the prompt builder, the camera config — never by
re-touching a single image. → gate `pilot`

**6. Full render** — `./bin/design render` does the rest. It refuses to run beyond the first
direction until `pilot` is approved, and refuses a paid backend until `spend` is approved. It stops
cleanly on a quota or a spend ceiling and resumes by skipping finished views.

**7. Report** — spawn `design-reporter`. → gate `report`

## The rules that make this work

- **One direction at a time, until the pilot passes.** Batch generation hides a defect in image one
  and then reproduces it a hundred times. That is the most expensive available mistake and it is
  entirely avoidable.
- **Fix at the source.** Every correction must land in the room model or shared code so it carries
  into every later direction.
- **The drawings are authoritative, not the renders.** Plans, elevations and isometrics are drawn
  from the room model by code and cannot invent geometry. They are handed to the renderer as
  references, which is what keeps the images honest.
- **Count the openings before trusting anything.** A missed opening is invisible to every check
  until a render looks wrong.
- **Retained items stay in the room.** Never design away what the household will not give up, and
  never "relocate it elsewhere".
- **Prove the scale.** Every spec carries `scale_check`, with the arithmetic done.
- **Never spend without an approved ceiling.** `render.max_spend_usd` is enforced against the real
  per-image cost the API reports.
- **Report faithfully.** Missing views are stated, not hidden. Inferred dimensions are never
  presented as measured.

## Reference

`docs/WORKFLOW.md` for the full walkthrough, `config/templates/room.yml` for every config option,
`projects/study-terrace/` for a worked job to copy the file shapes from.
