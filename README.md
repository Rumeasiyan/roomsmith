<div align="center">

# Roomsmith

**The open-source AI interior design agent.**
Photographs of a room go in. Measured drawings, photoreal renders and a design report where every
single change is justified come out.

[![License: MIT](https://img.shields.io/badge/License-MIT-black.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-black.svg)](https://www.python.org/)
[![No dependencies](https://img.shields.io/badge/dependencies-none-black.svg)](#requirements)
[![PRs welcome](https://img.shields.io/badge/PRs-welcome-black.svg)](CONTRIBUTING.md)

</div>

---

Roomsmith is an **AI interior design tool** that runs as a team of agents in
[Claude Code](https://claude.com/claude-code). Give it photos of a real room and it interviews you,
surveys the space, produces scaled floor plans and wall elevations, generates photoreal renders,
and writes a client-ready PDF report — with approval gates so nothing expensive happens without
your say-so.

It is not a mood-board generator. Every design direction is a **spatial thesis** with a measured
layout, and every change carries a specification, a reason, and a validation against the room's
real constraints.

```bash
./bin/design init my-room
cp ~/photos/*.jpg projects/my-room/refs/
```
then in Claude Code:
```
/interior-design
```

## What it produces

For each design direction:

| Output | What |
|---|---|
| **Floor plan** | Scaled, dimensioned, with furniture and the circulation route |
| **Blueprint** | The same plan in drafting style |
| **Wall elevations** | One per wall, square-on, with every opening dimensioned |
| **Isometric** | A dollhouse cutaway |
| **Photoreal renders** | One per camera view — hero, reverse, seated eye-level, corner overview… |
| **Justified changes** | Every item: specification, design reason, and validation |

Plus one PDF report containing all of it, a site survey, and a comparison matrix proving the
directions genuinely differ.

## Why not just prompt an image model?

Because it will draw you a room you cannot build.

| Problem | What Roomsmith does |
|---|---|
| Invents doors and windows that don't exist | The opening inventory and a "these walls are solid" clause are **generated from the room model** and pinned into every prompt |
| Draws a small room as a spacious one | Scaled drawings are passed in as references; every direction carries arithmetic proving the layout fits |
| Silently deletes furniture you can't part with | `must_appear` items are pinned into every prompt and checked by an adversarial critic |
| Gives you five variations of one idea | Two directions count as distinct only if they differ on **4+ of 7 axes** |
| Looks like a hotel lobby | The cultural register is part of the brief, not an afterthought |
| Costs a fortune before you notice it's wrong | One direction is built and reviewed before the rest run; spend ceilings are enforced against real API costs |

**Geometry never comes from the image model.** Plans, elevations and isometrics are *drawn by code*
from a single room model, then handed to the renderer as references. The image model does light,
material and atmosphere — it gets no say in what the room is.

## How the pieces fit

```
  Claude Code  ──  the six agents: interview, survey, strategise, author, critique, report
       │
       ├── design CLI (Python) ── room model · scaled drawings · prompts · report   ← no AI at all
       │
       └── image backend ─── codex CLI  (free, quota-limited)   ┐ both default to
                          └─ OpenRouter (paid, ~$0.18/image)    ┘ the same model
```

Claude does the **design thinking** — reading your photographs, writing the specifications, and
reviewing the results. It does not draw the plans and it does not generate the images. Geometry is
computed; images come from a dedicated image model through whichever backend you choose.

## The agents

| Agent | Job |
|---|---|
| `design-intake` | Interviews you. Asks the question most designers forget: *is there anything here that cannot leave?* |
| `design-surveyor` | Reads every photo, counts the openings out loud, builds the measured room model |
| `design-strategist` | Plans the direction set and proves each one is genuinely different |
| `design-author` | Writes one direction: thesis, measured layout, every change justified |
| `design-critic` | Read-only by design, so it reports **root causes** instead of patching one image |
| `design-reporter` | Compiles the report and reads the PDF back to catch layout errors |

## Approval gates

Nothing expensive or irreversible happens without a decision. The tool refuses rather than asking twice.

`brief` → `room-model` → `direction-set` → `pilot` → `spend` → `report`

```bash
./bin/design status
./bin/design approve room-model --note "measured on site"
```

## Worked example

`projects/compact-hall/` is a real completed job — a 3.12 × 6.25 m family hall:

**20 design directions · 291 justified changes · 168 measured drawings · 120 renders · 165-page report · $5.30 in render costs**

[`docs/EXAMPLE.md`](docs/EXAMPLE.md) documents the seven mistakes it took to get right — a missed
window, a mirrored floor plan, a design whose own arithmetic was impossible — and how each one is
now prevented structurally.

## FAQ

<details>
<summary><b>What do I need to run it?</b></summary>

Python 3.9+ (no third-party packages), Chrome or Chromium, and one render backend. That's it.
</details>

<details>
<summary><b>How much does it cost?</b></summary>

**A default report is free.** The `room` template is 6 directions × 3 views = 18 images, and a free
codex quota window fits about 45 — so it completes in one session with room to spare.

Beyond that, on OpenRouter it's **$0.183 per image**, measured over 29 billed renders:

| Job | Images | Free backend | Paid |
|---|---|---|---|
| Default report (6 × 3) | 18 | one session | ~$3.30 |
| One direction (6 views) | 6 | one session | ~$1.10 |
| Large set (20 × 6) | 120 | ~3 sessions, with pauses | ~$22 |

`design render` tells you which of these you're in for before it starts. `render.max_spend_usd` is
a hard ceiling enforced against the real per-image cost the API returns.
</details>

<details>
<summary><b>Will it finish in one free session?</b></summary>

A codex quota window yields roughly 45–50 images before the limit, then resets in about 4–5 hours.
Both shipped templates (18 and 20 images) fit inside one window. Anything above ~45 images will
pause; `./bin/design render --wait` sits out the reset and continues automatically, and finished
views are always skipped so nothing is rendered twice.
</details>

<details>
<summary><b>Does it work for kitchens / bedrooms / offices / L-shaped rooms?</b></summary>

Yes. The room model takes rectangles, rectangles with alcoves, or arbitrary polygons with walls at
any angle. Ships with `room` and `kitchen` templates; adding more is the easiest useful contribution.
</details>

<details>
<summary><b>Can I use my own image model?</b></summary>

Yes. A backend is one function in `engine/render.py`. Two ship: `codex` (free, via the Codex CLI's
built-in image generation) and `openrouter` (paid, any model it hosts). Both default to the same
model so a set rendered partly on each still looks like one document.
</details>

<details>
<summary><b>Is my room data private?</b></summary>

Client photographs and all generated output are gitignored by default. Only the brief, survey and
design specs are committed — they regenerate everything else.
</details>

<details>
<summary><b>Do I need Claude Code?</b></summary>

For the agents, yes. The `design` CLI works standalone if you'd rather write the specs yourself.
</details>

## Documentation

| | |
|---|---|
| [SETUP](docs/SETUP.md) | Install and first run |
| [USAGE](docs/USAGE.md) | Commands and recipes |
| [WORKFLOW](docs/WORKFLOW.md) | The full job, gate by gate |
| [CONFIG](docs/CONFIG.md) | Every `project.yml` option |
| [AGENTS](docs/AGENTS.md) | The team, handoffs, customising |
| [ARCHITECTURE](docs/ARCHITECTURE.md) | How it works and why |
| [TROUBLESHOOTING](docs/TROUBLESHOOTING.md) | When something goes wrong |
| [EXAMPLE](docs/EXAMPLE.md) | The worked 20-direction job |

## Requirements

Python 3.9+ · Chrome or Chromium · one render backend
([Codex CLI](https://github.com/openai/codex) free, or an [OpenRouter](https://openrouter.ai) key)

## Contributing

New room templates, render backends, drawing types and validation rules are all welcome —
see [CONTRIBUTING.md](CONTRIBUTING.md).

## Licence

MIT — see [LICENSE](LICENSE).

---

<div align="center">
<sub>Roomsmith · AI interior design agent · floor plans, elevations, renders and a justified design report from room photographs</sub>
</div>
