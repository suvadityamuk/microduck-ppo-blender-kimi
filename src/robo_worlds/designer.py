"""Theme -> LLM-written Blender script -> exported world -> MuJoCo feasibility gate, with repair loops.

Kimi-K3 (via HF Inference Providers) writes a Blender Python script against the `rw` API for a world the Microduck
biped will learn in. Blender runs it headless; build errors and gate failures go back to the LLM as precise
feedback. No image or image-to-3D model is involved anywhere.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

from huggingface_hub import InferenceClient

ROOT = Path(__file__).resolve().parents[2]
BLENDER = (os.environ.get("BLENDER") or shutil.which("blender")
           or "/Applications/Blender.app/Contents/MacOS/Blender")  # Blender 4.x, run headless
RUNNER = ROOT / "src" / "robo_worlds" / "bpy_api" / "runner.py"
API_DOC = (Path(__file__).parent / "api_doc.md").read_text()
EXAMPLE = (ROOT / "worlds_src" / "_sample_toyshop.py").read_text()
LLMS = ["moonshotai/Kimi-K3"]
EXTRA: dict = {}
DUCK_PY = Path(os.environ.get("DUCK_PY", ROOT / "third_party" / "microduck_rl" / ".venv" / "bin" / "python"))

SYSTEM = f"""You are a technical artist and robotics engineer. You design small, vivid, physically sound worlds in which
a real low-cost bipedal robot (the Microduck, 25 cm tall) practises skills that are hard, slow or unsafe to practise
in the real world. You write Blender Python against the `rw` API below. Reply with ONE complete script in a single
```python block.

{API_DOC}

## Example of the expected style (do NOT copy its theme, layout or names)
```python
{EXAMPLE}
```"""


def _chat(model: str, messages: list[dict], seed: int) -> str:
    last = None
    for attempt in range(3):
        try:
            client = InferenceClient(timeout=1800)  # Kimi-K3 / GLM-5.3 reason for 15-50k tokens first
            stream = client.chat_completion(model=model, messages=messages, max_tokens=64000, temperature=0.7,
                                            seed=seed + attempt, stream=True, extra_body=EXTRA.get(model))
            parts, n_reason, t0 = [], 0, time.time()
            for c in stream:
                if not c.choices:
                    continue
                dl = c.choices[0].delta
                if dl.content:
                    parts.append(dl.content)
                elif getattr(dl, "reasoning_content", None) or getattr(dl, "reasoning", None):
                    n_reason += 1
                if (len(parts) + n_reason) % 4000 == 0:
                    print(f"    [{model.split('/')[-1]}] {n_reason} reasoning / {len(parts)} content chunks, {time.time() - t0:.0f}s", flush=True)
            text = "".join(parts)
            if text.strip():
                return text
        except Exception as e:  # noqa: BLE001  transient provider errors
            last = e
            time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"{model} failed: {last}")


def _extract(text: str) -> str | None:
    blocks = re.findall(r"```(?:python)?\s*\n(.*?)```", text, re.S)
    if not blocks:  # an unterminated final block (reply cut off): take everything after the last opening fence
        m = re.search(r"```(?:python)?\s*\n(.*)$", text, re.S)
        if not m:
            return None
        blocks = [m.group(1)]
    whole = [b for b in blocks if "rw.world(" in b]
    if whole:
        return max(whole, key=len)
    return "\n\n".join(blocks)


def run_blender(script: Path, out_dir: Path, timeout: int = 300) -> dict:
    try:
        p = subprocess.run([BLENDER, "--background", "--factory-startup", "--python", str(RUNNER), "--", str(script), str(out_dir)],
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "kind": "timeout", "error": f"Blender took longer than {timeout}s (too many vertices / booleans?)"}
    for line in p.stdout.splitlines()[::-1]:
        if line.startswith("RW_RESULT "):
            return json.loads(line[len("RW_RESULT "):])
    return {"ok": False, "kind": "crash", "error": (p.stdout[-1500:] + p.stderr[-1500:]).strip()}


def run_gate(world_dir: Path, episodes: int = 3, timeout: int = 1800) -> dict:
    import os

    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    try:
        p = subprocess.run([str(DUCK_PY), "-m", "robo_worlds.duck_gate", str(world_dir), "--episodes", str(episodes), "--json"],
                           capture_output=True, text=True, timeout=timeout, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        return {"ok": False, "passing": [], "feedback": "validation timed out", "physical": ["timeout"], "structural": {}}
    for line in p.stdout.splitlines()[::-1]:
        if line.startswith("GATE_RESULT "):
            return json.loads(line[len("GATE_RESULT "):])
    return {"ok": False, "passing": [], "feedback": "the world crashed the simulator:\n" + p.stderr[-1500:],
            "physical": ["validator crashed"], "structural": {}}


def design_world(theme: str, out_root: Path, src_root: Path, seed: int = 0, model: str | None = None,
                 build_attempts: int = 5, gate_rounds: int = 3, log=print) -> dict:
    model = model or LLMS[seed % len(LLMS)]
    slug = re.sub(r"[^a-z0-9]+", "_", theme.lower()).strip("_")[:40]
    work = src_root / slug
    work.mkdir(parents=True, exist_ok=True)
    out = out_root / slug
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Theme: {theme}\nDesign the world. Name it {slug!r}. Put the WHOLE script "
                 "(from rw.world(...) to the last task) in ONE ```python block."}]
    history = []
    gate = None
    for rnd in range(gate_rounds + 1):
        built = None
        for att in range(build_attempts):
            reply = _chat(model, messages, seed * 100 + rnd * 10 + att)
            code = _extract(reply)
            messages.append({"role": "assistant", "content": reply})
            if code is None:
                messages.append({"role": "user", "content": "Reply with the complete script in one ```python block."})
                continue
            script = work / f"r{rnd}_a{att}.py"
            script.write_text(code)
            if out.exists():
                shutil.rmtree(out)
            res = run_blender(script, out)
            history.append({"round": rnd, "attempt": att, "build": {k: res.get(k) for k in ("ok", "kind", "error")}})
            log(f"[{slug}] {model.split('/')[1]} round {rnd} attempt {att}: build {'ok' if res['ok'] else res.get('kind')}")
            if res["ok"]:
                built = script
                break
            err = res.get("error", "")
            if res.get("traceback"):
                err += "\n" + res["traceback"][-1200:]
            messages.append({"role": "user", "content": f"The script failed in Blender with this exact error:\n{err}\n"
                             "Change ONLY what this error is about (keep names and everything else identical) and send the "
                             "complete corrected script in one ```python block."})
        if built is None:
            break
        gate = run_gate(out)
        history.append({"round": rnd, "gate": {k: gate.get(k) for k in ("ok", "passing", "feedback", "notes", "baseline")}})
        base = {k: v.get("rate") for k, v in (gate.get("baseline") or {}).items()}
        log(f"[{slug}] gate round {rnd}: {len(gate['passing'])}/{len(gate.get('structural', {}))} tasks feasible; "
            f"physical issues={len(gate.get('physical', []))}; stock-policy baseline {base}")
        if gate["ok"] or rnd == gate_rounds:
            break
        messages.append({"role": "user", "content": "The world was built, but the physics/feasibility check found problems:\n"
                         f"{gate['feedback']}\nRevise the world to fix these (keep everything that works) and send the complete script."})
    (work / "history.json").write_text(json.dumps(history, indent=2))
    (work / "messages.json").write_text(json.dumps(messages, indent=2))
    result = {"theme": theme, "slug": slug, "model": model, "dir": str(out), "gate": gate, "kept": False}
    if gate is None:
        return result
    # keep the world when the physical checks pass and >= 4 tasks (>= 2 multi-step) are feasible; drop the rest
    passing = gate["passing"]
    scene_path = out / "scene.json"
    if gate.get("ok") and scene_path.exists():
        scene = json.loads(scene_path.read_text())
        scene["tasks"] = [t for t in scene["tasks"] if t["name"] in passing]
        scene["designer_llm"] = model
        scene["theme"] = theme
        scene["gate"] = {"baseline": gate.get("baseline"), "notes": gate.get("notes")}
        scene_path.write_text(json.dumps(scene, indent=2))
        shutil.copy(built, work / "final.py")
        result["kept"] = True
    return result
