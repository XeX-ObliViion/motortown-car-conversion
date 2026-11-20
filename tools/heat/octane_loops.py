"""Fixed-rpm engine loops from a Heat car's Octane accel layers (+ its idle render) for Motor Town's sound cue.
usage: octane_loops.py <sound_dir> <car_prefix> <out_dir> rpm1 rpm2 ...
  l1.wav = the idle render (<prefix>_Idle_EXH/ENG .sps, vgmstream); l2.. = the given rpms.
Octane stores each layer as grains of exactly one engine cycle (4 firings = 2 crank turns on the 13B; grain table in the
asset): a steady-rpm loop is the 3 grains at that rpm repeated (what Octane itself does at constant rpm), so the pitch
never glides. (v1 cut 0.5 s straight out of the rising sweep: the pitch slid inside every repeat and 7 layers 1000 rpm
apart sounded like clicking between files, user 2026-11-13.) Layers EXH 1.0 / ENG 0.6 / INT 0.4, tone (24 kHz,
resampled) + noise (48 kHz); each layer's cycle is stretched to the exhaust tone's so they stay in phase.
~1 s per loop, 48 kHz mono, RMS LOOP_RMS (default 17000) + soft limiter."""
import glob, os, struct, subprocess, sys, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import octane as O

SR = 48000
TARGET = float(os.environ.get("LOOP_RMS", 17000))
src, pre, out = sys.argv[1], sys.argv[2], sys.argv[3]
rpms = [float(r) for r in sys.argv[4:]]
os.makedirs(out, exist_ok=True)


def layer(name):
    f = glob.glob(os.path.join(src, "%s_%s_*.bin" % (pre, name)))[0]
    b = open(f, "rb").read(); mn, mx, pts, ns, sr, o = O.parse(b)
    npts, ngr = struct.unpack_from("<II", b, 0x10)
    grains = np.array(struct.unpack_from("<%dI" % ngr, b, 0x20 + 4 * npts))[1:]     # [0] = end of the last grain
    x = O.decode(b[o:], ns).astype(float)
    rpm_of = lambda s: float(np.interp(s, pts, np.linspace(mn, mx, len(pts))))
    return {"x": x, "sr": sr, "g": grains, "rpm": np.array([rpm_of(s) for s in grains[:-1]])}


def cycle(L, rpm, n=3):
    """n consecutive grains around rpm, resampled to 48 kHz"""
    k = int(np.argmin(np.abs(L["rpm"] - rpm))); k = max(0, min(k - n // 2, len(L["rpm"]) - n))
    seg = L["x"][L["g"][k]:L["g"][k + n]]
    if L["sr"] != SR:
        seg = np.interp(np.arange(int(len(seg) * SR / L["sr"])) * L["sr"] / SR, np.arange(len(seg)), seg)
    return seg, float(L["rpm"][k + n // 2])


def stretch(seg, n):
    return np.interp(np.linspace(0, len(seg) - 1, n), np.arange(len(seg)), seg)


def save(name, loop):
    loop = loop * TARGET / np.sqrt((loop ** 2).mean())
    loop = (30000 * np.tanh(loop / 30000)).astype("<i2")
    w = wave.open(os.path.join(out, name + ".wav"), "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(loop.tobytes()); w.close()


# idle: the car's own idle renders, 2 s with a crossfade (a steady recording, not a sweep)
V = os.path.expanduser("~/tools/vgmstream/vgmstream-cli.exe")
idle = None
for nm, g in (("Idle_EXH", 1.0), ("Idle_ENG", 0.6)):
    sps = glob.glob(os.path.join(src, "wav", "%s_%s_*.sps" % (pre, nm)))[0]
    wv = sps[:-4] + ".wav"
    if not os.path.exists(wv):
        subprocess.run([V, "-o", wv, sps], capture_output=True)
    w = wave.open(wv); x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(float)
    if w.getnchannels() > 1: x = x.reshape(-1, w.getnchannels()).mean(1)
    idle = x * g if idle is None else idle[:min(len(idle), len(x))] + g * x[:min(len(idle), len(x))]
a, n, xf = 2 * SR, 2 * SR, int(0.08 * SR)
seg = idle[a:a + n + xf].copy(); r = np.linspace(0, 1, xf); il = seg[:n].copy(); il[:xf] = seg[:xf] * r + seg[n:n + xf] * (1 - r)
save("l1", il); print("l1 idle render")

L = {nm: (layer(nm + "_Tone"), layer(nm + "_Noise"), g) for nm, g in (("Accel_EXH", 1.0), ("Accel_ENG", 0.6), ("Accel_INT", 0.4))}
for i, rpm in enumerate(rpms, 2):
    base, got = cycle(L["Accel_EXH"][0], rpm)
    N = len(base); mix = np.zeros(N)
    for nm, (tl, nl, g) in L.items():
        t, _ = cycle(tl, rpm); z, _ = cycle(nl, rpm)
        mix += g * (stretch(t, N) + 0.8 * stretch(z, N))
    reps = max(1, int(round(1.0 * SR / N)))
    save("l%d" % i, np.tile(mix, reps))
    print("l%d target %.0f rpm: grains at %.0f rpm, cycle %.1f ms x%d" % (i, rpm, got, N / SR * 1000, reps))
