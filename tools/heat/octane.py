"""NFS Heat 'Octane' engine-sound assets (HeatExport sound -> <name>_<chunk>.bin, header 'Octn21') -> WAV + rpm map.
Layout (worked out 2026-11-13 on the RX-7 Spirit R): 0x00 'Octn21\\0\\0', 0x08 f32 min_rpm, 0x0C f32 max_rpm,
0x10 u32 n_points, 0x14 u32 n_grains, 0x18 u32 n_samples, 0x1C u32 sample_rate, then u32[n_points] sample positions of
evenly spaced rpm points (min..max), u32[n_grains] grain boundaries, a 16-byte audio header, then mono EA-XAS v0 audio:
76-byte blocks = 4 subframes of 19 bytes (u32 header: hist2|coef, hist1|shift; 15 bytes = 30 nibbles) = 128 samples.
usage: octane.py <file.bin> <out.wav> [--variant N]   (prints the rpm map: position (s) -> rpm)"""
import struct, sys, wave
import numpy as np

COEF = [(0, 0), (240, 0), (460, -208), (392, -220)]


def parse(b):
    assert b[:6] == b"Octn21", "not an Octane asset"
    mn, mx = struct.unpack_from("<ff", b, 8)
    npts, ngr, ns, sr = struct.unpack_from("<IIII", b, 0x10)
    pts = struct.unpack_from("<%dI" % npts, b, 0x20)
    o = 0x20 + 4 * npts + 4 * ngr + 8          # 16-byte audio header; first block 8 bytes in (frame period found at +8)
    return mn, mx, pts, ns, sr, o


def decode(data, ns, variant=0):
    """variant bit0: low nibble first; bit1: shift without +8 offset"""
    out = np.zeros(((len(data) // 76) * 128,), np.int32)
    k = 0
    for f in range(len(data) // 76):
        fr = data[f * 76:(f + 1) * 76]
        for s in range(4):
            sub = fr[s * 19:(s + 1) * 19]
            h, = struct.unpack_from("<I", sub, 0)
            c1, c2 = COEF[h & 3]
            shift = ((h >> 16) & 0x0F) + (0 if variant & 2 else 8)
            s16 = lambda v: v - 0x10000 if v & 0x8000 else v
            hist2 = s16(h & 0xFFF0); hist1 = s16((h >> 16) & 0xFFF0)
            out[k] = hist2; out[k + 1] = hist1; k += 2
            for byte in sub[4:]:
                for nib in ((byte & 0x0F, byte >> 4) if variant & 1 else (byte >> 4, byte & 0x0F)):
                    smp = ((nib << 28) - ((nib & 8) << 29)) >> shift          # sign-extended nibble, scaled
                    smp = (smp + c1 * hist1 + c2 * hist2 + 128) >> 8
                    smp = max(-32768, min(32767, smp))
                    out[k] = smp; k += 1
                    hist2, hist1 = hist1, smp
    return out[:ns].astype(np.int16)


if __name__ == "__main__":
    b = open(sys.argv[1], "rb").read()
    var = int(sys.argv[sys.argv.index("--variant") + 1]) if "--variant" in sys.argv else 0
    mn, mx, pts, ns, sr, o = parse(b)
    pcm = decode(b[o:], ns, var)
    w = wave.open(sys.argv[2], "w"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes()); w.close()
    x = pcm.astype(float)
    print("rpm %.0f..%.0f, %d samples @ %d Hz, rough %.3f" % (mn, mx, ns, sr, np.abs(np.diff(x)).mean() / (np.abs(x).mean() + 1e-9)))
    for i, p in enumerate(pts):
        print("  %.3f s  %.0f rpm" % (p / sr, mn + (mx - mn) * i / (len(pts) - 1)))
