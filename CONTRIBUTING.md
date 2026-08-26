# Contributing to Roomsmith

Thanks for considering it. This project is opinionated about a few things, and knowing which
will save you time.

## The opinions

These are load-bearing. A change that breaks one of them will be asked to change.

1. **Geometry is never produced by an image model.** Plans, elevations and isometrics are drawn by
   code from the room model. Image models add doors that do not exist.
2. **A dimension is written down once.** If you find yourself typing a room's size in a second
   place, that is the bug.
3. **The critic is read-only.** The moment it can edit, it fixes symptoms instead of causes.
4. **Gates refuse; they do not prompt.** An automated run must not be able to proceed past a
   decision nobody made.
5. **Outputs are not committed.** Anything in `drawings/`, `renders/`, `report/` or `prompts/` is
   reproducible and stays out of git. So do client photographs.

## Setting up

```bash
git clone https://github.com/Rumeasiyan/roomsmith
cd roomsmith
./bin/design init test-room
./bin/design check --project test-room
```

No dependencies to install. Python 3.9+ and Chrome/Chromium.

## Before opening a PR

```bash
./tests/run.sh
```

Runs everything: engine imports, unit tests, the example project, both templates, and drawing
rasterisation. No network, no API key, nothing to pay for. There is deliberately no CI — this is
the whole test suite and it takes seconds.

The unit tests run with PyYAML forcibly unavailable, because the built-in fallback parser is what
most people will actually hit and a bug there truncates a config silently rather than failing.

Then look at the drawings. Most regressions in this codebase are visual and invisible in a diff.

If you changed prompt building, print a prompt before and after and read both. If you changed
geometry, render one view and compare.

## Good first contributions

- **A project template** in `config/templates/` for a room type that is not covered — bedroom,
  bathroom, studio, office, retail. This is the highest-value contribution: the framework is
  generic but only ships two templates.
- **A render backend** in `engine/render.py`. The interface is one function.
- **A drawing type** — a reflected ceiling plan, a lighting layout, a section.
- **Validation rules** in `design check`. Every rule there came from a real mistake; if you make a
  new one, encode it.

## What to avoid

- Adding a dependency. The engine is standard library only, deliberately — it should run anywhere
  without a virtualenv.
- Baking a house style into the engine. Style belongs in `project.yml`.
- "Improving" a render by editing the image.

## Reporting a bug

Include the `project.yml` room block, the command, and — if it is visual — the drawing or render.
A screenshot of a wrong plan is worth more than a paragraph describing it.
