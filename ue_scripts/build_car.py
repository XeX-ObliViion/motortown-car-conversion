"""Runs inside the Unreal Editor (5.5) of the MotorTown cooking project:
    UnrealEditor-Cmd.exe MotorTown.uproject -run=pythonscript -script="Scripts/build_car.py" -- <car_build_dir>

<car_build_dir>/car.json describes the car (written by ps_to_mt.py). This script:
  1. makes stand-in parent materials at Motor Town's own material paths (so the cooked meshes reference the game's real
     materials at runtime; the stand-ins are never packed),
  2. imports the car's ProStreet textures and makes material instances of the game's textured master,
  3. imports each OBJ mesh into /Game/Cars/Models/<Car>/ (wheels into /Game/Cars/Parts/Wheels/) and assigns materials
     by slot name, adds simple collision to the body, and saves everything.
A mode 'axis_test' imports a lopsided triangle and prints its bounds, to learn how OBJ axes map into UE."""
import json
import os
import sys

import unreal

AT = unreal.AssetToolsHelpers.get_asset_tools()
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary

# stand-ins for the game's materials: path -> (is_textured_master, texture parameter name)
GAME_MATERIALS = {
    "Paint": "/Game/Cars/Materials/Body/M_Body",
    "Paint2": "/Game/Cars/Materials/Body/M_Body",   # second paint colour (stripes; final name Body_02)
    "Bottom": "/Game/Cars/Materials/Body/M_Body_Bottom",
    "Trim": "/Game/Cars/Materials/Body/M_Gray",
    "Glass": "/Game/Cars/Materials/Windows/M_Glass_Base",
    "LightCase": "/Game/Cars/Materials/Windows/M_Glass_LightCase",
    "HeadLight": "/Game/Cars/Materials/M_HeadLight",
    "TailLight": "/Game/Cars/Materials/M_TailLight",
    "Mirror": "/Game/Cars/Materials/M_Mirror",
    # the game renders its dashboard widgets (upper MFD: turn arrows, warning icons) through this material
    "DashboardUpperMFD": "/Game/Cars/Materials/M_WidgetRender",
}
TEXTURED_MASTER = ("/Game/Cars/Materials/Palette/M_Sketchfab_Base", "Base Texture")


def log(msg):
    unreal.log_warning("[PSCAR] " + msg)


def ensure_material(path, texture_param=None):
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    if texture_param:
        tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -300, 0)
        tex.set_editor_property("parameter_name", texture_param)
        MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("stand-in material " + path)
    return mat


def import_task(src, dest, name, options=None):
    t = unreal.AssetImportTask()
    t.filename = src
    t.destination_path = dest
    t.destination_name = name
    t.automated = True
    t.replace_existing = True
    t.save = True
    if options is not None:
        t.options = options
    AT.import_asset_tasks([t])
    return [unreal.load_asset(p) for p in t.imported_object_paths]


def ensure_paint_tex_material(path):
    """Our own paintable textured material: base colour = texture x vector param "Color" (white = untouched texture),
    so a part row's ColorSlots picker (e.g. Wheel_01 on rims) tints the source car's texture."""
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    tex.set_editor_property("parameter_name", "Base Texture")
    col = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -600, 250)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(1, 1, 1, 1))
    mul = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -300, 100)
    MEL.connect_material_expressions(tex, "RGB", mul, "A")
    MEL.connect_material_expressions(col, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_BASE_COLOR)
    met = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -300, 300)
    met.set_editor_property("parameter_name", "Metallic"); met.set_editor_property("default_value", 0.5)
    MEL.connect_material_property(met, "", unreal.MaterialProperty.MP_METALLIC)
    rough = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -300, 400)
    rough.set_editor_property("parameter_name", "Roughness"); rough.set_editor_property("default_value", 0.4)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("paintable texture material " + path)
    return mat


def ensure_masked_material(path):
    """Our own alpha-tested textured material: ProStreet badge textures (logos, lettering, the Elise's oval indicator
    lens) are cut-outs, so the texture alpha drives the opacity mask instead of showing its dark background."""
    if EAL.does_asset_exist(path):
        return unreal.load_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    tex.set_editor_property("parameter_name", "Base Texture")
    MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    MEL.connect_material_property(tex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    rough = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -300, 300)
    rough.set_editor_property("r", 0.35)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("masked material " + path)
    return mat



def ensure_vinyl_material(path):
    """NFS vinyl livery over the paint (a garage skin): base colour = lerp(Color, vinyl.rgb, vinyl.a). "Color",
    "Metallic", "Roughness" are the parameter names the game's M_Body exposes, so the chosen paint shows under the vinyl."""
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    col = MEL.create_material_expression(mat, unreal.MaterialExpressionVectorParameter, -700, -100)
    col.set_editor_property("parameter_name", "Color")
    col.set_editor_property("default_value", unreal.LinearColor(0.8, 0.8, 0.8, 1.0))
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 150)
    tex.set_editor_property("parameter_name", "Vinyl")
    lerp = MEL.create_material_expression(mat, unreal.MaterialExpressionLinearInterpolate, -300, 0)
    MEL.connect_material_expressions(col, "", lerp, "A")
    MEL.connect_material_expressions(tex, "RGB", lerp, "B")
    MEL.connect_material_expressions(tex, "A", lerp, "Alpha")
    MEL.connect_material_property(lerp, "", unreal.MaterialProperty.MP_BASE_COLOR)
    for i, (pn, dv, prop) in enumerate((("Metallic", 0.4, unreal.MaterialProperty.MP_METALLIC),
                                        ("Roughness", 0.3, unreal.MaterialProperty.MP_ROUGHNESS))):
        sp = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -300, 250 + 120 * i)
        sp.set_editor_property("parameter_name", pn)
        sp.set_editor_property("default_value", dv)
        MEL.connect_material_property(sp, "", prop)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("vinyl material " + path)
    return mat

def ensure_glow_material(path):
    """Our own material, shipped in the car's pak (it lives under Cars/Models/<car>, not Cars/Materials): the texture as
    base colour, plus emissive = texture^3 * Glow, so white/red markings light up while grey bezels and black faces stay
    dark. Used for instrument faces."""
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    tex.set_editor_property("parameter_name", "Base Texture")
    MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    gtex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -600, 250)
    gtex.set_editor_property("parameter_name", "Glow Texture")
    pw = MEL.create_material_expression(mat, unreal.MaterialExpressionPower, -350, 200)
    pw.set_editor_property("const_exponent", 3.0)
    MEL.connect_material_expressions(gtex, "RGB", pw, "Base")
    glow = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -350, 350)
    glow.set_editor_property("parameter_name", "Glow")
    glow.set_editor_property("default_value", 3.0)
    mul = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -150, 250)
    MEL.connect_material_expressions(pw, "", mul, "A")
    MEL.connect_material_expressions(glow, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -150, 450)
    rough.set_editor_property("r", 0.6)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("glow material " + path)
    return mat


LAMP_WEIGHTS = {
    # the game's light materials read scalar parameters named after the light (M_HeadLight: HeadLight,
    # M_TailLight: BrakeLight, M_ReverseLight: ReverseLight, M_TurnSignalLight: SideMarkerLight) and the vehicle sets
    # them when the lights switch on; tail lamps also glow softly with the headlights on
    "head": {"HeadLight": 25.0},
    "tail": {"HeadLight": 3.0, "BrakeLight": 18.0},
    # tail lamps whose texture is the dark "off" lens (Most Wanted): only red texels glow, in pure red, scaled by
    # how red they are (R - max(G, B)), so chrome rims stay dark and dark-red lenses still light up properly
    "tail_red": {"HeadLight": 12.0, "BrakeLight": 60.0},
    "reverse": {"ReverseLight": 15.0},
    # turn signals (slots LeftSignalLight / RightSignalLight): flash with TurnLight, faint side-marker glow
    "signal": {"TurnLight": 30.0, "SideMarkerLight": 1.0},
    # rear lamps that are both tail/brake and turn signal: red (lens texture) on brake + headlights, amber flash
    "signal_tail": {"TurnLight": 30.0, "BrakeLight": 18.0, "HeadLight": 3.0},
    # US-style red rear turn signal sharing the tail lamp (Shelby GT500 '67)
    "signal_tail_red": {"TurnLight": 30.0, "BrakeLight": 18.0, "HeadLight": 3.0},
    # one lamp face holding both (911 tail lamp): red from the texture on brake/headlights, amber flash only where
    # the lens is clear (texture green channel squared as the mask)
    "signal_tail_tex": {"TurnLight": 40.0, "BrakeLight": 18.0, "HeadLight": 3.0},
    # overlay copy of a lamp face (the lamp itself stays TailLight): visible only on the clear lens section
    # (opacity mask = 2 x texture green^2), flashes amber
    "signal_overlay": {"TurnLight": 40.0},
}
# per-parameter emissive tint (None = the lamp's own texture colour); kinds not listed use LAMP_TINT / the texture
LAMP_PARAM_TINT = {"signal_tail": {"TurnLight": (1.0, 0.42, 0.04), "BrakeLight": (1.0, 0.04, 0.02), "HeadLight": (1.0, 0.04, 0.02)},
                   "signal_tail_red": {"TurnLight": (1.0, 0.05, 0.02), "BrakeLight": (1.0, 0.04, 0.02), "HeadLight": (1.0, 0.04, 0.02)}}
LAMP_TINT = {"signal": (1.0, 0.42, 0.04)}   # emissive tint: indicators glow amber whatever the lens texture


def ensure_lamp_material(path, kind, masked=False):
    """Our own lamp material (shipped in the car's pak): base colour = the source car's lamp texture, emissive =
    texture x sum(weight x light parameter), so the textured lamp looks real when off and glows when switched on."""
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    folder, name = path.rsplit("/", 1)
    mat = AT.create_asset(name, folder, unreal.Material, unreal.MaterialFactoryNew())
    tex = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSampleParameter2D, -700, 0)
    tex.set_editor_property("parameter_name", "Base Texture")
    MEL.connect_material_property(tex, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    if masked:
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        MEL.connect_material_property(tex, "A", unreal.MaterialProperty.MP_OPACITY_MASK)
    total = None
    y = 200
    if kind == "signal_overlay":
        mat.set_editor_property("blend_mode", unreal.BlendMode.BLEND_MASKED)
        g2 = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -500, 450)
        MEL.connect_material_expressions(tex, "G", g2, "A"); MEL.connect_material_expressions(tex, "G", g2, "B")
        two = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, 550); two.set_editor_property("r", 2.0)
        mask = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -350, 450)
        MEL.connect_material_expressions(g2, "", mask, "A"); MEL.connect_material_expressions(two, "", mask, "B")
        MEL.connect_material_property(mask, "", unreal.MaterialProperty.MP_OPACITY_MASK)
        sp = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, 200)
        sp.set_editor_property("parameter_name", "TurnLight"); sp.set_editor_property("default_value", 0.0)
        amber = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -700, 300)
        w = LAMP_WEIGHTS[kind]["TurnLight"]
        amber.set_editor_property("constant", unreal.LinearColor(1.0 * w, 0.42 * w, 0.04 * w, 1.0))
        em = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -350, 200)
        MEL.connect_material_expressions(sp, "", em, "A"); MEL.connect_material_expressions(amber, "", em, "B")
        MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(mat)
        EAL.save_loaded_asset(mat)
        log("lamp material %s (%s)" % (path, kind))
        return mat
    if kind == "tail_red":
        w = LAMP_WEIGHTS[kind]
        def sp_(param, y_):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -900, y_)
            e.set_editor_property("parameter_name", param); e.set_editor_property("default_value", 0.0)
            return e
        def k_(v, y_):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -900, y_ + 60); e.set_editor_property("r", v)
            return e
        def op_(cls, a, b, y_, ao="", bo=""):
            e = MEL.create_material_expression(mat, cls, -600, y_)
            MEL.connect_material_expressions(a, ao, e, "A"); MEL.connect_material_expressions(b, bo, e, "B")
            return e
        gb = op_(unreal.MaterialExpressionMax, tex, tex, 200, "G", "B")
        red = op_(unreal.MaterialExpressionSubtract, tex, gb, 250, "R", "")
        sat = MEL.create_material_expression(mat, unreal.MaterialExpressionSaturate, -450, 250)
        MEL.connect_material_expressions(red, "", sat, "")
        lights = op_(unreal.MaterialExpressionAdd, op_(unreal.MaterialExpressionMultiply, sp_("HeadLight", 400), k_(w["HeadLight"], 400), 400),
                     op_(unreal.MaterialExpressionMultiply, sp_("BrakeLight", 550), k_(w["BrakeLight"], 550), 550), 480)
        col = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -900, 700)
        col.set_editor_property("constant", unreal.LinearColor(1.0, 0.03, 0.015, 1.0))
        em = op_(unreal.MaterialExpressionMultiply, op_(unreal.MaterialExpressionMultiply, sat, lights, 600), col, 650)
        MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(mat)
        EAL.save_loaded_asset(mat)
        log("lamp material %s (%s)" % (path, kind))
        return mat
    if kind == "signal_tail_tex":
        def sp_(param, y_):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -900, y_)
            e.set_editor_property("parameter_name", param); e.set_editor_property("default_value", 0.0)
            return e
        def k_(v, y_):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -900, y_ + 60); e.set_editor_property("r", v)
            return e
        def mul_(a, b, y_, ao="", bo=""):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -600, y_)
            MEL.connect_material_expressions(a, ao, e, "A"); MEL.connect_material_expressions(b, bo, e, "B")
            return e
        def add_(a, b, y_):
            e = MEL.create_material_expression(mat, unreal.MaterialExpressionAdd, -450, y_)
            MEL.connect_material_expressions(a, "", e, "A"); MEL.connect_material_expressions(b, "", e, "B")
            return e
        w = LAMP_WEIGHTS[kind]
        red = add_(mul_(sp_("BrakeLight", 200), k_(w["BrakeLight"], 200), 200), mul_(sp_("HeadLight", 350), k_(w["HeadLight"], 350), 350), 280)
        red_em = mul_(tex, red, 300, "RGB", "")
        mask = mul_(tex, tex, 500, "G", "G")
        amber = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -900, 650)
        amber.set_editor_property("constant", unreal.LinearColor(1.0 * w["TurnLight"], 0.42 * w["TurnLight"], 0.04 * w["TurnLight"], 1.0))
        turn = mul_(mul_(sp_("TurnLight", 800), amber, 700), mask, 600)
        MEL.connect_material_property(add_(red_em, turn, 450), "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        MEL.recompile_material(mat)
        EAL.save_loaded_asset(mat)
        log("lamp material %s (%s)" % (path, kind))
        return mat
    ptint = LAMP_PARAM_TINT.get(kind, {})
    for param, weight in LAMP_WEIGHTS[kind].items():
        sp = MEL.create_material_expression(mat, unreal.MaterialExpressionScalarParameter, -700, y)
        sp.set_editor_property("parameter_name", param)
        sp.set_editor_property("default_value", 0.0)
        if param in ptint:
            k = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -700, y + 80)
            k.set_editor_property("constant", unreal.LinearColor(*[weight * c for c in ptint[param]], 1.0))
        else:
            k = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -700, y + 80)
            k.set_editor_property("r", weight)
        mul = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -500, y)
        MEL.connect_material_expressions(sp, "", mul, "A")
        MEL.connect_material_expressions(k, "", mul, "B")
        if total is None:
            total = mul
        else:
            add = MEL.create_material_expression(mat, unreal.MaterialExpressionAdd, -350, y)
            MEL.connect_material_expressions(total, "", add, "A")
            MEL.connect_material_expressions(mul, "", add, "B")
            total = add
        y += 200
    em = MEL.create_material_expression(mat, unreal.MaterialExpressionMultiply, -200, 150)
    if ptint:                                   # colours already in the per-parameter terms
        one = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -500, -150)
        one.set_editor_property("r", 1.0)
        MEL.connect_material_expressions(one, "", em, "A")
    elif kind in LAMP_TINT:
        tint = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant3Vector, -500, -150)
        tint.set_editor_property("constant", unreal.LinearColor(*LAMP_TINT[kind], 1.0))
        MEL.connect_material_expressions(tint, "", em, "A")
    else:
        MEL.connect_material_expressions(tex, "RGB", em, "A")
    MEL.connect_material_expressions(total, "", em, "B")
    MEL.connect_material_property(em, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(mat)
    EAL.save_loaded_asset(mat)
    log("lamp material %s (%s)" % (path, kind))
    return mat


def setup_uvs(smesh, decal):
    """Motor Town car meshes: UV0 = texture UVs, UV1 = decal (livery) UVs read by M_Body, UV2 = lightmap.
    Needs the full editor (StaticMeshEditorSubsystem is None in a commandlet)."""
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    if sub is None:
        log("WARNING no StaticMeshEditorSubsystem (commandlet?): UV channels not set up")
        return
    while sub.get_num_uv_channels(smesh, 0) < 2:
        sub.add_uv_channel(smesh, 0)
    if decal:
        # side-on projection, so a livery wraps along the car like on the game's own bodies
        sub.generate_planar_uv_channel(smesh, 0, 1, unreal.Vector(0, 0, 60), unreal.Rotator(roll=90, pitch=0, yaw=0), unreal.Vector2D(1, 1))
    bs = sub.get_lod_build_settings(smesh, 0)
    bs.set_editor_property("generate_lightmap_u_vs", True)
    bs.set_editor_property("src_lightmap_index", 0)
    bs.set_editor_property("dst_lightmap_index", 2)
    sub.set_lod_build_settings(smesh, 0, bs)
    smesh.set_editor_property("light_map_coordinate_index", 2)
    log("UVs %s: %d channels, decal=%s" % (smesh.get_name(), sub.get_num_uv_channels(smesh, 0), decal))


def axis_test(build_dir):
    obj = os.path.join(build_dir, "axis_test.obj")
    with open(obj, "w") as f:
        f.write("v 100 0 0\nv 0 50 0\nv 0 0 25\nvn 0 0 1\nvt 0 0\nf 1/1/1 2/1/1 3/1/1\n")
    assets = import_task(obj, "/Game/AxisTest", "AxisTest")
    for a in assets:
        if isinstance(a, unreal.StaticMesh):
            b = a.get_bounding_box()
            log("AXIS_TEST min=%s max=%s" % (b.min, b.max))
            with open(os.path.join(build_dir, "axis_test_result.json"), "w") as f:
                json.dump({"min": [b.min.x, b.min.y, b.min.z], "max": [b.max.x, b.max.y, b.max.z]}, f)


def build(build_dir):
    car = json.load(open(os.path.join(build_dir, "car.json")))
    name = car["car"]
    model_dir = "/Game/Cars/Models/" + name
    tex_dir = model_dir + "/Textures"
    for path in GAME_MATERIALS.values():
        ensure_material(path)
    master = ensure_material(TEXTURED_MASTER[0], TEXTURED_MASTER[1])
    paint_tex = ensure_paint_tex_material(model_dir + "/M_PaintTex") if car.get("paintable_texture_slots") else None
    masked = ensure_masked_material(model_dir + "/M_TexMasked") if car.get("masked_texture_slots") else None
    # NFS vinyl liveries -> skin material instances (make_mt_assets adds them to the blueprint's BodyMaterialList)
    if car.get("skins"):
        vmat = ensure_vinyl_material(model_dir + "/M_VinylBody")
        for sk in car["skins"]:
            tname = "T_SKIN_" + sk["name"]
            assets = import_task(sk["png"], tex_dir, tname)
            vt = next((a for a in assets if isinstance(a, unreal.Texture2D)), None)
            mi_name = "MI_SKIN_" + sk["name"]
            mi_path = model_dir + "/" + mi_name
            mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else                 AT.create_asset(mi_name, model_dir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(mi, vmat)
            if vt is not None:
                MEL.set_material_instance_texture_parameter_value(mi, "Vinyl", vt)
            EAL.save_loaded_asset(mi)
            log("skin " + mi_path)
    # textures + material instances
    slot_materials = {k: unreal.load_asset(v) for k, v in GAME_MATERIALS.items()}
    slot_textures = {}
    for slot, png in car.get("textures", {}).items():
        tex_name = "T_" + slot.replace("Tex_", "")
        assets = import_task(png, tex_dir, tex_name)
        tex = next((a for a in assets if isinstance(a, unreal.Texture2D)), None)
        if tex is not None:
            # full resolution in game: no streaming down to low mips, sharpened mips for the cockpit close-ups
            tex.set_editor_property("never_stream", True)
            tex.set_editor_property("lod_bias", 0)
            tex.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_SHARPEN2)
            EAL.save_loaded_asset(tex)
        mi_name = "MI_" + slot.replace("Tex_", "")
        mi_path = model_dir + "/" + mi_name
        mi = unreal.load_asset(mi_path) if EAL.does_asset_exist(mi_path) else \
            AT.create_asset(mi_name, model_dir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, paint_tex if slot in car.get("paintable_texture_slots", []) else
                                         masked if slot in car.get("masked_texture_slots", []) else master)
        if tex is not None:
            MEL.set_material_instance_texture_parameter_value(mi, TEXTURED_MASTER[1], tex)
        # a parent swap alone doesn't dirty the package: force the save or an existing MI keeps its old parent
        EAL.save_asset(mi_path, only_if_is_dirty=False)
        slot_materials[slot] = mi
        slot_textures[slot] = tex
        log("material instance %s (%s)" % (mi_path, tex_name))
    lamp_mats = {}
    for slot, kind in car.get("lamp_slots", {}).items():
        tex_slot = slot
        if isinstance(kind, dict):          # {"kind": "signal", "texture_slot": <slot whose texture it shows>}
            tex_slot, kind = kind.get("texture_slot", slot), kind["kind"]
        lm = tex_slot in car.get("masked_texture_slots", [])
        if (kind, lm) not in lamp_mats:
            lamp_mats[(kind, lm)] = ensure_lamp_material(model_dir + "/M_Lamp_" + kind.capitalize() + ("_Masked" if lm else ""), kind, lm)
        mi_path = model_dir + "/MI_Lamp_" + slot
        if EAL.does_asset_exist(mi_path):
            EAL.delete_asset(mi_path)
        mi = AT.create_asset("MI_Lamp_" + slot, model_dir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
        MEL.set_material_instance_parent(mi, lamp_mats[(kind, lm)])
        if slot_textures.get(tex_slot) is not None:
            MEL.set_material_instance_texture_parameter_value(mi, "Base Texture", slot_textures[tex_slot])
        EAL.save_loaded_asset(mi)
        slot_materials[slot] = mi
        log("lamp instance %s (%s)" % (mi_path, kind))
    if car.get("emissive_slots"):
        glow_mat = ensure_glow_material(model_dir + "/M_Glow")
        for slot, e in car["emissive_slots"].items():
            mi_path = model_dir + "/MI_Glow_" + slot
            if EAL.does_asset_exist(mi_path):
                EAL.delete_asset(mi_path)
            mi = AT.create_asset("MI_Glow_" + slot, model_dir, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
            MEL.set_material_instance_parent(mi, glow_mat)
            if slot_textures.get(e["texture_slot"]) is not None:
                MEL.set_material_instance_texture_parameter_value(mi, "Base Texture", slot_textures[e["texture_slot"]])
                glow_tex = slot_textures.get(e["texture_slot"] + "_GLOW") or slot_textures[e["texture_slot"]]
                MEL.set_material_instance_texture_parameter_value(mi, "Glow Texture", glow_tex)
            MEL.set_material_instance_scalar_parameter_value(mi, "Glow", float(e.get("glow", 3.0)))
            EAL.save_loaded_asset(mi)
            slot_materials[slot] = mi
            log("glow instance %s (texture %s, glow %s)" % (mi_path, e["texture_slot"], e.get("glow")))
    # meshes
    for mesh in car["meshes"]:
        dest = mesh.get("dest", model_dir)
        opts = unreal.FbxImportUI()
        opts.import_mesh = True
        opts.import_materials = False
        opts.import_textures = False
        opts.import_as_skeletal = False
        sm = opts.static_mesh_import_data
        sm.combine_meshes = True
        sm.auto_generate_collision = False
        sm.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS
        sm.generate_lightmap_u_vs = True
        old_path = dest + "/" + mesh["name"]
        if EAL.does_asset_exist(old_path):   # reimporting over a mesh keeps its old slot names, so start fresh
            EAL.delete_asset(old_path)
        assets = import_task(mesh["obj"], dest, mesh["name"], opts)
        smesh = next((a for a in assets if isinstance(a, unreal.StaticMesh)), None)
        if smesh is None:
            log("FAILED to import " + mesh["obj"])
            continue
        for i, m in enumerate(smesh.static_materials):
            slot = str(m.material_slot_name)
            if slot.endswith("Mat") and slot[:-3] in slot_materials:   # the OBJ importer appends "Mat" to usemtl names
                slot = slot[:-3]
            mat = slot_materials.get(slot)
            if mat is None:
                log("WARNING slot %s on %s has no material, using Trim" % (slot, mesh["name"]))
                mat = slot_materials.get("Trim")
            smesh.set_material(i, mat)
        log("slots %s: %s" % (mesh["name"], [str(m.material_slot_name) for m in smesh.static_materials]))
        setup_uvs(smesh, any("Paint" in str(m.material_slot_name) for m in smesh.static_materials))
        # the game finds slots by name (the garage paints "Body_01", side mirrors use "Mirror"): strip the importer's
        # "Mat" suffix and apply renames. StaticMaterial structs must be rebuilt; editing them in place does not stick.
        renames = car.get("final_slot_names", {})
        mats = smesh.get_editor_property("static_materials")
        new_mats = []
        for sm_ in mats:
            base = str(sm_.get_editor_property("material_slot_name"))
            base = base[:-3] if base.endswith("Mat") else base
            new_mats.append(unreal.StaticMaterial(material_interface=sm_.get_editor_property("material_interface"),
                                                  material_slot_name=renames.get(base, base)))
        smesh.set_editor_property("static_materials", new_mats)
        log("final slots %s: %s" % (mesh["name"], [str(m.get_editor_property("material_slot_name")) for m in new_mats]))
        if mesh.get("collision_boxes"):
            # the EditorStaticMeshLibrary collision helpers do nothing in a commandlet, so write the boxes directly
            agg = smesh.get_editor_property("body_setup").get_editor_property("agg_geom")
            boxes = ",".join("(Center=(X=%g,Y=%g,Z=%g),X=%g,Y=%g,Z=%g)" % (tuple(b["center"]) + tuple(b["size"])) for b in mesh["collision_boxes"])
            agg.import_text("(BoxElems=(%s))" % boxes)
            smesh.get_editor_property("body_setup").set_editor_property("agg_geom", agg)
            log("collision boxes on %s: %s" % (mesh["name"], boxes))
        elif mesh.get("collision") == "convex":
            unreal.EditorStaticMeshLibrary.set_convex_decomposition_collisions(smesh, 8, 16, 100000)
        elif mesh.get("collision") == "box":
            unreal.EditorStaticMeshLibrary.add_simple_collisions(smesh, unreal.ScriptingCollisionShapeType.BOX)
        for sock in mesh.get("sockets", []):
            existing = smesh.find_socket(sock["name"])
            s_obj = existing or unreal.StaticMeshSocket(outer=smesh)
            s_obj.set_editor_property("socket_name", sock["name"])
            s_obj.set_editor_property("relative_location", unreal.Vector(*sock["loc"]))
            s_obj.set_editor_property("relative_rotation", unreal.Rotator(pitch=sock["rot"][0], yaw=sock["rot"][1], roll=sock["rot"][2]))
            if existing is None:
                smesh.add_socket(s_obj)
        EAL.save_loaded_asset(smesh)
        b = smesh.get_bounding_box()
        log("MESH %s/%s slots=%d bounds min=%s max=%s" % (dest, mesh["name"], len(smesh.static_materials), b.min, b.max))
    log("BUILD_DONE " + name)


args = [a for a in sys.argv[1:] if not a.startswith("-")]
build_dir = os.environ.get("PSCAR_BUILD_DIR") or (args[-1] if args else "")
if "axis_test" in sys.argv:
    axis_test(build_dir)
else:
    build(build_dir)
if os.environ.get("PSCAR_QUIT"):
    unreal.SystemLibrary.quit_editor()
