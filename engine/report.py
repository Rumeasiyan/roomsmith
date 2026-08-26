#!/usr/bin/env python3
"""Build the design report: direction specs + renders -> HTML -> PDF.

    scripts/build_report.py            # write report/report.html
    scripts/build_report.py --pdf      # and print report/report.pdf with headless Chrome
"""
import base64
import html
import json
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECTIONS = RENDERS = DRAWINGS = REFS = REPORT = SURVEY = None
PROJECT = None


def _bind(project):
    global DIRECTIONS, RENDERS, DRAWINGS, REFS, REPORT, SURVEY, PROJECT, VIEWS, DWGS
    PROJECT = project
    DIRECTIONS = project.path / "directions"
    RENDERS = project.path / "renders"
    DRAWINGS = project.path / "drawings"
    REFS = project.path / "refs"
    REPORT = project.path / "report"
    SURVEY = project.path / "brief" / "site-survey.md"
    VIEWS = [(v["id"], v.get("caption", v["id"]))
             for v in (project.get("deliverables.views") or [])]
    room = project.room()
    DWGS = ([("plan", "Measured floor plan"), ("iso", "Isometric cutaway — dollhouse view"),
             ("blueprint", "Blueprint")]
            + [(f"elev-{w}", f"Elevation — {room.wall(w).name}")
               for w in (project.get("deliverables.elevations") or [x.id for x in room.walls])])

TIER_NAME = {
    "A": "Tier A — light touch",
    "B": "Tier B — moderate",
    "C": "Tier C — deep",
}

AXIS_LABEL = {
    "plan": "Plan / zoning",
    "ceiling": "Ceiling",
    "floor": "Floor",
    "seating": "Seating typology",
    "storage": "Storage",
    "lighting": "Lighting architecture",
    "programme": "Programme",
}


def esc(s):
    return html.escape(str(s))


def data_uri(path, max_width=1600):
    """Embed an image, downscaled if Pillow is available, so the PDF stays portable."""
    path = pathlib.Path(path)
    if not path.exists():
        return None
    raw = path.read_bytes()
    try:
        import io

        from PIL import Image

        im = Image.open(io.BytesIO(raw))
        if im.width > max_width:
            im = im.convert("RGB")
            im = im.resize((max_width, round(im.height * max_width / im.width)), Image.LANCZOS)
        buf = io.BytesIO()
        im.convert("RGB").save(buf, "JPEG", quality=82, optimize=True)
        raw, mime = buf.getvalue(), "image/jpeg"
    except Exception:
        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def load_specs():
    specs = [json.loads(p.read_text()) for p in sorted(DIRECTIONS.glob("[0-9][0-9]-*.json"))]
    return sorted(specs, key=lambda s: s["id"])


def survey_html():
    """Render the site survey markdown - headings, tables, lists, paragraphs."""
    if not SURVEY.exists():
        return ""
    lines = SURVEY.read_text().splitlines()
    out, table, para = [], [], []

    def flush_para():
        if para:
            out.append("<p>" + inline(" ".join(para)) + "</p>")
            para.clear()

    def flush_table():
        if not table:
            return
        rows = [r for r in table if not re.match(r"^\|[\s:|-]+\|$", r)]
        cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
        out.append("<table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in cells[0]) + "</tr></thead><tbody>")
        for row in cells[1:]:
            out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>")
        out.append("</tbody></table>")
        table.clear()

    def inline(t):
        t = esc(t)
        t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
        t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
        return t

    for ln in lines:
        if ln.startswith("|"):
            flush_para()
            table.append(ln)
            continue
        flush_table()
        if not ln.strip() or ln.strip() == "---":
            flush_para()
        elif ln.startswith("#"):
            flush_para()
            lvl = len(ln) - len(ln.lstrip("#"))
            out.append(f"<h{min(lvl + 1, 5)}>{inline(ln.lstrip('# ').strip())}</h{min(lvl + 1, 5)}>")
        elif re.match(r"^\s*[-*]\s+", ln) or re.match(r"^\s*\d+\.\s+", ln):
            flush_para()
            out.append("<p class='li'>" + inline(re.sub(r"^\s*(?:[-*]|\d+\.)\s+", "", ln)) + "</p>")
        else:
            para.append(ln.strip())
    flush_para()
    flush_table()
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 16mm 14mm 18mm 14mm; }
* { box-sizing: border-box; }
body { font-family: "Georgia","Times New Roman",serif; color:#20201e; font-size:9.6pt; line-height:1.5; margin:0; }
h1,h2,h3,h4,h5 { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; color:#14140f; line-height:1.2; }
h1 { font-size:30pt; letter-spacing:-.5pt; margin:0 0 4mm; }
h2 { font-size:15pt; margin:0 0 3mm; border-bottom:1.5pt solid #14140f; padding-bottom:2mm; }
h3 { font-size:12pt; margin:6mm 0 2mm; }
h4 { font-size:9.5pt; margin:5mm 0 1.5mm; text-transform:uppercase; letter-spacing:.7pt; color:#6a6155; }
h5 { font-size:9pt; margin:4mm 0 1mm; }
p { margin:0 0 2.5mm; }
p.li { margin:0 0 1.2mm; padding-left:4mm; text-indent:-4mm; }
p.li::before { content:"— "; color:#8a7f6f; }
code { font-family:"SF Mono",Menlo,monospace; font-size:8.4pt; background:#f2efe9; padding:0 1mm; }
table { width:100%; border-collapse:collapse; margin:0 0 3mm; font-size:8.4pt; line-height:1.4; }
th { text-align:left; font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7.4pt;
     text-transform:uppercase; letter-spacing:.6pt; color:#6a6155; border-bottom:1pt solid #14140f;
     padding:1.6mm 2mm; vertical-align:bottom; }
td { padding:1.8mm 2mm; border-bottom:.4pt solid #ddd8ce; vertical-align:top; }
tr { page-break-inside:avoid; }
.page { page-break-after:always; }
.page:last-child { page-break-after:auto; }
.cover { height:245mm; display:flex; flex-direction:column; justify-content:space-between; }
.cover .kicker { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:8pt;
     text-transform:uppercase; letter-spacing:2.4pt; color:#8a7f6f; }
.cover .lede { font-size:12pt; line-height:1.5; max-width:130mm; color:#3d3a34; }
.cover-grid { display:grid; grid-template-columns:repeat(2,1fr); gap:3mm; }
.cover-grid img { width:100%; height:52mm; object-fit:cover; border:.4pt solid #ddd8ce; }
.meta { display:grid; grid-template-columns:repeat(4,1fr); gap:4mm; font-size:8.4pt;
     border-top:1.5pt solid #14140f; padding-top:3mm; }
.meta b { display:block; font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7pt;
     text-transform:uppercase; letter-spacing:.8pt; color:#8a7f6f; margin-bottom:1mm; }
.dir-head { display:flex; justify-content:space-between; align-items:flex-start; gap:6mm;
     border-bottom:1.5pt solid #14140f; padding-bottom:2.5mm; margin-bottom:3.5mm; }
.dir-num { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:34pt; font-weight:700;
     line-height:.85; color:#e0dbd1; letter-spacing:-2pt; }
.dir-title { flex:1; }
.dir-title h2 { border:0; padding:0; margin:0 0 1mm; font-size:19pt; }
.dir-title .tag { font-style:italic; color:#5c554a; font-size:10.5pt; }
.tier { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7.2pt; text-transform:uppercase;
     letter-spacing:.9pt; white-space:nowrap; border:.8pt solid #14140f; padding:1.4mm 2.4mm; }
.renders { display:grid; grid-template-columns:1fr 1fr 1fr; gap:2.5mm; margin-bottom:3.5mm; }
.dwg3 { display:grid; grid-template-columns:1fr 1fr; gap:3mm; margin-bottom:3mm; }
.dwg3 figure:first-child { grid-row:span 2; }
.dwg3 img, .dwg4 img { width:100%; border:.4pt solid #ddd8ce; display:block; background:#fff; }
.dwg3 figure, .dwg4 figure { margin:0; }
.dwg4 { display:grid; grid-template-columns:1fr 1fr; gap:3mm; }
.renders figure { margin:0; }
.renders img { width:100%; border:.4pt solid #ddd8ce; display:block; }
figcaption { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7pt; text-transform:uppercase;
     letter-spacing:.7pt; color:#8a7f6f; margin-top:1.2mm; }
.two { display:grid; grid-template-columns:1fr 1fr; gap:5mm; }
.thesis { font-size:10.4pt; line-height:1.55; }
.axes { font-size:8.2pt; }
.axes b { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7pt; text-transform:uppercase;
     letter-spacing:.6pt; color:#6a6155; }
.swatches { display:flex; gap:2mm; flex-wrap:wrap; margin:1mm 0 3mm; }
.sw { width:26mm; font-size:7pt; }
.sw i { display:block; height:9mm; border:.4pt solid rgba(0,0,0,.18); margin-bottom:.8mm; }
.callout { border-left:2.4pt solid #14140f; padding:2mm 0 2mm 3.5mm; margin:0 0 3.5mm; font-size:8.8pt; background:#faf8f4; }
.callout b { font-family:"Helvetica Neue",Helvetica,Arial,sans-serif; font-size:7pt; text-transform:uppercase;
     letter-spacing:.8pt; color:#6a6155; display:block; margin-bottom:1mm; }
.warn { border-left-color:#a1442c; }
.matrix { font-size:7.2pt; }
.matrix td, .matrix th { padding:1.3mm 1.4mm; }
.tag-list { font-size:8pt; color:#5c554a; }
.foot { font-size:7.4pt; color:#8a7f6f; font-family:"Helvetica Neue",Helvetica,Arial,sans-serif;
     border-top:.4pt solid #ddd8ce; padding-top:2mm; margin-top:5mm; }
"""


VIEWS = [
    ("hero-in",   "From the front door, looking in"),
    ("hero-back", "From the far end, looking back at the door and window"),
    ("corner",    "High corner overview — entrance wall and the whole right flank"),
    ("seated",    "From the settee, across the narrow width"),
    ("alcove",    "The entering-right flank: alcove, curtained doorway and shrine"),
    ("far-wall",  "The far end: eating table, far wall and the arch"),
]

DWGS = [
    ("plan",           "Measured floor plan"),
    ("iso",            "Isometric cutaway — dollhouse view"),
    ("blueprint",      "Blueprint"),
    ("elev-entrance",  "Elevation A — entrance wall"),
    ("elev-right",     "Elevation B — entering-right long wall"),
    ("elev-far",       "Elevation C — far wall"),
    ("elev-left",      "Elevation D — entering-left long wall"),
]


def figure_grid(items, cls):
    figs = ""
    for src, cap in items:
        if src:
            figs += f"<figure><img src='{src}'><figcaption>{esc(cap)}</figcaption></figure>"
    return f"<div class='{cls}'>{figs}</div>" if figs else ""


def render_direction(spec):
    stem = f"{spec['id']}-{spec['slug']}"
    got = [(data_uri(RENDERS / f"{stem}-{v}.png"), c) for v, c in VIEWS]
    got = [(s_, c) for s_, c in got if s_]
    renders = figure_grid(got, "renders")
    if not got:
        renders = ("<div class='callout warn'><b>Photoreal views</b>Not yet generated for this "
                   "direction. The measured drawings opposite are complete and are the "
                   "dimensionally authoritative record.</div>")

    axes = "".join(
        f"<p><b>{AXIS_LABEL[k]}</b><br>{esc(spec['axes'][k])}</p>" for k in AXIS_LABEL if k in spec["axes"]
    )
    moves = "".join(f"<p class='li'><strong>{esc(m['title'])}.</strong> {esc(m['detail'])}</p>" for m in spec["moves"])
    items = "".join(
        f"<tr><td><strong>{esc(i['item'])}</strong></td><td>{esc(i['change'])}</td>"
        f"<td>{esc(i['reason'])}</td><td>{esc(i['validation'])}</td></tr>"
        for i in spec["items"]
    )
    sw = "".join(
        f"<div class='sw'><i style='background:{esc(c['hex'])}'></i><strong>{esc(c['name'])}</strong><br>"
        f"{esc(c['hex'])}<br>{esc(c['use'])}</div>"
        for c in spec["palette"]
    )
    risks = "".join(f"<p class='li'>{esc(r)}</p>" for r in spec["risks"])
    keeps = ", ".join(spec.get("keeps", []))
    removes = ", ".join(spec.get("removes", []))
    solves = ", ".join(spec.get("solves", []))

    room = PROJECT.room()
    scale_callout = (f"<div class='callout'><b>Scale check — does it fit "
                     f"{room.narrow_dim():.2f} × {room.long_dim():.2f} m?</b>"
                     f"{esc(spec['scale_check'])}</div>") if spec.get("scale_check") else ""
    # `retained_treatment` is the generic field; `teak_treatment` is the older name kept working.
    retained = spec.get("retained_treatment") or spec.get("teak_treatment")
    retained_callout = (f"<div class='callout'><b>Retained items — how they are kept</b>"
                        f"{esc(retained)}</div>") if retained else ""
    table_callout = (f"<div class='callout'><b>Work surfaces and tables</b>"
                     f"{esc(spec['table'])}</div>") if spec.get("table") else ""

    plan_big = figure_grid(
        [(data_uri(DRAWINGS / f"{stem}-{k}.png", 1500), c) for k, c in DWGS[:3]], "dwg3")
    elevs = figure_grid(
        [(data_uri(DRAWINGS / f"{stem}-{k}.png", 1200), c) for k, c in DWGS[3:]], "dwg4")

    return f"""
<section class="page">
  <div class="dir-head">
    <div class="dir-num">{esc(spec['id'])}</div>
    <div class="dir-title">
      <h2>{esc(spec['name'])}</h2>
      <div class="tag">{esc(spec['tagline'])}</div>
    </div>
    <div class="tier">{esc(TIER_NAME[spec['budget_tier']])}</div>
  </div>
  {renders}
  <div class="two">
    <div>
      <h4>The idea</h4>
      <p class="thesis">{esc(spec['thesis'])}</p>
      <h4>Why this room, this household</h4>
      <p>{esc(spec['story'])}</p>
    </div>
    <div class="axes">
      <h4>How this differs from every other direction</h4>
      {axes}
    </div>
  </div>

  <h4>Headline interventions, in build order</h4>
  {moves}

  {scale_callout}
  {retained_callout}
  {table_callout}
</section>

<section class="page">
  <h3>{esc(spec['id'])} · {esc(spec['name'])} — every change, and why it survives this room</h3>
  <table>
    <thead><tr><th style="width:15%">Element</th><th style="width:30%">The change (specification)</th>
    <th style="width:22%">Design reason</th><th style="width:33%">Validation against this room's constraints</th></tr></thead>
    <tbody>{items}</tbody>
  </table>

  <div class="two">
    <div>
      <h4>Palette</h4>
      <div class="swatches">{sw}</div>
      <h4>Materials</h4>
      <p class="tag-list">{esc(', '.join(spec['materials']))}</p>
      <h4>Devotional shrine</h4>
      <p>{esc(spec.get('shrine',''))}</p>
      <h4>Heirlooms</h4>
      <p>{esc(spec.get('heirlooms',''))}</p>
      <h4>Ventilation and the fan</h4>
      <p>{esc(spec.get('ventilation',''))}</p>
    </div>
    <div>
      <h4>Retained</h4>
      <p class="tag-list">{esc(keeps)}</p>
      <h4>Removed</h4>
      <p class="tag-list">{esc(removes)}</p>
      <h4>Survey problems addressed</h4>
      <p class="tag-list">{esc(solves)}</p>
      <div class="callout warn"><b>Risks and things that must not be value-engineered</b>{risks}</div>
      <div class="callout warn"><b>Who this direction is wrong for</b>{esc(spec['not_for'])}</div>
    </div>
  </div>
</section>

<section class="page">
  <h3>{esc(spec['id'])} · {esc(spec['name'])} — measured drawings</h3>
  <p style="font-size:8.6pt;color:#6a6155">Drawn to scale from the confirmed room model, not
  generated. Room 3120 × 6250 mm, ceiling 2900 mm. The only openings are D1 (front door) and W1
  (window) on the entrance wall, D2 (curtained doorway, inside the alcove) and A1 (arch) on the
  entering-right flank. Both the far wall and the entering-left long wall are solid.</p>
  {plan_big}
  {elevs}
</section>
"""


def matrix(specs):
    rows = "".join(
        f"<tr><td><strong>{esc(s['id'])}</strong></td><td><strong>{esc(s['name'])}</strong><br>"
        f"<span style='color:#6a6155'>{esc(s['tagline'])}</span></td>"
        f"<td>{esc(s['budget_tier'])}</td>"
        + "".join(f"<td>{esc(s['axes'][k])}</td>" for k in AXIS_LABEL if k in s["axes"])
        + "</tr>"
        for s in specs
    )
    heads = "".join(f"<th>{esc(v)}</th>" for v in AXIS_LABEL.values())
    return f"""
<section class="page">
  <h2>Comparison matrix — proof that these are twenty different rooms</h2>
  <p>Two directions count as distinct only if they differ on at least four of the seven axes below.
  Read any two rows side by side: the plan, the ceiling, the floor, what you sit on, where things are
  kept, how the room is lit, and what the room is <em>for</em> all change. Colour and fabric are not
  on this list, because a colour change is not a design direction.</p>
  <table class="matrix">
    <thead><tr><th>#</th><th style="width:17%">Direction</th><th>Tier</th>{heads}</tr></thead>
    <tbody>{rows}</tbody>
  </table>
</section>"""


def build(project, pdf=True):
    _bind(project)
    specs = load_specs()
    REPORT.mkdir(exist_ok=True)

    cover_imgs = "".join(
        f"<img src='{u}'>" for u in filter(None, (
            data_uri(REFS / "from-entrance.jpg", 900),
            data_uri(REFS / "entrance.jpg", 900),
            data_uri(REFS / "right-side-of-entrance.jpg", 900),
            data_uri(REFS / "left-side-of-entrance.jpg", 900),
        ))
    )
    n_items = sum(len(s["items"]) for s in specs)
    n_renders = len(list(RENDERS.glob("*.png")))

    body = [f"""
<section class="page cover">
  <div>
    <div class="kicker">Interior design directions · compact family hall</div>
    <h1>Twenty Ways to<br>Rebuild One Room</h1>
    <p class="lede">A 3.12 by 6.25 metre family hall in a suburban house, surveyed from
    photographs and re-designed twenty times over. Every direction keeps the household's inherited
    carved teak settee, armchairs, curio cabinet and tables, keeps the shrine in daily use, keeps the
    cross-ventilation the room depends on, and is drawn at the room's true and unforgiving scale.
    Every single change carries a specification, a design reason, and a validation against this room's
    own constraints.</p>
  </div>
  <div class="cover-grid">{cover_imgs}</div>
  <div class="meta">
    <div><b>Directions</b>{len(specs)}</div>
    <div><b>Justified changes</b>{n_items}</div>
    <div><b>Renders</b>{n_renders}</div>
    <div><b>Room area</b>~19.5 m² / 210 ft²</div>
  </div>
</section>

<section class="page">
  <h2>How to read this report</h2>
  <p>Each direction occupies two pages. The first carries two renders taken from the same two
  standpoints as the owner's original photographs, so every scheme can be compared like with like;
  then the spatial idea, the reason it suits this particular household, the seven axes on which it
  differs from every other direction, the headline interventions in build order, and three checks —
  that the layout physically fits, that the inherited furniture is kept, and that the family's tables
  survive.</p>
  <p>The second page is the substance: a table in which every physical change is stated as a
  specification, given a design reason, and then <em>validated</em> — tested against this room's
  climate, its 2:1 proportion, its circulation, its damp, its devotional use and its budget. A change
  that cannot survive that test is not in the table. The page closes with the palette, the materials,
  what is retained, what is removed, the risks that must not be value-engineered away, and an honest
  statement of who the direction is wrong for.</p>
  <p>Nothing here was generated by describing a picture after the fact. Each direction was specified
  first; the renders illustrate the specification, and both are built from the same source file, so
  the images and the report cannot drift apart.</p>
  <h2 style="margin-top:8mm">The site survey</h2>
  {survey_html()}
</section>""", matrix(specs)]

    body += [render_direction(s) for s in specs]
    body.append("""
<section class="page">
  <h2>Choosing between them</h2>
  <h4>If the budget is tight and the household can live in the house throughout</h4>
  <p class="li"><strong>19 Conservation Restoration</strong> — repair everything, change nothing. The cheapest and the most durable.</p>
  <p class="li"><strong>14 Garden Room</strong> — one planted trough transforms the room's character with no demolition.</p>
  <p class="li"><strong>15 Kandyan Craft Hall</strong> — the same room re-made entirely in local craft, no construction.</p>
  <h4>If the real complaint is clutter and storage</h4>
  <p class="li"><strong>10 The Fitted Shell</strong> — about six cubic metres of closed storage; nothing else comes close.</p>
  <p class="li"><strong>07 Library Hall</strong> — 38 linear metres of shelf, if the household collects and reads.</p>
  <p class="li"><strong>02 Split-Level Deck Hall</strong> — 1.8 cubic metres inside a step that also divides the room.</p>
  <h4>If the real complaint is that the room feels like a corridor</h4>
  <p class="li"><strong>20 The Inner Room</strong> — shortens the hall by a third and gives the suite a near-square room.</p>
  <p class="li"><strong>01 Tropical Modernist Pavilion</strong> — separates the through-route from the sitting room.</p>
  <p class="li"><strong>18 Arched Lime Hall</strong> — turns the length into a rhythm of arches.</p>
  <h4>If the household's own life should set the brief</h4>
  <p class="li"><strong>11 Chapel Hall</strong> — for a household that wants its daily devotion to organise the room.</p>
  <p class="li"><strong>13 Reception and Workroom</strong> — for a household that works from home.</p>
  <p class="li"><strong>16 Convertible Guest Hall</strong> — for a household that regularly puts relatives up.</p>
  <p class="li"><strong>12 Media Snug</strong> — for a household that watches things together.</p>
  <h4>Three things that are true of every direction here</h4>
  <p class="li">The damp on the right-hand wall is repaired at source first, in every single scheme. No finish is specified over an unrepaired defect.</p>
  <p class="li">The house has no mechanical cooling, so the ventilation grilles stay clear and a fan turns in every scheme. Every enclosure that is built is ventilated.</p>
  <p class="li">The carved teak settee, the armchairs, the curio cabinet and the family's tables stay in this room in all twenty. They are stripped, polished, re-stained, bleached, re-caned, re-cushioned, raised, castored, recessed or framed — never removed.</p>
  <div class="foot">Directions specified from the owner's photographs and dimension sketch. Renders are
  illustrations of the written specifications, produced from the same source files, and are indicative
  of intent rather than construction drawings. All dimensions to be verified on site before any
  joinery is made.</div>
</section>""")

    out = REPORT / "report.html"
    out.write_text(
        "<!doctype html><html><head><meta charset='utf-8'>"
        "<title>Twenty Ways to Rebuild One Room</title>"
        f"<style>{CSS}</style></head><body>{''.join(body)}</body></html>"
    )
    print(f"wrote {out}  ({out.stat().st_size/1_048_576:.1f} MB, {len(specs)} directions, {n_items} justified changes)")

    if pdf:
        chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser")
                       if subprocess.run(["which", c], capture_output=True).returncode == 0), None)
        if not chrome:
            sys.exit("no chrome/chromium found for PDF printing")
        pdf = REPORT / "report.pdf"
        subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox",
                        "--no-pdf-header-footer", f"--print-to-pdf={pdf}",
                        "--virtual-time-budget=30000", out.as_uri()], check=True,
                       capture_output=True)
        print(f"wrote {pdf}  ({pdf.stat().st_size/1_048_576:.1f} MB)")


if __name__ == "__main__":
    from .project import resolve
    build(resolve(None))
