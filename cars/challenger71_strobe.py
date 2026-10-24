"""'71 Challenger R/T strobe stripe (a ProStreet stock vinyl) as side-view decal polygons -> challenger71.json "decals".
Two lines (thin upper, thick lower) following the beltline from behind the headlight to the rear quarter, where they
kick up toward an italic R/T. x forward, z up, cm. Rerun after tweaking: python cars/challenger71_strobe.py"""
import json, os

SPEC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "challenger71.json")
# side-surface beltline (top of the side-facing paint), measured from the KIT00 body / fender
BELT = [(-95, 70.5), (-60, 70.5), (40, 70.2), (70, 69.5), (100, 68), (120, 67), (140, 65.7), (170, 64), (190, 62),
        (212, 59)]
FRONT_X, KICK_X, KICK_SLOPE, KICK_R, SMOOTH = 208, -76, 0.45, 20, 12
LINES = [  # (offset of the line centre below the beltline, vertical thickness, rear end x)
    (3.9, 1.4, -99),     # thin: 3.2-4.6 below the beltline (below the shoulder, where the side is near vertical)
    (8.0, 3.4, -103),    # gap 1.7, thick 3.4 (ProStreet proportions ~1 : 1.2 : 2.5)
]
LETTERS_X, LETTERS_Z, SCALE, SHEAR, DROP = -101, 73.5, 1.45, 0.22, 0.42


def belt_lin(x):
    if x <= BELT[0][0]:
        return BELT[0][1]
    for (x0, z0), (x1, z1) in zip(BELT, BELT[1:]):
        if x <= x1:
            return z0 + (x - x0) / (x1 - x0) * (z1 - z0)
    return BELT[-1][1]


def belt(x):
    # moving average over +-SMOOTH cm so the lines don't kink at the measured points
    n = 12
    return sum(belt_lin(x + SMOOTH * (2 * i / n - 1)) for i in range(n + 1)) / (n + 1)


def kick(x):
    # rise behind KICK_X: eases in over KICK_R cm (parabola), then straight at KICK_SLOPE
    d = KICK_X - x
    if d <= 0:
        return 0
    return KICK_SLOPE * d * d / (2 * KICK_R) if d < KICK_R else KICK_SLOPE * (d - KICK_R / 2)


def line_poly(off, th, end_x):
    xs = sorted({FRONT_X, end_x} | set(range(int(end_x) + 1, FRONT_X, 2)), reverse=True)
    cz = lambda x: belt(x) - off + kick(x)
    return [[x, round(cz(x) + th / 2, 2)] for x in xs] + [[x, round(cz(x) - th / 2, 2)] for x in reversed(xs)]


# glyphs in a local frame: s along the reading direction, t up, 8 cm tall before SCALE; polygons may overlap
R = [[(0, 0), (1.4, 0), (1.4, 6.5), (0, 6.5)], [(0, 5.2), (4.2, 5.2), (4.2, 6.5), (0, 6.5)],
     [(0, 2.9), (4.2, 2.9), (4.2, 4.2), (0, 4.2)], [(3.1, 3.3), (4.5, 3.3), (4.5, 6.1), (3.1, 6.1)],
     [(3.1, 0), (4.6, 0), (3.5, 3.0), (2.0, 3.0)]]
SLASH = [[(5.3, 0), (6.5, 0), (8.3, 6.5), (7.1, 6.5)]]
T = [[(8.6, 5.2), (13.2, 5.2), (13.2, 6.5), (8.6, 6.5)], [(10.2, 0), (11.6, 0), (11.6, 5.3), (10.2, 5.3)]]
WIDTH = 13.2 * SCALE + SHEAR * 6.5 * SCALE


def letters(side):
    out = []
    for g in R + SLASH + T:
        pl = []
        for s, t in g:
            s, t = s * SCALE, t * SCALE
            s += SHEAR * t                       # italic: tops lean toward the reading direction
            z = LETTERS_Z + t - DROP * s         # the word steps down toward the back, as on the car
            # reading left to right: toward the back on the left side (-x), toward the front on the right (+x)
            x = LETTERS_X - s if side == "left" else LETTERS_X - WIDTH + s
            pl.append([round(x, 2), round(z, 2)])
        out.append(pl)
    return out


lines = [line_poly(*l) for l in LINES]
spec = json.load(open(SPEC))
spec.pop("stripes", None)
spec["decals"] = [{"from": "Paint", "to": "Paint2", "min_side_ny": 0.35,
                   "note": "71 R/T strobe stripe (ProStreet stock vinyl), traced from the ProStreet showroom; Body_02",
                   "left": lines + letters("left"), "right": lines + letters("right")}]
json.dump(spec, open(SPEC, "w"), indent=1)
print("decals:", len(spec["decals"][0]["left"]), "polygons per side")
