"""Generic room geometry.

A room is a closed loop of walls in plan, any shape, plus openings, vents and fixed features.
Nothing here knows what kind of room it is or what country it is in - that comes from the
project config. Every drawing, prompt and report figure is derived from this model, so a
dimension is only ever written down once.

Shapes may be given three ways:

  shape: {type: rectangle, width: 3.12, length: 6.25}

  shape: {type: rectangle_with_alcove, width: 3.12, length: 6.25,
          alcove: {wall: right, start: 2.0, end: 4.55, depth: 0.75}}

  shape: {type: polygon, points: [[0,0],[3.12,0],[3.12,6.25],[0,6.25]]}

Openings are placed by distance along the wall they sit in, measured from that wall's start
point, so they stay correct whatever the room's shape.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass
class Wall:
    id: str
    name: str
    p0: tuple
    p1: tuple
    role: str = ""          # free text: entrance / far / flank / return ...

    @property
    def length(self):
        return math.dist(self.p0, self.p1)

    @property
    def angle(self):
        return math.atan2(self.p1[1] - self.p0[1], self.p1[0] - self.p0[0])

    def point_at(self, u):
        """Plan coordinate u metres along the wall from p0."""
        t = u / self.length if self.length else 0
        return (self.p0[0] + (self.p1[0] - self.p0[0]) * t,
                self.p0[1] + (self.p1[1] - self.p0[1]) * t)

    @property
    def inward(self):
        """Unit normal pointing into the room (walls run anticlockwise)."""
        dx, dy = self.p1[0] - self.p0[0], self.p1[1] - self.p0[1]
        n = math.hypot(dx, dy) or 1
        return (-dy / n, dx / n)

    def project(self, pt):
        """Distance along the wall, and perpendicular distance from it, for a plan point."""
        dx, dy = self.p1[0] - self.p0[0], self.p1[1] - self.p0[1]
        L2 = dx * dx + dy * dy or 1
        t = ((pt[0] - self.p0[0]) * dx + (pt[1] - self.p0[1]) * dy) / L2
        proj = (self.p0[0] + dx * t, self.p0[1] + dy * t)
        return t * math.sqrt(L2), math.dist(pt, proj), t


@dataclass
class Opening:
    tag: str
    type: str               # door | window | doorway | arch | opening
    wall: str               # wall id
    pos: float              # centre, metres along the wall from its start
    width: float
    sill: float = 0.0
    head: float = 2.05
    desc: str = ""
    extra: str = ""

    @property
    def height(self):
        return self.head - self.sill


@dataclass
class Feature:
    tag: str
    kind: str               # vent | niche | fixture | column ...
    wall: str
    pos: float
    width: float = 0.36
    height: float = 0.16
    z: float = 2.42
    desc: str = ""


@dataclass
class Room:
    name: str = "Room"
    units: str = "m"
    ceiling_height: float = 2.9
    walls: list = field(default_factory=list)
    openings: list = field(default_factory=list)
    features: list = field(default_factory=list)
    existing: dict = field(default_factory=dict)
    confirmed: bool = False
    notes: list = field(default_factory=list)
    # The dimensions that describe how the room FEELS, which for a room with an alcove or a
    # bay is the main body, not the bounding box. Falls back to the bbox when not given.
    key_across: float = 0.0
    key_along: float = 0.0

    # ---------------------------------------------------------------- construction

    @staticmethod
    def _walls_from_shape(shape):
        t = shape.get("type", "rectangle")
        if t == "polygon":
            pts = [tuple(p) for p in shape["points"]]
        elif t == "rectangle":
            w, l = float(shape["width"]), float(shape["length"])
            pts = [(0, 0), (w, 0), (w, l), (0, l)]
        elif t == "rectangle_with_alcove":
            w, l = float(shape["width"]), float(shape["length"])
            a = shape["alcove"]
            s, e, d = float(a["start"]), float(a["end"]), float(a["depth"])
            if a.get("wall", "right") == "right":
                pts = [(0, 0), (w, 0), (w, s), (w + d, s), (w + d, e), (w, e), (w, l), (0, l)]
            else:
                pts = [(0, 0), (w, 0), (w, l), (0, l), (0, e), (-d, e), (-d, s), (0, s)]
        else:
            raise ValueError(f"unknown shape type {t!r}")

        walls = []
        for i, p0 in enumerate(pts):
            p1 = pts[(i + 1) % len(pts)]
            if math.dist(p0, p1) < 1e-6:
                continue
            walls.append(Wall(id=f"w{len(walls)+1}", name=f"Wall {len(walls)+1}", p0=p0, p1=p1))
        return walls

    @classmethod
    def from_config(cls, cfg):
        """cfg is the `room` block of a project config."""
        walls = ([Wall(id=w["id"], name=w.get("name", w["id"]), p0=tuple(w["from"]),
                       p1=tuple(w["to"]), role=w.get("role", ""))
                  for w in cfg["walls"]]
                 if cfg.get("walls") else cls._walls_from_shape(cfg["shape"]))

        # Friendly names / roles may be supplied separately, keyed by wall id.
        for wid, meta in (cfg.get("wall_names") or {}).items():
            for w in walls:
                if w.id == wid:
                    if isinstance(meta, str):
                        w.name = meta
                    else:
                        w.name = meta.get("name", w.name)
                        w.role = meta.get("role", w.role)

        return cls(
            name=cfg.get("name", "Room"),
            units=cfg.get("units", "m"),
            ceiling_height=float(cfg.get("ceiling_height", 2.9)),
            walls=walls,
            openings=[Opening(**o) for o in cfg.get("openings", [])],
            features=[Feature(**f) for f in cfg.get("features", [])],
            existing=cfg.get("existing", {}) or {},
            confirmed=bool(cfg.get("confirmed", False)),
            notes=cfg.get("notes", []) or [],
            key_across=float((cfg.get("key_dimensions") or {}).get("across", 0) or 0),
            key_along=float((cfg.get("key_dimensions") or {}).get("along", 0) or 0),
        )

    # ---------------------------------------------------------------- queries

    def wall(self, wid):
        for w in self.walls:
            if w.id == wid:
                return w
        raise KeyError(f"no wall {wid!r}. Known: {[w.id for w in self.walls]}")

    def outline(self):
        return [w.p0 for w in self.walls]

    def bbox(self):
        xs = [p[0] for p in self.outline()]
        ys = [p[1] for p in self.outline()]
        return min(xs), min(ys), max(xs), max(ys)

    def area(self):
        pts = self.outline()
        return abs(sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts)))) / 2

    def span(self):
        x0, y0, x1, y1 = self.bbox()
        return x1 - x0, y1 - y0

    def narrow_dim(self):
        if self.key_across:
            return self.key_across
        w, l = self.span()
        return min(w, l)

    def long_dim(self):
        if self.key_along:
            return self.key_along
        w, l = self.span()
        return max(w, l)

    def openings_on(self, wid):
        return [o for o in self.openings if o.wall == wid]

    def features_on(self, wid, kind=None):
        return [f for f in self.features if f.wall == wid and (kind is None or f.kind == kind)]

    def solid_walls(self):
        """Walls with no opening at all - the ones a render must never punch a hole in."""
        return [w for w in self.walls if not self.openings_on(w.id)]

    def opening_plan_segment(self, op):
        """The opening's two endpoints in plan coordinates."""
        w = self.wall(op.wall)
        return w.point_at(op.pos - op.width / 2), w.point_at(op.pos + op.width / 2)

    # An item must lie along a wall by at least this much to belong to it. Without the guard,
    # a rectangle that merely touches a wall at one corner is assigned to it with a zero-length
    # run and draws a ghost element on that elevation.
    MIN_RUN = 0.05

    def nearest_wall(self, rect, tol=0.12):
        """Which wall a plan rectangle {x,y,w,d} sits against, if any.

        Returns (wall, u_start, run) so the item can be drawn on that wall's elevation, or None.
        Generic: works for any wall angle, not just axis-aligned ones.

        Ties on perpendicular distance are broken by the LONGER run, so a unit in a corner is
        attributed to the wall it actually lies along rather than the one it merely abuts.
        """
        cx, cy = rect["x"] + rect["w"] / 2, rect["y"] + rect["d"] / 2
        corners = [(rect["x"], rect["y"]), (rect["x"] + rect["w"], rect["y"]),
                   (rect["x"] + rect["w"], rect["y"] + rect["d"]), (rect["x"], rect["y"] + rect["d"])]
        best = None
        for w in self.walls:
            dists, us = [], []
            for c in corners:
                u, perp, t = w.project(c)
                if -0.02 <= t <= 1.02:
                    dists.append(perp)
                    us.append(u)
            if not dists or min(dists) > tol:
                continue
            u0, u1 = max(0.0, min(us)), min(w.length, max(us))
            run = u1 - u0
            if run < self.MIN_RUN:
                continue
            _, cperp, _ = w.project((cx, cy))
            key = (round(cperp, 4), -run)
            if best is None or key < best[0]:
                best = (key, w, u0, run)
        if not best:
            return None
        _, w, u0, run = best
        return w, u0, run
