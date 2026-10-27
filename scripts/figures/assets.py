"""Render everything the blog's thumbnail and figures need, then screenshot the HTML pages.

    third_party/microduck_rl/.venv/bin/python scripts/figures/assets.py build/figures
    CHROME=/path/to/chrome third_party/microduck_rl/.venv/bin/python scripts/figures/assets.py build/figures --shoot

Writes into the output directory: the HTML pages and their CSS, the Fredoka font and the Hugging Face logo (downloaded),
a cutout of the duck mid-stride (duck.png), an overview of each world (<world>.jpg), a larger circus overview
(world.jpg) and the last frame of both walkers' greasepaint episode (eval_stock.jpg, eval_trained.jpg).
With --shoot it also writes thumbnail.png (1200x648), pipeline.png and ppo.png (2x scale) using headless Chrome.
Everything is rendered from the simulator; no image model is involved.
"""

import argparse
import math
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

import imageio.v2 as iio
import numpy as np
from PIL import Image

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import ROOT, STOCK, WORLDS, Cam, sim  # noqa: E402

from robo_worlds.expert import Expert  # noqa: E402

FONT_URL = "https://github.com/google/fonts/raw/main/ofl/fredoka/Fredoka%5Bwdth,wght%5D.ttf"
LOGO_URL = "https://huggingface.co/front/assets/huggingface_logo-noborder.svg"
TRAINED = ROOT / "checkpoints_cache" / "duck" / "world_policies"
PAGES = {"thumbnail.html": (1200, 648, 1), "pipeline.html": (1600, 580, 2), "ppo.html": (1600, 700, 2)}


def world(word):
    return next(p for p in WORLDS if word in p.name)


def tick(s, cmd13, on_ctrl):
    """One 10 Hz high-level tick, as DuckSim.step, calling on_ctrl() after every 50 Hz control step."""
    c = np.asarray(cmd13, np.float32).copy()
    c[0] = np.clip(c[0], -0.4, 0.4); c[1] = np.clip(c[1], -0.2, 0.2); c[2] = np.clip(c[2], -1.5, 1.5)
    c[3:7] = np.clip(c[3:7], -1.0, 1.0); c[7:] = 0.0
    s.cmd = c
    for _ in range(5):
        s._control_step(); s._monitor(); on_ctrl()
        if s.state.done:
            break


def overviews(out):
    for w in WORLDS:
        s = sim(w, w=960, h=540); s.reset(next(iter(s.tasks)), seed=0)
        iio.imwrite(out / f"{w.name}.jpg", Cam(s, 960, 540).overview().frame(), quality=90)
    s = sim(world("circus"), w=1600, h=900); s.reset("cross_the_greasepaint", seed=0)
    iio.imwrite(out / "world.jpg", Cam(s, 1600, 900).overview(az=135, el=-42, scale=0.95).frame(), quality=92)


def eval_frames(out, w=944, h=1000):
    """Last frame of the greasepaint episode at seed 1000 (with randomisation, as in the evaluation), per walker."""
    wd = world("circus")
    for who, policy in (("stock", STOCK), ("trained", TRAINED / f"{wd.name.strip('_')}.onnx")):
        s = sim(wd, policy=str(policy), dr=True, seed=1000, w=w, h=h); s.reset("cross_the_greasepaint", seed=1000)
        ex, cam, st = Expert(s), Cam(s, w, h), {"look": None, "az": None}

        def follow():
            if int(round(s.time * 50)) % 2:
                return
            p, yaw = s.pose()
            look = np.array([p[0], p[1], p[2] - 0.02])
            st["look"] = look if st["look"] is None else 0.9 * st["look"] + 0.1 * look
            az = math.degrees(yaw) + 210
            st["az"] = az if st["az"] is None else st["az"] + 0.04 * ((az - st["az"] + 180) % 360 - 180)

        while not s.state.done:
            tick(s, ex.act(), follow)
        cam.cam.lookat[:] = st["look"]; cam.cam.distance = 1.0; cam.cam.azimuth = st["az"]; cam.cam.elevation = -30
        Image.fromarray(cam.frame()).crop((0, 40, w, 900)).save(out / f"eval_{who}.jpg", quality=92)
        print(who, "success" if s.state.success else s.state.failure, round(s.time, 1), flush=True)


def duck(out, size=2000):
    """The duck mid-stride, cut out with segmentation rendering at 2x and downsampled."""
    s = sim(world("circus"), w=size, h=size); s.reset("into_the_spotlight", seed=0)
    cam = Cam(s, size, size)
    cmd = np.zeros(13, np.float32); cmd[0] = 0.32
    for _ in range(33):
        s.step(cmd)
    p, yaw = s.pose()
    cam.cam.lookat[:] = [p[0], p[1], p[2] + 0.02]; cam.cam.distance = 0.48
    cam.cam.azimuth = math.degrees(yaw) + 150; cam.cam.elevation = -6
    rgba = np.dstack([cam.frame(), (cam.robot_mask() * 255).astype(np.uint8)])
    im = Image.fromarray(rgba, "RGBA"); box = im.getbbox(); im = im.crop(box)
    im.resize((im.width // 2, im.height // 2), Image.LANCZOS).save(out / "duck.png")


def shoot(out):
    chrome = os.environ.get("CHROME") or shutil.which("chromium") or shutil.which("google-chrome")
    if not chrome:
        sys.exit("set CHROME=/path/to/chrome (any Chromium build) to screenshot the pages")
    for page, (w, h, scale) in PAGES.items():
        png = out / page.replace(".html", ".png")
        subprocess.run([chrome, "--headless", "--disable-gpu", "--hide-scrollbars", f"--force-device-scale-factor={scale}",
                        f"--window-size={w},{h}", "--virtual-time-budget=3000", f"--screenshot={png}", (out / page).as_uri()],
                       check=True, capture_output=True)
        print(png, Image.open(png).size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("--shoot", action="store_true", help="also screenshot the pages with headless Chrome")
    a = ap.parse_args()
    out = Path(a.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    for f in [*PAGES, "fig_common.css"]:
        shutil.copy(HERE / f, out / f)
    for url, name in ((FONT_URL, "Fredoka.ttf"), (LOGO_URL, "hf_logo.svg")):
        if not (out / name).exists():
            urllib.request.urlretrieve(url, out / name)
    overviews(out); eval_frames(out); duck(out)
    if a.shoot:
        shoot(out)


if __name__ == "__main__":
    main()
