"""Adds the shared S550 garage parts (tools/spec_gen/s550_parts.py) to the finished GT350R spec (cars/bng_gt350r.json is
hand-tuned after make_gt350r_spec.py, so it is patched in place; backup cars/bng_gt350r.before_s550parts.json).
Its own engine / gearbox rows are limited to the S550 ports too, like the GT500D's.
usage: python tools/spec_gen/add_s550_parts_gt350r.py"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s550_parts import apply, CARS
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
p = os.path.join(ROOT, "cars", "bng_gt350r.json")
s = json.load(open(p))
apply(s, {"FrontBumper": "GT350R", "RearBumper": "GT350", "Bonnet": "GT350", "Fender": "GT350", "RearWing": "GT350R", "Trunk": "NONE"})
for k in ("engines", "transmissions"):          # user 2026-11-17: fit every car (base row VehicleTypes)
    for e in s.get("custom_parts", {}).get(k, []):
        e.pop("vehicle_keys", None)
json.dump(s, open(p, "w"), indent=1)
print("-> %s: %d garage parts, %d liveries" % (p, len(s["aero_parts"]), len(s["skins"]["baked"])))
