"""Seamless fixed-rpm loops from AC FMOD engine recordings: mono, 3 s from a steady stretch, 0.15 s end->start crossfade, RMS-matched."""
import os, sys, wave, numpy as np
src, out = sys.argv[1], sys.argv[2]
# usage: ac_cut_loops.py <wav dir> <out dir> name:file:start_s ...   (Supra: l1:IDLE_EXT:2 l2:TEST_LOW:4 l3:PULL02:1 l4:TEST_O26:4 l5:EXNEARVELOW:4 l6:HIGHEXNEAR:1)
specs = [(a, b, float(c)) for a, b, c in (x.split(":") for x in sys.argv[3:])]
L, XF, TARGET = float(os.environ.get("LOOP_S", 3.0)), 0.15, float(os.environ.get("LOOP_RMS", 15000.0))   # other ports sit at RMS 14-18k (6k was ~8 dB quiet, user 2026-11-07)
for name, f, t0 in specs:
    w = wave.open("%s/%s.wav" % (src, f)); sr = w.getframerate(); ch = w.getnchannels()
    x = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').astype(float)
    if ch > 1: x = x.reshape(-1, ch).mean(1)
    a, n, xf = int(t0 * sr), int(L * sr), int(XF * sr)
    seg = x[a:a + n + xf].copy()
    assert len(seg) == n + xf, (f, len(seg))
    r = np.linspace(0, 1, xf)
    loop = seg[:n].copy()
    loop[:xf] = seg[:xf] * r + seg[n:n + xf] * (1 - r)   # the tail fades into the head: the wrap point is continuous
    loop *= TARGET / np.sqrt((loop ** 2).mean())
    loop = (30000 * np.tanh(loop / 30000)).astype("<i2")   # soft limiter: peaks round off instead of clipping
    o = wave.open("%s/%s.wav" % (out, name), "w"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(sr); o.writeframes(loop.tobytes()); o.close()
    print(name, f, sr, "peak %.0f" % np.abs(loop).max())
