"""`design` — the single entry point.

    design init <slug> [--from <template>]   scaffold a new job
    design status                            where the job is, what is approved, what is left
    design check                             validate config, geometry, layouts; find real errors
    design drawings [NN|--shell]             measured drawings
    design pack <NN>                         drawings + all views for ONE direction, then stop
    design render [NN] [--backend B] [--wait] [--dry]  photoreal views
                                             --dry validates everything, calls nothing
    design report                            build the PDF
    design approve <gate> [--note "..."]     record an approval
    design gates                             list gates and their status

Global: --project <slug>
"""
from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import sys

from . import drawings, render
from .project import GATES, PROJECTS, ROOT, Project, resolve

TEMPLATES = ROOT / "config" / "templates"


def cmd_init(a):
    slug = a.slug
    dest = PROJECTS / slug
    if dest.exists():
        sys.exit(f"{dest} already exists")
    tpl = TEMPLATES / f"{a.template}.yml"
    if not tpl.exists():
        sys.exit(f"no template {a.template!r}. Available: "
                 + ", ".join(sorted(p.stem for p in TEMPLATES.glob('*.yml'))))
    for d in ("refs", "brief", "directions", "drawings", "renders", "report"):
        (dest / d).mkdir(parents=True, exist_ok=True)
    shutil.copy(tpl, dest / "project.yml")
    (ROOT / "config").mkdir(exist_ok=True)
    (ROOT / "config" / "current").write_text(slug + "\n")
    print(f"created {dest}")
    print(f"  1. put the client's photographs and dimension sketch in {dest/'refs'}/")
    print(f"  2. edit {dest/'project.yml'} — or run the intake agent, which will interview you")
    print(f"  3. design check   then   design status")


def cmd_status(a):
    p = resolve(a.project)
    room = None
    try:
        room = p.room()
    except Exception as e:
        print(f"room model: NOT READY ({e})")
    specs = p.specs()
    views = p.views()
    done = sum(1 for s in specs for v in views
               if render.out_path(p, f"{s['id']}-{s['slug']}", v).exists())
    total = len(specs) * len(views)
    print(f"project        {p.slug}")
    print(f"brief          {p.get('brief.what_it_is','—')[:70]}")
    if room:
        w, l = room.span()
        print(f"room           {room.name}: {w:.2f} × {l:.2f} m, {room.area():.1f} m², "
              f"{len(room.openings)} openings, {'CONFIRMED' if room.confirmed else 'NOT confirmed'}")
    print(f"directions     {len(specs)} authored, target {p.get('deliverables.directions','—')}")
    print(f"views          {done}/{total} rendered ({len(views)} per direction)")
    dr = len(list((p.path / 'drawings').glob('*.png')))
    print(f"drawings       {dr}")
    missing = len(render.missing(p)) if specs else 0
    if missing:
        backend, _ = render.choose_backend(p)
        print(f"remaining      {render.forecast(backend, missing)}")
    sp = render.spent(p)
    print(f"spend          ${sp:.2f}" + (f" of ${p.get('render.max_spend_usd')} ceiling"
                                         if p.get("render.max_spend_usd") else ""))
    print("\ngates")
    for gid, desc, guards in GATES:
        mark = "✓" if p.approved(gid) else "·"
        at = p.state.get("approvals", {}).get(gid, {}).get("at", "")
        print(f"  {mark} {gid:<14} {at:<20} {desc}")
    nxt = next((g for g, _, _ in GATES if not p.approved(g)), None)
    if nxt:
        print(f"\nnext           approve '{nxt}' when it is right:  design approve {nxt}")


def cmd_gates(a):
    p = resolve(a.project)
    for gid, desc, guards in GATES:
        print(f"{'✓' if p.approved(gid) else '·'} {gid:<14} guards {guards}\n    {desc}")


def cmd_approve(a):
    p = resolve(a.project)
    if a.revoke:
        p.revoke(a.gate)
        print(f"revoked {a.gate}")
        return
    p.approve(a.gate, a.note or "")
    print(f"approved {a.gate}")
    nxt = next((g for g, _, _ in GATES if not p.approved(g)), None)
    print(f"next gate: {nxt}" if nxt else "all gates approved")


def cmd_check(a):
    p = resolve(a.project)
    room = p.room()
    bad = []
    x0, y0, x1, y1 = room.bbox()
    for o in room.openings:
        w = room.wall(o.wall)
        if o.pos - o.width / 2 < -0.01 or o.pos + o.width / 2 > w.length + 0.01:
            bad.append(f"opening {o.tag} runs past the end of {w.id}")
        if o.head > room.ceiling_height + 0.01:
            bad.append(f"opening {o.tag} is taller than the ceiling")
    for i, a1 in enumerate(room.openings):
        for b1 in room.openings[i + 1:]:
            if a1.wall == b1.wall and abs(a1.pos - b1.pos) < (a1.width + b1.width) / 2 - 0.01:
                bad.append(f"openings {a1.tag} and {b1.tag} overlap on {a1.wall}")
    for spec in p.specs():
        pl = (spec.get("layout") or {}).get("plan", [])
        if not pl:
            bad.append(f"{spec['id']} has no layout")
        for it in pl:
            if not (x0 - .01 <= it["x"] and it["x"] + it["w"] <= x1 + .01
                    and y0 - .01 <= it["y"] and it["y"] + it["d"] <= y1 + .01):
                bad.append(f"{spec['id']}: '{it['label']}' outside the room")
        for m, it in enumerate(pl):
            for jt in pl[m + 1:]:
                if it.get("z") or jt.get("z") or it.get("inside") or jt.get("inside"):
                    continue
                if (min(it["x"] + it["w"], jt["x"] + jt["w"]) - max(it["x"], jt["x"]) > .02 and
                        min(it["y"] + it["d"], jt["y"] + jt["d"]) - max(it["y"], jt["y"]) > .02):
                    bad.append(f"{spec['id']}: '{it['label']}' collides with '{jt['label']}'")
        for f in ("thesis", "items", "scale_check"):
            if not spec.get(f):
                bad.append(f"{spec['id']} missing {f}")
        for it in spec.get("items", []):
            for f in ("item", "change", "reason", "validation"):
                if not str(it.get(f, "")).strip():
                    bad.append(f"{spec['id']}: an item has no {f}")
    for v in (p.get("deliverables.views") or []):
        if not (v.get("from") and v.get("look_at")):
            bad.append(f"view '{v.get('id','?')}' has no from/look_at - no orientation block will "
                       f"be generated, so the render may mirror the room or invent daylight")
    print(f"room     {room.name}  {x1-x0:.2f} × {y1-y0:.2f} m  {len(room.walls)} walls  "
          f"{len(room.openings)} openings")
    print(f"specs    {len(p.specs())}")
    if bad:
        print("\nPROBLEMS:")
        for b in dict.fromkeys(bad):
            print("  ✗ " + b)
        sys.exit(1)
    print("\nall checks pass")


def cmd_drawings(a):
    p = resolve(a.project)
    p.require("room-model")
    if a.shell or not a.which:
        print("\n".join(drawings.build(p, None, "_shell")))
        return
    key = p.spec_key(a.which)
    spec = json.loads((p.path / "directions" / f"{key}.json").read_text())
    print("\n".join(drawings.build(p, spec, key)))


def cmd_pack(a):
    """One direction, end to end, then stop. The unit of review."""
    p = resolve(a.project)
    p.require("room-model")
    key = p.spec_key(a.which)
    spec = json.loads((p.path / "directions" / f"{key}.json").read_text())
    print(f"═══ PACK  {key}")
    print("--- measured drawings")
    for n in drawings.build(p, spec, key):
        print("    " + n)
    print("--- photoreal views")
    for v in p.views():
        try:
            render.render_one(p, key, v, a.backend, a.force)
        except render.QuotaExhausted as e:
            print(f"\nSTOPPED: {e}")
            sys.exit(2)
    miss = [v for v in p.views() if not render.out_path(p, key, v).exists()]
    print("\n" + ("complete" if not miss else f"MISSING: {', '.join(miss)}"))
    print(_qa_checklist(p))


def _qa_checklist(p):
    room = p.room()
    tags = ", ".join(f"{o.tag} ({o.type})" for o in room.openings)
    solid = ", ".join(w.name for w in room.solid_walls()) or "none"
    keep = "; ".join(p.get("brief.must_appear", []) or []) or "—"
    return f"""
--- QA CHECKLIST — check every view before starting the next direction
  1  OPENINGS   exactly these and no others: {tags}
  2  SOLID      these walls must show no opening at all: {solid}
  3  SCALE      the room must read {room.narrow_dim():.2f} m across. If it looks generous, FAIL
  4  CONTENTS   must appear: {keep}
  5  CONSISTENT all views must be the same room, matching the plan
Fix anything wrong in the room model or the shared code, not in one image, so the fix carries
forward. Then:  design approve pilot"""


def cmd_render(a):
    p = resolve(a.project)
    p.require("room-model")
    backend, why = render.choose_backend(p, a.backend)
    if a.which:
        key = p.spec_key(a.which)
        todo = [(key, v) for v in p.views()
                if a.force or a.dry or not render.out_path(p, key, v).exists()]
    elif a.force or a.dry:
        todo = [(f"{sp['id']}-{sp['slug']}", v) for sp in p.specs() for v in p.views()]
    else:
        todo = render.missing(p)
        if todo and not p.approved("pilot"):
            first = p.specs()[0]
            fk = f"{first['id']}-{first['slug']}"
            todo = [x for x in todo if x[0] == fk]
            if not todo:
                sys.exit("\nBLOCKED — gate 'pilot' is not approved.\n"
                         "  Direction 01's pack is rendered. Review every view, then:\n"
                         "    design approve pilot\n")
            print("gate 'pilot' not approved — rendering only the first direction")
    ceiling = float(p.get("render.max_spend_usd") or 0) or None
    spent0 = render.spent(p)
    if a.dry:
        print(f"DRY RUN — {len(todo)} views would render on '{backend}'. "
              f"No image model is called and nothing is written.\n")
        bad = warned = 0
        for key, v in todo:
            info, errors, warnings = render.dry_run(p, key, v)
            mark = "✗" if (errors or not info) else ("!" if warnings else "✓")
            bad += bool(errors or not info)
            warned += bool(warnings and not errors)
            detail = (f"  ~{info['prompt_tokens']} prompt tokens, refs: {', '.join(info['refs'])}"
                      if info else "")
            print(f"  {mark} {key}-{v}{detail}")
            for x in errors:
                print(f"      ERROR  {x}")
            for x in warnings:
                print(f"      warn   {x}")
        print(f"\n{len(todo) - bad}/{len(todo)} views ready"
              + (f", {warned} with warnings" if warned else ""))
        print(f"  {render.forecast(backend, len(todo))}")
        if bad:
            sys.exit(1)
        return

    fb, fb_why = render.fallback_backend(p, backend)
    print(f"{len(todo)} views to render · backend {backend} ({why})"
          + (f" · ceiling ${ceiling:.2f} (spent ${spent0:.2f})" if ceiling else ""))
    print(f"  {render.forecast(backend, len(todo))}")
    print(f"  fallback: {fb} ({fb_why})" if fb else f"  no fallback ({fb_why})")
    fails = 0
    for key, v in todo:
        if ceiling and render.spent(p) >= ceiling:
            print(f"\nSTOPPED: hit the ${ceiling:.2f} ceiling. Raise render.max_spend_usd to continue.")
            break
        while True:
            try:
                c = render.render_one(p, key, v, backend, a.force)
                break
            except render.QuotaExhausted as e:
                nxt, nxt_why = render.fallback_backend(p, backend)
                if nxt:
                    print(f"    {e} — switching to '{nxt}' ({nxt_why})")
                    p.log(f"backend fell back from '{backend}' to '{nxt}': {e}")
                    backend = nxt
                    continue
                if a.wait:
                    import time as _t
                    print(f"    {e} — no fallback ({nxt_why}); waiting {a.wait // 60} min")
                    _t.sleep(a.wait)
                    continue
                print(f"\nSTOPPED: {e}. No fallback ({nxt_why}).\n"
                      f"Re-run when it resets; finished views are skipped. Or set\n"
                      f"  render.fallback: openrouter   in project.yml, and approve the 'spend' gate.")
                sys.exit(2)
        if c is None:
            fails += 1
            if fails >= 3:
                sys.exit("3 consecutive failures — stopping")
        else:
            fails = 0
    print(f"\nspend this project: ${render.spent(p):.2f}")


def cmd_report(a):
    p = resolve(a.project)
    from . import report
    report.build(p, pdf=not a.no_pdf)


def main(argv=None):
    # --project is accepted either before or after the subcommand, because typing it after is
    # the natural thing to do and argparse would otherwise reject it.
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--project", help="project slug under projects/")

    ap = argparse.ArgumentParser(prog="design", description=__doc__, parents=[common],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", parents=[common]); s.add_argument("slug")
    s.add_argument("--from", dest="template", default="room")
    s.set_defaults(fn=cmd_init)

    for name, fn in (("status", cmd_status), ("gates", cmd_gates), ("check", cmd_check)):
        s = sub.add_parser(name, parents=[common]); s.set_defaults(fn=fn)

    s = sub.add_parser("approve", parents=[common]); s.add_argument("gate")
    s.add_argument("--note", default=""); s.add_argument("--revoke", action="store_true")
    s.set_defaults(fn=cmd_approve)

    s = sub.add_parser("drawings", parents=[common]); s.add_argument("which", nargs="?")
    s.add_argument("--shell", action="store_true"); s.set_defaults(fn=cmd_drawings)

    s = sub.add_parser("pack", parents=[common]); s.add_argument("which")
    s.add_argument("--backend"); s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_pack)

    s = sub.add_parser("render", parents=[common]); s.add_argument("which", nargs="?")
    s.add_argument("--missing", action="store_true"); s.add_argument("--backend")
    s.add_argument("--force", action="store_true")
    s.add_argument("--wait", type=int, nargs="?", const=600, default=0, metavar="SECONDS",
                   help="on quota exhaustion, wait and retry instead of stopping (default 600s)")
    s.add_argument("--dry", action="store_true",
                   help="validate prompts and references without calling any image model")
    s.set_defaults(fn=cmd_render)

    s = sub.add_parser("report", parents=[common]); s.add_argument("--no-pdf", action="store_true")
    s.set_defaults(fn=cmd_report)

    a = ap.parse_args(argv)
    render.load_dotenv(ROOT)
    return a.fn(a)


if __name__ == "__main__":
    main()
