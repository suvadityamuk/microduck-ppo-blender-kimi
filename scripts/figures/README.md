# Blog thumbnail and figures

`docs/thumbnail.png`, `docs/figures/pipeline.png` and `docs/figures/ppo.png` are HTML pages screenshotted with headless
Chrome. Every image on them is rendered from the simulator; no image model is involved.

```bash
CHROME=/path/to/chrome third_party/microduck_rl/.venv/bin/python scripts/figures/assets.py build/figures --shoot
```

`assets.py` copies the pages next to their inputs and renders those inputs: an overview of each world, the duck cut out
mid-stride (segmentation rendering at 2x), and the last frame of both walkers' *cross the greasepaint* episode. It needs the
world-trained circus policy in `checkpoints_cache/duck/world_policies/` (see the main README). It downloads the Fredoka
font (OFL) and the Hugging Face logo, which are not stored in this repository.
