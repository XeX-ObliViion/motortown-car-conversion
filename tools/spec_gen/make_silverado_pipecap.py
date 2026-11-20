"""black end caps inside the Silverado's fender-exit side pipes (LINE001/002): the AC model leaves the fender skin
showing inside the pipe, so it looked unconnected (user 2026-11-19). Writes geo/AC_SILVERADO_PIPECAP_A.dae (material
'muffler' -> Bottom); the cap sits on the pipe axis 0.6 cm outside the fender skin, perpendicular to the pipe."""
import sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.argv = sys.argv[:1]
from ps_to_mt import load_dae
from kn5_to_obj import write_dae
G = os.path.expanduser("~/nfs-work/ac/silverado/geo/AC_SILVERADO_")
body = np.array([c[0] for _, tr in load_dae(G + "022-0-22-44_A.dae") for t in tr for c in t]) * 100
parts = []
for pipe, sgn in (("LINE002", 1), ("LINE001", -1)):
    P = np.array([c[0] for _, tr in load_dae(G + pipe + "_A.dae") for t in tr for c in t]) * 100
    # axis from slice centres (bbox mid of each 3 cm band in |y|)
    cs = []
    for y0 in np.arange(80, 112, 3):
        s = P[(sgn * P[:, 1] >= y0) & (sgn * P[:, 1] < y0 + 3)]
        if len(s) > 50:
            cs.append([(s[:, 0].min() + s[:, 0].max()) / 2, y0 + 1.5, (s[:, 2].min() + s[:, 2].max()) / 2,
                       min(np.ptp(s[:, 0]), np.ptp(s[:, 2])) / 2])
    cs = np.array(cs)
    A = np.polyfit(cs[:, 1], cs[:, 0], 1), np.polyfit(cs[:, 1], cs[:, 2], 1)
    r = np.median(cs[:, 3])
    cx, cz = np.polyval(A[0], 95), np.polyval(A[1], 95)
    near = body[(abs(body[:, 0] - cx) < r) & (abs(body[:, 2] - cz) < r) & (sgn * body[:, 1] > 80)]
    yc = sgn * near[:, 1].max() + 0.6                      # just outside the fender skin
    c = np.array([np.polyval(A[0], yc), sgn * yc, np.polyval(A[1], yc)])
    ax = np.array([A[0][0], 1.0, A[1][0]]); ax[1] = 1.0; ax = ax / np.linalg.norm(ax) * sgn
    u = np.cross(ax, [0, 0, 1]); u /= np.linalg.norm(u); v = np.cross(ax, u)
    rr = r - 0.4                                           # inside the pipe wall
    n = 32
    # a solid 1 cm plug (outer disc, inner disc, side band, separate vertices): a flat two-sided disc was removed by
    # the body's LOD reduction (user 2026-11-19: "fender is still visible")
    c2 = c - ax * 1.0
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    rim = lambda cc: [cc + rr * (np.cos(a_) * u + np.sin(a_) * v) for a_ in ang]
    Pv, Nv, idx = [], [], []
    def add(pts, nrm):
        Pv.extend(pts); Nv.extend([nrm] * len(pts))
    base = 0; add([c] + rim(c), ax)                           # outer disc faces out (+ax)
    idx += [[0, 1 + k, 1 + (k + 1) % n] for k in range(n)]      # (u, v, ax) right-handed: CCW about +ax
    base = len(Pv); add([c2] + rim(c2), -ax)                  # inner disc faces in
    idx += [[base, base + 1 + (k + 1) % n, base + 1 + k] for k in range(n)]
    o, i_ = rim(c), rim(c2)
    for k in range(n):                                        # side band
        b0 = len(Pv); k2 = (k + 1) % n
        rad = (np.cos(ang[k]) * u + np.sin(ang[k]) * v)
        add([o[k], o[k2], i_[k2], i_[k]], rad)
        idx += [[b0, b0 + 2, b0 + 1], [b0, b0 + 3, b0 + 2]]
    Pv = np.array(Pv) / 100.0; N = np.array(Nv)
    parts.append({"P": Pv, "N": N, "uv": np.full((len(Pv), 2), 0.5), "idx": np.array(idx), "mat": 0})
    print(pipe, "cap centre", np.round(c, 1), "r", round(rr, 2), "axis", np.round(ax, 3))
write_dae(G + "PIPECAP_A.dae", parts, [{"name": "muffler", "tex": {}}])
print("wrote", G + "PIPECAP_A.dae")
