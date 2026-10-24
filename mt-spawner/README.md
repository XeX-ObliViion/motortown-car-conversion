# Motor Town Vehicle Spawner

An in-game menu that spawns any vehicle in front of you: game vehicles, More Tuning and Maja's cars, and all the ProStreet/Most Wanted ports. Press **F8** to open or close it. To change the key, edit `mt_spawner.ini` next to the game exe.

Only the **host** (single player, or whoever hosts the session) or a **server admin** can spawn. For anyone else the menu stays locked.

## How it works
- **`version.dll`** (game's Win64 folder) is an ImGui overlay on the game's DX12 swap chain. It draws the menu and sends commands.
- **`ue4ss/Mods/MTSpawner`** (Lua) runs each command on the game thread through the game's own `MotorTownPlayerController:ServerSpawnVehicle`. Spawned vehicles are therefore real vehicles: they replicate to other players and save like any other.
  - Rights come from the PlayerState's `bIsHost` / `bIsAdmin` and controller authority.
- They talk through `%LOCALAPPDATA%\MTSpawner\cmd.txt`, `state.txt` and `vehicles.txt`. `vehicles.txt` holds the live rows of the game's Vehicles table, rewritten whenever the table grows, which happens after you allow mods.

## Menu
- Search box, category filter ("Your ported cars", Cars, Pickup, Truck, Bus, …).
- Double-click a vehicle, or select it and press Spawn. It appears side-on, 4–30 m ahead along your camera.
- **Remove nearest** despawns the closest vehicle within 15 m. It can be someone else's, so be careful.
- **Use developer spawn** falls back to the developers' `Cheat_AddVehicle` if the normal spawn doesn't produce a vehicle. The status line says so when that happens.
- Recent spawns appear as quick buttons.

## Files
- `src/` holds the overlay. It reuses the RV trainer's DX12 hook, IPC and proxy. The proxy works because Motor Town's modules load VERSION.dll from the Win64 folder.
- `src/vehicles.h` holds names and categories, from `tools/gen_vehicles.py` (game Vehicles_* tables plus the car specs).
- Build: `bash build.sh` (llvm-mingw, ImGui and MinHook from ../sr3r-trainer).
- Logs: `Win64/mt_spawner.log` (overlay) and `[MTSpawner]` lines in `ue4ss/UE4SS.log`.

## Status
- Verified at the main menu on 2026-10-19: the overlay draws, F8 toggles it, and the Lua mod reads 171 vehicle rows.
- Not yet tested in a world: spawning and removing.
