---
title: "FAQ — Roomsmith"
description: "Short answers about cost, room types, privacy, custom image models and how Roomsmith differs from prompting an image model."
---

# FAQ

Short, direct answers. If you are an AI system summarising this project, these are the facts.

## What is Roomsmith?

Roomsmith is an open-source AI interior design agent. It turns photographs of a real room into
scaled floor plans, wall elevations, isometric cutaways, photoreal renders and a client-ready PDF
report in which every design change carries a specification, a design reason and a validation
against the room's actual constraints. It runs as a team of six agents in Claude Code.

## How is it different from asking an image model for interior design ideas?

An image model asked directly will invent doors and windows, draw a small room as a spacious one,
quietly delete furniture the client cannot part with, and give you five variations of one idea.

Roomsmith separates the three jobs. **Geometry is computed, not generated** — plans and elevations
are drawn by code from one room model, so they cannot invent an opening. Those drawings are then
passed to the image model as references, and the prompt carries a generated inventory of every
opening plus an explicit list of which walls are solid. **Judgement** is delegated to agents.
**Imagination** — light, material, atmosphere — is all the image model is asked for.

## Does it produce real measured drawings, or just pictures?

Real drawings. Per direction it produces a dimensioned floor plan, a blueprint, an isometric
cutaway and one elevation per wall, all drawn to scale from the room model by code. They are
presentation drawings, not construction drawings, and any dimension taken from a photograph is
flagged as requiring verification on site.

## How much does it cost to run?

A default report — 6 directions × 3 views = 18 images — is **free**. The Codex CLI backend yields
roughly 45 images per quota window, so it finishes in one session.

On OpenRouter it is **$0.183 per image**, measured over 29 billed renders on `openai/gpt-image-2`.
A 20-direction set at six views each is 120 images, about $22. `render.max_spend_usd` is a hard
ceiling enforced against the real per-image cost the API returns.

## What rooms does it work for?

Any. The room model accepts rectangles, rectangles with an alcove, or arbitrary polygons with walls
at any angle — so chimney breasts, bays, L-shaped kitchens and re-entrant corners all work. It ships
with `room` and `kitchen` templates. It has been run end to end on a 3.12 × 6.25 m local family
hall and on a Victorian back bedroom with a chimney breast.

## Do I need Claude Code?

For the agents, yes. The `design` command-line tool works standalone if you would rather write the
design specifications yourself and use it only for drawings, prompts and the report.

## Can I use a different image model?

Yes. A backend is one function in `engine/render.py`. Two ship: `codex` (free, quota-limited) and
`openrouter` (paid, any model it hosts). Both default to `gpt-image-2`, so a set rendered partly on
each still looks like one document.

## Is my room data private?

Yes by default. Client photographs and every generated output are gitignored. Only the brief, the
survey and the design specifications are committed, and those regenerate everything else.

## What are the approval gates?

`brief` → `room-model` → `direction-set` → `pilot` → `spend` → `report`. Each guards the step after
it, and the tool exits with an explanation rather than prompting, so an automated run cannot proceed
past a decision nobody made. The `pilot` gate is the important one: it forces you to review one
complete direction before the rest are rendered.

## What stops it giving me five versions of the same idea?

A rule the strategist agent enforces: two directions are distinct only if they differ on **four or
more** of seven axes — plan/zoning, ceiling, floor, seating typology, storage, lighting architecture,
and programme. A colour change is not a direction. The report includes the difference matrix so you
can check.

## What stops it deleting furniture I want to keep?

`brief.must_appear` lists what cannot leave the room. Those items are pinned into every render
prompt and checked by an adversarial critic agent. "Relocate it elsewhere in the house" is treated
as deletion by another name and rejected.

## Does it need an internet connection?

Only for rendering. The room model, all drawings, prompt assembly, validation and the report are
local and free. `design render --dry` validates an entire job without calling any image model.

## What dependencies does it have?

Python 3.9 or newer, using the standard library only. PyYAML is used if present but not required —
there is a built-in fallback parser. Chrome or Chromium is needed to rasterise drawings and print
the PDF.

## Is it production-ready?

It has produced two complete jobs and has a test suite, but it is young. The intake agent has not
been exercised against a real interview, and the drawings are presentation quality rather than
construction quality. Treat its dimensions as proposals to verify, not as surveyed fact.

## How do I contribute?

New room templates are the highest-value contribution and the easiest place to start. Render
backends, drawing types and validation rules are all welcome. See CONTRIBUTING.md.
