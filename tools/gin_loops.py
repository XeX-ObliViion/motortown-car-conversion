"""Engine-sound loops from a ProStreet granular engine recording (SOUND/ENGINE/car_NNN-*.tmx -> 'Gnsu20' blocks,
decoded to WAV with vgmstream). Each grain is one engine cycle (2 revs), so its length gives its rpm
(rpm = 120 * rate / samples). A loop at a target rpm = the grains closest to it played forwards then backwards,
repeated to the wanted length; grains end on cycle boundaries, so joins only need a short crossfade.
Usage: gin_loops.py <file.gin> <file.wav> <out_prefix> rpm[:name] [rpm:name ...]"""
import struct, sys, wave


def grains(gin):
    b = open(gin, "rb").read()
    assert b[:4] == b"Gnsu"
    mn, mx = struct.unpack_from("<2f", b, 8)
    nb, n, total, rate = struct.unpack_from("<4I", b, 16)
    starts = list(struct.unpack_from("<%dI" % (n + nb), b, 32)) + [total]
    gs = [(starts[i], starts[i + 1]) for i in range(len(starts) - 1) if starts[i + 1] > starts[i]]
    return mn, mx, rate, gs


def main():
    gin, wav, prefix = sys.argv[1:4]
    mn, mx, rate, gs = grains(gin)
    w = wave.open(wav); pcm = struct.unpack("<%dh" % w.getnframes(), w.readframes(w.getnframes()))
    rpm_of = lambda g: 120.0 * rate / (g[1] - g[0])
    print("rpm range %.0f-%.0f, %d grains, grain rpm %.0f..%.0f" % (mn, mx, len(gs), rpm_of(gs[0]), rpm_of(gs[-1])))
    for spec in sys.argv[4:]:
        target, name = (spec.split(":") + ["%s" % spec])[:2]
        target = float(target)
        best = min(range(len(gs)), key=lambda i: abs(rpm_of(gs[i]) - target))
        sel = [i for i in range(max(0, best - 6), min(len(gs), best + 7)) if abs(rpm_of(gs[i]) / target - 1) < 0.05] or [best]
        seq = sel + sel[-2:0:-1]                      # forwards then backwards: the loop ends where it starts
        out = []
        xf = 24
        while len(out) < rate * 2.0:
            for i in seq:
                a, b_ = gs[i]
                chunk = list(pcm[a:b_])
                if out and len(chunk) > xf:
                    for k in range(xf):                  # short crossfade at each grain join
                        t = (k + 1) / (xf + 1)
                        out[-xf + k] = int(out[-xf + k] * (1 - t) + chunk[k] * t)
                    chunk = chunk[xf:]
                out += chunk
        peak = max(1, max(abs(x) for x in out)); g = min(1.0, 30000 / peak)
        out = [max(-32768, min(32767, int(x * g))) for x in out]
        o = wave.open("%s_%s.wav" % (prefix, name), "w"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(rate)
        o.writeframes(struct.pack("<%dh" % len(out), *out)); o.close()
        print("%s: target %.0f rpm, grains %s (rpm %.0f..%.0f), %.2f s" % (name, target, sel, min(rpm_of(gs[i]) for i in sel),
                                                                     max(rpm_of(gs[i]) for i in sel), len(out) / rate))


if __name__ == "__main__":
    main()
