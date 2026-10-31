"""Make the Motor Town-side assets for converted ProStreet cars, by editing cooked game assets as UAssetGUI JSON:
  * a car Blueprint cloned from a base car (e.g. Zino): new package/class name, body/doors/mirrors/wheels pointed at
    the car's new meshes, wheel/seat/camera positions from the car spec;
  * a DataTable Vehicles_ProStreet (cloned from the one-row Vehicles_Jeep) with one VehicleRow per car, copied from the
    base car's row with a new name, class and price;
  * the composite Vehicles table with Vehicles_ProStreet added to its parent tables.
Inputs are this PC's own game files (unpacked with repak); nothing from the game is shipped except these edited assets
in the user's own mod pak.

usage: make_mt_assets.py <out_dir> <car_spec.json> [<car_spec.json> ...]"""
import copy
import json
import os
import subprocess
import sys

UAG = os.path.expanduser("~/tools/uassetgui/UAssetGUI.exe")
# MT_UNPACKED: the dedicated server needs blueprints/tables made from ITS copies of the game files
# MT_BASE: client base files to build on (e.g. ~/mt-work/unpacked_maja: Maja's Wheel Works wheel table) without server mode
UNPACKED = os.path.expanduser(os.environ.get("MT_UNPACKED", os.environ.get("MT_BASE", "~/mt-work/unpacked_maja/MotorTown/Content")))
WHEEL_MESH_SCALE = 0.6466   # must match ps_to_mt.WHEEL_MESH_SCALE


def win(p):
    return p.replace("/", "\\")


def tojson(uasset, out_json):
    if not os.path.exists(uasset):
        # not in the server pak (e.g. a More Tuning template): fall back to the client extract
        alt = uasset.replace(UNPACKED, os.path.expanduser("~/mt-work/unpacked/MotorTown/Content"))
        if os.path.exists(alt):
            uasset = alt
    subprocess.run([UAG, "tojson", win(uasset), win(out_json), "VER_UE5_5", "MotorTown"], check=True, cwd=os.path.dirname(UAG))  # mappings resolve from its folder
    d = json.load(open(out_json, encoding="utf-8"))
    if os.environ.get("MT_UNPACKED"):
        _ptn_learn(d)
    return d


_PTN_SEEN = {}


def _ptn_learn(o):
    """remember the property-type tags of every tagged property seen (server assets are versioned)"""
    if isinstance(o, dict):
        t = o.get("PropertyTypeName")
        if t and "$type" in o:
            _PTN_SEEN.setdefault(("n", o.get("Name"), o["$type"], o.get("StructType")), t)
            if o.get("StructType"):
                _PTN_SEEN.setdefault(("s", o["StructType"]), t)
            _PTN_SEEN.setdefault(("t", o["$type"], o.get("StructType")), t)
        for v in o.values():
            _ptn_learn(v)
    elif isinstance(o, list):
        for v in o:
            _ptn_learn(v)


SIMPLE_PTN = {"IntPropertyData": "IntProperty", "FloatPropertyData": "FloatProperty", "BoolPropertyData": "BoolProperty",
              "NamePropertyData": "NameProperty", "StrPropertyData": "StrProperty", "ObjectPropertyData": "ObjectProperty",
              "SoftObjectPropertyData": "SoftObjectProperty", "TextPropertyData": "TextProperty", "BytePropertyData": "ByteProperty",
              "DoublePropertyData": "DoubleProperty", "Int64PropertyData": "Int64Property", "UInt32PropertyData": "UInt32Property"}


def _ptn_fill(props, missing):
    """give every tagged property (export Data / generic struct members) a PropertyTypeName"""
    for o in props or []:
        if not isinstance(o, dict) or "$type" not in o:
            continue
        if "RichCurveKeyPropertyData" in o["$type"]:
            continue            # curve keys are serialized natively, untagged
        if o.get("PropertyTypeName") is None:
            t = (_PTN_SEEN.get(("n", o.get("Name"), o["$type"], o.get("StructType")))
                 or (_PTN_SEEN.get(("s", o["StructType"])) if o.get("StructType") else None)
                 or _PTN_SEEN.get(("t", o["$type"], o.get("StructType"))))
            if t is None:
                short = o["$type"].split(",")[0].rsplit(".", 1)[-1]
                if short in SIMPLE_PTN:
                    t = [{"$type": "UAssetAPI.UnrealTypes.FPropertyTypeNameNode, UAssetAPI", "Name": SIMPLE_PTN[short], "InnerCount": 0}]
            if t is None:
                missing.add((o.get("Name"), o["$type"].split(",")[0], o.get("StructType")))
            else:
                o["PropertyTypeName"] = t
        _ptn_children(o, missing)


def _ptn_children(o, missing):
    v = o.get("Value")
    if not isinstance(v, list):
        return
    if "StructPropertyData" in o["$type"].split(",")[0]:
        # natively serialized struct: its single value carries the struct's own name; nothing inside is tagged
        if not (len(v) == 1 and isinstance(v[0], dict) and v[0].get("Name") == o.get("Name") and "StructPropertyData," not in v[0].get("$type", "")):
            _ptn_fill(v, missing)
    else:   # arrays / sets / maps: elements are untagged, but generic struct elements have tagged members
        for e in v:
            for x in (e if isinstance(e, list) else [e]):
                if isinstance(x, dict) and "$type" in x and "StructPropertyData," in x["$type"]:
                    _ptn_children(x, missing)


def fix_versioned(data):
    """server (versioned) assets: properties copied from client (unversioned) templates lack PropertyTypeName"""
    if not os.environ.get("MT_UNPACKED"):
        return
    _ptn_learn(data)
    missing = set()
    for e in data.get("Exports", []):
        _ptn_fill(e.get("Data"), missing)
    if missing:
        print("  type tags still missing:", sorted(missing)[:8])


def fromjson(data, json_path, uasset):
    fix_versioned(data)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.makedirs(os.path.dirname(uasset), exist_ok=True)
    before = os.path.getmtime(uasset) if os.path.exists(uasset) else None
    subprocess.run([UAG, "fromjson", win(json_path), win(uasset), "MotorTown"], check=True, cwd=os.path.dirname(UAG))
    # UAssetGUI exits 0 and writes nothing when the JSON is invalid (e.g. an FName missing from the NameMap)
    if not os.path.exists(uasset) or os.path.getmtime(uasset) == before:
        raise SystemExit("UAssetGUI did not write %s (check NameMap for new names in %s)" % (uasset, json_path))


def deep_replace(o, pairs):
    if isinstance(o, str):
        for a, b in pairs:
            if o == a or (a.startswith("/") and o.startswith(a + ".")) or (a.startswith("/") and o.startswith(a)):
                o = o.replace(a, b, 1)
        return o
    if isinstance(o, list):
        return [deep_replace(x, pairs) for x in o]
    if isinstance(o, dict):
        return {k: deep_replace(v, pairs) for k, v in o.items()}
    return o


def find_prop(export, name):
    data = export.get("Data")
    if not isinstance(data, list):
        return None
    for p in data:
        if isinstance(p, dict) and p.get("Name") == name:
            return p
    return None


def set_vector(prop, xyz):
    v = prop["Value"][0]["Value"] if isinstance(prop["Value"], list) else prop["Value"]
    v["X"], v["Y"], v["Z"] = float(xyz[0]), float(xyz[1]), float(xyz[2])



def _imp(d, path, cls, cls_pkg="/Script/Engine"):
    """Package + object import for an asset path; returns the object import index."""
    obj = path.rsplit("/", 1)[1]
    d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": path, "OuterIndex": 0,
                         "ClassPackage": "/Script/CoreUObject", "ClassName": "Package", "PackageName": None, "bImportOptional": False})
    pkg = -len(d["Imports"])
    d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": obj, "OuterIndex": pkg,
                         "ClassPackage": cls_pkg, "ClassName": cls, "PackageName": None, "bImportOptional": False})
    for n in (path, obj, cls, "Package", cls_pkg, "/Script/CoreUObject"):
        if n not in d["NameMap"]:
            d["NameMap"].append(n)
    return -len(d["Imports"])


def add_skins(d, car, skins):
    """NFS vinyl liveries as garage skins: append MTVehicleBodyMaterial entries (MI_SKIN_<name>, built by build_car)
    to the CDO's BodyMaterialList, creating the list (entry 0 = the paintable M_Body) on bases without one (Cora)."""
    P = lambda t, n, v, **k: dict({"$type": "UAssetAPI.PropertyTypes.Objects.%s, UAssetAPI" % t, "Name": n, "ArrayIndex": 0,
                                   "PropertyGuid": None, "IsZero": False, "PropertyTagFlags": "None", "PropertyTypeName": None,
                                   "PropertyTagExtensions": "NoExtension", "Value": v}, **k)
    def entry(i, mat_index):
        return {"$type": "UAssetAPI.PropertyTypes.Structs.StructPropertyData, UAssetAPI", "StructType": "MTVehicleBodyMaterial",
                "SerializeNone": True, "StructGUID": "{00000000-0000-0000-0000-000000000000}", "SerializationControl": "NoExtension",
                "Operation": "None", "Name": str(i), "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False,
                "PropertyTagFlags": "None", "PropertyTypeName": None, "PropertyTagExtensions": "NoExtension",
                "Value": [P("ObjectPropertyData", "Material", mat_index),
                          P("MapPropertyData", "SlotMaterials", [], KeyType="NameProperty", ValueType="ObjectProperty", KeysToRemove=[]),
                          P("BoolPropertyData", "bUseForAIVehicle", False)]}
    for n in ("BodyMaterialList", "MTVehicleBodyMaterial", "Material", "SlotMaterials", "bUseForAIVehicle", "ArrayProperty",
              "StructProperty", "ObjectProperty", "MapProperty", "NameProperty", "BoolProperty", "MaterialInstanceConstant"):
        if n not in d["NameMap"]:
            d["NameMap"].append(n)
    cdo = next(e for e in d["Exports"] if str(e.get("ObjectName", "")).startswith("Default__"))
    bml = next((p for p in cdo["Data"] if p.get("Name") == "BodyMaterialList"), None)
    if bml is None:
        bml = P("ArrayPropertyData", "BodyMaterialList", [entry(0, _imp(d, "/Game/Cars/Materials/Body/M_Body", "Material"))],
                ArrayType="StructProperty")
        cdo["Data"].append(bml)
        print("  skins: created BodyMaterialList (entry 0 = M_Body)")
    for sk in skins:
        bml["Value"].append(entry(len(bml["Value"]), _imp(d, "/Game/Cars/Models/%s/MI_SKIN_%s" % (car, sk), "MaterialInstanceConstant")))
    print("  skins: %d liveries added (%d entries)" % (len(skins), len(bml["Value"])))

def clone_blueprint(spec, work, out_root):
    base = spec["base_vehicle"]
    car = spec["car"]
    # variant blueprints live in their family's folder and reuse its wheels / steering wheel
    # (Muhan_Police: Cars/Models/Muhan/Muhan_Police.uasset, Muhan_L/R, SteeringWheels/Muhan)
    bdir, wb = spec.get("base_dir", base), spec.get("base_dir", base)
    src = os.path.join(UNPACKED, "Cars/Models/%s/%s.uasset" % (bdir, base))
    d = tojson(src, os.path.join(work, "%s_base.json" % base))
    pairs = [
        ("/Game/Cars/Models/%s/%s" % (bdir, base), "/Game/Cars/Models/%s/%s" % (car, car)),
        ("Default__%s_C" % base, "Default__%s_C" % car),
        ("%s_C" % base, "%s_C" % car),
        ("/Game/Cars/Parts/Wheels/%s_L" % wb, "/Game/Cars/Parts/Wheels/%s_L" % car),
        ("/Game/Cars/Parts/Wheels/%s_R" % wb, "/Game/Cars/Parts/Wheels/%s_R" % car),
        ("%s_L" % wb, "%s_L" % car),
        ("%s_R" % wb, "%s_R" % car),
    ]
    for a, b in spec.get("base_parts", {}).items():     # e.g. Police_Body -> our Body
        pairs += [("/Game/Cars/Models/%s/%s" % (bdir, a), "/Game/Cars/Models/%s/%s" % (car, b)), (a, b)]
    if spec.get("gauge_ranges") or spec.get("needle_color") or spec.get("needle_scales"):
        # the Dashboard component's GaugeConfigs map (RPM/Speed/Fuel/Temp): needle range must match our painted dials
        # (every base stops the RPM needle at 8 x1000 and the Tuscan's speed at 180), and our own coloured needles
        rng = spec.get("gauge_ranges", {})
        for e in d["Exports"]:
            gc = find_prop(e, "GaugeConfigs")
            if not gc:
                continue
            for kv in gc["Value"]:
                key = kv[0]["Value"].split("::")[-1]
                want = rng.get(key)
                for p in kv[1]["Value"]:
                    if want and p["Name"] == "MaxValue":
                        print("  gauge %s max %s -> %s" % (key, p["Value"], want["max"])); p["Value"] = float(want["max"])
                    if p["Name"] == "NiddleMeshScale" and key in spec.get("needle_scales", {}):
                        # per-car needle size: 85% of that dial's measured radius (the game needle is 4.39 cm long,
                        # the small one 2.2 cm; bases scaled them 1.0 or 0.5 whatever the dial size)
                        k = float(spec["needle_scales"][key])
                        v = p["Value"][0]["Value"] if isinstance(p["Value"], list) else p["Value"]
                        v["X"], v["Y"] = k, k
                        print("  gauge %s needle scale -> %s" % (key, k))
                    if want and p["Name"] == "ValueScale" and "value_scale" in want:
                        # needle value = raw / ValueScale (RPM: 1000); the game feeds km/h, so 1.609344 reads in mph
                        print("  gauge %s ValueScale %s -> %s" % (key, p["Value"], want["value_scale"]))
                        p["Value"] = float(want["value_scale"])
        if spec.get("needle_color"):
            for big, ours in (("Niddle", "Needle"), ("SmallNiddle", "SmallNeedle")):
                for imp in d["Imports"]:
                    if imp["ObjectName"] == big and imp["ClassName"] == "StaticMesh":
                        pkg = d["Imports"][-imp["OuterIndex"] - 1]
                        pkg["ObjectName"] = "/Game/Cars/Models/%s/%s" % (car, ours); imp["ObjectName"] = ours
                        for n in (pkg["ObjectName"], ours):
                            if n not in d["NameMap"]:
                                d["NameMap"].append(n)
                        print("  needle %s -> %s" % (big, pkg["ObjectName"]))
    if "SteeringWheel" in spec.get("extract", {}):   # the car's own steering wheel replaces the base car's
        pairs = [("/Game/Cars/Parts/SteeringWheels/%s" % wb, "/Game/Cars/Parts/SteeringWheels/%s" % car)] + pairs
    parts = ["Body", "Door_L", "Door_R", "Door_Left", "Door_Right", "SideMirror_L", "SideMirror_R", "SideMirror", "LeftSideMirror"] + \
        (["Dashboard"] if spec.get("dashboard") else [])
    for part in parts:
        pairs.append(("/Game/Cars/Models/%s/%s" % (bdir, part), "/Game/Cars/Models/%s/%s" % (car, part)))
    d["NameMap"] = [deep_replace(n, pairs) for n in d["NameMap"]]
    for imp in d["Imports"]:
        for k in ("ObjectName", "ClassName", "ClassPackage"):
            imp[k] = deep_replace(imp[k], pairs)
    if spec.get("dashboard"):
        # our gauge carrier is modelled in car space: zero the base car's DashboardMeshLocation/Rotation offset
        # (the Magis places its shared Dashboard_01 with one; left in, the needles floated outside the car)
        for e in d["Exports"]:
            for nm in ("DashboardMeshLocation", "DashboardMeshRotation"):
                pr = find_prop(e, nm)
                if pr:
                    v = pr["Value"][0]["Value"] if isinstance(pr["Value"], list) else pr["Value"]
                    print("  %s %s -> 0" % (nm, {k: v[k] for k in v if k in ("X", "Y", "Z", "Pitch", "Yaw", "Roll")}))
                    for k in ("X", "Y", "Z", "Pitch", "Yaw", "Roll"):
                        if k in v:
                            v[k] = 0.0
        # bases like the Magis use a shared dashboard (/Game/Cars/Parts/Dashboard/Dashboard_01): repoint whatever the
        # Dashboard component's DashboardMesh imports to the car's own gauge carrier
        for e in d["Exports"]:
            dm = find_prop(e, "DashboardMesh")
            if dm and isinstance(dm.get("Value"), int) and dm["Value"] < 0:
                imp = d["Imports"][-dm["Value"] - 1]
                pkg = d["Imports"][-imp["OuterIndex"] - 1]
                if pkg["ObjectName"] != "/Game/Cars/Models/%s/Dashboard" % car:
                    print("  dashboard %s -> /Game/Cars/Models/%s/Dashboard" % (pkg["ObjectName"], car))
                    pkg["ObjectName"] = "/Game/Cars/Models/%s/Dashboard" % car; imp["ObjectName"] = "Dashboard"
                    for n in (pkg["ObjectName"], "Dashboard"):
                        if n not in d["NameMap"]:
                            d["NameMap"].append(n)
    if "SteeringWheel" in spec.get("extract", {}):
        # the StaticMesh import inside the steering wheel package is named after the base car too
        for imp in d["Imports"]:
            outer = imp.get("OuterIndex", 0)
            if imp["ClassName"] == "StaticMesh" and outer < 0 and                     d["Imports"][-outer - 1]["ObjectName"] == "/Game/Cars/Parts/SteeringWheels/%s" % car:
                imp["ObjectName"] = car
        if car not in d["NameMap"]:
            d["NameMap"].append(car)
        sw_pkg = "/Game/Cars/Parts/SteeringWheels/%s" % car
        if not any(imp["ObjectName"] == sw_pkg for imp in d["Imports"]):
            # bases whose SteeringWheel component sets no mesh (Vista) show the game's generic default wheel: add
            # the import and a StaticMesh property (copied from the Mesh component's) pointing at the car's own wheel
            d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": sw_pkg, "OuterIndex": 0,
                                 "ClassPackage": "/Script/CoreUObject", "ClassName": "Package", "PackageName": None,
                                 "bImportOptional": False})
            d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": car, "OuterIndex": -len(d["Imports"]),
                                 "ClassPackage": "/Script/Engine", "ClassName": "StaticMesh", "PackageName": None,
                                 "bImportOptional": False})
            sm_i = -len(d["Imports"])
            for n in (sw_pkg, car, "StaticMesh", "/Script/Engine", "Package", "/Script/CoreUObject"):
                if n not in d["NameMap"]:
                    d["NameMap"].append(n)
            tmpl = next(copy.deepcopy(p) for e in d["Exports"] if e.get("ObjectName") == "Mesh"
                        for p in e.get("Data", []) if p["Name"] == "StaticMesh")
            tmpl["Value"] = sm_i
            for e in d["Exports"]:
                if e.get("ObjectName") == "SteeringWheel":
                    e["Data"] = [p for p in e["Data"] if p["Name"] != "StaticMesh"]
                    e["Data"].insert(0, tmpl)
                    print("  SteeringWheel component -> %s (base set no mesh)" % sw_pkg)
    keep = spec.get("blueprint", {}).get("keep_body_materials")
    if keep is not None:
        # the base car's skin list: entry 0 is the paintable M_Body ("Paint #1"); the rest are liveries drawn for the
        # base car's UVs that come out scrambled on another body
        for e in d["Exports"]:
            bml = find_prop(e, "BodyMaterialList")
            if bml:
                bml["Value"] = bml["Value"][:keep]
                bm = spec.get("blueprint", {}).get("body_material")
                if bm:
                    # bases whose skin list holds only liveries (Vista: PolygonStreetRacer instances) - make "Paint #1"
                    # the game's paintable M_Body, as on the Zino
                    obj = bm.rsplit("/", 1)[1]
                    d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": bm, "OuterIndex": 0,
                                         "ClassPackage": "/Script/CoreUObject", "ClassName": "Package", "PackageName": None,
                                         "bImportOptional": False})
                    pkg_i = -len(d["Imports"])
                    d["Imports"].append({"$type": "UAssetAPI.Import, UAssetAPI", "ObjectName": obj, "OuterIndex": pkg_i,
                                         "ClassPackage": "/Script/Engine", "ClassName": "Material", "PackageName": None,
                                         "bImportOptional": False})
                    mat_i = -len(d["Imports"])
                    for n in (bm, obj, "Material", "Package", "/Script/Engine", "/Script/CoreUObject"):
                        if n not in d["NameMap"]:
                            d["NameMap"].append(n)
                    for q in bml["Value"][0]["Value"]:
                        if q["Name"] == "Material":
                            q["Value"] = mat_i
                    print("  skin 0 -> %s" % bm)
    skins = [sk["name"] for sk in json.load(open(os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "car.json"))).get("skins", [])]         if spec.get("skins") else []
    if skins:
        add_skins(d, spec["car"], skins)
    engines = spec.get("custom_parts", {}).get("engines")
    if spec.get("default_engine"):
        # an existing engine asset, e.g. More Tuning's /Game/Cars/Parts/Engine/2JZ320HP
        engines = [{"asset": spec["default_engine"].rsplit("/", 1)[1], "dir": spec["default_engine"].rsplit("/", 1)[0]}]
    if engines:
        # the blueprint's EngineComponent has a default EngineData (the base car's engine, e.g. the Zino's V8);
        # point it at the car's own engine so it is used whether the game reads the part or the default
        eng = engines[0]["asset"]
        eng_pkg = engines[0].get("dir", "/Game/Cars/Parts/Engine") + "/" + eng
        for i, imp in enumerate(d["Imports"]):
            if imp["ClassName"] == "MHEngineDataAsset":
                pkg = d["Imports"][-imp["OuterIndex"] - 1]
                old_name, old_pkg = imp["ObjectName"], pkg["ObjectName"]
                imp["ObjectName"] = eng; pkg["ObjectName"] = eng_pkg
                for n in (eng, eng_pkg):
                    if n not in d["NameMap"]:
                        d["NameMap"].append(n)
                print("  default engine %s -> %s" % (old_name, eng))
    hide = set(spec.get("blueprint", {}).get("hide_meshes", []))   # e.g. the base car's dashboard pod and needles
    if hide:
        hidden_imports = {-(i + 1) for i, imp in enumerate(d["Imports"]) if imp["ClassName"] == "StaticMesh" and imp["ObjectName"] in hide}
        def clear(o):   # any object property pointing at a hidden mesh (StaticMesh, DashboardMesh, NiddleMesh...)
            if isinstance(o, dict):
                v = o.get("Value")
                if isinstance(v, int) and v in hidden_imports and "ObjectPropertyData" in o.get("$type", ""):
                    o["Value"] = 0
                for x in o.values():
                    clear(x)
            elif isinstance(o, list):
                for x in o:
                    clear(x)
        for e in d["Exports"]:
            clear(e.get("Data"))
    for e in d["Exports"]:
        e["ObjectName"] = deep_replace(e["ObjectName"], pairs)
    d["SoftPackageReferenceList"] = deep_replace(d.get("SoftPackageReferenceList"), pairs)
    # positions
    w = spec["wheels"]
    # rear_z: the base car's rear springs may be longer (Zino 11 vs 9), so the rear mount can sit higher
    rz = w.get("rear_z", w["z"]); rt = w.get("rear_half_track", w["half_track"])
    wheel_locs = {"Wheel0": (w["front_x"], w["half_track"], w["z"]), "Wheel1": (w["front_x"], -w["half_track"], w["z"]),
                  "Wheel2": (w["rear_x"], rt, rz), "Wheel3": (w["rear_x"], -rt, rz)}
    bp = spec.get("blueprint", {})
    for e in d["Exports"]:
        name = e.get("ObjectName")
        if name in wheel_locs:
            loc = find_prop(e, "RelativeLocation")
            if loc:
                set_vector(loc, wheel_locs[name])
            sc = find_prop(e, "RelativeScale3D")
            if sc:
                # same scale as the game's cars use (their rims are modelled ~50 cm in radius); our own wheel meshes
                # are pre-enlarged by 1/scale in ps_to_mt, so they keep their size and game rims fit too
                k = spec.get("wheel_mesh_scale", WHEEL_MESH_SCALE)
                set_vector(sc, (k, k, k))
        if name in bp.get("seats", {}):
            loc = find_prop(e, "RelativeLocation")
            if loc:
                set_vector(loc, bp["seats"][name])
        for prop, val in spec.get("blueprint", {}).get("set_props", {}).get(name, {}).items():
            # simple property values on base components, e.g. RHD door roles (DoorType DriverDoor <-> PassengerDoor)
            pr = find_prop(e, prop)
            if pr is not None:
                pr["Value"] = val
                if isinstance(val, str) and val not in d["NameMap"]:
                    d["NameMap"].append(val)
                print("  %s.%s = %s" % (name, prop, val))
        own = spec.get("mirror_meshes", {}).get(name)
        if own:
            # this component gets its own mesh (e.g. RightSideMirror with its own counter-rotated glass): add a
            # Package + StaticMesh import pair and point the component's StaticMesh at it
            sm = find_prop(e, "StaticMesh")
            if sm and isinstance(sm["Value"], int) and sm["Value"] < 0:
                old_imp = d["Imports"][-sm["Value"] - 1]
                pkg = copy.deepcopy(d["Imports"][-old_imp["OuterIndex"] - 1])
                pkg["ObjectName"] = "/Game/Cars/Models/%s/%s" % (car, own)
                d["Imports"].append(pkg); pkg_i = -len(d["Imports"])
                mi = copy.deepcopy(old_imp); mi["ObjectName"] = own; mi["OuterIndex"] = pkg_i
                d["Imports"].append(mi); sm["Value"] = -len(d["Imports"])
                for n in (pkg["ObjectName"], own):
                    if n not in d["NameMap"]:
                        d["NameMap"].append(n)
                print("  %s -> own mesh %s" % (name, own))
        mc = spec.get("mirror_components", {}).get(name)
        if mc:   # "SideMirror" or "SideMirror:mirror" -> the recentered mesh's centre (Y mirrored for the right side)
            mesh, _, flip = mc.partition(":")
            c = list(spec.get("recentered", {}).get(mesh, [0, 0, 0]))
            if flip:
                c[1] = -c[1]
            loc = find_prop(e, "RelativeLocation")
            if loc:
                set_vector(loc, c)
        if name in bp.get("components", {}):   # lights, room mirror, dome lights... moved to fit this body
            loc = find_prop(e, "RelativeLocation")
            if loc:
                set_vector(loc, bp["components"][name])
        if name == "Mesh" and "body_mass" in bp:   # chassis mass; the game adds each part's MassKg on top
            bi = find_prop(e, "BodyInstance")
            for q in (bi["Value"] if bi else []):
                if q["Name"] == "MassInKgOverride":
                    q["Value"] = float(bp["body_mass"])
        if name in bp.get("component_rotations", {}):   # [pitch, yaw, roll]
            r = find_prop(e, "RelativeRotation")
            if r:
                v = r["Value"][0]["Value"] if isinstance(r["Value"], list) else r["Value"]
                v["Pitch"], v["Yaw"], v["Roll"] = [float(x) for x in bp["component_rotations"][name]]
        if name == "CockpitCamera" and "cockpit_camera" in bp:
            loc = find_prop(e, "RelativeLocation")
            if loc:
                set_vector(loc, bp["cockpit_camera"])
    if spec.get("drivetrain") == "awd":
        make_awd(d, work)
    out = os.path.join(out_root, "MotorTown/Content/Cars/Models/%s/%s.uasset" % (car, car))
    fromjson(d, os.path.join(work, "%s_bp.json" % car), out)
    return out


def make_awd(d, work):
    """All-wheel drive on a RWD base blueprint, wired like the game's Neo: the base's 'Differential' (fed by the
    Transmission) becomes the centre diff (CenterLSD), new components DifferentialF (FrontLSD, LinkGearRatio -1) and
    DifferentialR (RearLSD) hang off it, front wheels drive through DifferentialF, rear wheels through DifferentialR.
    Each new component = a copy of the Differential template export + its SCS_Node (added to the construction script's
    RootNodes/AllNodes and the CDO's dependencies) + a class variable like 'Differential'."""
    import uuid
    neo = tojson(os.path.join(UNPACKED, "Cars/Models/Neo/Neo.uasset"), os.path.join(work, "Neo_src.json"))
    nprops = {e["ObjectName"]: {p["Name"]: p for p in e.get("Data", [])} for e in neo["Exports"]
              if e.get("ObjectName", "").startswith("Differential")}
    ex = d["Exports"]
    idx = {e.get("ObjectName"): i + 1 for i, e in enumerate(ex)}
    diff_i = idx["Differential_GEN_VARIABLE"]
    diff = ex[diff_i - 1]
    data_asset = next(p for p in diff["Data"] if p["Name"] == "DataAsset")
    node_i = next(i + 1 for i, e in enumerate(ex) if e.get("ObjectName", "").startswith("SCS_Node")
                  and any(p["Name"] == "ComponentTemplate" and p["Value"] == diff_i for p in e.get("Data", [])))
    scs_i = idx[next(n for n in idx if n and n.startswith("SimpleConstructionScript"))]
    cls = next(e for e in ex if "LoadedProperties" in e)
    cdo = next(e for e in ex if e.get("ObjectName", "").startswith("Default__"))
    for n in ("DifferentialF", "DifferentialR", "DifferentialF_GEN_VARIABLE", "DifferentialR_GEN_VARIABLE", "LSDSlotName",
              "LSDSlotIndex", "LinkGearRatio", "DifferentialComponentName", "TextProperty", "IntProperty", "FloatProperty",
              "StrProperty", "NameProperty", "SCS_Node",
              "/Game/DataAsset/StringTables/VehicleParts.VehicleParts"):   # LSDSlotName text = VehicleParts string-table key
        if n not in d["NameMap"]:
            d["NameMap"].append(n)

    def neo_prop(comp, name):
        q = copy.deepcopy(nprops[comp + "_GEN_VARIABLE"][name])
        return q
    # centre: the base Differential keeps TransmissionComponentName, gets the centre LSD slot
    diff["Data"] = [neo_prop("DifferentialC", "LSDSlotName"), neo_prop("DifferentialC", "LSDSlotIndex")] + diff["Data"]
    n_nodes = sum(1 for e in ex if e.get("ObjectName", "").startswith("SCS_Node"))
    for k, comp in enumerate(("DifferentialF", "DifferentialR")):
        t = copy.deepcopy(diff)
        t["ObjectName"] = comp + "_GEN_VARIABLE"
        props = [neo_prop(comp, "LSDSlotName")]
        if "LSDSlotIndex" in nprops[comp + "_GEN_VARIABLE"]:
            props.append(neo_prop(comp, "LSDSlotIndex"))
        dcn = neo_prop(comp, "DifferentialComponentName"); dcn["Value"] = "Differential"
        props.append(dcn)
        if "LinkGearRatio" in nprops[comp + "_GEN_VARIABLE"]:
            props.append(neo_prop(comp, "LinkGearRatio"))
        props += [copy.deepcopy(p) for p in diff["Data"] if p["Name"] in ("Inertia", "DataAsset")]
        t["Data"] = props
        ex.append(t); t_i = len(ex)
        node = copy.deepcopy(ex[node_i - 1])
        node["ObjectName"] = "SCS_Node_%d" % (100 + k)
        for p in node["Data"]:
            if p["Name"] == "ComponentTemplate":
                p["Value"] = t_i
            elif p["Name"] == "InternalVariableName":
                p["Value"] = comp
            elif p["Name"] == "VariableGuid":
                p["Value"][0]["Value"] = "{%s}" % str(uuid.uuid4()).upper()
        node["CreateBeforeSerializationDependencies"] = [t_i if x == diff_i else x for x in node.get("CreateBeforeSerializationDependencies", [])]
        ex.append(node); n_i = len(ex)
        scs = ex[scs_i - 1]
        for p in scs["Data"]:
            if p["Name"] in ("RootNodes", "AllNodes"):
                q = copy.deepcopy(p["Value"][0]); q["Name"] = str(len(p["Value"])); q["Value"] = n_i
                p["Value"].append(q)
        scs["CreateBeforeSerializationDependencies"] = scs.get("CreateBeforeSerializationDependencies", []) + [n_i]
        cdo["SerializationBeforeSerializationDependencies"] = cdo.get("SerializationBeforeSerializationDependencies", []) + [t_i, n_i]
        lp = copy.deepcopy(next(p for p in cls["LoadedProperties"] if p["Name"] == "Differential"))
        lp["Name"] = comp
        cls["LoadedProperties"].insert(0, lp)
    # wheels: 0/1 front through DifferentialF, 2/3 rear through DifferentialR; the right-hand wheel of each axle mirrored
    tmpl = None
    for e in ex:
        if e.get("ObjectName") in ("Wheel2", "Wheel3"):
            tmpl = tmpl or next(p for p in e["Data"] if p["Name"] == "DifferentialComponentName")
    lgr_t = next(p for e in ex if e.get("ObjectName") == "Wheel3" for p in e["Data"] if p["Name"] == "LinkGearRatio")
    for e in ex:
        w = e.get("ObjectName")
        if w not in ("Wheel0", "Wheel1", "Wheel2", "Wheel3"):
            continue
        e["Data"] = [p for p in e["Data"] if p["Name"] not in ("DifferentialComponentName", "LinkGearRatio")]
        q = copy.deepcopy(tmpl); q["Value"] = "DifferentialF" if w in ("Wheel0", "Wheel1") else "DifferentialR"
        new = [q]
        if w in ("Wheel1", "Wheel3"):
            new.append(copy.deepcopy(lgr_t))
        e["Data"] = new + e["Data"]
    print("  AWD: centre Differential -> DifferentialF (front) + DifferentialR (rear)")


def text_literal(prop, key, text):
    """A 'Base' FText of our own: namespace Vehicles_ProStreet, key <car>_VehicleName, source string = display name."""
    prop["HistoryType"] = "Base"
    prop["Namespace"] = "Vehicles_ProStreet"
    prop["Value"] = key
    prop["CultureInvariantString"] = text


def make_table(specs, work, out_root):
    base_tbl = tojson(os.path.join(UNPACKED, "DataAsset/Vehicles/Vehicles_1.uasset"), os.path.join(work, "Vehicles_1.json"))
    rows = {r["Name"]: r for r in base_tbl["Exports"][0]["Table"]["Data"]}
    jeep = tojson(os.path.join(UNPACKED, "DataAsset/Vehicles/Vehicles_Jeep.uasset"), os.path.join(work, "Vehicles_Jeep.json"))
    new_rows = []
    for spec in specs:
        row = copy.deepcopy(rows[spec["base_vehicle"]])
        row["Name"] = spec["car"]
        for p in row["Value"]:
            if p["Name"] == "VehicleName":
                text_literal(p, spec["car"] + "_VehicleName", spec["display_name"])
            elif p["Name"] == "VehicleClass":
                ap = p["Value"]["AssetPath"]
                ap["PackageName"] = "/Game/Cars/Models/%s/%s" % (spec["car"], spec["car"])
                ap["AssetName"] = "%s_C" % spec["car"]
            elif p["Name"] == "Cost" and "cost" in spec:
                p["Value"] = int(spec["cost"])
            elif p["Name"] == "Parts":
                # drop the base car's body kit and rims: those parts are its own meshes and would cover ours
                strip = set(spec.get("strip_part_slots", []))
                p["Value"] = [kv for kv in p["Value"] if str(kv[0].get("Value", "")).split("::")[-1] not in strip]
                present = set()
                for kv in p["Value"]:   # e.g. Wheel0..3 -> the car's own rim part
                    slot = str(kv[0].get("Value", "")).split("::")[-1]
                    present.add(slot)
                    if slot in spec.get("part_overrides", {}):
                        kv[1]["Value"] = spec["part_overrides"][slot]
                for slot, key in spec.get("part_overrides", {}).items():   # slots the base row lacks (body kits)
                    if slot not in present:
                        kv = copy.deepcopy(p["Value"][0])
                        kv[0]["Value"] = "EMTVehiclePartSlot::" + slot
                        kv[1]["Value"] = key
                        p["Value"].append(kv)
            elif p["Name"] == "NotOptionalPartTypes":
                p["Value"] = [{"$type": "UAssetAPI.PropertyTypes.Objects.EnumPropertyData, UAssetAPI", "EnumType": None,
                               "InnerType": None, "Name": str(i), "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False,
                               "PropertyTagFlags": "None", "PropertyTypeName": None,
                               "PropertyTagExtensions": "NoExtension", "Value": "EMTVehiclePartType::" + t}
                              for i, t in enumerate(spec.get("not_optional_part_types", []))]
        new_rows.append(row)
    jeep["Exports"][0]["Table"]["Data"] = new_rows
    pairs = [("/Game/DataAsset/Vehicles/Vehicles_Jeep", "/Game/DataAsset/Vehicles/Vehicles_ProStreet"),
             ("Vehicles_Jeep", "Vehicles_ProStreet")]
    jeep["NameMap"] = [deep_replace(n, pairs) for n in jeep["NameMap"]]
    for n in jeep["NameMap"]:
        pass
    for e in jeep["Exports"]:
        e["ObjectName"] = deep_replace(e["ObjectName"], pairs)
    # names used by the copied rows must exist in this table's name map (incl. every part key a row now names)
    for spec in specs:
        for n in [spec["car"], "/Game/Cars/Models/%s/%s" % (spec["car"], spec["car"]), "%s_C" % spec["car"]] + \
                list(spec.get("part_overrides", {}).values()) + \
                ["EMTVehiclePartSlot::" + k for k in spec.get("part_overrides", {})] + \
                ["EMTVehiclePartType::" + t for t in spec.get("not_optional_part_types", [])]:
            if n not in jeep["NameMap"]:
                jeep["NameMap"].append(n)
    for n in base_tbl["NameMap"]:
        if n not in jeep["NameMap"]:
            jeep["NameMap"].append(n)
    out = os.path.join(out_root, "MotorTown/Content/DataAsset/Vehicles/Vehicles_ProStreet.uasset")
    fromjson(jeep, os.path.join(work, "Vehicles_ProStreet.json"), out)
    return out, new_rows, jeep["NameMap"]


def remap_imports(value, src_imps, dst, cache):
    """Rows copied from one package into another carry object references as import indices (-1 = first import) of
    their SOURCE package. Re-create each referenced import (and its outer chain) in dst and rewrite the index, in place.
    Without this the merged rows in the composite pointed at unrelated or out-of-range imports, which crashed the game
    at boot once our tables had more imports than the composite (2026-10-19: 389 aero rows)."""
    def imp_index(i):   # i: negative source index -> negative dst index
        if i in cache:
            return cache[i]
        src = copy.deepcopy(src_imps[-i - 1])
        if src.get("OuterIndex", 0) < 0:
            src["OuterIndex"] = imp_index(src["OuterIndex"])
        for k, x in enumerate(dst["Imports"]):
            if all(x.get(f) == src.get(f) for f in ("ObjectName", "ClassName", "ClassPackage", "OuterIndex")):
                cache[i] = -(k + 1)
                return cache[i]
        dst["Imports"].append(src)
        for n in (src["ObjectName"], src.get("ClassName"), src.get("ClassPackage")):
            if n and n not in dst["NameMap"]:
                dst["NameMap"].append(n)
        cache[i] = -len(dst["Imports"])
        return cache[i]
    if isinstance(value, dict):
        t = value.get("$type", "")
        if "ObjectPropertyData" in t and isinstance(value.get("Value"), int) and value["Value"] < 0:
            value["Value"] = imp_index(value["Value"])
        for k, v in value.items():
            if isinstance(v, (dict, list)):
                remap_imports(v, src_imps, dst, cache)
    elif isinstance(value, list):
        for v in value:
            remap_imports(v, src_imps, dst, cache)


def patch_composite(work, out_root, new_rows, row_names, folder="Vehicles", comp_name="Vehicles",
                    template="Vehicles_Jeep", new_name="Vehicles_ProStreet"):
    """Add our table to a composite table's ParentTables. The cooked composite also keeps a merged copy of every
    parent's rows, so the new rows go in there too (the game re-merges parents at load, which is why mods that only
    replace a parent table work)."""
    comp = tojson(os.path.join(UNPACKED, "DataAsset/%s/%s.uasset" % (folder, comp_name)), os.path.join(work, comp_name + ".json"))
    imps = comp["Imports"]
    # copy the template's import pair (DataTable + its Package) under our table's name
    pkg_path = "/Game/DataAsset/%s/%s" % (folder, new_name)
    pkg_i = next(i for i, x in enumerate(imps) if x["ObjectName"] == "/Game/DataAsset/%s/%s" % (folder, template))
    tbl_i = next(i for i, x in enumerate(imps) if x["ObjectName"] == template and x["ClassName"] != "Package")
    new_pkg = copy.deepcopy(imps[pkg_i]); new_pkg["ObjectName"] = pkg_path
    imps.append(new_pkg)
    new_tbl = copy.deepcopy(imps[tbl_i]); new_tbl["ObjectName"] = new_name; new_tbl["OuterIndex"] = -len(imps)
    imps.append(new_tbl)
    for n in (pkg_path, new_name):
        if n not in comp["NameMap"]:
            comp["NameMap"].append(n)
    e = comp["Exports"][0]
    parents = find_prop(e, "ParentTables")
    if parents is None:
        raise SystemExit("composite has no ParentTables property: " + str([p["Name"] for p in e.get("Data", [])]))
    entry = copy.deepcopy(parents["Value"][-1])
    entry["Value"] = -len(imps)
    entry["Name"] = str(len(parents["Value"]))
    parents["Value"].append(entry)
    have = {r["Name"] for r in e["Table"]["Data"]}
    src_path = os.path.join(work, new_name + ".json")   # the parent table as just written: its imports
    src_imps = json.load(open(src_path, encoding="utf-8"))["Imports"] if os.path.exists(src_path) else None
    cache = {}
    for r in new_rows:
        if r["Name"] not in have:
            r2 = copy.deepcopy(r)
            if src_imps is not None:
                remap_imports(r2, src_imps, comp, cache)
            e["Table"]["Data"].append(r2)
    for n in row_names:
        if n not in comp["NameMap"]:
            comp["NameMap"].append(n)
    out = os.path.join(out_root, "MotorTown/Content/DataAsset/%s/%s.uasset" % (folder, comp_name))
    fromjson(comp, os.path.join(work, comp_name + "_patched.json"), out)
    return out


def clone_named_asset(src_rel, dst_rel, work, extra_pairs=()):
    """Copy a game asset under a new package/object name (e.g. an engine data asset) as UAssetGUI JSON."""
    d = tojson(os.path.join(UNPACKED, src_rel + ".uasset"), os.path.join(work, os.path.basename(dst_rel) + "_src.json"))
    pairs = [("/Game/" + src_rel, "/Game/" + dst_rel), (os.path.basename(src_rel), os.path.basename(dst_rel))] + list(extra_pairs)
    def rep(n):
        for a, b in pairs:
            if n == a:
                return b
        return n
    d["NameMap"] = [rep(n) for n in d["NameMap"]]
    for imp in d["Imports"]:
        imp["ObjectName"] = rep(imp["ObjectName"])
    for e in d["Exports"]:
        e["ObjectName"] = rep(e["ObjectName"])
    return d


def make_sound_cue(snd, work, out_root):
    """Engine SoundCue for our own loops (e.g. the ProStreet 997's exhaust grains): clone a base cue (More Tuning's
    S58: RPM crossfade of idle/mid/high looping waves, each pitch-modulated by RPM), repoint its waves to our imported
    SoundWaves (snd["dir"], cooked from the UE project) and set each wave's pitch so it plays at 1.0 at the rpm it
    was recorded at (pitch = rpm / recorded rpm across the modulator's input range)."""
    base_rel = snd["cue_base"]
    base_dir = "/Game/" + base_rel.rsplit("/", 1)[0] + "/"
    new_dir = "/Game/Cars/Parts/Engine/Sound/" + snd["dir"] + "/"
    rel = "Cars/Parts/Engine/Sound/%s/SC_%s" % (snd["dir"], snd["dir"])
    d = clone_named_asset(base_rel, rel, work)
    txt = json.dumps(d).replace(base_dir, new_dir)
    d = json.loads(txt)
    ex = d["Exports"]
    parent = {}
    for i, e in enumerate(ex, 1):
        for p in e.get("Data", []):
            if p["Name"] == "ChildNodes":
                for c in p["Value"]:
                    parent[c["Value"]] = i
    for i, e in enumerate(ex, 1):
        ptr = next((p for p in e.get("Data", []) if p["Name"] == "SoundWaveAssetPtr"), None)
        if not ptr:
            continue
        wave = ptr["Value"]["AssetPath"]["AssetName"]
        rec = snd.get("pitch_rpm", {}).get(wave)
        if not rec:
            continue
        mod = ex[parent[i] - 1]
        pm = next((p for p in mod.get("Data", []) if p["Name"] == "PitchModulationParams"), None)
        if not pm:
            continue
        f = {q["Name"]: q for q in pm["Value"]}
        lo = float(f["MinInput"]["Value"]) if "MinInput" in f else 0.0
        hi = float(f["MaxInput"]["Value"]) if "MaxInput" in f else 1.0
        for k, v in (("MinOutput", lo / rec), ("MaxOutput", hi / rec)):
            if k in f:
                f[k]["Value"] = round(v, 4)
            else:
                q = copy.deepcopy(f["MinInput"]); q["Name"] = k; q["Value"] = round(v, 4); pm["Value"].append(q)
        print("  cue %s: %s recorded at %d rpm -> pitch %.3f..%.3f over %d..%d rpm" % (rel, wave, rec, lo / rec, hi / rec, lo, hi))
    if "MaxOutput" not in d["NameMap"]:
        d["NameMap"].append("MaxOutput")
    fromjson(d, os.path.join(work, os.path.basename(rel) + ".json"), os.path.join(out_root, "MotorTown/Content", rel + ".uasset"))
    return "/Game/" + rel


def make_engine(e, work, out_root):
    """Engine data asset + its torque curve. Torque is stored as N*m x 10000; the curve's time axis is rpm / MaxRPM."""
    if e.get("curve") is None:
        return make_engine_tune_only(e, work, out_root)
    curve_rel = "Cars/Parts/Engine/TorqueCurve/TorqueCurve_" + e["asset"]
    c = clone_named_asset("Cars/Parts/Engine/TorqueCurve/TorqueCurve_SOHC", curve_rel, work)
    keys = c["Exports"][0]["Data"][0]["Value"][0]["Value"]
    tmpl = keys[0]
    new_keys = []
    for i, (t, v) in enumerate(e["curve"]):
        k = copy.deepcopy(tmpl); k["Name"] = str(i)
        kv = k["Value"][0]["Value"]
        kv.update({"InterpMode": "RCIM_Linear", "TangentMode": "RCTM_Auto", "Time": float(t), "Value": float(v),
                   "ArriveTangent": 0.0, "LeaveTangent": 0.0})
        new_keys.append(k)
    c["Exports"][0]["Data"][0]["Value"][0]["Value"] = new_keys
    fromjson(c, os.path.join(work, os.path.basename(curve_rel) + ".json"), os.path.join(out_root, "MotorTown/Content", curve_rel + ".uasset"))
    eng_rel = "Cars/Parts/Engine/" + e["asset"]
    d = clone_named_asset(e["base_asset"], eng_rel, work)
    for imp in d["Imports"]:   # point the engine at our curve, whatever curve the base engine used
        if imp["ClassName"] == "CurveFloat":
            imp["ObjectName"] = os.path.basename(curve_rel)
            d["Imports"][-imp["OuterIndex"] - 1]["ObjectName"] = "/Game/" + curve_rel
    for n in (os.path.basename(curve_rel), "/Game/" + curve_rel):
        if n not in d["NameMap"]:
            d["NameMap"].append(n)
    if e.get("sound"):
        # engine sound set (MTEngineSoundDataAsset): swap the import, e.g. to V6Sport_02
        pkg_path, obj = e["sound"].rsplit(".", 1)
        for imp in d["Imports"]:
            if imp["ClassName"] == "MTEngineSoundDataAsset":
                imp["ObjectName"] = obj
                d["Imports"][-imp["OuterIndex"] - 1]["ObjectName"] = pkg_path
        for n in (obj, pkg_path):
            if n not in d["NameMap"]:
                d["NameMap"].append(n)
    if e.get("sound_cue"):
        # our own engine SoundCue (make_sound_cue) in place of the base engine's main cue
        cue = make_sound_cue(e["sound_cue"], work, out_root)
        base_cue = e["sound_cue"]["cue_base"].rsplit("/", 1)[1]
        for imp in d["Imports"]:
            if imp["ClassName"] == "SoundCue" and imp["ObjectName"] == base_cue:
                imp["ObjectName"] = cue.rsplit("/", 1)[1]
                d["Imports"][-imp["OuterIndex"] - 1]["ObjectName"] = cue
        for n in (cue, cue.rsplit("/", 1)[1]):
            if n not in d["NameMap"]:
                d["NameMap"].append(n)
    apply_engine_props(d, e)
    fromjson(d, os.path.join(work, e["asset"] + ".json"), os.path.join(out_root, "MotorTown/Content", eng_rel + ".uasset"))
    return "/Game/" + eng_rel, e["asset"]


def apply_engine_props(d, e):
    prop = find_prop(d["Exports"][0], "EngineProperty")
    for q in prop["Value"]:
        if q["Name"] == "MaxTorque" and e.get("max_torque_nm"):
            q["Value"] = float(e["max_torque_nm"]) * 10000.0
        elif q["Name"] == "MaxTorque" and e.get("torque_scale"):
            q["Value"] = float(q["Value"]) * float(e["torque_scale"])
        elif q["Name"] == "MaxRPM" and e.get("max_rpm"):
            q["Value"] = float(e["max_rpm"])
        elif q["Name"] == "MaxRPM" and e.get("rpm_add"):
            q["Value"] = float(q["Value"]) + float(e["rpm_add"])
        elif q["Name"] == "FuelConsumption" and e.get("fuel_scale"):
            q["Value"] = float(q["Value"]) * float(e["fuel_scale"])
        elif q["Name"] == "AfterFireProbability" and e.get("afterfire") is not None:
            q["Value"] = float(e["afterfire"])


def make_engine_tune_only(e, work, out_root):
    """a tune of an existing engine asset: same torque curve / sound, scaled MaxTorque etc."""
    eng_rel = "Cars/Parts/Engine/" + e["asset"]
    d = clone_named_asset(e["base_asset"], eng_rel, work)
    apply_engine_props(d, e)
    fromjson(d, os.path.join(work, e["asset"] + ".json"), os.path.join(out_root, "MotorTown/Content", eng_rel + ".uasset"))
    return "/Game/" + eng_rel, e["asset"]


# ProStreet-style ECU / timing tunes: (suffix, label, torque x, rpm +, fuel x, afterfire %)
ENGINE_TUNES = [("T1", "Street Tune", 1.06, 150, 1.05, 60.0), ("T2", "Race Tune", 1.12, 300, 1.12, 75.0),
                ("T3", "Pro Tune", 1.20, 500, 1.22, 90.0)]


def engine_tunes(spec, engines_table_src):
    """tuned versions of the car's engine: its own custom engine (same curve, scaled torque) or, for a car that ships
    with a base-game engine, a clone of that engine asset with scaled MaxTorque"""
    out = []
    cars_eng = spec.get("custom_parts", {}).get("engines") or []
    for k, (suf, lab, tq, rpm, fuel, af) in enumerate(ENGINE_TUNES):
        if cars_eng:
            e0 = cars_eng[0]
            t = copy.deepcopy(e0)
            t.update({"row": "%s_%s" % (e0["row"], suf), "asset": "%s_%s" % (e0["asset"], suf),
                      "display_name": "%s - %s" % (e0["display_name"].split(" (")[0], lab),
                      "max_torque_nm": round(float(e0["max_torque_nm"]) * tq, 1), "max_rpm": float(e0["max_rpm"]) + rpm,
                      "cost": int(e0.get("cost", 20000) * (1 + 0.5 * (k + 1)))})
        else:
            key = spec.get("part_overrides", {}).get("Engine")
            rows_ = engines_table_src["Exports"][0]["Table"]["Data"]
            row = next((r for r in rows_ if r["Name"] == key), None)
            if row is not None:
                ap = next(p for p in row["Value"] if p["Name"] == "EngineAsset")["Value"]["AssetPath"]
                base_asset, base_row = ap["PackageName"].replace("/Game/", ""), key
            elif os.path.exists(os.path.expanduser("~/mt-work/unpacked/MotorTown/Content/Cars/Parts/Engine/%s.uasset" % key)):
                # an engine row added by another mod (Viper: More Tuning's V10ACR): its asset is in the game files;
                # any game engine row serves as the row template
                base_asset, base_row = "Cars/Parts/Engine/" + key, rows_[0]["Name"]
            else:
                return out
            t = {"row": "%s_%s_%s" % (spec["car"], key, suf), "base_row": base_row, "asset": "%s_%s_%s" % (spec["car"], key, suf),
                 "base_asset": base_asset, "display_name": "%s - %s" % (spec.get("engine_label", key), lab),
                 "curve": None, "torque_scale": tq, "rpm_add": rpm, "cost": int(20000 * (1 + 0.5 * (k + 1)))}
        t.update({"fuel_scale": fuel, "afterfire": af, "vehicle_keys": [spec["car"]], "tune": True})
        t.pop("sound_cue", None) if False else None
        out.append(t)
    return out


def make_transmission(t, work, out_root):
    rel = "Cars/Parts/Transmission/" + t["asset"]
    d = clone_named_asset(t["base_asset"], rel, work)
    prop = find_prop(d["Exports"][0], "TransmissionProperty")
    gears = next(q for q in prop["Value"] if q["Name"] == "Gears")
    if t.get("drop_gears"):
        # e.g. a 3-speed TorqueFlite from the game's 4-speed muscle automatic
        gears["Value"] = [g for g in gears["Value"]
                          if str(next(q["Value"] for q in g["Value"] if q["Name"] == "Name")) not in t["drop_gears"]]
        for i, g in enumerate(gears["Value"]):
            g["Name"] = str(i)
    for g in gears["Value"]:
        f = {q["Name"]: q for q in g["Value"]}
        nm = str(f["Name"]["Value"])
        if nm in t["ratios"]:
            f["GearRatio"]["Value"] = float(t["ratios"][nm])
    fromjson(d, os.path.join(work, t["asset"] + ".json"), os.path.join(out_root, "MotorTown/Content", rel + ".uasset"))
    return "/Game/" + rel, t["asset"]


def custom_part_rows(spec, work, out_root, name_map):
    """Rows for the car's own engine/transmission parts (same row struct as wheels), pointing at cloned assets."""
    rows = []
    cp = spec.get("custom_parts", {})
    for kind, table, asset_prop, maker in (("engines", "Engines", "EngineAsset", make_engine),
                                           ("transmissions", "Transmissions", "TransmissionAsset", make_transmission)):
        if not cp.get(kind) and not (kind == "engines" and spec.get("part_overrides", {}).get("Engine")):
            continue
        src = tojson(os.path.join(UNPACKED, "DataAsset/VehicleParts/%s.uasset" % table), os.path.join(work, table + ".json"))
        base_rows = {r["Name"]: r for r in src["Exports"][0]["Table"]["Data"]}
        for n in src["NameMap"]:
            if n not in name_map:
                name_map.append(n)
        parts = list(cp.get(kind) or [])
        if kind == "engines" and spec.get("engine_tunes", True) and not spec.get("kind"):
            parts += engine_tunes(spec, src)
        for part in parts:
            pkg, obj = maker(part, work, out_root)
            row = copy.deepcopy(base_rows[part["base_row"]]); row["Name"] = part["row"]
            for p in row["Value"]:
                if p["Name"] == "Name":
                    text_literal(p, part["row"] + "_Name", part["display_name"])
                elif p["Name"] == asset_prop:
                    p["Value"]["AssetPath"]["PackageName"] = pkg; p["Value"]["AssetPath"]["AssetName"] = obj
                elif p["Name"] == "MassKg" and "mass" in part:
                    p["Value"] = float(part["mass"])
                elif p["Name"] == "Cost" and "cost" in part:
                    p["Value"] = int(part["cost"])
                elif p["Name"] == "VehicleKeys" and part.get("vehicle_keys"):
                    p["Value"] = [{"$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI", "Name": str(i),
                                   "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False, "PropertyTagFlags": "None",
                                   "PropertyTypeName": None, "PropertyTagExtensions": "NoExtension", "Value": k}
                                  for i, k in enumerate(part["vehicle_keys"])]
            for n in (part["row"], pkg, obj) + tuple(part.get("vehicle_keys") or ()):
                if n not in name_map:
                    name_map.append(n)
            rows.append(row)
    return rows


def make_wheel_table(specs, work, out_root):
    """Wheels_ProStreet: one Wheel part row per car (copied from the base car's rim row), pointing at the car's
    own rim meshes /Game/Cars/Parts/Wheels/<car>_L/_R."""
    t = tojson(os.path.join(UNPACKED, "DataAsset/VehicleParts/Wheels.uasset"), os.path.join(work, "Wheels.json"))
    rows = {r["Name"]: r for r in t["Exports"][0]["Table"]["Data"]}
    imps = t["Imports"]
    pkg_tmpl = next(x for x in imps if x["ClassName"] == "Package" and x["ObjectName"].startswith("/Game/Cars/Parts/Wheels/"))
    mesh_tmpl = next(x for x in imps if x["ClassName"] == "StaticMesh")
    new_rows = []

    civo = next(r for r in t["Exports"][0]["Table"]["Data"] if r["Name"] == "Civo")
    civo_colors = copy.deepcopy(next(p for p in civo["Value"] if p["Name"] == "ColorSlots"))
    # satin finish by default (Civo's mirror-chrome made our textured rims glare white)
    def _finish(o):
        if isinstance(o, dict):
            if o.get("Name") == "DefaultMetallic" and isinstance(o.get("Value"), (int, float)):
                o["Value"] = 0.3
            elif o.get("Name") == "DefaultRoughness" and isinstance(o.get("Value"), (int, float)):
                o["Value"] = 0.45
            for v in o.values():
                _finish(v)
        elif isinstance(o, list):
            for v in o:
                _finish(v)
    _finish(civo_colors)
    # 7.15+ wheel customization (what Maja's Wheel Works enables on old wheels): the rim's material slots listed in
    # DecalableMaterialSlotNames. Without it the rim colour option is locked in multiplayer
    civo_decal = copy.deepcopy(next(p for p in civo["Value"] if p["Name"] == "DecalableMaterialSlotNames"))

    def _white(o):   # default picker colour white, so the rim texture shows untouched until a colour is chosen
        if isinstance(o, dict):
            if "ColorPropertyData" in o.get("$type", "") and isinstance(o.get("Value"), str):
                o["Value"] = ", ".join("255" for _ in o["Value"].split(","))
            if "TextPropertyData" in o.get("$type", "") and o.get("Name") == "DisplayName":
                o["CultureInvariantString"] = "Rim"
            for x in o.values():
                _white(x)
        elif isinstance(o, list):
            for x in o:
                _white(x)
    _white(civo_colors)
    if "Wheel_01" not in t["NameMap"]:
        t["NameMap"].append("Wheel_01")

    def add_rim(row_name, left, right, display, base, vehicle_keys=None, cost=None, rear=None):
        """One Wheel part row whose meshes are /Game/Cars/Parts/Wheels/<left|right>; vehicle_keys limits which
        vehicles may fit it (rims sized for ProStreet cars look wrong on the game's own cars)."""
        meshes = {}
        for side, name in (("L", left), ("R", right)) + ((("RL", rear[0]), ("RR", rear[1])) if rear else ()):
            pkg = copy.deepcopy(pkg_tmpl); pkg["ObjectName"] = "/Game/Cars/Parts/Wheels/" + name
            imps.append(pkg)
            m = copy.deepcopy(mesh_tmpl); m["ObjectName"] = name; m["OuterIndex"] = -len(imps)
            imps.append(m)
            meshes[side] = -len(imps)
            for n in (pkg["ObjectName"], name):
                if n not in t["NameMap"]:
                    t["NameMap"].append(n)
        row = copy.deepcopy(rows[base])
        row["Name"] = row_name
        for p in row["Value"]:
            if p["Name"] == "Name":
                text_literal(p, row_name + "_WheelName", display)
            elif p["Name"] == "Wheel":
                for q in p["Value"]:
                    if q["Name"] == "LeftWheelMesh":
                        q["Value"] = meshes["L"]
                    elif q["Name"] == "RightWheelMesh":
                        q["Value"] = meshes["R"]
                    elif q["Name"] == "RearLeftWheelMesh" and rear:      # own (wider) rear rims, e.g. Viper 345s
                        q["Value"] = meshes["RL"]
                    elif q["Name"] == "RearRightWheelMesh" and rear:
                        q["Value"] = meshes["RR"]
            elif p["Name"] == "VehicleKeys" and vehicle_keys:
                p["Value"] = [{"$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI", "Name": str(i),
                               "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False, "PropertyTagFlags": "None",
                               "PropertyTypeName": None, "PropertyTagExtensions": "NoExtension", "Value": k}
                              for i, k in enumerate(vehicle_keys)]
            elif p["Name"] == "Cost" and cost is not None:
                p["Value"] = int(cost)
            elif p["Name"] == "ColorSlots":
                p["Value"] = copy.deepcopy(civo_colors["Value"])   # Wheel_01 colour picker (paintable rim)
            elif p["Name"] == "DecalableMaterialSlotNames":
                p["Value"] = copy.deepcopy(civo_decal["Value"])
        for n in [row_name] + list(vehicle_keys or []):
            if n not in t["NameMap"]:
                t["NameMap"].append(n)
        new_rows.append(row)

    for spec in specs:
        if spec.get("kind") == "rims":
            # rim pack built by ps_rims.py: rows listed in <build>/rims.json
            for r in json.load(open(os.path.join(os.path.dirname(os.path.expanduser(spec["out_dir"])), "rims.json"))):
                add_rim(r["row"], r["left"], r["right"], r["display_name"], spec.get("base_wheel", "Zino"),
                        spec.get("vehicle_keys"), spec.get("cost"))
            continue
        if not spec.get("wheel_part"):
            continue
        # the car's own stock rim; the meshes are swapped like spec mesh_names (Wheel_L geometry is the _R asset)
        rear = (spec["car"] + "_REAR_L", spec["car"] + "_REAR_R") if spec.get("rear_wheel_meshes") else None
        add_rim(spec["car"], spec["car"] + "_L", spec["car"] + "_R",
                spec.get("wheel_display_name", spec["display_name"]), spec.get("base_wheel", spec["base_vehicle"]),
                rear=rear)
    for spec in specs:
        if spec.get("kind") != "rims":
            new_rows += custom_part_rows(spec, work, out_root, t["NameMap"])
    t["Exports"][0]["Table"]["Data"] = new_rows
    pairs = [("/Game/DataAsset/VehicleParts/Wheels", "/Game/DataAsset/VehicleParts/Wheels_ProStreet")]
    t["NameMap"] = [deep_replace(n, pairs) if n == "/Game/DataAsset/VehicleParts/Wheels" else n for n in t["NameMap"]]
    t["Exports"][0]["ObjectName"] = "Wheels_ProStreet"
    if "Wheels_ProStreet" not in t["NameMap"]:
        t["NameMap"].append("Wheels_ProStreet")
    out = os.path.join(out_root, "MotorTown/Content/DataAsset/VehicleParts/Wheels_ProStreet.uasset")
    fromjson(t, os.path.join(work, "Wheels_ProStreet.json"), out)
    return out, new_rows, t["NameMap"]


def patch_composite_from(out_root, work, new_rows, row_names, template, new_name):
    """Like patch_composite for DataAsset/VehicleParts/VehicleParts, but starting from the copy already written to
    out_root (so Wheels_ProStreet and Aero_ProStreet both end up as parents)."""
    global UNPACKED
    saved = UNPACKED
    UNPACKED = os.path.join(out_root, "MotorTown", "Content")
    try:
        return patch_composite(work, out_root, new_rows, row_names, folder="VehicleParts", comp_name="VehicleParts",
                               template=template, new_name=new_name)
    finally:
        UNPACKED = saved


def make_aero_table(specs, work, out_root):
    """Aero_ProStreet: one AeroParts row per body-kit piece (spec aero_parts, from add_body_kits.py), copied from a game
    row of the same PartType, pointing at the car's own car-space mesh /Game/Cars/Models/<car>/<mesh>, limited to that
    car (VehicleKeys) and attached at the body origin (bUseCustomSocket False)."""
    t = tojson(os.path.join(UNPACKED, "DataAsset/VehicleParts/AeroParts.uasset"), os.path.join(work, "AeroParts.json"))
    by_type = {}
    for r in t["Exports"][0]["Table"]["Data"]:
        by_type.setdefault(str(next(p["Value"] for p in r["Value"] if p["Name"] == "PartType")).split("::")[-1], r)
    # wings paint with the body only when the row lists their slot in BodyMaterialNames (Stella/Cora wings do)
    by_type["RearWing"] = next(r for r in t["Exports"][0]["Table"]["Data"] if r["Name"] == "Stella_RearWing_03")
    imps = t["Imports"]
    mesh_tmpl = next(x for x in imps if x["ClassName"] == "StaticMesh")
    pkg_tmpl = next(x for x in imps if x["ClassName"] == "Package" and x["ObjectName"].startswith("/Game/Cars/"))
    name_item = lambda i, v: {"$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI", "Name": str(i),
                              "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False, "PropertyTagFlags": "None",
                              "PropertyTypeName": None, "PropertyTagExtensions": "NoExtension", "Value": v}
    rows = []
    for spec in specs:
        for a in spec.get("aero_parts", []):
            pkg = copy.deepcopy(pkg_tmpl); pkg["ObjectName"] = "/Game/Cars/Models/%s/%s" % (spec["car"], a["mesh"])
            imps.append(pkg)
            m = copy.deepcopy(mesh_tmpl); m["ObjectName"] = a["mesh"]; m["OuterIndex"] = -len(imps)
            imps.append(m)
            row = copy.deepcopy(by_type[a["part_type"]]); row["Name"] = a["row"]
            for p in row["Value"]:
                if p["Name"] == "Name":
                    text_literal(p, a["row"] + "_Name", a["display_name"])
                elif p["Name"] == "VehicleKeys":
                    # aero packs (universal wings / roof scoops) list every car they fit; car specs only themselves
                    keys = a.get("vehicle_keys") or spec.get("vehicle_keys") or [spec["car"]]
                    p["Value"] = [name_item(i, k) for i, k in enumerate(keys)]
                    for k in keys:
                        if k not in t["NameMap"]:
                            t["NameMap"].append(k)
                elif p["Name"] == "VehicleTypes":
                    p["Value"] = []
                elif p["Name"] == "Cost":
                    p["Value"] = int(a.get("cost", 1500))
                elif p["Name"] == "BodyMaterialNames" and p["Value"]:
                    paint = spec.get("paint_slot") or spec.get("final_slot_names", {}).get("Paint", "Paint")
                    entry = p["Value"][0]
                    entry[0]["Value"] = paint            # key: the mesh slot that takes the body paint
                    p["Value"] = [entry]
                    if paint not in t["NameMap"]:
                        t["NameMap"].append(paint)
                elif p["Name"] == "Aero":
                    for q in p["Value"]:
                        if q["Name"] == "Mesh":
                            q["Value"] = -len(imps)
                        elif q["Name"] == "bUseCustomSocket":
                            q["Value"] = bool(a.get("socket"))
                        elif q["Name"] == "CustomSocketName" and a.get("socket"):
                            q["Value"] = a["socket"]          # e.g. RoofScoop on the car's Body
                            if a["socket"] not in t["NameMap"]:
                                t["NameMap"].append(a["socket"])
            rows.append(row)
            for n in (pkg["ObjectName"], a["mesh"], a["row"], spec["car"]):
                if n not in t["NameMap"]:
                    t["NameMap"].append(n)
    t["Exports"][0]["Table"]["Data"] = rows
    t["NameMap"] = ["/Game/DataAsset/VehicleParts/Aero_ProStreet" if n == "/Game/DataAsset/VehicleParts/AeroParts" else n
                    for n in t["NameMap"]]
    t["Exports"][0]["ObjectName"] = "Aero_ProStreet"
    if "Aero_ProStreet" not in t["NameMap"]:
        t["NameMap"].append("Aero_ProStreet")
    out = os.path.join(out_root, "MotorTown/Content/DataAsset/VehicleParts/Aero_ProStreet.uasset")
    fromjson(t, os.path.join(work, "Aero_ProStreet.json"), out)
    return out, rows, t["NameMap"]


# ProStreet-style tuning parts for our cars (Motor Town's own Turbocharger / Intake systems):
# (row, template row in VehicleParts0, display name, cost, {struct: {field: value}})
TUNING_PARTS = [
    ("PS_Turbo_LowBoost", "Turbocharger_Stage1", "ProStreet Turbo - Low Boost", 8000,
     6),  # psi, turned into psi_turbo(psi) below
    ("PS_Turbo_MedBoost", "Turbocharger_Stage1", "ProStreet Turbo - Medium Boost", 16000,
     12),  # psi, turned into psi_turbo(psi) below
    ("PS_Turbo_HighBoost", "Turbocharger_Stage1", "ProStreet Turbo - High Boost", 28000,
     20),  # psi, turned into psi_turbo(psi) below
    ("PS_Cams_Street", "202", "ProStreet Cams - Street (low-end torque)", 3000,
     {"Intake": {"Slope": -0.12, "BaseRPMRatio": 0.6, "IntakeSpeedEfficencyMultiplier": 0.9}}),
    ("PS_Cams_Sport", "201", "ProStreet Cams - Sport (balanced)", 6000,
     {"Intake": {"Slope": 0.05, "BaseRPMRatio": 0.7, "IntakeSpeedEfficencyMultiplier": 1.2}}),
    ("PS_Cams_Race", "201", "ProStreet Cams - Race (top-end power)", 12000,
     {"Intake": {"Slope": 0.15, "BaseRPMRatio": 0.85, "IntakeSpeedEfficencyMultiplier": 1.6}}),
]


def psi_turbo(psi):
    # Boost curve for the adjustable turbo, modelled on More Tuning's turbos (light turbine, low aspect ratio,
    # IntakePressureMultiplier 0.99, a real BaseTorqueMultiplier gain). The first version scaled the turbine up with
    # psi like the game's laggy Stage1 and never spooled, so 7 and 51 psi felt the same (2026-10-22).
    # ProStreet scale: +8% torque per psi at full boost, so a ~320 hp 2JZ makes ~1600 hp at 50 psi (5x, user 2026-10-23);
    # off-boost keeps 60% of the gain; heat and fuel climb with it. Turbine stays light and small at every psi
    # (stock turbo / More Tuning dragster: AR 1, 20-30 kg): with AR up to 4.6 and 56 kg it never got past half spool
    # at 51.5 psi (2026-10-22).
    gain = 0.08 * psi
    return {"Turbocharger": {"BaseTorqueMultiplier": round(1.0 + 0.6 * gain, 4), "TorqueMultiplier": round(1.0 + gain, 4),
                             "TurbineAspectRatio": round(1.0 + 0.01 * psi, 3), "IntakePressureMultiplier": 0.99,
                             "HeatingMultiplier": round(1.0 + 0.012 * psi, 4), "FuelConsumptionMultiplier": round(1.0 + 0.02 * psi, 4),
                             "TurbineWeight": round(20.0 + 0.15 * psi, 2)}}


PSI_STEPS = [x / 2 for x in range(2, 104)]          # 1.0 .. 51.5 psi in 0.5 steps
psi_row = lambda psi: "PS_Boost_%03dpsi" % round(psi * 10)   # 14.5 psi -> PS_Boost_145psi (no trailing digits: FName would split them off) (the F8 menu uses the same names)
# The adjustable turbo is the only one sold in the garage; buying it unlocks the PSI picker in the F8 menu, which swaps
# the part to one of the hidden PSI rows below.
# the fixed Low/Medium/High turbos use the same curve as the adjustable one (6 / 12 / 20 psi)
TUNING_PARTS[:] = [(r, t, l, c, psi_turbo(f) if isinstance(f, int) else f) for r, t, l, c, f in TUNING_PARTS]
TUNING_PARTS.append(("PS_Turbo_Adjustable", "Turbocharger_Stage1", "ProStreet Adjustable Turbo (set PSI in F8 menu)", 30000, psi_turbo(10.0)))
TUNING_PARTS += [(psi_row(p), "Turbocharger_Stage1", "ProStreet Adjustable Turbo - %g psi" % p, 30000, dict(psi_turbo(p), hidden=True))
                 for p in PSI_STEPS]


def make_tuning_table(specs, work, out_root):
    """Tuning_ProStreet: boost (Turbocharger) and cam profile (Intake) rows, copied from the game's own rows in
    VehicleParts0 and limited to our cars (VehicleKeys). More Tuning's own turbos / intakes stay separate."""
    t = tojson(os.path.join(UNPACKED, "DataAsset/VehicleParts/VehicleParts0.uasset"), os.path.join(work, "VehicleParts0_src.json"))
    base = {r["Name"]: r for r in t["Exports"][0]["Table"]["Data"]}
    keys = [sp["car"] for sp in specs if not sp.get("kind")]
    name_item = lambda i, v: {"$type": "UAssetAPI.PropertyTypes.Objects.NamePropertyData, UAssetAPI", "Name": str(i),
                              "ArrayIndex": 0, "PropertyGuid": None, "IsZero": False, "PropertyTagFlags": "None",
                              "PropertyTypeName": None, "PropertyTagExtensions": "NoExtension", "Value": v}
    rows = []
    for row_name, tmpl, label, cost, fields in TUNING_PARTS:
        row = copy.deepcopy(base[tmpl]); row["Name"] = row_name
        for p in row["Value"]:
            if p["Name"] == "Name":
                text_literal(p, row_name + "_Name", label)
            elif p["Name"] == "Cost":
                p["Value"] = int(cost)
            elif p["Name"] == "bIsHidden":
                p["Value"] = bool(fields.get("hidden", False))
            elif p["Name"] == "VehicleKeys":
                p["Value"] = [name_item(i, k) for i, k in enumerate(keys)]
            elif p["Name"] == "VehicleTypes":
                p["Value"] = []
            elif p["Name"] == "LevelRequirementToBuy":
                for q in (p["Value"] if isinstance(p["Value"], list) else []):
                    if isinstance(q, dict) and isinstance(q.get("Value"), int):
                        q["Value"] = 0
            elif p["Name"] in fields:
                for q in p["Value"]:
                    if q["Name"] in fields[p["Name"]]:
                        q["Value"] = float(fields[p["Name"]][q["Name"]])
        rows.append(row)
        for n in [row_name] + keys:
            if n not in t["NameMap"]:
                t["NameMap"].append(n)
    t["Exports"][0]["Table"]["Data"] = rows
    t["NameMap"] = ["/Game/DataAsset/VehicleParts/Tuning_ProStreet" if n == "/Game/DataAsset/VehicleParts/VehicleParts0" else n
                    for n in t["NameMap"]]
    t["Exports"][0]["ObjectName"] = "Tuning_ProStreet"
    if "Tuning_ProStreet" not in t["NameMap"]:
        t["NameMap"].append("Tuning_ProStreet")
    out = os.path.join(out_root, "MotorTown/Content/DataAsset/VehicleParts/Tuning_ProStreet.uasset")
    fromjson(t, os.path.join(work, "Tuning_ProStreet.json"), out)
    return out, rows, t["NameMap"]

if __name__ == "__main__":
    out_root = sys.argv[1]
    specs = [json.load(open(p)) for p in sys.argv[2:]]
    work = os.path.join(out_root, "_work")
    os.makedirs(work, exist_ok=True)
    cars = [s for s in specs if s.get("kind") not in ("rims", "aero_pack")]   # packs only add part rows
    packs = [s for s in specs if s.get("kind") == "aero_pack"]
    for s in cars:
        print("blueprint:", clone_blueprint(s, work, out_root))
    tbl, rows, names = make_table(cars, work, out_root)
    print("table:", tbl)
    print("composite:", patch_composite(work, out_root, rows, names))
    wtbl, wrows, wnames = make_wheel_table(specs, work, out_root)
    print("wheel table:", wtbl, [r["Name"] for r in wrows])
    print("parts composite:", patch_composite(work, out_root, wrows, wnames, folder="VehicleParts", comp_name="VehicleParts",
                                              template="Wheels", new_name="Wheels_ProStreet"))
    if any(sp.get("aero_parts") for sp in cars):
        atbl, arows, anames = make_aero_table(cars + packs, work, out_root)
        print("aero table:", atbl, len(arows), "rows")
        # second parent on the same composite: patch the copy just written (so both tables are parents)
        print("parts composite (+aero):", patch_composite_from(out_root, work, arows, anames, "AeroParts", "Aero_ProStreet"))
        ttbl, trows, tnames = make_tuning_table(cars, work, out_root)
        print("tuning table:", ttbl, len(trows), "rows")
        print("parts composite (+tuning):", patch_composite_from(out_root, work, trows, tnames, "VehicleParts0", "Tuning_ProStreet"))
