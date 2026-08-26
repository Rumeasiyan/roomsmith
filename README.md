# Compact Hall — Design Directions

Twenty distinct interior design directions for a 3.12 × 6.25 m family hall in a suburban local
house, each with a full item-by-item justification and two photoreal renders, compiled into a
125-page PDF report.

Produced by the reusable **`interior-designer`** agent / **`/interior-design`** skill in this repo.

## Deliverables

| Path | What |
|---|---|
| `report/report.pdf` | The report — 125 pages, 20 directions, 291 justified changes, 40 renders |
| `report/report.html` | Same, as HTML |
| `drawings/` | 147 measured drawings — per direction: plan, blueprint, isometric dollhouse and four wall elevations, all drawn by code from `brief/room.json` |
| `renders/` | photoreal views, six camera angles per direction, covering all four walls |
| `directions/NN-slug.json` | The authored specs — single source of truth for both renders and report |
| `brief/site-survey.md` | Surveyed ground truth: geometry, openings, fabric, problems P1–P8, constraints |

## Hard constraints every direction obeys

1. The inherited carved teak settee, both armchairs, the curio cabinet and the family's tables
   **stay in this room**. They may be stripped, polished, re-stained, bleached, re-caned,
   re-cushioned, raised, castored, recessed or framed — never removed or re-sited.
2. The household shrine stays, in daily use, reachable, with room for a lit votive lamp.
3. The heirlooms stay on show.
4. Cross-ventilation stays — no mechanical cooling exists, so V1–V3 stay clear and a fan turns.
5. Circulation spine ≥ 900 mm from the front door to the rear arch.
6. The damp on the right wall is repaired at source before any finish, in every direction.
7. True scale: every spec carries a `scale_check` adding up widths across the 3.12 m dimension.
8. The register is a lived-in local family front room, not a gallery, loft or showroom.
9. **Exactly four openings.** D1 front door and W1 window on the entrance wall; D2 curtained doorway
   inside the alcove on the entering-right flank; A1 arch at the far end of the same flank. The far
   wall and the entering-left long wall are solid. The render prompts generate this inventory from
   `brief/room.json`, so no image can invent a door.
10. **One direction at a time.** Build a pack, inspect it, fix defects in the shared code, then start
   the next. Never batch-generate a whole set.

## Configuration

Secrets live in `.env`, which is gitignored. `.env.example` is committed and documents every
variable; it must never contain a real key.

```bash
cp .env.example .env      # then edit .env and paste your OpenRouter key
```

| Variable | Purpose |
|---|---|
| `OPENROUTER_API_KEY` | Only needed for the OpenRouter render backend |
| `OPENROUTER_IMAGE_MODEL` | Defaults to `openai/gpt-image-2` — the same model codex's `image_gen` uses, so every image in the set stays visually consistent |
| `OPENROUTER_IMAGE_QUALITY` | `high` matches codex output; `medium` is ~1/3 the cost and softer |
| `OPENROUTER_MAX_SPEND_USD` | Hard ceiling for one `--missing` run, using the real per-image cost the API reports |

Two interchangeable render backends, same prompts and same reference drawings:

```bash
./scripts/resume_renders.sh                        # via codex image_gen (free, quota-limited)
python3 scripts/render_openrouter.py --missing     # via OpenRouter (paid, no quota)
```

## Rebuilding

```bash
python3 scripts/drawings.py --shell        # measured drawings of the empty room
python3 scripts/drawings.py 07             # drawings for one direction
./scripts/make_pack.sh 07                  # ONE direction: 7 drawings + 6 renders, then stop
./scripts/resume_renders.sh                # continue any directions still missing renders
python3 scripts/build_prompts.py          # specs -> prompts/
JOBS=5 ./scripts/render_all.sh            # all renders (resumable; skips existing)
./scripts/render_all.sh 07 12             # just these directions
python3 scripts/build_report.py --pdf     # report/report.html + report.pdf
```

Renders go through `codex exec`, which carries the `image_gen` tool. Reference photographs in
`refs/` are passed as `referenced_image_paths` so every image keeps the real room's geometry.
PDF printing uses headless Chrome.

## Reusing on another room

1. Replace `refs/` with the new photographs and dimension sketch. Clear `directions/`,
   `renders/`, `report/`.
2. Invoke `/interior-design` (or the `interior-designer` agent) and follow its procedure —
   survey, plan the direction set, write the specs, render, report.
3. The scripts are project-agnostic; `scripts/render.sh` takes `REF_A` / `REF_B` overrides if the
   new room's camera anchors have different filenames.
