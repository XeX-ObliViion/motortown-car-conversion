# Motor Town car porting kit

Tools and Claude Code skill used to port Need for Speed ProStreet / Most Wanted cars into
**Motor Town: Behind The Wheel** (UE 5.5.4) as pak mods, plus the in-game F8 menu (spawner, tuning, admin tools)
and the NFS dealership map patch.

This repository holds **code only**: no game files, no converted cars, no textures, no encryption keys.
Cars converted from EA games are for personal use; don't publish them.

## Layout

| Folder | What |
|---|---|
| `skill/motortown-custom-cars/` | The Claude Code skill (copy to `%USERPROFILE%\.claude\skills\`). It is the full how-to and the list of every fix found so far. |
| `tools/` | Python/shell pipeline: `ps_to_mt.py` (mesh conversion), `make_mt_assets.py` (blueprints, vehicle and part tables), `add_mw_parts.py`, `pack_car.py` / `pack_common.py`, renderers, rims, wings, liveries, `ue_build.sh`. |
| `ue_scripts/` | Unreal Editor Python scripts run by `ue_build.sh` (`build_car.py`, `fix_rim_parents.py`, `import_sounds.py`). |
| `cars/` | One spec per car (`350z.json` is the template) and per-car helper scripts. |
| `mappatch/` | C# tool (UAssetAPI) that patches the world map: dealer spots, copying a dealership showroom, map icon labels. |
| `dealers/` | Dealer spot list and `rebuild_dealers.sh` (client / `PLATFORM=server`), NFS dealership spec + generator. |
| `modpack/` | Builds the friends' modpack zip and its README. |
| `mt-spawner/` | F8 menu: DX12 ImGui overlay (`src/`, proxy `version.dll`), UE4SS Lua mod (`lua/MTSpawner`), server mod (`server/MTAdminServer`). |

## What you need to set up yourself

- Motor Town (the scripts assume the same game version the paks are built for; servers often run the beta branch).
- The game's AES key in `~/mt-work/aes.key` (not included; find it yourself).
- Unreal Engine 5.5 with a project at `C:/UE/Projects/MotorTown` (cooking, `ue_scripts/` are run in it).
- [repak](https://github.com/trumank/repak), [UAssetGUI](https://github.com/atenfyr/UAssetGUI),
  [UAssetAPI](https://github.com/atenfyr/UAssetAPI) (built by `mappatch.csproj`), .NET 8 SDK.
- For the source cars: NFS ProStreet / Most Wanted and the NFS model tools (e.g. NFS-ModTools) to export them.
- [UE4SS](https://github.com/UE4SS-RE/RE-UE4SS) for the F8 menu's Lua side and in-game probes; the menu's `build.sh`
  expects ImGui + MinHook and the llvm-mingw toolchain next to it (see `mt-spawner/README.md`).
- Python 3.13 with numpy / Pillow (see the imports at the top of each script).

Paths in the scripts and the skill are the original author's (`C:\Users\noust\...`, `D:\SteamLibrary\...`);
change them to yours, or let Claude Code adapt them while it follows the skill.
