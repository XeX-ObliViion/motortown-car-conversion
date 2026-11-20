"""Red tail-lamp lenses (user 2026-11-18: many cars' tail lamps looked like a bare reflector without its red lens).
Most Wanted / ProStreet tail lamp textures are the reflector only; the games tinted the lens red in their shaders. For
every tail / brake lamp slot (kinds tail, tail_red, signal_tail, signal_tail_red) whose texture is not already red,
write <texture>_REDLENS.png = the texture seen through a red lens and add it to car.json "textures"; build_car's lamp
instances use it (the overlay / reverse / amber-mask kinds keep the original texture, so clear sections still work).

    from redlens import apply; apply(car, build_dir)         (ps_to_mt, when writing car.json)
    python tools/redlens.py <build dir> [...]                 (update existing builds in place; then build_car)"""
import json
import os
import sys

TAIL_KINDS = ("tail", "tail_red", "signal_tail", "signal_tail_red")


def red_share(im):
    """fraction of the lit texels (max channel > 50) that already read as red."""
    import numpy as np
    a = np.asarray(im.convert("RGB"), dtype=np.float32)
    lit = a.max(-1) > 50
    if not lit.any():
        return 1.0
    r, g, b = a[..., 0][lit], a[..., 1][lit], a[..., 2][lit]
    return float(((r > 1.35 * g) & (r > 1.35 * b)).mean())


def lens(im):
    """reflector texture -> through a red lens: brightness drives red, red texels stay as they are."""
    import numpy as np
    from PIL import Image
    a = np.asarray(im.convert("RGBA"), dtype=np.float32)
    rgb, al = a[..., :3], a[..., 3:]
    lum = rgb @ np.array([0.30, 0.59, 0.11], dtype=np.float32)
    out = np.stack([np.clip(35 + lum * 0.95, 0, 255), lum * 0.10, lum * 0.08], -1)
    red = (rgb[..., 0] > 1.35 * rgb[..., 1]) & (rgb[..., 0] > 1.35 * rgb[..., 2])
    out[red] = rgb[red]
    return Image.fromarray(np.concatenate([out, al], -1).astype("uint8"), "RGBA")


def apply(car, build_dir):
    from PIL import Image
    done = []
    for slot, kind in car.get("lamp_slots", {}).items():
        tex_slot, k = (kind.get("texture_slot", slot), kind["kind"]) if isinstance(kind, dict) else (slot, kind)
        if k not in TAIL_KINDS or tex_slot in done:
            continue
        png = car.get("textures", {}).get(tex_slot)
        if not png or not os.path.exists(png):
            continue
        im = Image.open(png)
        share = red_share(im)
        if share >= 0.3:
            continue
        out = png[:-4] + "_REDLENS.png"
        lens(im).save(out)
        car["textures"][tex_slot + "_REDLENS"] = out.replace("\\", "/")
        done.append(tex_slot)
        print("red lens: %s (red share %.2f) -> %s" % (tex_slot, share, os.path.basename(out)))
    return done


def _selftest():
    from PIL import Image
    w = Image.new("RGBA", (4, 4), (200, 200, 200, 255))
    assert red_share(w) == 0.0 and red_share(Image.new("RGB", (4, 4), (200, 20, 20))) == 1.0
    r = lens(w).getpixel((0, 0))
    assert r[0] > 150 and r[1] < 40 and r[3] == 255


if __name__ == "__main__":
    _selftest()
    for b in sys.argv[1:]:
        p = os.path.join(os.path.expanduser(b), "car.json")
        car = json.load(open(p))
        if apply(car, os.path.dirname(p)):
            json.dump(car, open(p, "w"), indent=1)
