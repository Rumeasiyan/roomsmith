# Troubleshooting

## "BLOCKED — gate X is not approved"

Working as intended. Review the work, then `./bin/design approve X --note "..."`. To see what each
gate guards: `./bin/design gates`.

## A render shows a door or window that does not exist

The room model is missing an opening, or has one on the wrong wall. **Never fix this in the image.**

```bash
./bin/design check                 # does the model agree with reality?
$EDITOR projects/<slug>/project.yml
./bin/design drawings --shell      # look at the plan
./bin/design render 03 --force
```

If the model is right and the render still invents an opening, check that the view's `drawings`
reference is sensible — a square-on view given only the plan will drift.

## The room looks too big

Three causes, in order of likelihood:

1. `key_dimensions` is missing and an alcove or bay is inflating the bounding box.
2. The view is anchored to the wrong drawing.
3. `brief.register` is vague, so the model reaches for showroom styling.

Print the prompt (see `USAGE.md`) and read what it actually says about size.

## Renders look bare

`style.richness` is set to something thin. Leave it empty to use the built-in rules — layered
textiles, objects in use, planting, and several lamps actually lit. Bareness is a prompt failure,
not a style.

## A camera will not rotate

Give that view its wall's elevation as the first entry in `drawings`, and say in `camera` what must
**not** be in frame. A view told only what to include tends to produce the default long shot.

## "quota exhausted"

The free codex quota. Either wait and re-run — finished views are skipped — or:

```bash
./bin/design render --wait                  # poll and continue automatically
./bin/design render --backend openrouter    # paid, needs the `spend` gate
```

## "Insufficient credits" (HTTP 402)

OpenRouter balance is empty. Top up, or switch back to `--backend codex`.

## Drawings are blank or missing

Chrome or Chromium was not found. Install one; it rasterises the SVGs and prints the PDF.

## `design check` reports a collision I do not believe

Two layout rectangles overlap in plan. Legitimate nesting — a cabinet recessed into a joinery wall,
an object standing on a platform — is declared with `"inside": true` or a non-zero `"z"`. If it is
genuinely nested, mark it. If not, the layout is wrong.

## Report is enormous

Expected: renders are embedded so the PDF is portable. A 20-direction job is 30–40 MB. It is not
committed for exactly this reason.

## `--project` is rejected

It works before or after the command. If it still fails you are on an old build — pull.

## A change I made keeps coming back

You edited a generated file. Everything in `drawings/`, `renders/`, `report/` and `prompts/` is
output. Edit `project.yml` or the direction spec instead.
