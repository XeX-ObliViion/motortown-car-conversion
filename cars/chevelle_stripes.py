"""'70 Chevelle SS hood + trunk stripes (a ProStreet stock vinyl) as top-view decal polygons -> chevelle.json "decals".
Two wide stripes either side of a narrow body-colour gap, each outlined by a thin pinstripe, traced from the user's
ProStreet showroom shots. x forward, y right, cm. Rerun after tweaking: python cars/chevelle_stripes.py"""
import json, math, os

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chevelle.json")
Y_IN, Y_OUT = 5.4, 43.0          # stripe edges (|y|)
PIN_GAP, PIN_W = 1.2, 0.6        # pinstripe: gap outside the stripe, line width
# stripe outlines per side as (x, |y|) corners, counter-clockwise in (x, |y|)
HOOD = [(82, Y_IN), (230, Y_IN), (217, Y_OUT), (82, Y_OUT)]          # front end follows the pointed hood nose
TRUNK = [(-236, Y_IN), (-178, Y_IN), (-178, Y_OUT), (-236, Y_OUT)]


def offset_strip(a, b, d1, d2, ext):
    """A band outside edge a->b (outward = right-hand normal for a counter-clockwise polygon) from d1 to d2."""
    ex, ey = b[0] - a[0], b[1] - a[1]
    L = math.hypot(ex, ey); ux, uy = ex / L, ey / L
    nx, ny = uy, -ux                               # outward for CCW
    a2 = (a[0] - ux * ext, a[1] - uy * ext); b2 = (b[0] + ux * ext, b[1] + uy * ext)
    return [(a2[0] + nx * d1, a2[1] + ny * d1), (b2[0] + nx * d1, b2[1] + ny * d1),
            (b2[0] + nx * d2, b2[1] + ny * d2), (a2[0] + nx * d2, a2[1] + ny * d2)]


def ccw(pl):
    area = sum(pl[i][0] * pl[i - 1][1] - pl[i - 1][0] * pl[i][1] for i in range(len(pl)))
    return pl if area < 0 else pl[::-1]          # (x, y) with the cross product sign of the offset maths


def shapes(quad):
    out = [quad]
    q = ccw(quad)
    for i in range(len(q)):
        out.append(offset_strip(q[i - 1], q[i], PIN_GAP, PIN_GAP + PIN_W, PIN_GAP + PIN_W))
    return out


polys = []
for quad in (HOOD, TRUNK):
    for side in (1, -1):
        for pl in shapes(quad):
            polys.append([[round(x, 2), round(side * y, 2)] for x, y in pl])

spec = json.load(open(SPEC))
spec.pop("stripes", None)
spec["decals"] = [{"from": "Paint", "to": "Paint2", "projection": "top", "min_up_nz": 0.2,
                   "meshes": ["Body", "Aero_Bonnet"],
                   "note": "70 SS hood/trunk stripes with pinstripe outlines (ProStreet stock vinyl), Body_02",
                   "polys": polys}]
json.dump(spec, open(SPEC, "w"), indent=1)
print("decals:", len(polys), "polygons")
