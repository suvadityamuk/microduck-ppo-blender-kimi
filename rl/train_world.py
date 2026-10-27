"""Train a world-specialised Microduck walking policy with PPO (mjlab + rsl_rl), warm-started from Pollen's
deployed walk, and export it to ONNX with the observation normaliser baked in (the robot's runtime format).

    python rl/train_world.py worlds_duck/<world> --iters 1500 --num-envs 4096 --out runs/<world>
    python rl/train_world.py worlds_duck/<world> --iters 3 --num-envs 8 --device cpu   # smoke test

Warm start: the actor (MLP 61->512->256->128->14 + obs normaliser) is lifted from the ONNX of the stock walking
policy; the critic starts fresh and is trained alone for --critic-warmup iterations so the first PPO updates do not
wreck the gait.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "rl"))
sys.path.insert(0, str(ROOT / "src"))


def actor_from_onnx(onnx_path, init_std=0.3):
    import onnx
    import torch
    from onnx import numpy_helper

    m = onnx.load(str(onnx_path))
    w = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    div = next(v for k, v in w.items() if k.startswith("onnx::Div"))
    sd = {k: torch.tensor(v) for k, v in w.items() if k.startswith("mlp.")}
    sd["obs_normalizer._mean"] = torch.tensor(w["obs_normalizer._mean"])
    std = torch.tensor(div - 1e-2).clamp(min=1e-6)  # the exported divisor is std + eps (rsl_rl eps = 1e-2)
    sd["obs_normalizer._std"] = std
    sd["obs_normalizer._var"] = std ** 2
    sd["obs_normalizer.count"] = torch.tensor(1e7)
    sd["distribution.std_param"] = torch.full((14,), float(init_std))
    return sd


def install_anchor(runner, coef, decay_iters, batch=32768, steps=4, lr=3e-4):
    """Behaviour-cloning anchor (as Pollen's distill.py): after each PPO update, pull the actor's deterministic
    output towards the frozen warm-start walk on the states the student just visited. The weight decays linearly to
    0 over `decay_iters` iterations, so early PPO steps cannot rewrite the gait but the world skill can still form."""
    import copy

    import torch

    alg = runner.alg
    anchor = copy.deepcopy(alg.actor).eval()
    for p in anchor.parameters():
        p.requires_grad_(False)
    opt = torch.optim.Adam(alg.actor.parameters(), lr=lr)
    orig = alg.update
    state = {"it": 0}

    def update():
        out = orig()
        w = coef * max(0.0, 1.0 - state["it"] / max(1, decay_iters))
        state["it"] += 1
        if w <= 0 or not any(p.requires_grad for p in alg.actor.parameters()):
            return out
        td = alg.storage.observations.flatten(0, 1)
        n = td.batch_size[0]
        total = 0.0
        for _ in range(steps):
            sel = torch.randint(0, n, (min(n, batch),), device=alg.device)
            with torch.no_grad():
                target = anchor(td[sel])
            loss = w * (alg.actor(td[sel]) - target).pow(2).mean()
            opt.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(alg.actor.parameters(), 1.0)
            opt.step()
            total += loss.item()
        out["bc_anchor"] = total / steps
        return out

    alg.update = update
    print(f"[warm start] BC anchor to the stock walk, coef {coef}, decays over {decay_iters} it", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("world")
    ap.add_argument("--iters", type=int, default=1500)
    ap.add_argument("--num-envs", type=int, default=4096)
    ap.add_argument("--device", default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--warm", default=str(ROOT / "checkpoints_cache/duck/policies/alpha_walking.onnx"))
    ap.add_argument("--critic-warmup", type=int, default=40)
    ap.add_argument("--init-std", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--ang-std", type=float, default=None, help="std of the yaw-rate tracking kernel (recipe: 0.71)")
    ap.add_argument("--ang-weight", type=float, default=None)
    ap.add_argument("--inside-fraction", type=float, default=1.0, help="share of envs inside the room (rest on open floor)")
    ap.add_argument("--progress-weight", type=float, default=0.0, help="reward weight for metres/s of planned-path progress")
    ap.add_argument("--symmetry", action="store_true", help="enable Pollen's left/right symmetry loss")
    ap.add_argument("--flat", action="store_true", help="diagnostic: Pollen's flat plane instead of the world")
    ap.add_argument("--anchor", type=float, default=0.0, help="BC anchor weight towards the warm-start walk (0 = off)")
    ap.add_argument("--anchor-decay-iters", type=int, default=600)
    ap.add_argument("--adapt-normalizer", action="store_true", help="let the warm-started actor's obs normaliser keep updating")
    ap.add_argument("--nav-fraction", type=float, default=0.0, help="share of envs with closed-loop path-following commands")
    ap.add_argument("--lr", type=float, default=2e-4, help="PPO learning rate after the warm start")
    args = ap.parse_args()

    import torch
    from mjlab.envs import ManagerBasedRlEnv
    from mjlab.rl import RslRlVecEnvWrapper
    from mjlab.rl.exporter_utils import attach_metadata_to_onnx, get_base_metadata
    from mjlab.utils.torch import configure_torch_backends
    from mjlab_microduck.tasks import MicroduckOnPolicyRunner

    import duck_world_task as dwt

    configure_torch_backends()
    device = args.device or ("cuda:0" if torch.cuda.is_available() else "cpu")
    world = Path(args.world).resolve()
    slug = world.name.strip("_")[:40]
    out = Path(args.out or ROOT / "runs" / slug).resolve()
    out.mkdir(parents=True, exist_ok=True)

    scratch = args.warm in ("", "none")
    env_cfg = dwt.make_duck_world_env_cfg(str(world), flat=args.flat, collapse=not scratch, inside_fraction=args.inside_fraction,
                                          progress_weight=args.progress_weight)
    env_cfg.scene.num_envs = args.num_envs
    import math as _m
    if args.ang_std is not None:
        env_cfg.rewards["track_angular_velocity"].params["std"] = args.ang_std
    if args.ang_weight is not None:
        env_cfg.rewards["track_angular_velocity"].weight = args.ang_weight
    if not args.flat:
        env_cfg.commands["twist"].nav_fraction = args.nav_fraction
    env_cfg.seed = args.seed
    agent = dwt.rl_cfg(slug, args.iters, symmetry=args.symmetry)
    agent.seed = args.seed
    if args.warm not in ("", "none"):
        agent.algorithm.learning_rate = args.lr
    env = ManagerBasedRlEnv(cfg=env_cfg, device=device)
    env = RslRlVecEnvWrapper(env, clip_actions=agent.clip_actions)
    runner = MicroduckOnPolicyRunner(env, asdict(agent), str(out), device)

    if args.warm and Path(args.warm).exists():
        sd = actor_from_onnx(args.warm, args.init_std)
        missing = runner.alg.actor.load_state_dict({k: v.to(device) for k, v in sd.items()}, strict=False)
        print(f"[warm start] actor <- {args.warm}  ({missing})", flush=True)
        if not args.adapt_normalizer:  # keep the stock walk's input scaling: the obs stats would otherwise drift
            runner.alg.actor.obs_normalizer.until = 1
            print("[warm start] actor obs normaliser frozen", flush=True)
        if args.anchor > 0:
            install_anchor(runner, args.anchor, args.anchor_decay_iters)
        actor_params = list(runner.alg.actor.parameters())
        if args.critic_warmup > 0:
            for p in actor_params:
                p.requires_grad_(False)
            t = time.time()
            runner.learn(num_learning_iterations=min(args.critic_warmup, args.iters), init_at_random_ep_len=True)
            print(f"[warm start] critic warm-up {args.critic_warmup} it in {time.time() - t:.0f}s", flush=True)
            for p in actor_params:
                p.requires_grad_(True)
        # The adaptive schedule raised the LR while the frozen actor's KL was zero: fine-tune from a small LR again.
        runner.alg.learning_rate = args.lr
        for g in runner.alg.optimizer.param_groups:
            g["lr"] = args.lr
        print(f"[warm start] actor unfrozen, lr reset to {args.lr}", flush=True)
    remaining = args.iters - runner.current_learning_iteration
    if remaining > 0:
        runner.learn(num_learning_iterations=remaining, init_at_random_ep_len=runner.current_learning_iteration == 0)
    if runner.current_learning_iteration > 0:
        runner.save(str(out / "model_final.pt"))
    runner.export_policy_to_onnx(str(out), "policy.onnx")
    md = get_base_metadata(runner.env.unwrapped, run_path=str(out))
    attach_metadata_to_onnx(str(out / "policy.onnx"), md)
    (out / "train_info.json").write_text(json.dumps({"world": str(world), "iters": args.iters, "num_envs": args.num_envs,
                                                     "warm": args.warm, "seed": args.seed}, indent=2))
    print(f"[done] {out / 'policy.onnx'}", flush=True)


if __name__ == "__main__":
    main()
