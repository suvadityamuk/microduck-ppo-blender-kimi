#!/bin/bash
# Re-check of the flagged and dropped tasks: 100 episodes per walker on seeds 6000-6099, disjoint from the evaluation
# (1000-1019), clip selection (2000-2011) and checkpoint selection (5000-5007). Results go to split6000/.
cd "$(dirname "$0")/../.."
export ORT_THREADS=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1 MKL_NUM_THREADS=1
PY=third_party/microduck_rl/.venv/bin/python; B=results/recheck
STOCK=checkpoints_cache/duck/policies/velstand.onnx; TRAINED=checkpoints_cache/duck/world_policies
mkdir -p $B/logs
one() { # world_dir task stock|specialist
  local name=${1%_}; local p=$STOCK; [ "$3" = specialist ] && p=$TRAINED/$name.onnx
  local o=$B/split6000/${name}__$2__$3
  [ -f $o/summary.json ] && return
  $PY scripts/duck_eval.py worlds_duck/$1 --policies $3=$p --episodes 100 --seed0 6000 --videos 0 --tasks $2 --out $o > $B/logs/${name}__$2__$3.log 2>&1
}
for which in stock specialist; do
  one a_low_gravity_orbital_hab_module_with_ma dock_the_cargo $which &
  one a_circus_ring_with_a_sawdust_floor_a_tig grand_parade $which &
  one a_hospital_corridor_with_wet_floor_zones scrub_in $which &
  one a_hospital_corridor_with_wet_floor_zones nurse_rounds $which &
  one a_low_gravity_orbital_hab_module_with_ma morning_patrol $which &
  one a_frozen_lake_ice_fishing_village_where_ climb_the_lookout $which &
  one a_hospital_corridor_with_wet_floor_zones xray_appointment $which &
  one an_abandoned_mine_with_rubble_rail_track ore_to_bay $which &
done
wait
$PY $B/aggregate.py
