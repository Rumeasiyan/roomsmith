---
title: "Workflow — Roomsmith"
description: "The full interior design job gate by gate: intake, survey, strategy, authoring, pilot pack, render, report."
---

# Workflow

A job runs through seven steps and six gates. The gates exist because the expensive and
hard-to-undo work comes late; each one is approved by the client, never by the agent.

```
 intake → survey → strategy → author → pilot pack → full render → report
    ↓        ↓         ↓                    ↓                        ↓
  brief  room-model direction-set         pilot                    report
```

## 0 · Scaffold

```bash
./bin/design init drawing-room --from room     # or --from kitchen
cp ~/photos/*.jpg projects/drawing-room/refs/
```

## 1 · Intake → gate `brief`

`design-intake` interviews you in small batches and writes `project.yml`.

The question that matters most: **is there anything in this room that cannot leave it?** Inherited
furniture, religious objects, a piano. Whatever you name goes into `must_appear` and is then pinned
into every render prompt and checked by the critic. It is the most under-asked question in interior
design and the one that most often invalidates finished work.

```bash
./bin/design approve brief --note "confirmed by client"
```

## 2 · Survey → gate `room-model`

`design-surveyor` reads every photograph, **counts the openings out loud**, and fills in `room:`.

A missed opening is invisible to every downstream check until a render looks wrong, so the count is
stated explicitly before anything else is written.

```bash
./bin/design drawings --shell     # then LOOK at the plan and elevations
./bin/design check
```

Drawings expose what prose hides: overlapping openings, an opening running off the end of a wall, a
proportion that is obviously wrong. Confirm anything inferred — especially which flank is which. A
mirrored model invalidates every later drawing and render.

```bash
./bin/design approve room-model --note "measured on site"
```

## 3 · Strategy → gate `direction-set`

`design-strategist` plans the whole set and proves each pair differs on four or more of the seven
axes, spread across budget tiers. Written to `brief/direction-set.md`.

## 4 · Author

`design-author`, one direction at a time, into `directions/NN-slug.json`. Run `./bin/design check`
after each: it catches furniture outside the room, collisions and empty justifications.

## 5 · Pilot pack → gate `pilot`

```bash
./bin/design pack 01
```

Builds ONE direction completely — measured drawings, then every camera view — then stops and prints
a QA checklist. Run `design-critic` on it.

**Fix every defect at the source**: the room model, the prompt builder, the camera config. Never by
re-touching a single image. A fix that does not carry forward will recur in every remaining
direction. This gate is the whole reason the pipeline is shaped this way.

```bash
./bin/design approve pilot
```

## 6 · Full render

```bash
./bin/design render                      # free backend
./bin/design render --backend openrouter # paid; requires the `spend` gate
```

Refuses to go past the first direction until `pilot` is approved. Stops cleanly on quota or on the
spend ceiling, and resumes by skipping finished views.

## 7 · Report → gate `report`

```bash
./bin/design report
```

`design-reporter` builds it and reads the PDF back, because layout errors are invisible in source
and obvious on the page.

## When something is wrong later

Change the source and regenerate. If a dimension turns out wrong:

```bash
$EDITOR projects/<slug>/project.yml
./bin/design check
./bin/design drawings 07
./bin/design render 07 --force
```

Revoke a gate if the basis for it changed:

```bash
./bin/design approve room-model --revoke
```
