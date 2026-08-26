"""Render prompts, assembled from the room model and the project config.

Nothing about the room's geometry or the client's brief is typed here. The opening inventory,
the solid-wall clause and the scale discipline are all GENERATED, which is what stops a render
inventing a door or drawing a small room as a large one.
"""
from __future__ import annotations

import math


def openings_inventory(room):
    lines = []
    for o in room.openings:
        w = room.wall(o.wall)
        extra = f" {o.extra}" if o.extra else ""
        sill = f", sill {o.sill*1000:.0f} mm above the floor" if o.sill else ""
        lines.append(
            f"  {o.tag} — {o.desc or o.type}. {o.width*1000:.0f} mm wide, "
            f"{o.height*1000:.0f} mm high{sill}. In {w.name}, centred {o.pos:.2f} m "
            f"from that wall's start.{extra}")
    return "\n".join(lines)


def solid_clause(room):
    solid = room.solid_walls()
    if not solid:
        return ""
    out = ["WALLS THAT ARE COMPLETELY SOLID — NO OPENING OF ANY KIND:"]
    for w in solid:
        feats = room.features_on(w.id)
        note = (f" Its only feature is {len(feats)} small "
                f"{feats[0].kind}{'s' if len(feats) != 1 else ''} high up near the ceiling."
                if feats else "")
        out.append(f"  · {w.name.upper()} is SOLID from floor to ceiling.{note}")
    out.append("  There is NO window, NO door, NO archway, NO glazed panel and NO view of daylight,")
    out.append("  greenery or another room in any of those walls.")
    return "\n".join(out)


def shell_block(room, project):
    narrow, long = room.narrow_dim(), room.long_dim()
    feats = {}
    for f in room.features:
        feats.setdefault(f.kind, 0)
        feats[f.kind] += 1
    feat_txt = ", ".join(f"{n} {k}{'s' if n != 1 else ''}" for k, n in feats.items())
    extra = project.get("room.shell_notes") or []
    return f"""THE REAL ROOM — these facts are fixed and must be true in the image:
- {room.name}: {narrow:.2f} m across its narrow dimension and {long:.2f} m along its long one,
  floor area about {room.area():.1f} m², ceiling {room.ceiling_height:.2f} m.
{chr(10).join('- ' + s for s in extra)}
{('- Fixed features present: ' + feat_txt) if feat_txt else ''}

THE COMPLETE LIST OF OPENINGS. THIS ROOM HAS EXACTLY {len(room.openings)} OPENINGS AND NO OTHERS:
{openings_inventory(room)}

{solid_clause(room)}

DO NOT ADD ANY OPENING THAT IS NOT IN THAT LIST. No extra window, no extra doorway, no
pass-through, no internal window, no glazed screen, no French doors, no skylight — unless this
direction explicitly forms a NEW opening, in which case build only that one. Inventing an
opening makes the image useless, because it cannot be built."""


def scale_block(room):
    narrow, long = room.narrow_dim(), room.long_dim()
    tight = narrow <= 4.0
    if tight:
        return f"""SCALE DISCIPLINE — THE MOST IMPORTANT INSTRUCTION:
This room is TIGHT. It is {narrow:.2f} m across and {long:.2f} m the other way, about
{room.area():.1f} m² in total. A single large piece of furniture takes a big share of that width.
Furniture stands close to the walls and the walkway past it is under a metre. Both side walls crop
the frame. The opposite wall is close, so it reads as the end of a modest room, not a distant vista.
Do NOT render a wide, airy, spacious interior. Do NOT widen the room or add floor area. If the
image looks like a gallery, a loft, a hotel lobby or a showroom, it is WRONG. It should look
tight, well organised and full but not chaotic.
A MEASURED DRAWING OF THIS EXACT ROOM IS ATTACHED. Match it: proportion, every opening's
position, and where the furniture sits."""
    return f"""SCALE DISCIPLINE:
The room is {narrow:.2f} m by {long:.2f} m, about {room.area():.1f} m². Render it at exactly that
size — neither cramped nor inflated. A MEASURED DRAWING OF THIS EXACT ROOM IS ATTACHED. Match it:
proportion, every opening's position, and where the furniture sits."""


def orientation_block(room, vc):
    """Say which wall lands on which side of THIS frame.

    Without this the model has world coordinates and a prose camera description, and no way to
    turn one into the other - so it mirrors the room about half the time, and invents daylight on
    whichever wall it decided was the window wall. Generated from a camera vector, never prose.

    Needs `from: [x, y]` and `look_at: [x, y]` on the view. Returns "" if they are absent.
    """
    eye, target = vc.get("from"), vc.get("look_at")
    if not (eye and target and len(eye) == 2 and len(target) == 2):
        return ""
    fx, fy = target[0] - eye[0], target[1] - eye[1]
    n = math.hypot(fx, fy) or 1
    fx, fy = fx / n, fy / n
    rx, ry = fy, -fx          # screen-right, for a plan with y running away from the viewer

    sides = {"LEFT": [], "RIGHT": [], "AHEAD": [], "BEHIND": []}
    for w in room.walls:
        # Judge from both ends, not the midpoint: a wall you are standing against has a midpoint
        # off to one side but is really behind you.
        samples = []
        for px, py in (w.p0, w.p1, ((w.p0[0] + w.p1[0]) / 2, (w.p0[1] + w.p1[1]) / 2)):
            vx, vy = px - eye[0], py - eye[1]
            d = math.hypot(vx, vy) or 1
            samples.append(((vx * fx + vy * fy) / d, (vx * rx + vy * ry) / d))
        fwds = [s[0] for s in samples]
        side = sum(s[1] for s in samples) / len(samples)
        if max(fwds) < 0.25:
            key = "BEHIND"
        elif min(fwds) > 0.3 and abs(side) < 0.55:
            key = "AHEAD"
        else:
            key = "RIGHT" if side > 0 else "LEFT"
        ops = room.openings_on(w.id)
        label = w.name + (f" (with {', '.join(o.tag + ' ' + o.type for o in ops)})" if ops
                          else " — SOLID, no opening")
        sides[key].append(label)

    out = ["ORIENTATION — WHAT IS WHERE IN THIS FRAME. Get this right or the image is unusable:"]
    for key in ("LEFT", "AHEAD", "RIGHT", "BEHIND"):
        if sides[key]:
            verb = ("is behind the camera and NOT in shot" if key == "BEHIND"
                    else f"is on your {key}" if key in ("LEFT", "RIGHT") else "is directly AHEAD")
            out.append(f"  · {verb}: " + "; ".join(sides[key]))
    lit = [o for w in room.walls for o in room.openings_on(w.id)
           if o.type == "window" and w.name in " ".join(sides["LEFT"] + sides["RIGHT"] + sides["AHEAD"])]
    if lit:
        out.append("  Daylight enters ONLY through: " + ", ".join(o.tag for o in lit)
                   + ". Every other wall in this frame is solid and must show no daylight, no "
                     "window reflection and no window-shaped light patch.")
    else:
        out.append("  No window is in this frame. Any daylight is spill from off-camera - do not "
                   "draw a window, a reflection or a window-shaped patch of light on any wall here.")
    return "\n".join(out)


def context_block(project):
    b = project.get("brief", {}) or {}
    lines = [f"WHAT THIS ROOM IS:\n{b.get('what_it_is', 'A room in a home.')}"]
    if b.get("register"):
        lines.append(f"\nREGISTER: {b['register']} It must read as a real, lived-in place, "
                     f"not a styled magazine set.")
    keep = b.get("must_appear") or []
    if keep:
        lines.append("\nPERMANENT CONTENTS — present in EVERY image, never absent:")
        lines += [f"- {k}" for k in keep]
    return "\n".join(lines)


DEFAULT_RICHNESS = """RICHNESS AND DEPTH — the image must not look bare:
Render the DENSITY a real occupied home has, held in order by the design rather than tidied away:
- Layered textiles: a rug, cushions in two or three fabrics and scales, a folded throw, curtains
  with real weight.
- Things in use: a tray with cups, a jug, a newspaper or books, glasses, a bowl of fruit, a basket.
- Greenery: two or three potted plants at different heights, in clay, brass or glazed pots.
- Material richness rendered honestly: visible grain, the unevenness of hand-applied plaster, the
  weave of upholstery, patina on metal, the sheen of a polished floor. Dust-free but not sterile.
- LIGHT IN LAYERS, which is what makes an image read rich rather than flat: strong directional
  daylight falling across the floor and up a wall, PLUS at least three warm artificial sources
  actually switched on and visibly glowing. Real contrast, deep shadow in the corners, warm pools
  of light. Late afternoon or early evening reads best.
- Compose with depth: something close to the lens, the main furniture in the midground, and a lit
  focal object at the back.
It should still be ORDERED — designed, not messy. The test is that it looks like a home somebody
loves and keeps well, photographed on a good evening."""


QUALITY = ("Photoreal interior photograph of a real, occupied home. Full-frame camera, verticals "
           "kept vertical, f/8, natural daylight balanced against the designed artificial lighting, "
           "no HDR halos, no fisheye distortion, no people, no text, no watermark, no logos, "
           "correct perspective, physically plausible shadows and reflections, true furniture "
           "scale. 16:9 landscape.")


def build(project, spec, view):
    room = project.room()
    vc = project.view_cfg(view)
    camera = vc.get("camera", f"CAMERA: {view}.")
    moves = "\n".join(f"- {m['title']}: {m['detail']}" for m in spec.get("moves", []))
    palette = ", ".join(f"{c['name']} {c['hex']} ({c['use']})" for c in spec.get("palette", []))
    materials = ", ".join(spec.get("materials", []))
    scene = (spec.get("render", {}) or {}).get(view) \
        or (spec.get("render", {}) or {}).get("default") \
        or spec.get("thesis", "")
    richness = project.get("style.richness") or DEFAULT_RICHNESS
    newops = (spec.get("layout", {}) or {}).get("new_openings") or []
    newop = ("\n\nTHE ONE EXCEPTION TO THE OPENING LIST — this direction forms a NEW opening:\n  "
             + "\n  ".join(newops)) if newops else ""
    fixed = project.get("brief.fixed_furniture_note") or ""

    return f"""{QUALITY}

DESIGN DIRECTION {spec['id']} — {spec['name'].upper()}
{spec.get('tagline','')}

{shell_block(room, project)}{newop}

{scale_block(room)}

{context_block(project)}

{richness}

{camera}

{orientation_block(room, vc)}

WHAT THE ROOM HAS BECOME:
{scene}

HEADLINE INTERVENTIONS VISIBLE IN THIS IMAGE:
{moves}

WHERE THINGS SIT (this matches the attached measured drawing):
{spec.get('scale_check','')}

{('HOW THE RETAINED FURNITURE IS TREATED:' + chr(10) + (spec.get('retained_treatment') or spec.get('teak_treatment') or '')) if (spec.get('retained_treatment') or spec.get('teak_treatment')) else ''}
{fixed}

MATERIALS: {materials}
COLOUR PALETTE: {palette}
"""
