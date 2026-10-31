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

## What's new (2026-10-31)
- **Most Wanted twins** (`tools/mw_twin.py`, `tools/mw_materials.py`): build a car on its own MW body (so MW body kits fit natively), copying drivetrain, stance, blueprint and gauges from an existing ProStreet port, and mapping MW materials to Motor Town slots by texture. Examples: `cars/mw_supra.json`, `mw_viper.json`, `mw_elise.json`, `mw_350z.json`.
- **One-piece bodies on door bases:** `drop_coincident_with` takes `keep_only` (cut doors out of a one-piece body along a reference car's door panels).
- **Add-on / modder cars:** generic material names are keyed by texture hash automatically; driver figures are dropped via a texture slot (`cars/mw_diablosv.json`).
- **Police vehicles** (`cars/mw_copsuv.json`): `base_vehicle` can be a variant blueprint (`base_dir`, `base_parts`), e.g. the game's Muhan_Police, which brings the police tags, licence, siren, light bar and NPC police AI. Light-bar lenses go to slots `EmergencyRed` / `EmergencyBlue`.
- **Lamps:** reverse lamps (signal rule tag `_V`), masked overlay kinds `reverse_overlay` / `signal_overlay` for lenses that mix red with white/amber; keep red brake sections in `TailLight` (signal-named slots don't get the brake glow).
- **Gauges:** `gauge_faces` entries take `flip_x` for dash art that is UV-mirrored on the car.
- **Wheels / meshes:** `smooth_normals` (per-mesh), `radius_slot` to give a rim lip its own material; `slot_boxes` take `drop: true`.
- **Dealerships:** second copied showroom (`dealers/nfs_dealership/showroom_mw.txt`); `skip <class regex>` removes source actors (e.g. the turntable); `bay <CAR> x y z yaw` adds a fixed world-space bay; mappatch now remaps (multicast) delegates when transplanting/cloning actors (copied lights work).
- **Base car defaults:** strip every default part the base row fits that would sit on your body (`strip_part_slots`, e.g. SideSkirt/Fender/Bonnet); see the skill for the full checklist.
