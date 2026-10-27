"""Collect the re-check results (split6000/) and apply the verdict rules, which were fixed before looking at the data:
a regression persists if the world-trained walker is more than 2 standard errors below stock; a no-gain task persists if
the world-trained walker is not above stock. Dropped tasks are reported without a verdict rule. Writes verdicts_6000.json."""
import json
import math
from pathlib import Path

B = Path(__file__).resolve().parent
FLAG = {("a_low_gravity_orbital_hab_module_with_ma", "dock_the_cargo"): "regressed",
        ("a_circus_ring_with_a_sawdust_floor_a_tig", "grand_parade"): "regressed",
        ("a_hospital_corridor_with_wet_floor_zones", "scrub_in"): "no gain",
        ("a_hospital_corridor_with_wet_floor_zones", "nurse_rounds"): "no gain",
        ("a_low_gravity_orbital_hab_module_with_ma", "morning_patrol"): "no gain",
        ("a_frozen_lake_ice_fishing_village_where", "climb_the_lookout"): "no gain",
        ("a_hospital_corridor_with_wet_floor_zones", "xray_appointment"): "dropped",
        ("an_abandoned_mine_with_rubble_rail_track", "ore_to_bay"): "dropped"}
rows = []
for (w, t), flag in FLAG.items():
    r = {"world": w, "task": t, "flag": flag}
    for k in ("stock", "specialist"):
        f = B / "split6000" / f"{w}__{t}__{k}" / "summary.json"
        if f.exists():
            v = json.loads(f.read_text())[k][t]
            r[k], r[k + "_n"], r[k + "_fail"] = v["success"], v["episodes"], v["failures"]
    if "stock" in r and "specialist" in r:
        s, p, n = r["stock"], r["specialist"], r["stock_n"]
        se = math.sqrt(max(s * (1 - s) + p * (1 - p), 1e-9) / n)
        r["diff"], r["se"] = round(p - s, 3), round(se, 3)
        if flag == "regressed":
            r["verdict"] = "persists" if p < s - 2 * se else "not reproduced"
        elif flag == "no gain":
            r["verdict"] = "persists" if p <= s else "not reproduced"
        else:
            r["verdict"] = "gain" if p > s + 2 * se else ("worse" if p < s - 2 * se else "no difference")
    rows.append(r)
(B / "verdicts_6000.json").write_text(json.dumps(rows, indent=1))
for r in rows:
    print(f"{r['world'][:28]:28s} {r['task']:20s} {r['flag']:9s} stock {r.get('stock')} trained {r.get('specialist')} -> {r.get('verdict')}")
