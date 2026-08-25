#!/usr/bin/env python3
"""Generate measured drawings for a direction: plan, blueprint, four wall elevations, isometric.

These are DRAWN BY CODE from brief/room.json and the direction's `layout` block. They are not
generated images, so they cannot invent a door, move a window or enlarge the room. They are also
used as dimensional reference images for the photoreal renders.

    drawings.py <NN-slug>        # write drawings/<NN-slug>-{plan,blueprint,elev-*,iso}.svg + .png
    drawings.py --shell          # write drawings/_shell-*.svg+png (the empty room, no direction)
"""
import json
import math
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
DRAW = ROOT / "drawings"
ROOM = json.loads((ROOT / "brief" / "room.json").read_text())

W = ROOM["width"]
L = ROOM["length"]
H = ROOM["ceiling_height"]
ALC = ROOM["alcove"]

INK = "#16181d"
MID = "#7b8189"
LIGHT = "#c8ccd2"
PAPER = "#fbfaf7"
ACCENT = "#a1442c"
FURN = "#e2ddd2"
JOIN = "#c9b98f"

BLUE_BG = "#123a63"
BLUE_LINE = "#dbe7f3"
BLUE_FAINT = "#6f93b8"

FONT = "'Helvetica Neue',Helvetica,Arial,sans-serif"


# ---------------------------------------------------------------- geometry helpers

def wall_openings(wall):
    return [o for o in ROOM["openings"] if o["wall"] == wall]


def wall_vents(wall):
    return [v for v in ROOM["vents"] if v["wall"] == wall]


def wall_run(wall):
    """Length of a wall in its own elevation coordinates."""
    return W if wall in ("entrance", "far") else L


def plan_outline():
    """Room outline as a list of (x, y), including the alcove step-out on the right flank."""
    a0, a1, d = ALC["y_start"], ALC["y_end"], ALC["depth"]
    if ALC["wall"] == "right":
        return [(0, 0), (W, 0), (W, a0), (W + d, a0), (W + d, a1), (W, a1), (W, L), (0, L)]
    return [(0, 0), (W, 0), (W, L), (0, L), (0, a1), (-d, a1), (-d, a0), (0, a0)]


def alcove_x(y):
    """Right-hand wall X at a given Y - accounts for the alcove."""
    if ALC["wall"] == "right" and ALC["y_start"] <= y <= ALC["y_end"]:
        return W + ALC["depth"]
    return W


# ---------------------------------------------------------------- svg helpers

def svg(w, h, body, bg=PAPER):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}"><rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>')


def t(x, y, s, size=11, fill=INK, anchor="start", weight=400, rot=None, ls=0):
    r = f' transform="rotate({rot} {x} {y})"' if rot is not None else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" font-size="{size}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" letter-spacing="{ls}"{r}>{s}</text>')


def line(x1, y1, x2, y2, stroke=INK, w=1, dash=None, cap="butt"):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
            f'stroke-width="{w}" stroke-linecap="{cap}"{d}/>')


def rect(x, y, w, h, fill="none", stroke=INK, sw=1, dash=None, rx=0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{max(w,0):.1f}" height="{max(h,0):.1f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"{d}/>')


def poly(pts, fill="none", stroke=INK, sw=1, dash=None):
    p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<polygon points="{p}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def path(d_, fill="none", stroke=INK, sw=1, dash=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<path d="{d_}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"{da}/>'


def dim(x1, y1, x2, y2, label, off=0, colour=MID, size=9, flip=False):
    """A dimension line with ticks and a centred label."""
    out = [line(x1, y1, x2, y2, colour, 0.7)]
    ang = math.degrees(math.atan2(y2 - y1, x2 - x1))
    for (px, py) in ((x1, y1), (x2, y2)):
        out.append(f'<line x1="{px-4:.1f}" y1="{py-4:.1f}" x2="{px+4:.1f}" y2="{py+4:.1f}" '
                   f'stroke="{colour}" stroke-width="0.9" transform="rotate({ang} {px} {py})"/>')
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    if abs(ang) > 60:
        out.append(t(mx - 4, my, label, size, colour, "middle", 500, rot=-90))
    else:
        out.append(t(mx, my - 4 + off, label, size, colour, "middle", 500))
    return "".join(out)


def mm(v):
    return f"{v*1000:.0f}"


# ---------------------------------------------------------------- PLAN

def draw_plan(spec=None, blueprint=False):
    S = 118.0                      # px per metre
    ml, mt = 130, 118              # margins
    total_w = W + ALC["depth"]
    ww = int(total_w * S + ml + 210)
    hh = int(L * S + mt + 140)

    ink = BLUE_LINE if blueprint else INK
    mid = BLUE_FAINT if blueprint else MID
    faint = BLUE_FAINT if blueprint else LIGHT
    bg = BLUE_BG if blueprint else PAPER
    fill_room = "none" if blueprint else "#ffffff"
    fill_furn = "none" if blueprint else FURN
    fill_join = "none" if blueprint else JOIN

    def px(x, y):
        return ml + x * S, mt + y * S

    o = []

    # grid
    if blueprint:
        for gx in range(0, int(total_w * 2) + 2):
            X, _ = px(gx / 2, 0)
            o.append(line(X, mt, X, mt + L * S, "#1d4c7d", 0.6))
        for gy in range(0, int(L * 2) + 2):
            _, Y = px(0, gy / 2)
            o.append(line(ml, Y, ml + total_w * S, Y, "#1d4c7d", 0.6))

    # wall poison: draw the room as a thick-walled outline
    pts = [px(x, y) for x, y in plan_outline()]
    o.append(poly(pts, fill_room, ink, 3.2))

    # 225 mm wall thickness shown outside the internal face
    tw = 0.225 * S
    outer = []
    for (x, y) in plan_outline():
        ox = x - tw if x <= 0.01 else x + tw
        oy = y - tw if y <= 0.01 else (y + tw if y >= L - 0.01 else y)
        outer.append(px(ox, oy))
    o.append(poly(outer, "none", mid, 1.0))

    # ---- openings, cut through the wall line
    for op in ROOM["openings"]:
        wall, p, w_ = op["wall"], op["pos"], op["width"]
        if wall == "entrance":
            x1, y1 = px(p - w_ / 2, 0)
            x2, _ = px(p + w_ / 2, 0)
            o.append(line(x1, y1, x2, y1, bg, 5.0))
            o.append(line(x1, y1, x2, y1, ACCENT if not blueprint else BLUE_LINE, 2.2))
            if op["type"] == "door":                      # leaf + swing, opens inward
                o.append(path(f"M {x1:.1f} {y1:.1f} L {x1:.1f} {y1 + w_*S/2:.1f}", stroke=mid, sw=1.2))
                o.append(path(f"M {x2:.1f} {y1:.1f} L {x2:.1f} {y1 + w_*S/2:.1f}", stroke=mid, sw=1.2))
                o.append(path(f"M {x1:.1f} {y1 + w_*S/2:.1f} A {w_*S/2:.1f} {w_*S/2:.1f} 0 0 1 "
                              f"{x1 + w_*S/2:.1f} {y1:.1f}", stroke=mid, sw=0.7, dash="3 3"))
                o.append(path(f"M {x2:.1f} {y1 + w_*S/2:.1f} A {w_*S/2:.1f} {w_*S/2:.1f} 0 0 0 "
                              f"{x2 - w_*S/2:.1f} {y1:.1f}", stroke=mid, sw=0.7, dash="3 3"))
            o.append(t((x1 + x2) / 2, y1 - 12, op["tag"], 11, ACCENT if not blueprint else BLUE_LINE,
                       "middle", 700))
        else:                                              # right flank
            xw = alcove_x(p)
            x1, y1 = px(xw, p - w_ / 2)
            _, y2 = px(xw, p + w_ / 2)
            o.append(line(x1, y1, x1, y2, bg, 5.0))
            o.append(line(x1, y1, x1, y2, ACCENT if not blueprint else BLUE_LINE, 2.2))
            if op["type"] == "arch":
                o.append(path(f"M {x1:.1f} {y1:.1f} q {12} {(y2-y1)/2:.1f} 0 {(y2-y1):.1f}",
                              stroke=mid, sw=0.8, dash="3 3"))
            o.append(t(x1 + 14, (y1 + y2) / 2 + 4, op["tag"], 11,
                       ACCENT if not blueprint else BLUE_LINE, "start", 700))

    # ---- vents (dashed, above head height)
    for v in ROOM["vents"]:
        if v["wall"] == "entrance":
            x1, y1 = px(v["pos"] - v["width"] / 2, 0)
            x2, _ = px(v["pos"] + v["width"] / 2, 0)
            o.append(line(x1, y1 - 4, x2, y1 - 4, mid, 1.6, dash="2 2"))
        elif v["wall"] == "far":
            x1, y1 = px(v["pos"] - v["width"] / 2, L)
            x2, _ = px(v["pos"] + v["width"] / 2, L)
            o.append(line(x1, y1 + 4, x2, y1 + 4, mid, 1.6, dash="2 2"))

    # ---- fan
    f = ROOM["existing"]["fan"]
    fx, fy = px(f["x"], f["y"])
    r = f["blade_span"] / 2 * S
    o.append(f'<circle cx="{fx:.1f}" cy="{fy:.1f}" r="{r:.1f}" fill="none" stroke="{mid}" '
             f'stroke-width="0.8" stroke-dasharray="4 4"/>')
    o.append(t(fx, fy + 4, "FAN", 8, mid, "middle", 600))

    # ---- direction layout
    if spec and spec.get("layout"):
        for it in spec["layout"].get("plan", []):
            x, y = it["x"], it["y"]
            w_, d_ = it["w"], it["d"]
            X, Y = px(x, y)
            fillc = fill_join if it.get("kind") == "built" else fill_furn
            o.append(rect(X, Y, w_ * S, d_ * S, fillc, ink, 1.3))
            lbl = it.get("label", "")
            if lbl:
                cx, cy = X + w_ * S / 2, Y + d_ * S / 2 + 3
                rotate = -90 if d_ > w_ * 1.6 else None
                o.append(t(cx, cy, lbl.upper(), 8, ink, "middle", 600, rot=rotate, ls=0.4))

    # ---- circulation spine
    if spec and spec.get("layout", {}).get("route"):
        rt = [px(p[0], p[1]) for p in spec["layout"]["route"]]
        d_ = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in rt)
        o.append(path(d_, stroke=ACCENT if not blueprint else "#7fd4ff", sw=2.0, dash="7 5"))
        mx, my = rt[len(rt) // 2]
        o.append(t(mx + 8, my, "circulation", 8.5, ACCENT if not blueprint else "#7fd4ff", "start", 600))

    # ---- dimensions
    o.append(dim(*px(0, -0.42), *px(W, -0.42), f"{mm(W)} — room width", colour=mid))
    o.append(dim(*px(-0.42, 0), *px(-0.42, L), f"{mm(L)} — room length", colour=mid))
    ax0, ay0 = px(W + ALC["depth"] + 0.30, ALC["y_start"])
    ax1, ay1 = px(W + ALC["depth"] + 0.30, ALC["y_end"])
    o.append(dim(ax0, ay0, ax1, ay1, f'{mm(ALC["y_end"]-ALC["y_start"])} alcove', colour=mid))
    o.append(dim(*px(W, ALC["y_start"] - 0.30), *px(W + ALC["depth"], ALC["y_start"] - 0.30),
                 mm(ALC["depth"]), colour=mid))

    # ---- title block
    ttl = f"{spec['id']} {spec['name']}" if spec else "Existing shell"
    o.append(line(ml, mt + L * S + 46, ml + total_w * S, mt + L * S + 46, ink, 1.4))
    o.append(t(ml, mt + L * S + 38, "FLOOR PLAN" + ("  ·  BLUEPRINT" if blueprint else ""),
               13, ink, "start", 700, ls=2.2))
    o.append(t(ml, mt + L * S + 62, ttl, 11, mid))
    o.append(t(ml, mt + L * S + 78, f"Scale 1:{1000/S*10:.0f} at A4  ·  all dimensions in mm  ·  "
                                    f"north of the plan is the far wall", 8.5, mid))
    o.append(t(ml + total_w * S, mt + L * S + 38, f"{W*L:.1f} m²", 13, ink, "end", 700))

    # compass-ish entry marker
    ex, ey = px(1.35, -0.05)
    o.append(t(ex, ey - 26, "▼  ENTER", 9, ACCENT if not blueprint else "#7fd4ff", "middle", 700, ls=1.2))

    return svg(ww, hh, "".join(o), bg)


# ---------------------------------------------------------------- ELEVATIONS

def derive_elevation(spec, wall):
    """Elevation elements inferred from the plan, so plan and elevation cannot disagree."""
    out, eps = [], 0.08
    for it in spec.get("layout", {}).get("plan", []):
        x, y, w_, d_ = it["x"], it["y"], it["w"], it["d"]
        z, h = it.get("z", 0.0), it.get("h", 0.45)
        hit = None
        if wall == "left" and x <= eps:
            hit = (y, d_)
        elif wall == "right" and x + w_ >= alcove_x(y + d_ / 2) - eps:
            hit = (y, d_)
        elif wall == "entrance" and y <= eps:
            hit = (x, w_)
        elif wall == "far" and y + d_ >= L - eps:
            hit = (x, w_)
        if hit:
            out.append({"u": hit[0], "w": hit[1], "z": z, "h": h,
                        "label": it.get("label", ""), "kind": it.get("kind", "")})
    return out


WALL_TITLE = {
    "entrance": "Elevation A — entrance wall (front door and window)",
    "far": "Elevation C — far wall",
    "left": "Elevation D — entering-LEFT long wall (curio and photographs; damp wall)",
    "right": "Elevation B — entering-RIGHT long wall (alcove, curtained doorway, arch)",
}


def draw_elevation(wall, spec=None):
    S = 132.0
    run = wall_run(wall)
    ml, mt = 118, 96
    ww = int(run * S + ml + 150)
    hh = int(H * S + mt + 150)

    def px(u, z):
        """u along the wall, z above floor."""
        return ml + u * S, mt + (H - z) * S

    o = []
    # floor / ceiling / wall box
    o.append(rect(ml, mt, run * S, H * S, "#ffffff", INK, 2.4))
    o.append(line(ml - 30, mt + H * S, ml + run * S + 30, mt + H * S, INK, 3.0))
    o.append(t(ml - 34, mt + H * S + 14, "FFL", 8.5, MID, "end", 600))
    o.append(line(ml - 20, mt, ml + run * S + 20, mt, MID, 0.9, dash="6 4"))
    o.append(t(ml - 24, mt + 4, "CEILING", 8.5, MID, "end", 600))

    # cornice line of the existing coffered ceiling
    _, cz = px(0, H - 0.16)
    o.append(line(ml, cz, ml + run * S, cz, LIGHT, 1.0, dash="3 3"))

    # openings on this wall
    for op in wall_openings(wall):
        x1, y1 = px(op["pos"] - op["width"] / 2, op["head"])
        x2, y2 = px(op["pos"] + op["width"] / 2, op["sill"])
        if op["type"] == "arch":
            rr = op["width"] / 2 * S
            spring = y2 - (op["head"] - op["width"] / 2) * S + 0  # visual only
            o.append(path(f"M {x1:.1f} {y2:.1f} L {x1:.1f} {y1+rr:.1f} "
                          f"A {rr:.1f} {rr:.1f} 0 0 1 {x2:.1f} {y1+rr:.1f} L {x2:.1f} {y2:.1f}",
                          "#f4f1ea", ACCENT, 2.0))
        else:
            o.append(rect(x1, y1, x2 - x1, y2 - y1, "#f4f1ea", ACCENT, 2.0))
        if op["type"] == "door":
            xm = (x1 + x2) / 2
            o.append(line(xm, y1, xm, y2, ACCENT, 1.0))
            if op.get("extra"):
                _, ty = px(0, 2.40)
                o.append(rect(x1, ty, x2 - x1, y1 - ty, "none", ACCENT, 1.2))
                for i in range(1, 9):
                    xx = x1 + (x2 - x1) * i / 9
                    o.append(line(xx, ty + 2, xx, y1 - 2, ACCENT, 0.8))
        o.append(t((x1 + x2) / 2, y2 + 16, f'{op["tag"]}  {mm(op["width"])}×{mm(op["head"]-op["sill"])}',
                   8.5, ACCENT, "middle", 600))
        if op["sill"] > 0:
            o.append(t(x2 + 6, (y1 + y2) / 2, f'sill {mm(op["sill"])}', 8, MID, "start"))

    # vents
    for v in wall_vents(wall):
        x1, y1 = px(v["pos"] - v["width"] / 2, v["z"] + v["height"])
        x2, y2 = px(v["pos"] + v["width"] / 2, v["z"])
        o.append(rect(x1, y1, x2 - x1, y2 - y1, "#eef1f4", MID, 1.2))
        for i in range(1, 6):
            xx = x1 + (x2 - x1) * i / 6
            o.append(line(xx, y1 + 1.5, xx, y2 - 1.5, MID, 0.6))
        o.append(t((x1 + x2) / 2, y1 - 5, v["tag"], 7.5, MID, "middle", 600))

    # alcove extent shown on the right elevation
    if wall == "right":
        for yv in (ALC["y_start"], ALC["y_end"]):
            X, _ = px(yv, 0)
            o.append(line(X, mt, X, mt + H * S, MID, 0.8, dash="5 4"))
        x1, _ = px(ALC["y_start"], 0)
        x2, _ = px(ALC["y_end"], 0)
        o.append(t((x1 + x2) / 2, mt + 16, f'ALCOVE — {mm(ALC["depth"])} DEEP', 8.5, MID, "middle", 700, ls=1))

    # direction elements on this wall
    if spec and spec.get("layout"):
        for el in spec["layout"].get("elevations", {}).get(wall) or derive_elevation(spec, wall):
            x1, y1 = px(el["u"], el["z"] + el["h"])
            x2, y2 = px(el["u"] + el["w"], el["z"])
            fillc = JOIN if el.get("kind") == "built" else FURN
            o.append(rect(x1, y1, x2 - x1, y2 - y1, fillc, INK, 1.4))
            o.append(t((x1 + x2) / 2, (y1 + y2) / 2 + 3, el.get("label", "").upper(), 8, INK,
                       "middle", 600, ls=0.3))
            o.append(t((x1 + x2) / 2, y2 + 12, f'{mm(el["w"])}w × {mm(el["h"])}h', 7.5, MID, "middle"))

    # dimensions
    o.append(dim(ml, mt + H * S + 46, ml + run * S, mt + H * S + 46, f"{mm(run)} wall length"))
    o.append(dim(ml - 46, mt, ml - 46, mt + H * S, f"{mm(H)} floor to ceiling"))

    # title
    o.append(line(ml, mt + H * S + 82, ml + run * S, mt + H * S + 82, INK, 1.4))
    o.append(t(ml, mt + H * S + 76, WALL_TITLE[wall].upper(), 11, INK, "start", 700, ls=1.4))
    ttl = f"{spec['id']} {spec['name']}" if spec else "Existing shell"
    o.append(t(ml, mt + H * S + 98, ttl + "  ·  dimensions in mm  ·  viewed square-on from inside the room",
               8.5, MID))
    return svg(ww, hh, "".join(o))


# ---------------------------------------------------------------- ISOMETRIC / DOLLHOUSE

def draw_iso(spec=None, flip=False):
    """Axonometric cutaway: two walls removed so the room reads like a dollhouse."""
    ww, hh = 1240, 980
    pad, foot = 90, 130
    ca, sa = math.cos(math.radians(30)), 0.62

    def raw(x, y, z):
        sx = (y - x) * ca if flip else (x - y) * ca
        sy = (x + y) * sa - z
        return sx, sy

    # Auto-fit: project the bounding volume, then scale and centre it on the canvas.
    corners = [(x, y, z) for x, y in plan_outline() + [(0, 0), (W, L)] for z in (0, H)]
    rx = [raw(*c)[0] for c in corners]
    ry = [raw(*c)[1] for c in corners]
    S = min((ww - 2 * pad) / (max(rx) - min(rx)), (hh - pad - foot) / (max(ry) - min(ry)))
    ml = pad - min(rx) * S + ((ww - 2 * pad) - (max(rx) - min(rx)) * S) / 2
    mt = pad - min(ry) * S

    def p3(x, y, z):
        sx, sy = raw(x, y, z)
        return ml + sx * S, mt + sy * S

    o = []

    def quad(a, b, c, d, fill, stroke=INK, sw=1.2, op=1.0):
        pts = [p3(*a), p3(*b), p3(*c), p3(*d)]
        s = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        return (f'<polygon points="{s}" fill="{fill}" fill-opacity="{op}" stroke="{stroke}" '
                f'stroke-width="{sw}" stroke-linejoin="round"/>')

    # floor, including alcove
    fl = [p3(x, y, 0) for x, y in plan_outline()]
    o.append('<polygon points="' + " ".join(f"{x:.1f},{y:.1f}" for x, y in fl) +
             f'" fill="#efe7dd" stroke="{INK}" stroke-width="1.6"/>')

    # the two walls we keep: entering-LEFT (x=0) and the FAR wall (y=L)
    o.append(quad((0, 0, 0), (0, L, 0), (0, L, H), (0, 0, H), "#f7f5f0"))
    o.append(quad((0, L, 0), (W, L, 0), (W, L, H), (0, L, H), "#eeece6"))

    # ghost the two removed walls
    o.append(quad((W, 0, 0), (W, L, 0), (W, L, H), (W, 0, H), "none", LIGHT, 0.8))
    o.append(quad((0, 0, 0), (W, 0, 0), (W, 0, H), (0, 0, H), "none", LIGHT, 0.8))

    # openings drawn onto the kept walls, and ghosted on the removed ones
    for op_ in ROOM["openings"]:
        w_, s_, h_ = op_["width"], op_["sill"], op_["head"]
        p = op_["pos"]
        if op_["wall"] == "entrance":
            o.append(quad((p - w_/2, 0, s_), (p + w_/2, 0, s_), (p + w_/2, 0, h_), (p - w_/2, 0, h_),
                          "none", ACCENT, 1.4))
            xx, yy = p3(p, 0, h_ + 0.12)
            o.append(t(xx, yy, op_["tag"], 10, ACCENT, "middle", 700))
        else:
            xw = alcove_x(p)
            o.append(quad((xw, p - w_/2, s_), (xw, p + w_/2, s_), (xw, p + w_/2, h_), (xw, p - w_/2, h_),
                          "#dfe6ee", ACCENT, 1.4))
            xx, yy = p3(xw, p, h_ + 0.12)
            o.append(t(xx, yy, op_["tag"], 10, ACCENT, "middle", 700))

    for v in ROOM["vents"]:
        if v["wall"] == "far":
            o.append(quad((v["pos"] - v["width"]/2, L, v["z"]), (v["pos"] + v["width"]/2, L, v["z"]),
                          (v["pos"] + v["width"]/2, L, v["z"] + v["height"]),
                          (v["pos"] - v["width"]/2, L, v["z"] + v["height"]), "#e6eaee", MID, 0.9))

    # furniture as extruded boxes, painter-sorted back to front
    items = []
    if spec and spec.get("layout"):
        for it in spec["layout"].get("plan", []):
            items.append(it)
    items.sort(key=lambda i: -(i["x"] + i["y"] + i.get("w", 0) / 2 + i.get("d", 0) / 2))

    for it in items:
        x, y, w_, d_ = it["x"], it["y"], it["w"], it["d"]
        z0 = it.get("z", 0.0)
        hgt = it.get("h", 0.45)
        z1 = z0 + hgt
        base = "#d8cfbe" if it.get("kind") != "built" else "#c9b98f"
        top = "#efe8da" if it.get("kind") != "built" else "#ddcfa8"
        side = "#c2b9a6" if it.get("kind") != "built" else "#b3a37b"
        o.append(quad((x, y, z1), (x + w_, y, z1), (x + w_, y + d_, z1), (x, y + d_, z1), top, INK, 1.0))
        o.append(quad((x, y + d_, z0), (x + w_, y + d_, z0), (x + w_, y + d_, z1), (x, y + d_, z1),
                      side, INK, 1.0))
        o.append(quad((x + w_, y, z0), (x + w_, y + d_, z0), (x + w_, y + d_, z1), (x + w_, y, z1),
                      base, INK, 1.0))
        cx, cy = p3(x + w_ / 2, y + d_ / 2, z1 + 0.06)
        if it.get("label"):
            o.append(t(cx, cy, it["label"].upper(), 7.5, INK, "middle", 600, ls=0.3))

    # fan
    f = ROOM["existing"]["fan"]
    fx, fy = p3(f["x"], f["y"], H - 0.35)
    o.append(f'<ellipse cx="{fx:.1f}" cy="{fy:.1f}" rx="{f["blade_span"]/2*S*1.15:.1f}" '
             f'ry="{f["blade_span"]/2*S*0.42:.1f}" fill="none" stroke="{MID}" stroke-width="1" '
             f'stroke-dasharray="4 4"/>')

    # dimension rails
    a = p3(0, 0, 0); b = p3(W, 0, 0); c = p3(0, L, 0)
    o.append(dim(a[0], a[1] + 34, b[0], b[1] + 34, f"{mm(W)}"))
    o.append(dim(a[0] - 34, a[1], c[0] - 34, c[1], f"{mm(L)}"))

    ttl = f"{spec['id']} {spec['name']}" if spec else "Existing shell"
    o.append(line(70, hh - 76, ww - 70, hh - 76, INK, 1.4))
    o.append(t(70, hh - 82, "ISOMETRIC CUTAWAY — DOLLHOUSE VIEW", 13, INK, "start", 700, ls=2.2))
    o.append(t(70, hh - 58, ttl + "  ·  entering-right flank and entrance wall removed to show the room",
               10, MID))
    o.append(t(70, hh - 42, "Drawn to scale from brief/room.json. Openings D1, W1, D2 and A1 are the only "
                            "openings in this room.", 9, MID))
    return svg(ww, hh, "".join(o))


# ---------------------------------------------------------------- output

def rasterise(svg_path, png_path, width):
    chrome = next((c for c in ("google-chrome", "chromium", "chromium-browser")
                   if subprocess.run(["which", c], capture_output=True).returncode == 0), None)
    if not chrome:
        return False
    txt = svg_path.read_text()
    w = int(txt.split('width="')[1].split('"')[0])
    h = int(txt.split('height="')[1].split('"')[0])
    scale = width / w
    html = svg_path.with_suffix(".html")
    html.write_text(f'<html><body style="margin:0">{txt}</body></html>')
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                    f"--force-device-scale-factor={scale:.4f}",
                    f"--window-size={w},{h}", f"--screenshot={png_path}", html.as_uri()],
                   capture_output=True)
    html.unlink(missing_ok=True)
    return png_path.exists()


def build(spec=None, stem="_shell"):
    DRAW.mkdir(exist_ok=True)
    made = []
    jobs = [
        (f"{stem}-plan", draw_plan(spec, False), 1500),
        (f"{stem}-blueprint", draw_plan(spec, True), 1500),
        (f"{stem}-iso", draw_iso(spec), 1600),
    ]
    for wall in ("entrance", "right", "far", "left"):
        jobs.append((f"{stem}-elev-{wall}", draw_elevation(wall, spec), 1500))
    for name, content, w in jobs:
        p = DRAW / f"{name}.svg"
        p.write_text(content)
        png = DRAW / f"{name}.png"
        rasterise(p, png, w)
        made.append(png.name)
    return made


def main():
    if "--shell" in sys.argv:
        print("\n".join(build(None, "_shell")))
        return
    key = sys.argv[1]
    specs = {f"{s['id']}-{s['slug']}": s
             for s in (json.loads(p.read_text()) for p in (ROOT / "directions").glob("[0-9][0-9]-*.json"))}
    spec = specs.get(key) or next((v for k, v in specs.items() if k.startswith(key)), None)
    if not spec:
        sys.exit(f"no direction {key!r}")
    print("\n".join(build(spec, f"{spec['id']}-{spec['slug']}")))


if __name__ == "__main__":
    main()
