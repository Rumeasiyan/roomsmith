"""Render backends. Two, interchangeable, driven by the same prompts and reference drawings.

  codex       free, quota-limited, via the codex CLI's built-in image_gen tool (gpt-image-2)
  openrouter  paid, no quota, same model by default so the set stays visually consistent

Reference images per view: the measured drawing that best constrains that camera (an elevation
for a square-on view, the plan for an axial one) plus whichever client photograph was taken from
nearest that standpoint. Both are declared per view in project.yml.
"""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

from . import prompts

ENDPOINT = "https://openrouter.ai/api/v1/images"

# Measured on this project across several quota windows: the free codex backend yields roughly
# 45-50 images before the limit, then resets in about 4-5 hours. Deliberately conservative.
CODEX_IMAGES_PER_WINDOW = 45

# Measured mean over 29 billed images on openai/gpt-image-2 at high quality, 16:9.
OPENROUTER_USD_PER_IMAGE = 0.183
PREAMBLE = (
    "The first reference images are MEASURED DRAWINGS of this exact room — a scaled plan, "
    "elevation or isometric. They are authoritative on geometry: room proportion, the position "
    "and width of every opening, and where the furniture sits. If a drawing is a WALL ELEVATION, "
    "look SQUARE-ON at that wall and match it. Any remaining reference images are BEFORE "
    "photographs of the same room — use them for the architectural shell only; their finishes, "
    "furniture and colours are the condition being replaced.\n\n")


def load_dotenv(root):
    f = root / ".env"
    if not f.exists():
        return
    for raw in f.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip("'").strip('"')
        if k and k not in os.environ:
            os.environ[k] = v


def refs_for(project, key, view):
    vc = project.view_cfg(view)
    d = project.path / "drawings"
    out = []
    for name in vc.get("drawings", ["plan", "iso"]):
        p = d / f"{key}-{name}.png"
        if not p.exists():
            p = d / f"_shell-{name}.png"
        if p.exists():
            out.append(p)
    for photo in vc.get("photos", []):
        p = project.path / "refs" / photo
        if p.exists():
            out.append(p)
    return out


def out_path(project, key, view):
    return project.path / "renders" / f"{key}-{view}.png"


# ---------------------------------------------------------------- codex backend

def render_codex(project, key, view, prompt, refs):
    out = out_path(project, key, view)
    log = out.with_suffix(".log")
    ref_list = "\n".join(str(r) for r in refs)
    img_args = []
    for r in refs:
        img_args += ["-i", str(r)]
    instruction = (
        f"Generate exactly one image with the image_gen tool, then save it and stop.\n\n"
        f"Pass these as referenced_image_paths:\n{ref_list}\n\n{PREAMBLE}"
        f"After the tool returns, copy the generated PNG to exactly this path:\n{out}\n"
        f"Then reply with only that path. Do not generate a second image.\n\n"
        f"--- IMAGE PROMPT ---\n{prompt}\n")
    with tempfile.TemporaryDirectory() as work:
        r = subprocess.run(
            ["codex", "exec", "--dangerously-bypass-approvals-and-sandbox",
             "--skip-git-repo-check", "-C", work, "--add-dir", str(project.path.parent.parent),
             *img_args, "-"],
            input=instruction, capture_output=True, text=True, timeout=900)
    log.write_text((r.stdout or "") + (r.stderr or ""))
    if out.exists() and out.stat().st_size:
        return 0.0
    for token in (r.stdout or "").split():
        if "generated_images" in token and token.endswith(".png"):
            p = pathlib.Path(token.strip("'\"()[],"))
            if p.exists():
                out.write_bytes(p.read_bytes())
                return 0.0
    blob = ((r.stdout or "") + (r.stderr or "")).lower()
    if "usage limit" in blob or "quota" in blob:
        raise QuotaExhausted(_reset_hint(blob))
    return None


class QuotaExhausted(Exception):
    pass


def _reset_hint(blob):
    i = blob.find("try again at")
    return blob[i:i + 30].strip() if i >= 0 else "quota exhausted"


# ---------------------------------------------------------------- openrouter backend

def _data_url(p):
    mime = mimetypes.guess_type(p.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def render_openrouter(project, key, view, prompt, refs):
    api = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api or api.startswith("sk-or-v1-replace"):
        sys.exit("no key. cp .env.example .env and set OPENROUTER_API_KEY")
    model = os.environ.get("OPENROUTER_IMAGE_MODEL") or "openai/gpt-image-2"
    quality = os.environ.get("OPENROUTER_IMAGE_QUALITY") or "high"
    body = {"model": model, "prompt": PREAMBLE + prompt, "n": 1,
            "aspect_ratio": project.get("deliverables.aspect_ratio", "16:9"),
            "quality": quality, "output_format": "png",
            "input_references": [{"type": "image_url", "image_url": {"url": _data_url(p)}}
                                 for p in refs]}
    req = urllib.request.Request(
        ENDPOINT, method="POST", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api}", "Content-Type": "application/json",
                 "X-Title": "interior-design-agent"})
    try:
        with urllib.request.urlopen(req, timeout=900) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        if e.code == 402:
            raise QuotaExhausted("OpenRouter credits exhausted")
        print(f"FAIL  {key}-{view}: HTTP {e.code} {detail}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"FAIL  {key}-{view}: {e}", file=sys.stderr)
        return None
    items = payload.get("data") or []
    if not items or not items[0].get("b64_json"):
        print(f"FAIL  {key}-{view}: no image returned", file=sys.stderr)
        return None
    out_path(project, key, view).write_bytes(base64.b64decode(items[0]["b64_json"]))
    return float((payload.get("usage") or {}).get("cost") or 0.0)


BACKENDS = {"codex": render_codex, "openrouter": render_openrouter}


# ---------------------------------------------------------------- driver

def forecast(backend, n_images):
    """A one-line honest expectation before a run starts, so nobody is surprised."""
    if n_images <= 0:
        return "nothing to render"
    if backend == "codex":
        windows = -(-n_images // CODEX_IMAGES_PER_WINDOW)
        if windows <= 1:
            return (f"~{n_images} images · free · a codex window fits about "
                    f"{CODEX_IMAGES_PER_WINDOW}, so this should finish in one go")
        return (f"~{n_images} images · free · a codex window fits about "
                f"{CODEX_IMAGES_PER_WINDOW}, so expect about {windows} windows "
                f"({windows - 1} quota pause{'s' if windows > 2 else ''}, ~4-5 h each). "
                f"Use --wait to ride them out")
    est = n_images * OPENROUTER_USD_PER_IMAGE
    return (f"~{n_images} images · estimated ${est:.2f} "
            f"(${OPENROUTER_USD_PER_IMAGE:.3f}/image measured) · no quota pauses")


def choose_backend(project, requested=None):
    """Resolve which backend to use, and why. Explicit beats configured beats default.

    There is no cleverness here on purpose: a tool that silently decides to start spending
    money is a tool you cannot trust with an API key.
    """
    if requested:
        return requested, "--backend flag"
    configured = project.get("render.backend")
    if configured:
        return configured, "render.backend in project.yml"
    return "codex", "default"


def fallback_backend(project, current):
    """The backend to degrade to when `current` runs out, if the project opted in.

    Returns (backend, reason) or (None, why-not). Requires an explicit `render.fallback`,
    the `spend` gate if the fallback costs money, and headroom under the ceiling.
    """
    fb = project.get("render.fallback")
    if not fb:
        return None, "no render.fallback configured"
    if fb == current:
        return None, "fallback is the same as the current backend"
    if fb not in BACKENDS:
        return None, f"unknown fallback backend {fb!r}"
    if fb != "codex" and not project.approved("spend"):
        return None, f"fallback '{fb}' costs money and the 'spend' gate is not approved"
    ceiling = float(project.get("render.max_spend_usd") or 0) or None
    if ceiling and spent(project) >= ceiling:
        return None, f"already at the ${ceiling:.2f} ceiling"
    return fb, f"render.fallback, {'spend gate approved' if fb != 'codex' else 'free'}"


def dry_run(project, key, view):
    """Everything a real render does, except calling the image model.

    Builds the prompt, resolves the reference images and checks they exist. Catches a missing
    drawing, a photo named in the config but not in refs/, an empty scene description or a broken
    view before any quota or money is spent on finding out.
    """
    errors, warnings = [], []
    try:
        spec = json.loads((project.path / "directions" / f"{key}.json").read_text())
    except Exception as e:
        return None, [f"cannot read spec: {e}"], []

    vc = project.view_cfg(view)
    if not vc:
        errors.append(f"view '{view}' is not declared in deliverables.views")
    if not vc.get("camera"):
        errors.append(f"view '{view}' has no camera description")
    if not (vc.get("from") and vc.get("look_at")):
        warnings.append("view has no `from`/`look_at`, so no orientation block is generated - the "
                        "render may mirror the room or invent daylight on a solid wall")

    for name in vc.get("drawings", []):
        own = project.path / "drawings" / f"{key}-{name}.png"
        shell = project.path / "drawings" / f"_shell-{name}.png"
        if own.exists():
            continue
        if shell.exists():
            warnings.append(f"'{name}' falls back to the empty-room drawing - this direction's "
                            f"furniture will not appear on it. Run: design drawings {key}")
        else:
            errors.append(f"reference drawing '{name}' missing - run: design drawings {key}")
    if not vc.get("photos"):
        warnings.append("no photographic anchor for this view - geometry comes only from the "
                        "drawings, so 3D judgements (ceiling height, wall length, depth) may drift")
    if not project.get("room.confirmed"):
        warnings.append("room.confirmed is false - these dimensions have not been measured on site")
    for photo in vc.get("photos", []):
        if not (project.path / "refs" / photo).exists():
            warnings.append(f"reference photo '{photo}' not in refs/ - the render loses its "
                            f"photographic anchor but will still run")

    scene = (spec.get("render") or {}).get(view) or (spec.get("render") or {}).get("default")
    if not scene:
        warnings.append(f"no scene for '{view}' and no render.default - falling back to the thesis, "
                        f"which is thinner than a written scene")

    try:
        prompt = prompts.build(project, spec, view)
    except Exception as e:
        return None, errors + [f"prompt build failed: {e}"], warnings

    refs = refs_for(project, key, view)
    if not refs:
        errors.append("no reference images at all - the render has nothing to anchor geometry to")
    return ({"prompt_chars": len(prompt), "prompt_tokens": len(prompt) // 4,
             "refs": [p.name for p in refs]}, errors, warnings)


def render_one(project, key, view, backend=None, force=False):
    out = out_path(project, key, view)
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists() and out.stat().st_size and not force:
        print(f"skip  {key}-{view}")
        return 0.0
    backend = backend or project.get("render.backend", "codex")
    if backend not in BACKENDS:
        sys.exit(f"unknown backend {backend!r}. Options: {', '.join(BACKENDS)}")
    if backend != "codex":
        project.require("spend")
    spec = json.loads((project.path / "directions" / f"{key}.json").read_text())
    prompt = prompts.build(project, spec, view)
    refs = refs_for(project, key, view)
    cost = BACKENDS[backend](project, key, view, prompt, refs)
    if cost is None:
        print(f"FAIL  {key}-{view}", file=sys.stderr)
        return None
    ledger = project.path / "renders" / "_cost.jsonl"
    with ledger.open("a") as f:
        f.write(json.dumps({"at": time.strftime("%F %T"), "key": key, "view": view,
                            "backend": backend, "cost": cost}) + "\n")
    print(f"ok    {key}-{view}" + (f"  ${cost:.4f}" if cost else ""))
    return cost


def missing(project):
    out = []
    for spec in project.specs():
        key = f"{spec['id']}-{spec['slug']}"
        for v in project.views():
            p = out_path(project, key, v)
            if not p.exists() or not p.stat().st_size:
                out.append((key, v))
    return out


def spent(project):
    f = project.path / "renders" / "_cost.jsonl"
    if not f.exists():
        return 0.0
    return sum(json.loads(l).get("cost", 0) for l in f.read_text().splitlines() if l.strip())
