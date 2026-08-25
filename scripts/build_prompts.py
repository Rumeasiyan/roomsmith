#!/usr/bin/env python3
"""Build image-generation prompts from direction specs.

Single source of truth: the render prompt and the PDF report are both derived from
directions/NN-slug.json, so a render can never describe something the report does not.

Usage:
    build_prompts.py                 # write prompts/<slug>-<view>.txt for every direction
    build_prompts.py <slug> <view>   # print one prompt to stdout
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DIRECTIONS = ROOT / "directions"
PROMPTS = ROOT / "prompts"

# Facts about the physical shell that must survive every direction, so that all 40 images
# are recognisably the SAME room. Without this the set becomes twenty unrelated rooms.
SHELL = """FIXED ARCHITECTURE OF THIS REAL ROOM - these must be true in the image:
- A SMALL, NARROW family hall: only 3.12 m wall to wall and 6.25 m long. Ceiling 2.9 m.
- Short entrance wall carries a timber double-leaf front door slightly left of centre, and a
  single timber-framed window to its right with a sill about 0.85 m above the floor.
- The opposite short wall carries a plastered arched opening to a rear corridor, positioned
  left of centre.
- The left flank wall has a doorway to a side corridor near the entrance end, and a shallow
  recess further down.
- Three small pierced masonry ventilation grilles sit high on the walls just under the
  ceiling line and remain unobstructed.
- A ceiling fan turns on the centreline."""

# The two failure modes this project keeps hitting: the room drawn far larger than it is,
# and the room drawn as a gallery instead of a local family front room.
SCALE = """SCALE DISCIPLINE - THE SINGLE MOST IMPORTANT INSTRUCTION:
This room is CRAMPED. It is 3.12 m wide - roughly ten feet. A three-seat settee is 1.8 m
wide, which is well over half the width of the room. Furniture is close to the walls, the
walkway past it is about 0.9 m, and both side walls are near the lens on either side of the
frame. The far wall is only 6.25 m from the camera, so the arched opening reads as a normal
domestic doorway, NOT a distant vista.
Do NOT render a wide, airy, spacious interior. Do NOT widen the room. Do NOT add floor area,
extra bays, extra windows, double-height space or long empty runs of floor. If the image
looks like a gallery, a loft, a hotel lobby, a showroom or an architect's villa, it is WRONG.
It should look tight, well-organised and full but not chaotic - a small room that has been
designed properly, with furniture at true scale nearly touching the walls."""

CONTEXT = """WHAT THIS ROOM IS:
The front hall of a modest suburban family house. It is where visitors are
received on the settee, where the family eats and the children study at a table, where a
household shrine is prayed at daily, where family photographs hang, and where everyone walks
through to reach the rest of the house. It must read as a LIVED-IN FAMILY HOME, warm and
occupied, not as a styled magazine set.

PERMANENT CONTENTS - these appear in EVERY image and may never be absent:
- The inherited carved teak sofa set: a 1.8 m three-seat settee and two matching armchairs,
  turned and carved hardwood frames. They stay in this room. This direction may re-polish,
  re-stain and re-upholster them, and may re-arrange them, but they are present.
- A low table in front of the settee.
- A table the family eats and studies at.
- The inherited carved teak glass-fronted curio cabinet holding the family's devotional
  statues, souvenirs and small framed portraits. It stays in this room, though it may be
  re-finished, re-glazed, re-lit or re-positioned.
- The household shrine with a crucifix or statue and a lit votive lamp, in daily use.
- Framed family and wedding photographs on the wall.
- Shoes near the front door."""

CAMERAS = {
    "a": (
        "CAMERA VIEW A: standing with your back against the main double door - only 6.25 m of "
        "room in front of you - looking down the hall toward the far arched opening. 28 mm lens, "
        "eye level 1.55 m. Both side walls are close on either side and crop the frame; furniture "
        "along them is near the camera and large in the frame. The far arch is a normal domestic "
        "doorway at the end of a short room, not a distant vanishing point."
    ),
    "b": (
        "CAMERA VIEW B: standing in the far arched opening, looking back toward the main double "
        "door and the window beside it, 6.25 m away. 28 mm lens, eye level 1.55 m. The entrance "
        "wall with its door and window fills the end of the frame at close range; the side walls "
        "crop both edges."
    ),
}

QUALITY = (
    "Photoreal interior photograph of a real, occupied, modest family home. Full-frame camera, "
    "28 mm lens, verticals kept vertical, tripod height 1.55 m, f/8, natural daylight from the "
    "single window balanced against the designed artificial lighting, no HDR halos, no fisheye "
    "or barrel distortion, no people, no text, no watermark, no logos, correct one-point "
    "perspective, physically plausible shadows and reflections, true furniture scale against a "
    "3.12 m wall-to-wall width. 16:9 landscape."
)


def load_all():
    out = []
    for p in sorted(DIRECTIONS.glob("[0-9][0-9]-*.json")):
        out.append(json.loads(p.read_text()))
    return out


def build(spec, view):
    scene = spec["render"][view]
    moves = "\n".join(f"- {m['title']}: {m['detail']}" for m in spec["moves"])
    palette = ", ".join(f"{c['name']} {c['hex']} ({c['use']})" for c in spec["palette"])
    materials = ", ".join(spec["materials"])
    return f"""{QUALITY}

DESIGN DIRECTION {spec['id']} - {spec['name'].upper()}
{spec['tagline']}

{SHELL}

{SCALE}

{CONTEXT}

{CAMERAS[view]}

WHAT THE ROOM HAS BECOME:
{scene}

HEADLINE INTERVENTIONS VISIBLE IN THIS IMAGE:
{moves}

HOW THE INHERITED CARVED TEAK FURNITURE IS TREATED IN THIS DIRECTION:
{spec.get('teak_treatment', 'Re-polished and re-upholstered, retained in place.')}

MATERIALS: {materials}
COLOUR PALETTE: {palette}

WHAT CHANGES FROM THE BEFORE STATE: the brown stencilled coffered ceiling, the dated floral
upholstery, the lace curtains, the bare bulkhead lamps, the surface conduit and the general
clutter are gone. The carved teak settee, armchairs, curio cabinet, a low table, the shrine,
the family photographs and the ceiling fan REMAIN - reworked as described above, never absent.
"""


def main():
    if len(sys.argv) == 3:
        slug, view = sys.argv[1], sys.argv[2]
        for spec in load_all():
            if spec["slug"] == slug or f"{spec['id']}-{spec['slug']}" == slug:
                sys.stdout.write(build(spec, view))
                return
        sys.exit(f"no direction matching {slug!r}")

    PROMPTS.mkdir(exist_ok=True)
    n = 0
    for spec in load_all():
        for view in ("a", "b"):
            out = PROMPTS / f"{spec['id']}-{spec['slug']}-{view}.txt"
            out.write_text(build(spec, view))
            n += 1
    print(f"wrote {n} prompts to {PROMPTS}")


if __name__ == "__main__":
    main()
