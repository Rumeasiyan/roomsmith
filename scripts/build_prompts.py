#!/usr/bin/env python3
"""Build image-generation prompts from brief/room.json + a direction spec.

Single source of truth. The opening inventory below is GENERATED from the room model, not typed
by hand, so a render prompt can never describe a door the room does not have.

    build_prompts.py                     # write prompts/<key>-<view>.txt for every direction
    build_prompts.py <key> <view>        # print one prompt to stdout
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECTIONS = ROOT / "directions"
PROMPTS = ROOT / "prompts"
ROOM = json.loads((ROOT / "brief" / "room.json").read_text())

W, L, H = ROOM["width"], ROOM["length"], ROOM["ceiling_height"]
ALC = ROOM["alcove"]

WALLNAME = {
    "entrance": "the ENTRANCE wall (the short wall you come in through)",
    "far": "the FAR wall (the short wall opposite the front door)",
    "left": "the entering-LEFT long wall",
    "right": "the entering-RIGHT long wall",
}


def openings_inventory():
    """The exhaustive, generated list of every opening. This is the anti-invention control."""
    lines = []
    for o in ROOM["openings"]:
        side = "left of centre" if o["pos"] < W / 2 else "right of centre"
        if o["wall"] in ("left", "right"):
            where = f'{o["pos"]:.2f} m from the entrance wall along {WALLNAME[o["wall"]]}'
        else:
            where = f'centred {o["pos"]:.2f} m from the entering-left corner, {side}, on {WALLNAME[o["wall"]]}'
        extra = f' {o["extra"]}.' if o.get("extra") else ""
        lines.append(
            f'  {o["tag"]} — {o["desc"]}. {o["width"]*1000:.0f} mm wide, '
            f'{(o["head"]-o["sill"])*1000:.0f} mm high'
            + (f', sill {o["sill"]*1000:.0f} mm above the floor' if o["sill"] else "")
            + f'. Located on {where}.{extra}'
        )
    nv_e = len([v for v in ROOM["vents"] if v["wall"] == "entrance"])
    nv_f = len([v for v in ROOM["vents"] if v["wall"] == "far"])
    return "\n".join(lines), nv_e, nv_f


OPENINGS, NV_E, NV_F = openings_inventory()


def solid_walls_clause():
    """Name every wall that has no openings at all. Generated, so it can never drift."""
    solid = [w for w in ("entrance", "far", "left", "right")
             if not [o for o in ROOM["openings"] if o["wall"] == w]]
    if not solid:
        return ""
    out = ["WALLS THAT ARE COMPLETELY SOLID — NO OPENING OF ANY KIND:"]
    for w in solid:
        vents = [v for v in ROOM["vents"] if v["wall"] == w]
        v = (f' Its only feature is {len(vents)} small pierced ventilation grille'
             f'{"s" if len(vents) != 1 else ""} high up near the ceiling.') if vents else ""
        out.append(f'  · {WALLNAME[w].upper()} is SOLID PLASTER from floor to ceiling.{v}')
    out.append("  There is NO window, NO door, NO archway, NO glazed panel and NO view of daylight,")
    out.append("  greenery or another room in any of those walls. If you can see outdoors anywhere")
    out.append("  except through the single window W1 on the entrance wall, the image is WRONG.")
    return "\n".join(out)


SOLID = solid_walls_clause()

SHELL = f"""THE REAL ROOM — these facts are fixed and must be true in the image:
- A SMALL NARROW family hall, {W:.2f} m wide and {L:.2f} m long, ceiling {H:.2f} m.
- On the entering-RIGHT flank there is a shallow ALCOVE: the wall steps out {ALC['depth']*1000:.0f} mm
  for {(ALC['y_end']-ALC['y_start'])*1000:.0f} mm of its length, starting {ALC['y_start']:.2f} m in from
  the entrance. THE SECOND WINDOW W2 SITS IN THE BACK WALL OF THIS ALCOVE, with two pierced
  ventilation grilles above it - so the alcove is a small daylit bay, the brightest corner of the
  room, and every direction should use it as such. The household's wall shrine sits on the alcove's
  entrance-side return wall.
- The entering-LEFT long wall is COMPLETELY SOLID — no door, no window, no opening of any kind. It is
  the wall that carries the family's curio cabinet and their framed photographs, and it is the wall
  with the damp problem.
- {NV_E} small pierced masonry ventilation grilles sit high on the entrance wall just under the
  ceiling line, and {NV_F} more sit high on the far wall. They stay unobstructed.
- A ceiling fan turns near the middle of the room.

THE COMPLETE LIST OF OPENINGS. THIS ROOM HAS EXACTLY {len(ROOM['openings'])} OPENINGS AND NO OTHERS:
{OPENINGS}

{SOLID}

DO NOT ADD ANY OPENING THAT IS NOT IN THAT LIST. No second window. No extra doorway. No opening in
the entering-LEFT long wall. No opening in the far wall. No pass-through, no internal window, no
glazed screen, no French doors, no skylight — unless the direction description below explicitly
says a NEW opening is being formed, in which case build only that one. Inventing an opening makes
the image useless, because the client cannot cut a door into a wall that has a neighbour behind it."""

SCALE = f"""SCALE DISCIPLINE — THE MOST IMPORTANT INSTRUCTION:
This room is CRAMPED. It is {W:.2f} m wide — about ten feet. A three-seat settee is 1.8 m wide, which
is well over half the width of the room. Furniture stands close to the walls and the walkway past it
is about 0.9 m. Both side walls are near the lens on either side of the frame. The far wall is only
{L:.2f} m away, so it reads as the end of a short room, not a distant vista.
Do NOT render a wide, airy, spacious interior. Do NOT widen the room, add floor area, add extra bays
or long empty runs of floor. If the image looks like a gallery, a loft, a hotel lobby, a showroom or
an architect's villa, it is WRONG. It should look tight, well organised and full but not chaotic —
a small room designed properly, furniture at true scale nearly touching the walls.
A MEASURED FLOOR PLAN OF THIS EXACT ROOM IS ATTACHED AS A REFERENCE IMAGE. Match it: the room's
proportion, the position of every opening, and where the furniture sits."""

CONTEXT = """WHAT THIS ROOM IS:
The front hall of a modest suburban family house. Visitors are received on the settee, the
family eats and the children study at a table, a household shrine is prayed at daily, family
photographs hang on the wall, and everyone walks through to reach the rest of the house. It must read
as a LIVED-IN FAMILY HOME — warm and occupied, not a styled magazine set.

PERMANENT CONTENTS — present in EVERY image, never absent:
- The inherited carved teak sofa set: a 1.8 m three-seat settee and two matching armchairs, turned and
  carved hardwood frames. They stay in this room. This direction may re-polish, re-stain and
  re-upholster them and may re-arrange them, but they are present.
- A low table in front of the settee.
- A table the family eats and studies at.
- The inherited carved teak glass-fronted curio cabinet holding the family's devotional statues,
  souvenirs and small framed portraits. It stays in this room.
- The household shrine with a crucifix or statue and a lit votive lamp, in daily use.
- Framed family and wedding photographs on the wall.
- Shoes near the front door."""

RICHNESS = """RICHNESS AND DEPTH - the images must not look bare:
This is a family home that has been lived in for decades, not an empty show flat. Render it with the
DENSITY a real occupied local house has, held in order by the design rather than tidied away:
- Layered textiles: a patterned or handwoven rug over the floor, cushions in two or three fabrics and
  scales, a folded throw over an arm, a runner on the table, curtains with real weight and folds.
- Things in use: a tea tray with cups, a covered dish, a jug of water, a newspaper, schoolbooks and a
  pencil tin, reading glasses, a bowl of mangoes or bananas, a basket, slippers by the door.
- The family's own objects densely present: the curio cabinet FULL of painted plaster saints, brass
  oil lamps, souvenirs and small framed portraits on every shelf; framed wedding and graduation
  photographs on the wall; a wall clock; a small brass or ceramic figure on a shelf.
- Greenery: two or three real potted plants at different heights - a palm or Dracaena on the floor, a
  small pot on a shelf, something trailing - in clay, brass or glazed pots.
- Devotion visible: a lit votive lamp with a real flame glow, fresh flowers or a small garland at the
  shrine, a rosary.
- Material richness rendered honestly: visible grain and carving shadow in the teak, the slight
  unevenness of hand-applied plaster, the weave of the upholstery, patina on brass, the sheen and
  faint mottling of a polished oxide floor, dust-free but not sterile.
- LIGHT IN LAYERS, and this is what makes an image read as rich rather than flat: strong directional
  daylight from a window falling across the floor and up a wall, PLUS at least three warm artificial
  sources actually switched on and visibly glowing - the lit curio cabinet, a pendant or wall lamp, a
  concealed cove or strip, the votive flame. Let there be real contrast, deep shadow in the corners
  and warm pools of light. Late afternoon or early evening reads best.
- Compose with depth: something close to the lens in the foreground, the main furniture in the
  midground, and a lit focal object at the back of the room.
It should still be ORDERED - designed, not messy, and never a hoarded room. The test is that it looks
like a home somebody loves and keeps well, photographed on a good evening."""

CAMERAS = {
    "hero-in": (
        "CAMERA — HERO, LOOKING IN. Standing with your back to the front door, {L:.2f} m of room in "
        "front of you, looking straight down the hall to the far wall. 28 mm lens, eye level 1.55 m. "
        "Both side walls crop the frame and the furniture along them is close and large. The alcove and "
        "the curtained doorway are on your RIGHT; the solid curio-and-photograph wall is on your LEFT; "
        "the arch to the rear corridor is at the far end of the RIGHT wall."
    ),
    "hero-back": (
        "CAMERA — HERO, LOOKING BACK. Standing at the far end of the room, looking back at the entrance "
        "wall {L:.2f} m away, with the front door and the window filling the end of the frame. 28 mm "
        "lens, eye level 1.55 m. The alcove and curtained doorway are now on your LEFT; the solid "
        "curio-and-photograph wall is on your RIGHT."
    ),
    "seated": (
        "CAMERA — FROM THE SETTEE. Seated on the settee about a third of the way down the room, eye "
        "level 1.15 m, looking across the narrow width of the room at the opposite wall, which is only "
        "about 2 m away. 35 mm lens. This is the view a visitor actually has. The opposite wall fills "
        "the frame; the ceiling and floor are both visible because the room is narrow."
    ),
    "corner": (
        "CAMERA — HIGH CORNER. From the entering-LEFT corner beside the front door, 1.85 m up, angled "
        "down and across the room toward the far arch. 24 mm lens. A three-quarter overview that shows "
        "the entrance wall, the whole entering-RIGHT flank with its alcove, and the floor plan of the "
        "furniture — a photographic equivalent of the dollhouse drawing."
    ),
    "alcove": (
        "CAMERA — THE ALCOVE AND SHRINE. Standing in the middle of the room about 2 m in from the front "
        "door, turned to face the entering-RIGHT flank square-on from about 2.4 m. 35 mm lens, eye "
        "level 1.55 m. Shows the alcove step-out, the curtained doorway inside it, the shrine, and how "
        "this direction treats that wall."
    ),
    "far-wall": (
        "CAMERA — THE FAR END. Standing about 2.5 m in from the front door, looking at the far wall and "
        "the arch in the corner beside it from about 3.5 m. 35 mm lens, eye level 1.55 m. Shows the "
        "family's eating and study table, the far wall with its two ventilation grilles, and the arch."
    ),
}

VIEWS = list(CAMERAS)

QUALITY = (
    "Photoreal interior photograph of a real, occupied, modest family home. Full-frame camera, "
    "verticals kept vertical, f/8, natural daylight from the single window balanced against the "
    "designed artificial lighting, no HDR halos, no fisheye or barrel distortion, no people, no text, "
    "no watermark, no logos, correct perspective, physically plausible shadows and reflections, true "
    "furniture scale against a {W:.2f} m wall-to-wall width. 16:9 landscape."
)


def load_all():
    return sorted((json.loads(p.read_text()) for p in DIRECTIONS.glob("[0-9][0-9]-*.json")),
                  key=lambda s: s["id"])


def build(spec, view):
    moves = "\n".join(f"- {m['title']}: {m['detail']}" for m in spec["moves"])
    palette = ", ".join(f"{c['name']} {c['hex']} ({c['use']})" for c in spec["palette"])
    materials = ", ".join(spec["materials"])
    scene = spec["render"].get(view) or spec["render"].get("a", "")
    newops = spec.get("layout", {}).get("new_openings") or []
    newop_txt = ("\n\nTHE ONE EXCEPTION TO THE OPENING LIST — this direction forms a NEW opening:\n  "
                 + "\n  ".join(newops)) if newops else ""
    layout_note = spec.get("scale_check", "")

    return f"""{QUALITY.format(W=W)}

DESIGN DIRECTION {spec['id']} - {spec['name'].upper()}
{spec['tagline']}

{SHELL}{newop_txt}

{SCALE}

{CONTEXT}

{RICHNESS}

{CAMERAS[view].format(L=L)}

WHAT THE ROOM HAS BECOME:
{scene}

HEADLINE INTERVENTIONS VISIBLE IN THIS IMAGE:
{moves}

WHERE THINGS SIT (this matches the attached measured plan):
{layout_note}

HOW THE INHERITED CARVED TEAK FURNITURE IS TREATED:
{spec.get('teak_treatment', 'Re-polished and re-upholstered, retained in place.')}

MATERIALS: {materials}
COLOUR PALETTE: {palette}

WHAT CHANGES FROM THE BEFORE STATE: the brown stencilled coffered ceiling, the dated floral
upholstery, the lace curtains, the bare bulkhead lamps, the surface conduit and the general clutter
are gone. The carved teak settee, armchairs, curio cabinet, a low table, the shrine, the family
photographs and the ceiling fan REMAIN - reworked as described above, never absent.
"""


def main():
    if len(sys.argv) == 3:
        key, view = sys.argv[1], sys.argv[2]
        for spec in load_all():
            if key in (spec["slug"], f"{spec['id']}-{spec['slug']}", spec["id"]):
                sys.stdout.write(build(spec, view))
                return
        sys.exit(f"no direction matching {key!r}")

    PROMPTS.mkdir(exist_ok=True)
    n = 0
    for spec in load_all():
        for view in VIEWS:
            (PROMPTS / f"{spec['id']}-{spec['slug']}-{view}.txt").write_text(build(spec, view))
            n += 1
    print(f"wrote {n} prompts to {PROMPTS}")


if __name__ == "__main__":
    main()
