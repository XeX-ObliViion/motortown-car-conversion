# regenerate every build's meshes from source (clean wheel OBJs before wheel_mats.py), 2026-11-14
cd ~/OneDrive/Documents/claude/ps2motortown
for s in $(cat tools/ALL_SPECS.txt); do
  case $s in
    cars/nfs_wings.json) continue;;
    cars/ps_rims.json) python tools/ps_rims.py $s > /dev/null 2>&1 || echo "FAIL $s";;
    cars/mw_rims.json) python tools/mw_rims.py $s > /dev/null 2>&1 || echo "FAIL $s";;
    cars/ac_rims.json) py -3.13 tools/ac_rims.py $s > /dev/null 2>&1 || echo "FAIL $s";;
    cars/bng_rims.json) python bng/bng_rims.py $s > /dev/null 2>&1 || echo "FAIL $s";;
    *) python tools/ps_to_mt.py $s > /dev/null 2>&1 || echo "FAIL $s";;
  esac
done
echo regen-done
