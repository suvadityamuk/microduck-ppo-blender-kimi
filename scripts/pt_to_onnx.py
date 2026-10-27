"""Convert an rsl_rl actor checkpoint (model_N.pt) to the robot's ONNX format (normaliser baked in)."""
import sys
import torch
import torch.nn as nn


class Actor(nn.Module):
    def __init__(self, sd, eps=1e-2):
        super().__init__()
        self.register_buffer("mean", sd["obs_normalizer._mean"])
        self.register_buffer("std", sd["obs_normalizer._std"] + eps)
        layers = []
        ks = sorted({int(k.split(".")[1]) for k in sd if k.startswith("mlp.") and k.endswith("weight")})
        for i, k in enumerate(ks):
            lin = nn.Linear(sd[f"mlp.{k}.weight"].shape[1], sd[f"mlp.{k}.weight"].shape[0])
            lin.weight.data, lin.bias.data = sd[f"mlp.{k}.weight"], sd[f"mlp.{k}.bias"]
            layers += [lin] + ([nn.ELU()] if i < len(ks) - 1 else [])
        self.mlp = nn.Sequential(*layers)

    def forward(self, obs):
        return self.mlp((obs - self.mean) / self.std)


def convert(pt, out):
    sd = torch.load(pt, map_location="cpu", weights_only=False)["actor_state_dict"]
    m = Actor(sd).eval()
    torch.onnx.export(m, torch.zeros(1, 61), out, input_names=["obs"], output_names=["actions"], dynamo=False)


if __name__ == "__main__":
    convert(sys.argv[1], sys.argv[2])
