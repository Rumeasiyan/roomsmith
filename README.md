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
| `renders/` | 40 renders, two camera views per direction |
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

## Rebuilding

```bash
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
