"""Generate Blender-built worlds from themes with Kimi-K3, in parallel, keeping those that pass the gate.

    uv run python scripts/make_duck_worlds.py --themes worlds_src/duck_themes.json --parallel 6
"""

import argparse
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from robo_worlds.designer import design_world

LOCK = threading.Lock()


def log(msg):
    with LOCK:
        print(msg, flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--themes", default="worlds_src/duck_themes.json")
    ap.add_argument("--out", default="worlds_duck")
    ap.add_argument("--src", default="worlds_src/duck")
    ap.add_argument("--parallel", type=int, default=6)
    ap.add_argument("--only", nargs="*", default=None)
    ap.add_argument("--skip", nargs="*", default=None)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    themes = json.loads(Path(args.themes).read_text())
    if args.only:
        themes = [t for t in themes if any(o in t["theme"] for o in args.only)]
    if args.skip:
        themes = [t for t in themes if not any(o in t["theme"] for o in args.skip)]
    res_path = Path(args.out) / f"_generation{'_' + args.tag if args.tag else ''}.json"
    results = json.loads(res_path.read_text()) if res_path.exists() else {}

    def one(item):
        i, t = item
        try:
            r = design_world(t["theme"], Path(args.out), Path(args.src), seed=t.get("seed", i), log=log)
        except Exception as e:  # noqa: BLE001
            r = {"theme": t["theme"], "kept": False, "error": f"{type(e).__name__}: {e}"}
        r["split"] = t.get("split", "train")
        with LOCK:
            results[t["theme"]] = r
            res_path.parent.mkdir(parents=True, exist_ok=True)
            res_path.write_text(json.dumps(results, indent=2, default=str))
        log(f"== {t['theme']}: {'KEPT' if r.get('kept') else 'dropped'} {r.get('error', '')}")

    todo = [(i, t) for i, t in enumerate(themes) if not results.get(t["theme"], {}).get("kept")]
    with ThreadPoolExecutor(args.parallel) as pool:
        list(pool.map(one, todo))
    kept = [r for r in results.values() if r.get("kept")]
    print(f"kept {len(kept)}/{len(results)}: " + ", ".join(f"{r['slug']}({r['split']})" for r in kept))


if __name__ == "__main__":
    main()
