---
title: "Setup — Roomsmith"
description: "Install Roomsmith and run your first interior design job. Python 3.9+, Chrome, and a free or paid image backend."
---

# Setup

## Requirements

| Need | Check | Why |
|---|---|---|
| Python 3.9+ | `python3 --version` | the engine. No required third-party packages |
| Chrome or Chromium | `command -v google-chrome \|\| command -v chromium` | rasterises drawings, prints the PDF |
| A render backend | see below | photoreal views |
| PyYAML *(optional)* | `python3 -c "import yaml"` | nicer YAML. A built-in mini-parser is used otherwise |

## Render backends

You need at least one. They are interchangeable — same prompts, same reference drawings.

**codex** — free, quota-limited. Install the codex CLI and sign in; its built-in `image_gen`
tool (gpt-image-2) is used. Nothing else to configure.

```bash
codex --version
```

**openrouter** — paid, no quota, about $0.18 per image.

```bash
cp .env.example .env      # then set OPENROUTER_API_KEY
```

`.env` is gitignored. `.env.example` is committed and must never contain a real key. Keep
`OPENROUTER_IMAGE_MODEL` at `openai/gpt-image-2` unless you have a reason to change it: it is the
same model codex uses, which is what keeps every image in a set visually consistent.

## First run

```bash
./bin/design init my-room
cp ~/photos/*.jpg projects/my-room/refs/
./bin/design check
```

`check` will complain until the room model is filled in — that is expected, and the surveyor
agent's job. In Claude Code, run `/interior-design` and it will walk you through.

## Working on several jobs

Each job is a directory under `projects/`. The tool uses the only one present, or the slug in
`config/current`, or `--project <slug>`:

```bash
./bin/design status --project kitchen-refit
echo kitchen-refit > config/current
```

## Troubleshooting

**"BLOCKED — gate X is not approved"** — working as intended. Review the work, then
`./bin/design approve X`.

**Drawings are blank or missing** — Chrome was not found. Install Chromium.

**"quota exhausted"** — the codex free quota. Re-run later; finished views are skipped. Or switch
to `--backend openrouter`.

**A render shows a door that does not exist** — the room model is missing an opening, or has one on
the wrong wall. Fix `project.yml`, run `./bin/design check`, regenerate drawings, re-render. Never
fix it in the image.
