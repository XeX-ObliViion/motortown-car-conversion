"""F40 engine loops from the car's own bank (slang_ferrari_f40.bank -> ~/nfs-work/ac/f40/sfx). Every F40_ex_* recording
is stored at the idle pitch (77 Hz = 1155 rpm flat-plane firing, measured), so each band is a speed-up of its recording
to the band rpm. Resampling is band-limited (scipy resample_poly), else the 3-6x speed-up folds the top end back as
harsh aliasing (user 2026-11-19: "very distorted at about 3000 rpm"). verylow_low fills the old 2200 -> 3600 gap.
Writes ~/mt-work/sounds/AC_F40/l1..l7.wav (1.5 s, mono 44.1 kHz, loop seam crossfaded) and prints the spec loops list.
Run with the Store python (has scipy)."""
import os, wave, json
from fractions import Fraction
import numpy as np
from scipy.signal import resample_poly

SRC = os.path.expanduser("~/nfs-work/ac/f40/sfx/")
OUT = os.path.expanduser("~/mt-work/sounds/AC_F40/")
REC_RPM = 1155.0
# the exterior on-load recordings above verylow are hard-clipped in the mod (20-29% of samples flat at peak, measured):
# they sounded distorted from ~3300 rpm (user 2026-11-19, twice). The interior on-load set is clean (~2%): use it there.
# (band, file, band rpm, rpm the file is pitched at). The bank is pitch-normalised, but not all to the same rpm: idle and
# ex_on_verylow peak at 77 Hz (firing = rpm/15 -> 1155), the on-load sets peak at 154 Hz (-> 2310). Treating them all as
# 1155 played the upper bands an octave high ("sped up, high pitched above 4000", user 2026-11-19).
BANDS = [("l1", "F40_ex_idle.wav", 1155, 1155), ("l2", "F40_ex_on_verylow.wav", 2200, 1155),
         ("l3", "F40_in_on_verylow_d_new.wav", 2900, 2310), ("l4", "F40_in_on_verylow_d_new.wav", 3600, 2310),
         ("l5", "F40_in_on_mid_d_3_new.wav", 5000, 2310), ("l6", "F40_in_on_mid_d_3_new.wav", 6400, 2310),
         ("l7", "F40_in_on_mid_d_3_new.wav", 7600, 2310)]
SEC, XF = 1.5, 0.08


def load(f):
    w = wave.open(SRC + f)
    a = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float64).reshape(-1, w.getnchannels())
    return a.mean(1) / 32768.0, w.getframerate()


os.makedirs(OUT, exist_ok=True)
loops = []
for name, f, rpm, REC_RPM in BANDS:
    a, sr = load(f)
    r = Fraction(rpm / REC_RPM).limit_denominator(200)      # speed-up = play rpm/rec faster -> keep 1/r of the samples
    sec = min(SEC, (len(a) - 2000) / sr * REC_RPM / rpm - XF)   # short recordings (on_high 8.5 s) give a shorter loop
    need = int((sec + XF) * sr * rpm / REC_RPM) + 1000
    assert sec > 0.8 and len(a) > need, (f, len(a) / sr, need / sr)
    seg = a[len(a) // 2 - need // 2: len(a) // 2 + need // 2]  # middle of the recording (steady state)
    y = resample_poly(seg, r.denominator, r.numerator)        # band-limited
    n, x = int(sec * sr), int(XF * sr)
    y = y[:n + x]
    t = np.linspace(0, 1, x)
    out = y[:n].copy()
    out[:x] = y[n:n + x] * (1 - t) + y[:x] * t                # seamless loop: tail fades into the head
    out *= 0.30 / max(1e-9, np.sqrt((out ** 2).mean()))     # equal loudness across bands (interior set is quieter)
    if np.abs(out).max() > 0.95:
        out *= 0.95 / np.abs(out).max()
    w = wave.open(OUT + name + ".wav", "wb"); w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(out, -1, 1) * 32767).astype(np.int16).tobytes()); w.close()
    # check: firing frequency of the result = rpm / 15
    z = out - out.mean(); S = np.fft.rfft(z * np.hanning(len(z)), 2 * len(z)); ac = np.fft.irfft(np.abs(S) ** 2)[:len(z)]
    exp = rpm / 15.0; lags = np.arange(int(sr / (exp * 1.15)), int(sr / (exp * 0.87)))
    got = sr / lags[np.argmax(ac[lags])]
    print("%s %-26s %5d rpm  ratio %s  f0 %.0f Hz (expect %.0f)" % (name, f, rpm, r, got, exp))
    loops.append([name, rpm])
print(json.dumps(loops))
