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
# Enough YAML for a project file when PyYAML is not installed, so the repo stays
# dependency-free: nested maps, block sequences, flow sequences and maps with unquoted
# scalars, folded/literal block scalars, and inline comments.

def _strip_comment(v):
    """Remove a trailing # comment that is not inside quotes."""
    out, quote = [], None
    for i, ch in enumerate(v):
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or v[i - 1] in " \t"):
            break
        else:
            out.append(ch)
    return "".join(out).strip()


def _split_flow(body):
    """Split a flow sequence/map body on commas at depth zero."""
    parts, depth, cur, quote = [], 0, "", None
    for ch in body:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            cur += ch
        elif ch in "[{":
            depth += 1
            cur += ch
        elif ch in "]}":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return [p.strip() for p in parts if p.strip()]


def _coerce(v):
    v = _strip_comment(v)
    if v == "" or v in ("~", "null", "None"):
        return None
    if v in ("true", "True", "yes", "on"):
        return True
    if v in ("false", "False", "no", "off"):
        return False
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        return [_coerce(x) for x in _split_flow(v[1:-1])]
    if v.startswith("{") and v.endswith("}"):
        out = {}
        for item in _split_flow(v[1:-1]):
            k, _, val = item.partition(":")
            out[_strip_comment(k).strip("\"'")] = _coerce(val)
        return out
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def _depth_delta(line):
    """Net bracket depth of a line, ignoring brackets inside quotes and comments."""
    d, quote = 0, None
    for i, ch in enumerate(line):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or line[i - 1] in " \t"):
            break
        elif ch in "[{":
            d += 1
        elif ch in "]}":
            d -= 1
    return d


def _join_flow_lines(lines):
    """Join a flow collection that wraps across lines into one logical line."""
    out, buf, depth = [], None, 0
    for line in lines:
        if buf is None:
            depth = _depth_delta(line)
            if depth > 0:
                buf = line
            else:
                out.append(line)
        else:
            buf += " " + line.strip()
            depth += _depth_delta(line)
            if depth <= 0:
                out.append(buf)
                buf = None
    if buf is not None:
        out.append(buf)
    return out


def _mini_yaml(text):
    lines = _join_flow_lines(text.splitlines())

    def indent_of(i):
        return len(lines[i]) - len(lines[i].lstrip())

    def skip(i):
        while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith("#")):
            i += 1
        return i

    def block_scalar(i, parent_indent, fold):
        """Consume an indented block after > or | and return (text, next_index)."""
        buf, j = [], i
        while j < len(lines):
            if not lines[j].strip():
                buf.append("")
                j += 1
                continue
            if indent_of(j) <= parent_indent:
                break
            buf.append(lines[j].strip())
            j += 1
        while buf and buf[-1] == "":
            buf.pop()
        return ((" ".join(x for x in buf if x) if fold else "\n".join(buf)), j)

    def parse(i, indent):
        """Parse a block at the given indent. Returns (value, next_index)."""
        i = skip(i)
        if i >= len(lines):
            return {}, i
        if lines[i].lstrip().startswith("- "):
            seq = []
            while True:
                i = skip(i)
                if i >= len(lines) or indent_of(i) != indent or not lines[i].lstrip().startswith("- "):
                    break
                item = lines[i].lstrip()[2:].strip()
                i += 1
                if item and ":" in item and not item.startswith(("{", "[")):
                    k, _, v = item.partition(":")
                    entry = {}
                    v = _strip_comment(v)
                    if v:
                        entry[k.strip()] = _coerce(v)
                    nxt = skip(i)
                    if nxt < len(lines) and indent_of(nxt) > indent:
                        rest, i = parse(nxt, indent_of(nxt))
                        if isinstance(rest, dict):
                            entry.update(rest)
                    seq.append(entry)
                else:
                    seq.append(_coerce(item))
            return seq, i

        mapping = {}
        while True:
            i = skip(i)
            if i >= len(lines) or indent_of(i) != indent or lines[i].lstrip().startswith("- "):
                break
            k, _, v = lines[i].lstrip().partition(":")
            k, v = k.strip(), v.strip()
            i += 1
            if v in (">", "|", ">-", "|-"):
                mapping[k], i = block_scalar(i, indent, v.startswith(">"))
                continue
            v = _strip_comment(v)
            if v == "":
                nxt = skip(i)
                if nxt < len(lines) and indent_of(nxt) > indent:
                    mapping[k], i = parse(nxt, indent_of(nxt))
                else:
                    mapping[k] = None
            else:
                mapping[k] = _coerce(v)
        return mapping, i

    value, _ = parse(0, indent_of(skip(0)) if skip(0) < len(lines) else 0)
    return value if isinstance(value, dict) else {}
