"""Map texture points (u, image row) onto a converted mesh: prints the car-space position and face normal of every
triangle of <slot> that contains the point (row = 1 - v_json). Usage: uv_to_3d.py <mesh.json> <slot> u,row [u,row ...]"""
import json, sys


def main():
    d = json.load(open(sys.argv[1])); slot = sys.argv[2]
    pts = [tuple(float(x) for x in a.split(",")) for a in sys.argv[3:]]
    s = next(x for x in d["slots"] if x["slot"] == slot)
    P, U = s["positions"], s["uvs"]
    for (u, row) in pts:
        v = 1 - row
        for i in range(0, len(P), 3):
            (u0, v0), (u1, v1), (u2, v2) = U[i], U[i + 1], U[i + 2]
            den = (v1 - v2) * (u0 - u2) + (u2 - u1) * (v0 - v2)
            if abs(den) < 1e-12:
                continue
            a = ((v1 - v2) * (u - u2) + (u2 - u1) * (v - v2)) / den
            b = ((v2 - v0) * (u - u2) + (u0 - u2) * (v - v2)) / den
            c = 1 - a - b
            if min(a, b, c) < -1e-4:
                continue
            p = [a * P[i][k] + b * P[i + 1][k] + c * P[i + 2][k] for k in range(3)]
            e1 = [P[i + 1][k] - P[i][k] for k in range(3)]; e2 = [P[i + 2][k] - P[i][k] for k in range(3)]
            n = [e1[1] * e2[2] - e1[2] * e2[1], e1[2] * e2[0] - e1[0] * e2[2], e1[0] * e2[1] - e1[1] * e2[0]]
            l = sum(x * x for x in n) ** 0.5 or 1
            print("uv (%.3f,%.3f) -> %s normal %s" % (u, row, [round(x, 2) for x in p], [round(x / l, 3) for x in n]))


if __name__ == "__main__":
    main()
