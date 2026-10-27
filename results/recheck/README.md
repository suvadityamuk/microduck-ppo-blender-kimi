# Re-check of the flagged tasks

The 20-episode evaluation (`results/eval/`) flagged some tasks as **regressed** (the world-trained walker clearly worse)
or **no gain** (not better), and two tasks were left out of the world averages. This folder re-runs those eight tasks
for 100 episodes per walker on fresh seeds, with the same policies and no retraining.

- **Seeds** 6000-6099, disjoint from the evaluation (1000-1019), the clip selection (2000-2011) and the checkpoint
  selection (5000-5007, in `scripts/select_ckpt.py`).
- **Verdict rules**, fixed before looking (`aggregate.py`): a regression persists if the world-trained walker is more
  than two standard errors below stock; a no-gain task persists if the world-trained walker is not above stock.
- **Run it** with `results/recheck/run.sh`. It reads the world-trained policies from
  `checkpoints_cache/duck/world_policies/` and writes `split6000/` and `verdicts_6000.json`.

| World | Task | Flag | Stock | World-trained | Verdict |
| --- | --- | --- | ---: | ---: | --- |
| Orbital hab | dock the cargo | regressed | 0.95 | 0.57 | persists |
| Circus ring | grand parade | regressed | 0.42 | 0.01 | persists |
| Hospital corridor | scrub in | no gain | 0.01 | 0.02 | both walkers fail |
| Hospital corridor | nurse rounds | no gain | 0.00 | 0.00 | persists |
| Orbital hab | morning patrol | no gain | 0.00 | 0.00 | persists |
| Frozen lake | climb the lookout | no gain | 0.00 | 0.00 | persists |
| Hospital corridor | X-ray appointment | left out | 0.01 | 0.62 | world bug, below |
| Abandoned mine | ore to bay | left out | 0.36 | 0.31 | no difference |

*Scrub in* clears the no-gain rule by one episode in 100, but neither walker can do the task.

## Hospital X-ray task: a world bug

Both walkers stall where the blue ramp meets the X-ray platform, with full forward command. `xray_seam_test.py` lowers
the platform deck by a few millimetres at runtime and re-runs 20 episodes per walker:

| Deck lowered by | Stock | World-trained |
| --- | ---: | ---: |
| 0 mm | 0/20 | 11/20 |
| 2 mm | 20/20 | 20/20 |
| 5 mm | 20/20 | 20/20 |

The stall is a contact snag at the coplanar ramp/platform seam, not walking skill, so the task is left out of the
hospital's average. The world-trained walker's 0.62 measures how often it gets past the snag.
