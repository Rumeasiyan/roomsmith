#!/usr/bin/env python3
"""Render one view through OpenRouter, using the SAME model codex's image_gen uses.

codex's built-in image_gen calls gpt-image-2 (gpt-image-1.5 is only its transparency fallback),
so rendering through OpenRouter with openai/gpt-image-2 keeps the whole 120-image set visually
consistent - same model, same prompt, same reference drawings and photographs.

    cp .env.example .env        # then put your key in OPENROUTER_API_KEY
    scripts/render_openrouter.py --missing --dry    # price it, call nothing
    scripts/render_openrouter.py --missing          # render everything still missing
    scripts/render_openrouter.py <NN-slug> <view>   # one view

Config comes from .env (gitignored): OPENROUTER_API_KEY, OPENROUTER_IMAGE_MODEL,
OPENROUTER_IMAGE_QUALITY, OPENROUTER_MAX_SPEND_USD. A real environment variable overrides .env.
The key is never logged and never committed.
"""
import base64
import json
import mimetypes
import os
import pathlib
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
RENDERS = ROOT / "renders"
DRAWINGS = ROOT / "drawings"
REFS = ROOT / "refs"
COSTLOG = RENDERS / "_openrouter_cost.jsonl"

ENDPOINT = "https://openrouter.ai/api/v1/images"


def load_dotenv():
    """Read .env into os.environ without adding a dependency. Real environment wins."""
    f = ROOT / ".env"
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


load_dotenv()

MODEL = os.environ.get("OPENROUTER_IMAGE_MODEL") or "openai/gpt-image-2"
QUALITY = os.environ.get("OPENROUTER_IMAGE_QUALITY") or "high"
MAX_SPEND = float(os.environ.get("OPENROUTER_MAX_SPEND_USD") or 0) or None
VIEWS = ["hero-in", "hero-back", "seated", "corner", "alcove", "far-wall"]

# Must mirror scripts/render.sh exactly, or the two backends would not be interchangeable.
PHOTOS = {
    "hero-in":   ["from-entrance.jpg", "left-side-of-entrance.jpg"],
    "hero-back": ["entrance.jpg"],
    "seated":    ["left-side-of-entrance.jpg"],
    "corner":    ["entrance.jpg", "from-entrance.jpg"],
    "alcove":    ["right-side-of-entrance.jpg"],
    "far-wall":  ["from-entrance.jpg"],
}
DWGS = {
    "alcove":   ("elev-right", "plan"),
    "far-wall": ("elev-far", "plan"),
    "seated":   ("elev-left", "plan"),
}
DEFAULT_DWGS = ("plan", "iso")


def api_key():
    k = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not k:
        f = ROOT / ".openrouter_key"          # legacy fallback
        if f.exists():
            k = f.read_text().strip()
    if not k or k.startswith("sk-or-v1-replace"):
        sys.exit("no key. Run:  cp .env.example .env   then put your key in OPENROUTER_API_KEY")
    return k


def data_url(path):
    path = pathlib.Path(path)
    mime = mimetypes.guess_type(path.name)[0] or "image/png"
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def refs_for(key, view):
    d1, d2 = DWGS.get(view, DEFAULT_DWGS)
    out = []
    for d in (d1, d2):
        p = DRAWINGS / f"{key}-{d}.png"
        if not p.exists():
            p = DRAWINGS / f"_shell-{d}.png"
        if p.exists():
            out.append(p)
    out += [REFS / n for n in PHOTOS.get(view, ["from-entrance.jpg"]) if (REFS / n).exists()]
    return out


def prompt_for(key, view):
    r = subprocess.run([sys.executable, str(ROOT / "scripts/build_prompts.py"), key, view],
                       capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"prompt build failed for {key} {view}: {r.stderr.strip()}")
    return r.stdout


PREAMBLE = (
    "The first one or two reference images are MEASURED DRAWINGS of this exact room - a scaled plan, "
    "elevation or isometric. They are authoritative on geometry: room proportion, the position and "
    "width of every opening, and where the furniture sits. If a drawing is a WALL ELEVATION, look "
    "SQUARE-ON at that wall and match it. The remaining reference images are BEFORE photographs of "
    "the same room from roughly this camera position - use them for the architectural shell only; "
    "their finishes, furniture, ceiling and colours are the condition being replaced.\n\n"
)


def render(key, view, dry=False):
    out = RENDERS / f"{key}-{view}.png"
    if out.exists() and out.stat().st_size > 0 and os.environ.get("FORCE") != "1":
        print(f"skip  {key}-{view}")
        return 0.0
    refs = refs_for(key, view)
    body = {
        "model": MODEL,
        "prompt": PREAMBLE + prompt_for(key, view),
        "n": 1,
        "aspect_ratio": "16:9",
        "quality": QUALITY,
        "output_format": "png",
        "input_references": [{"type": "image_url", "image_url": {"url": data_url(p)}} for p in refs],
    }
    if dry:
        print(f"would render {key}-{view}  ({len(refs)} refs, ~{len(body['prompt'])//4} prompt tokens)")
        return 0.0

    req = urllib.request.Request(
        ENDPOINT, method="POST",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {api_key()}",
                 "Content-Type": "application/json",
                 "HTTP-Referer": "https://localhost/compact-hall-design-directions",
                 "X-Title": "compact-hall-design-directions"},
    )
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            payload = json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:400]
        print(f"FAIL  {key}-{view}: HTTP {e.code} {detail}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"FAIL  {key}-{view}: {e}", file=sys.stderr)
        return None

    items = payload.get("data") or []
    if not items or not items[0].get("b64_json"):
        print(f"FAIL  {key}-{view}: no image in response {str(payload)[:300]}", file=sys.stderr)
        return None
    RENDERS.mkdir(exist_ok=True)
    out.write_bytes(base64.b64decode(items[0]["b64_json"]))
    cost = float((payload.get("usage") or {}).get("cost") or 0.0)
    with COSTLOG.open("a") as f:
        f.write(json.dumps({"key": key, "view": view, "cost": cost,
                            "usage": payload.get("usage")}) + "\n")
    print(f"ok    {key}-{view}  ${cost:.4f}")
    return cost


def missing():
    out = []
    for p in sorted((ROOT / "directions").glob("[0-9][0-9]-*.json")):
        k = p.stem
        for v in VIEWS:
            f = RENDERS / f"{k}-{v}.png"
            if not f.exists() or f.stat().st_size == 0:
                out.append((k, v))
    return out


def main():
    dry = "--dry" in sys.argv
    if "--missing" in sys.argv:
        todo = missing()
        print(f"{len(todo)} views missing  ·  model {MODEL}  ·  quality {QUALITY}"
              + (f"  ·  ceiling ${MAX_SPEND:.2f}" if MAX_SPEND else ""))
        total, fails = 0.0, 0
        for k, v in todo:
            if MAX_SPEND and total >= MAX_SPEND:
                print(f"\nstopping: hit the ${MAX_SPEND:.2f} ceiling from OPENROUTER_MAX_SPEND_USD")
                break
            c = render(k, v, dry)
            if c is None:
                fails += 1
                if fails >= 3:
                    sys.exit("3 consecutive failures - stopping")
            else:
                fails = 0
                total += c
        print(f"\ntotal spend this run: ${total:.2f}")
        return
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    render(sys.argv[1], sys.argv[2], dry)


if __name__ == "__main__":
    main()
