"""Project config, run state, and the approval gates.

One project = one job = one directory under projects/<slug>/ containing:

    project.yml     what the client wants and what the room is       (the only file they edit)
    STATE.json      which gates have been approved, and by whom       (written by the tool)
    refs/           the client's photographs and dimension sketches
    brief/          the surveyed brief, written by the surveyor agent
    directions/     one authored spec per design direction
    drawings/       measured drawings, generated
    renders/        photoreal views, generated
    report/         the deliverable

Approval gates exist because the expensive and hard-to-undo steps come late. Each gate must be
approved before the step it guards will run, and the tool refuses rather than asking twice.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROJECTS = ROOT / "projects"

# Ordered. Each gate guards the step named in `guards`.
GATES = [
    ("brief",        "The client brief is understood and recorded",
                     "writing the room model"),
    ("room-model",   "The room's dimensions, walls and openings are correct",
                     "generating drawings and any renders"),
    ("direction-set","The list of design directions is agreed",
                     "authoring the full specs"),
    ("pilot",        "The first direction's complete pack was reviewed and is right",
                     "rendering the remaining directions"),
    ("spend",        "A budget ceiling is set for paid rendering",
                     "using a paid render backend"),
    ("report",       "The report is approved for issue",
                     "marking the job delivered"),
]
GATE_IDS = [g[0] for g in GATES]


def slugify(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "project"


class Project:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.cfg = self._load_cfg()
        self.state = self._load_state()

    # ---------------------------------------------------------------- io

    @property
    def slug(self):
        return self.path.name

    def _cfg_file(self):
        for n in ("project.yml", "project.yaml", "project.json"):
            f = self.path / n
            if f.exists():
                return f
        raise SystemExit(f"no project.yml in {self.path}. Run:  design init <slug>")

    def _load_cfg(self):
        f = self._cfg_file()
        text = f.read_text()
        if f.suffix == ".json":
            return json.loads(text)
        try:
            import yaml
            return yaml.safe_load(text)
        except ImportError:
            return _mini_yaml(text)

    def _load_state(self):
        f = self.path / "STATE.json"
        if f.exists():
            return json.loads(f.read_text())
        return {"created": time.strftime("%Y-%m-%d %H:%M:%S"), "approvals": {}, "log": []}

    def save_state(self):
        (self.path / "STATE.json").write_text(json.dumps(self.state, indent=2) + "\n")

    def log(self, msg):
        self.state.setdefault("log", []).append(
            {"at": time.strftime("%Y-%m-%d %H:%M:%S"), "msg": msg})
        self.save_state()

    # ---------------------------------------------------------------- gates

    def approved(self, gate):
        return bool(self.state.get("approvals", {}).get(gate, {}).get("at"))

    def approve(self, gate, note="", by="client"):
        if gate not in GATE_IDS:
            raise SystemExit(f"unknown gate {gate!r}. Gates: {', '.join(GATE_IDS)}")
        self.state.setdefault("approvals", {})[gate] = {
            "at": time.strftime("%Y-%m-%d %H:%M:%S"), "by": by, "note": note}
        self.log(f"approved gate '{gate}'" + (f": {note}" if note else ""))

    def revoke(self, gate):
        self.state.get("approvals", {}).pop(gate, None)
        self.log(f"revoked gate '{gate}'")

    def require(self, gate):
        """Refuse to continue until the gate is approved. This is the whole point."""
        if self.approved(gate):
            return
        g = next(x for x in GATES if x[0] == gate)
        sys.exit(
            f"\nBLOCKED — gate '{gate}' is not approved.\n"
            f"  {g[1]}.\n"
            f"  It guards: {g[2]}.\n\n"
            f"Review the work, then:\n"
            f"  design approve {gate} --project {self.slug} --note \"...\"\n")

    # ---------------------------------------------------------------- config accessors

    def get(self, path, default=None):
        cur = self.cfg
        for part in path.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    @property
    def room_cfg(self):
        rc = self.get("room")
        if not rc:
            raise SystemExit("project.yml has no `room:` block")
        return rc

    def room(self):
        from .room import Room
        return Room.from_config(self.room_cfg)

    def views(self):
        return [v["id"] for v in self.get("deliverables.views", []) or []]

    def view_cfg(self, vid):
        for v in self.get("deliverables.views", []) or []:
            if v["id"] == vid:
                return v
        return {}

    def dirs(self):
        d = {k: self.path / k for k in
             ("refs", "brief", "directions", "drawings", "renders", "report", "prompts")}
        for p in d.values():
            p.mkdir(parents=True, exist_ok=True)
        return d

    def specs(self):
        out = []
        for f in sorted((self.path / "directions").glob("[0-9][0-9]-*.json")):
            out.append(json.loads(f.read_text()))
        return sorted(out, key=lambda s: s["id"])

    def spec_key(self, partial):
        for f in sorted((self.path / "directions").glob("[0-9][0-9]-*.json")):
            if f.stem.startswith(str(partial)) or f.stem == str(partial):
                return f.stem
        raise SystemExit(f"no direction matching {partial!r} in {self.path/'directions'}")


def resolve(slug=None):
    """Find the project to work on: named, or the only one, or the configured default."""
    PROJECTS.mkdir(exist_ok=True)
    if slug:
        p = PROJECTS / slug
        if not p.exists():
            raise SystemExit(f"no project {slug!r} in {PROJECTS}")
        return Project(p)
    cur = ROOT / "config" / "current"
    if cur.exists():
        name = cur.read_text().strip()
        if (PROJECTS / name).exists():
            return Project(PROJECTS / name)
    candidates = [d for d in PROJECTS.iterdir()
                  if d.is_dir() and any((d / n).exists()
                                        for n in ("project.yml", "project.yaml", "project.json"))]
    if len(candidates) == 1:
        return Project(candidates[0])
    if not candidates:
        raise SystemExit("no projects yet. Run:  design init <slug>")
    raise SystemExit("several projects; pass --project <slug>: "
                     + ", ".join(sorted(d.name for d in candidates)))


# ---------------------------------------------------------------------------- tiny YAML
# Enough YAML for the project file when PyYAML is not installed: nested maps, lists of
# scalars, lists of maps, and inline {..} / [..] flow scalars. Keeps the repo dependency-free.

def _coerce(v):
    v = v.strip()
    if v == "" or v in ("~", "null"):
        return None
    if v in ("true", "True", "yes"):
        return True
    if v in ("false", "False", "no"):
        return False
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        return v[1:-1]
    if v.startswith("[") or v.startswith("{"):
        try:
            return json.loads(v.replace("'", '"'))
        except Exception:
            return v
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _mini_yaml(text):
    root, stack = {}, [(-1, root)]
    lines = [l.rstrip() for l in text.splitlines()]
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]

        if line.startswith("- "):
            item = line[2:].strip()
            if not isinstance(parent, list):
                continue
            if ":" in item and not item.startswith("{"):
                d = {}
                k, _, v = item.partition(":")
                d[k.strip()] = _coerce(v)
                parent.append(d)
                stack.append((indent, d))
                # following deeper lines belong to this map
                while i < len(lines):
                    nxt = lines[i]
                    if not nxt.strip() or nxt.lstrip().startswith("#"):
                        i += 1
                        continue
                    ni = len(nxt) - len(nxt.lstrip())
                    if ni <= indent:
                        break
                    nk, _, nv = nxt.strip().partition(":")
                    if nxt.strip().startswith("- "):
                        break
                    if nv.strip() == "":
                        child = []
                        d[nk.strip()] = child
                        stack.append((ni, child))
                    else:
                        d[nk.strip()] = _coerce(nv)
                    i += 1
            else:
                parent.append(_coerce(item))
            continue

        k, _, v = line.partition(":")
        k, v = k.strip(), v.strip()
        if v == "":
            nxt = next((l for l in lines[i:] if l.strip() and not l.lstrip().startswith("#")), "")
            ni = len(nxt) - len(nxt.lstrip())
            child = [] if nxt.strip().startswith("- ") and ni > indent else {}
            if isinstance(parent, dict):
                parent[k] = child
            stack.append((indent, child))
        else:
            if isinstance(parent, dict):
                parent[k] = _coerce(v)
    return root
