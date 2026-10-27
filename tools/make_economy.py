"""NFS_Economy_P.pak: job payouts for everyone on the server (and single player).

Only data the game reads from its paks, so the server computes the new pay itself (no UE4SS needed):
  - DataAsset/Cargos: every delivery pays BASE x (PaymentPer1Km / BasePayment / ManualLoadingPayment), the "hard" ones
    (heavy, oversize, fragile, timed, hazardous) HARD x;
  (taxi / bus / tow pay live in GameResource, which loads before mods mount: not moddable, see main()).
The game's mh.* payout multipliers (taxi/limo/company profit share...) can NOT be changed: the shipping build ignores
them from UserEngine.ini / Engine.ini and from console commands (tested on the local server, 2026-10-27), which is
also why the old "5x Income" mod no longer does anything. Company vehicles still earn more, from the higher pay.
The server checks the clients' cargo data against its own (game data hash): client and server paks must be built from
the same settings, and everybody needs the pak (it is in the friends' modpack).

    py -3.13 make_economy.py client   -> ~/mt-work/build/NFS_Economy_P.pak (+ installs into the game)
    py -3.13 make_economy.py server   -> ~/mt-work/build/server/NFS_Economy_P.pak (from the server's own files)
"""
import os
import shutil
import subprocess
import sys

TARGET = sys.argv[1] if len(sys.argv) > 1 else "client"
if TARGET == "server":
    os.environ["MT_UNPACKED"] = os.path.expanduser("~/mt-work/unpacked_server/MotorTown/Content")
import make_mt_assets as m   # noqa: E402  (reads MT_UNPACKED at import)

BASE = 2.0      # every job
HARD = 20.0     # hard deliveries
BALANCE = {"TaxiPaymentPer100Meter": 1000.0}   # x1000 like Easy Money (user choice 2026-10-27)   # field -> multiplier
HARD_CARGO = [   # heavy, oversize, fragile, timed or hazardous: these pay HARD x
    "Log_30ft_30t", "Log_Oak_24ft", "Container_30ft_20t", "Container_40ft_01", "SteelCoil_10t", "lHBeam_6m",
    "CopperRodCoil_2t", "Transformer_5MVA", "Transformer_20MVA", "Transformer_50MVA", "Tank_250kL",
    "CircuitBoardPallet", "LiveFish_01", "AirlineMealPallet", "MilitarySupplyBox_01", "Fuel", "Oil", "CrudeOil",
]
PAY_FIELDS = ("PaymentPer1Km", "BasePayment", "ManualLoadingPayment")

PAK_SRC = {"client": "/d/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks/MotorTown-Windows.pak",
           "server": os.path.expanduser("~/mt-server/local/MotorTown/Content/Paks/MotorTown-WindowsServer.pak")}
REPAK = os.path.expanduser("~/tools/repak/bin/repak.exe")
WORK = os.path.expanduser(f"~/mt-work/economy_{TARGET}")
OUT = os.path.expanduser("~/mt-work/build/server/NFS_Economy_P.pak" if TARGET == "server" else "~/mt-work/build/NFS_Economy_P.pak")
GAME_PAKS = "D:/SteamLibrary/steamapps/common/Motor Town/MotorTown/Content/Paks"


def sh(p):
    return subprocess.check_output(["cygpath", "-w", p]).decode().strip() if p.startswith("/") else p


def main():
    shutil.rmtree(WORK, ignore_errors=True)
    stage = os.path.join(WORK, "stage")
    os.makedirs(os.path.join(stage, "MotorTown/Content/DataAsset"))
    key = open(os.path.expanduser("~/mt-work/aes.key")).read().strip()
    src = os.path.join(WORK, "src")
    os.makedirs(src)
    for name in ("Cargos", "GameResource"):
        for ext in ("uasset", "uexp"):
            data = subprocess.check_output([REPAK, "--aes-key", key, "get", sh(PAK_SRC[TARGET]), f"MotorTown/Content/DataAsset/{name}.{ext}"])
            open(os.path.join(src, f"{name}.{ext}"), "wb").write(data)

    # cargo table: every delivery BASE x, the hard ones HARD x
    t = m.tojson(os.path.join(src, "Cargos.uasset"), os.path.join(WORK, "Cargos.json"))
    rows = {r["Name"]: r for r in t["Exports"][0]["Table"]["Data"]}
    missing = [c for c in HARD_CARGO if c not in rows]
    if missing:
        print("not in this game version:", missing)
    for name, row in rows.items():
        mult = HARD if name in HARD_CARGO else BASE
        for p in row.get("Value", []):
            if p["Name"] in PAY_FIELDS and isinstance(p.get("Value"), (int, float)):
                v = p["Value"] * mult
                p["Value"] = int(round(v)) if isinstance(p["Value"], int) else float(v)
    m.fromjson(t, os.path.join(WORK, "Cargos_out.json"), os.path.join(stage, "MotorTown/Content/DataAsset/Cargos.uasset"))

    # balance table (DataAsset/GameResource): taxi pay per 100 m, like the old Easy Money mod (x1000 there). Reading
    # the value from memory showed the vanilla 25, but a real taxi ride paid the new rate (2026-10-27): it works.
    t = m.tojson(os.path.join(src, "GameResource.uasset"), os.path.join(WORK, "GameResource.json"))
    hits = []
    def scale(o):
        if isinstance(o, dict):
            if o.get("Name") in BALANCE and isinstance(o.get("Value"), (int, float)):
                o["Value"] = type(o["Value"])(o["Value"] * BALANCE[o["Name"]]); hits.append(o["Name"])
            for x in o.values(): scale(x)
        elif isinstance(o, list):
            for x in o: scale(x)
    scale(t)
    print("balance fields scaled:", hits)
    m.fromjson(t, os.path.join(WORK, "GameResource_out.json"), os.path.join(stage, "MotorTown/Content/DataAsset/GameResource.uasset"))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    subprocess.check_call([REPAK, "pack", "--version", "V11", sh(stage), sh(OUT)])
    print("packed", OUT)
    if TARGET == "client":
        shutil.copy(OUT, GAME_PAKS)
        print("installed to", GAME_PAKS)


if __name__ == "__main__":
    main()
