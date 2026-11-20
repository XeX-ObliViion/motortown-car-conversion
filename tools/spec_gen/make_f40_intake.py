"""F40 engine bay: join the curved intake duct (from the rear grille, on top of the airbox) to the throttle-body tube.
The SRP model leaves a ~8 cm gap between the duct outlet and the tube inlet (user 2026-11-19, circled screenshot).
Writes geo/AC_F40_INTAKEJOIN_A.dae:
  * a black pipe (material EXT_Plastic -> baked black) lofted along a Hermite curve from inside the duct outlet into
    the tube inlet, radius blending duct -> tube;
  * a white cap inside the tube inlet (material F40_WHITE): the throttle body is "blocked off" (user).
Rims measured from the open edges of CHASSIS groups 25/30 (duct) and 35 (tube) in the dae frame (x fwd, y left)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = sys.argv[:1]
from kn5_to_obj import write_dae

G = os.path.expanduser("~/nfs-work/ac/f40/geo/AC_F40_")
# duct outlet, traced from the duct's top band (built mesh, 2026-11-19 round 2: the first guess sat 7 cm behind it):
# centre line (-160, 15.7) -> (-152, 10.5), width ~12 cm, top z ~81 -> end (-151.5, 10.5, 76), heading (0.84, -0.55, 0)
C1, D1, R1 = np.array([-151.5, 10.5, 75.5]), np.array([0.84, -0.55, 0.0]), 5.4   # duct ~12 cm wide, top z 81
# tube inlet: open rim at x -149.6 (bbox y +-4.6, z 71.4..80.6), the tube runs forward (+x)
C2, D2, R2 = np.array([-149.6, 0.0, 76.0]), np.array([1.0, 0.0, 0.0]), 4.6
D1, D2 = D1 / np.linalg.norm(D1), D2 / np.linalg.norm(D2)
# cubic Bezier elbow: out of the duct, round behind the inlet, straight into the tube; ends overlap 2 cm into each
A, B = C1 - D1 * 6.0, C2 + D2 * 2.0          # 6 cm inside the duct so the joint blends (user: "blend into the duct")
Q1, Q2 = C1 + D1 * 4.0, C2 - D2 * 7.0
L = np.linalg.norm(B - A)


def frame(t):
    p = (1 - t)**3 * A + 3 * (1 - t)**2 * t * Q1 + 3 * (1 - t) * t**2 * Q2 + t**3 * B
    d = 3 * (1 - t)**2 * (Q1 - A) + 6 * (1 - t) * t * (Q2 - Q1) + 3 * t**2 * (B - Q2)
    return p, d / np.linalg.norm(d)


NS, NR = 24, 24
rings, up = [], np.array([0, 0, 1.0])
for i in range(NS + 1):
    t = i / NS
    p, d = frame(t)
    u = np.cross(d, up); u /= np.linalg.norm(u); v = np.cross(u, d)
    w_ = min(1.0, max(0.0, (t - 0.3) / 0.7)); r = R1 + (R2 - R1) * w_ * w_ * (3 - 2 * w_)   # duct size until clear of it, then ease to the tube
    rings.append([(p + r * (np.cos(a) * u + np.sin(a) * v), np.cos(a) * u + np.sin(a) * v)
                  for a in np.linspace(0, 2 * np.pi, NR, endpoint=False)])
P, N, idx = [], [], []
for ring in rings:
    for q, n in ring:
        P.append(q); N.append(n)
for i in range(NS):
    for k in range(NR):
        a, b = i * NR + k, i * NR + (k + 1) % NR
        c, d = a + NR, b + NR
        idx += [[a, b, d], [a, d, c],        # outside
                [a, d, b], [a, c, d]]        # inside (seen down the pipe)
pipe = {"P": np.array(P) / 100.0, "N": np.array(N), "uv": np.full((len(P), 2), 0.5), "idx": np.array(idx), "mat": 0}

# white cap 3 cm inside the tube, facing back down the pipe
cc = C2 + D2 * 3.0
u = np.cross(D2, up); u /= np.linalg.norm(u); v = np.cross(u, D2)
rim = [cc + (R2 - 0.2) * (np.cos(a) * u + np.sin(a) * v) for a in np.linspace(0, 2 * np.pi, NR, endpoint=False)]
cp = np.array([cc] + rim)
ci = [[0, 1 + (k + 1) % NR, 1 + k] for k in range(NR)] + [[0, 1 + k, 1 + (k + 1) % NR] for k in range(NR)]
cap = {"P": cp / 100.0, "N": np.tile(-D2, (len(cp), 1)), "uv": np.full((len(cp), 2), 0.5), "idx": np.array(ci), "mat": 1}

write_dae(G + "INTAKEJOIN_A.dae", [pipe, cap], [{"name": "EXT_Plastic", "tex": {}}, {"name": "F40_WHITE", "tex": {}}])
print("intake join: %d + %d tris, length %.1f cm" % (len(idx), len(ci), L))
