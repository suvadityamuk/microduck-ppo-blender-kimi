"""Print the results table from results/eval/<world>/eval_summary.json (20 episodes per task, seeds 1000-1019).

    python scripts/results_table.py

Mean task success per world for Pollen's stock walker and the world-trained walker. Two tasks are left out of the means:
the hospital's xray_appointment (decided by a ramp/platform contact snag, see results/recheck/) and the mine's ore_to_bay.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {"xray_appointment", "ore_to_bay"}
NAMES = {"a_chocolate_factory_with_molten_chocolat": "Chocolate factory", "a_hospital_corridor_with_wet_floor_zones": "Hospital corridor",
         "a_low_gravity_orbital_hab_module_with_ma": "Low-gravity orbital hab", "a_circus_ring_with_a_sawdust_floor_a_tig": "Circus ring",
         "an_abandoned_mine_with_rubble_rail_track": "Abandoned mine", "a_frozen_lake_ice_fishing_village_where": "Frozen-lake fishing village"}


def main():
    rows = []
    for d in sorted((ROOT / "results" / "eval").iterdir()):
        s = json.loads((d / "eval_summary.json").read_text())
        world = next(p for p in (ROOT / "worlds_duck").iterdir() if p.name.strip("_") == d.name)
        g = json.loads((world / "scene.json").read_text())["env"].get("gravity", 9.81)
        rate = {k: [v["success"] for t, v in s[k].items() if not t.startswith("_") and t not in EXCLUDED] for k in ("stock", "specialist")}
        st, tr = (sum(rate[k]) / len(rate[k]) for k in ("stock", "specialist"))
        rows.append((tr - st, NAMES.get(d.name, d.name), g, st, tr))
    print("| World | Gravity m/s² | Stock walker | World-trained | Change |\n| --- | ---: | ---: | ---: | ---: |")
    for diff, name, g, st, tr in sorted(rows, reverse=True):
        print(f"| {name} | {g:.2f} | {st:.3f} | {tr:.3f} | {diff:+.3f} |")


if __name__ == "__main__":
    main()
