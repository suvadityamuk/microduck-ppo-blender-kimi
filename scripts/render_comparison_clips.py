"""Side-by-side clips for the blog: one episode per task (seed 1000), stock walker left, world-trained walker right,
both driven by the planner, played at 2x (10 Hz frames written at 20 fps), with the outcome on the last frame.

    third_party/microduck_rl/.venv/bin/python scripts/render_comparison_clips.py outputs/clips

Needs the world-trained policies in checkpoints_cache/duck/world_policies/ (see README). Writes <world>__<task>.mp4
and meta.json into the output directory.
"""
import sys, json
from pathlib import Path
import numpy as np
import imageio.v2 as iio
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from robo_worlds.duck_sim import DuckSim
from robo_worlds.expert import Expert
V = Path(sys.argv[1]); V.mkdir(parents=True, exist_ok=True); H, W = 270, 360
STOCK = ROOT / "checkpoints_cache/duck/policies/velstand.onnx"
TRAINED = ROOT / "checkpoints_cache/duck/world_policies"
try:
    font = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)
except Exception:
    font = ImageFont.load_default()
def episode(sim, ex, tn):
    sim.reset(tn, seed=1000); ex.reset(); fr = [sim.render("chase", (H, W))]
    while True:
        _, done, info = sim.step(ex.act()); fr.append(sim.render("chase", (H, W)))
        if done: break
    return fr, {"success": bool(info["success"]), "failure": info["failure"], "t": round(sim.time, 1)}
def label(frames, title, r):
    out = []
    txt = f"{title}: " + (f"done in {r['t']:.0f} s" if r["success"] else {"fell": "fell", "timeout": "ran out of time"}.get((r["failure"] or "").split(" ")[0], "stepped into a hazard") + f" at {r['t']:.0f} s")
    col = (40, 160, 70) if r["success"] else (200, 60, 50)
    for i, f in enumerate(frames):
        im = Image.fromarray(f); d = ImageDraw.Draw(im)
        d.rectangle([0, 0, W, 24], fill=(20, 22, 26)); d.text((8, 4), title, fill=(235, 235, 235), font=font)
        if i == len(frames) - 1 or i >= len(frames) - 1:
            pass
        out.append(np.asarray(im))
    # final banner on the last frame
    last = Image.fromarray(frames[-1]); d = ImageDraw.Draw(last)
    d.rectangle([0, 0, W, 24], fill=col); d.text((8, 4), txt, fill=(255, 255, 255), font=font)
    out[-1] = np.asarray(last)
    return out
meta = {}
for wd in sorted(p for p in (ROOT / "worlds_duck").iterdir() if (p / "scene.json").exists()):
    w = wd.name
    sims = {k: DuckSim(str(wd), str(p), seed=1000, dr=True) for k, p in (("stock", STOCK), ("trained", TRAINED / f"{w.strip('_')}.onnx"))}
    exs = {k: Expert(s) for k, s in sims.items()}
    for tn, task in sims["stock"].tasks.items():
        res = {}
        frames = {}
        for k in ("stock", "trained"):
            f, r = episode(sims[k], exs[k], tn); res[k] = r
            frames[k] = label(f, "Stock walker" if k == "stock" else "World-trained walker", r)
        n = max(len(frames["stock"]), len(frames["trained"])) + 10
        for k in frames:
            frames[k] = frames[k] + [frames[k][-1]] * (n - len(frames[k]))
        gap = np.full((H, 4, 3), 245, np.uint8)
        clip = [np.concatenate([a, gap, b], 1) for a, b in zip(frames["stock"], frames["trained"])]
        name = f"{w.strip('_')}__{tn}.mp4"
        iio.mimwrite(V / name, clip, fps=20, quality=5, macro_block_size=4, ffmpeg_params=["-movflags", "+faststart"])
        meta[name] = {"world": w.strip("_"), "task": tn, "kind": task["kind"], "instruction": task["instruction"], **{k: res[k] for k in res}}
        print(name, res["stock"], res["trained"], flush=True)
json.dump(meta, open(V / "meta.json", "w"), indent=1)
