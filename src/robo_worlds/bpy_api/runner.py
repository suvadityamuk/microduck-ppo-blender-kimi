"""Blender entry point: run an LLM-written world script with the `rw` API and export the scene.

    Blender --background --python runner.py -- <script.py> <out_dir>

Prints a final line `RW_RESULT {json}` so the caller can read success / error details.
"""

import json
import sys
import traceback
from pathlib import Path

import bpy

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rw  # noqa: E402


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    script, out_dir = Path(argv[0]), Path(argv[1])
    # empty scene
    bpy.ops.wm.read_factory_settings(use_empty=True)
    code = script.read_text()
    ns = {"__name__": "__rw_world__", "rw": rw, "bpy": bpy, "math": __import__("math")}
    try:
        exec(compile(code, str(script), "exec"), ns)
        w = rw.current_world()
        if w is None:
            raise rw.WorldError("the script must create a world with rw.world(...)")
        w.save(out_dir)
        n_tasks = len(w.tasks)
        print("RW_RESULT " + json.dumps({"ok": True, "out": str(out_dir), "tasks": n_tasks, "bodies": len(w.bodies)}))
    except rw.WorldError as e:
        print("RW_RESULT " + json.dumps({"ok": False, "kind": "design", "error": str(e)}))
        sys.exit(2)
    except Exception as e:  # noqa: BLE001
        tb = traceback.format_exc(limit=-6)
        print("RW_RESULT " + json.dumps({"ok": False, "kind": "exception", "error": f"{type(e).__name__}: {e}", "traceback": tb}))
        sys.exit(3)


main()
