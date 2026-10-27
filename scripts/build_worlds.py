"""Rebuild the worlds' meshes and textures with Blender from the Kimi-K3 scripts in worlds_src/.

The repository ships each world's scene.json (tasks filtered by the feasibility gate) but not its meshes/ and
textures/, which are large and fully determined by the script. This re-runs every script headless and copies only
meshes/ and textures/ into worlds_duck/<world>/, keeping the shipped scene.json.

    uv run python scripts/build_worlds.py                    # all worlds
    uv run python scripts/build_worlds.py circus hospital    # worlds whose name contains any of these words

Needs Blender 4.x or 5.x: set BLENDER=/path/to/blender if it is not on PATH (macOS app bundle is found too).
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from robo_worlds.designer import BLENDER, run_blender  # noqa: E402


def source_for(world: Path) -> Path:
    if world.name == "_sample_toyshop":
        return ROOT / "worlds_src" / "_sample_toyshop.py"
    return ROOT / "worlds_src" / "duck" / world.name / "final.py"


def missing_meshes(world: Path) -> list[str]:
    scene = json.loads((world / "scene.json").read_text())
    files = {g["file"] for b in scene["bodies"] for g in b.get("geoms", []) if g.get("file")}
    return sorted(f for f in files if not (world / f).exists())


def build(world: Path) -> str:
    src = source_for(world)
    if not src.exists():
        return f"{world.name}: no source script at {src.relative_to(ROOT)}"
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / world.name
        res = run_blender(src, out, timeout=900)
        if not res.get("ok"):
            return f"{world.name}: Blender failed ({res.get('kind')}): {res.get('error', '')[:300]}"
        for sub in ("meshes", "textures"):
            if (world / sub).exists():
                shutil.rmtree(world / sub)
            if (out / sub).exists():
                shutil.copytree(out / sub, world / sub)
    miss = missing_meshes(world)
    return f"{world.name}: ok" if not miss else f"{world.name}: built, but {len(miss)} meshes in scene.json are missing, e.g. {miss[:3]}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("only", nargs="*", help="build only worlds whose name contains one of these words")
    ap.add_argument("--parallel", type=int, default=4)
    a = ap.parse_args()
    worlds = sorted(p for p in (ROOT / "worlds_duck").iterdir() if (p / "scene.json").exists())
    if a.only:
        worlds = [w for w in worlds if any(k in w.name for k in a.only)]
    print(f"Blender: {BLENDER}\nbuilding {len(worlds)} worlds", flush=True)
    with ThreadPoolExecutor(a.parallel) as ex:
        for msg in ex.map(build, worlds):
            print(msg, flush=True)


if __name__ == "__main__":
    main()
