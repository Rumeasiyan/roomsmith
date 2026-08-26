"""Tests that need no network, no API key and no browser.

The fallback YAML parser matters more than it looks: it is what runs on any machine without
PyYAML, and a bug in it silently truncates a project config rather than failing loudly.
"""
import builtins
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

_real_import = builtins.__import__


def _no_yaml(name, *a, **k):
    if name == "yaml":
        raise ImportError("blocked so the fallback parser is exercised")
    return _real_import(name, *a, **k)


def parse_without_pyyaml(text):
    builtins.__import__ = _no_yaml
    try:
        from engine.project import _mini_yaml
        return _mini_yaml(text)
    finally:
        builtins.__import__ = _real_import


def test_templates_parse_without_pyyaml():
    for tpl in sorted((ROOT / "config" / "templates").glob("*.yml")):
        d = parse_without_pyyaml(tpl.read_text())
        b, r, dl = d.get("brief", {}), d.get("room", {}), d.get("deliverables", {})

        assert isinstance(d.get("name"), str), f"{tpl.name}: name"
        assert len(b.get("what_it_is", "")) > 30, f"{tpl.name}: folded block scalar"
        assert isinstance(b.get("must_appear"), list) and b["must_appear"], f"{tpl.name}: must_appear"
        assert isinstance(b.get("problems"), list) and isinstance(b["problems"][0], dict), \
            f"{tpl.name}: list of maps"

        assert isinstance(r.get("shape"), dict), f"{tpl.name}: shape"
        assert isinstance(r.get("wall_names", {}).get("w1"), dict), f"{tpl.name}: nested flow map"
        assert isinstance(r.get("openings"), list) and isinstance(r["openings"][0], dict), \
            f"{tpl.name}: openings"
        assert r["openings"][0].get("desc"), f"{tpl.name}: multi-line flow map lost a key"
        assert isinstance(r.get("notes"), list), f"{tpl.name}: notes after nested blocks"

        assert dl.get("elevations") and dl["elevations"][0] == "w1", f"{tpl.name}: flow sequence"
        assert isinstance(dl.get("views"), list) and dl["views"], f"{tpl.name}: views"
        for v in dl["views"]:
            assert v.get("id") and v.get("camera"), f"{tpl.name}: view {v} incomplete"
            assert isinstance(v.get("drawings"), list), f"{tpl.name}: view drawings"

        assert isinstance(d["render"]["max_spend_usd"], (int, float)), \
            f"{tpl.name}: inline comment leaked into a number"
        assert d["render"]["backend"] == "codex", f"{tpl.name}: backend"


def test_room_geometry_from_each_shape():
    from engine.room import Room
    rect = Room.from_config({"shape": {"type": "rectangle", "width": 3, "length": 5},
                             "ceiling_height": 2.5, "openings": []})
    assert len(rect.walls) == 4 and abs(rect.area() - 15) < 1e-6

    alc = Room.from_config({"shape": {"type": "rectangle_with_alcove", "width": 3, "length": 5,
                                      "alcove": {"wall": "right", "start": 1, "end": 3, "depth": 0.5}},
                            "ceiling_height": 2.5, "openings": []})
    assert len(alc.walls) == 8 and abs(alc.area() - 16) < 1e-6

    poly = Room.from_config({"shape": {"type": "polygon",
                                       "points": [[0, 0], [4, 0], [4, 2], [2, 2], [2, 4], [0, 4]]},
                             "ceiling_height": 2.5, "openings": []})
    assert len(poly.walls) == 6 and abs(poly.area() - 12) < 1e-6


def test_opening_sits_on_its_wall():
    from engine.room import Room
    r = Room.from_config({"shape": {"type": "rectangle", "width": 4, "length": 5},
                          "ceiling_height": 2.5,
                          "openings": [{"tag": "D1", "type": "door", "wall": "w1",
                                        "pos": 2.0, "width": 0.9}]})
    a, b = r.opening_plan_segment(r.openings[0])
    assert abs(a[0] - 1.55) < 1e-6 and abs(b[0] - 2.45) < 1e-6
    assert a[1] == 0 and b[1] == 0
    assert [w.id for w in r.solid_walls()] == ["w2", "w3", "w4"]


def test_wall_attribution_rejects_grazing_contact():
    """A rectangle that only touches a wall at a corner must not be drawn on its elevation.

    Found in a real project: an alcove unit grazed the chimney-breast face and appeared on that
    elevation as a zero-width, full-height ghost.
    """
    from engine.room import Room
    # a chimney breast projecting into the room, leaving an alcove either side
    room = Room.from_config({
        "shape": {"type": "polygon",
                  "points": [[0, 0], [3.4, 0], [3.4, 3.8], [2.4, 3.8],
                             [2.4, 3.45], [1.0, 3.45], [1.0, 3.8], [0, 3.8]]},
        "ceiling_height": 2.65, "openings": []})

    grazing = room.nearest_wall({"x": 2.40, "y": 3.45, "w": 0.92, "d": 0.35})
    assert grazing is not None
    wall, u, run = grazing
    assert run >= room.MIN_RUN, "a grazing contact must never yield a near-zero run"
    assert wall.id != "w5", "must not be attributed to the wall it merely touches at a corner"

    free = room.nearest_wall({"x": 0.9, "y": 1.65, "w": 1.6, "d": 0.9})
    assert free is None, "a free-standing item belongs to no wall"


def test_example_project_still_valid():
    from engine.project import Project
    p = Project(ROOT / "projects" / "compact-hall")
    room = p.room()
    assert room.confirmed
    assert len(room.openings) == 5
    assert abs(room.narrow_dim() - 3.12) < 1e-6, "key_dimensions must beat the bounding box"
    assert len(p.specs()) == 20
    assert sum(len(s["items"]) for s in p.specs()) == 291


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for fn in fns:
        fn()
        print(f"  ok  {fn.__name__}")
    print(f"\n{len(fns)} tests passed")
