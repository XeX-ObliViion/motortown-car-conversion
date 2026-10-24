---
name: motortown-custom-cars
description: "Add custom/converted cars to Motor Town: Behind The Wheel (UE 5.5.4) as standalone pak mods, from mesh conversion through blueprint, vehicle tables, wheel parts, a permanent dealer spot, and in-game fixes. Use whenever the user wants a new car in Motor Town, to continue the ProStreet → Motor Town project, or to debug a modded Motor Town car (flicker, wrong look, missing wheels, interior)."
---

# Custom cars in Motor Town

The project journal is `~/OneDrive/Documents/claude/ps2motortown/MODLOG.md`. Read its tail first; it records the latest state and open issues. Converted car models from other games are for the user's own install only. Never publish or upload them (not to Melty, Nexus or anywhere else).

## Standing rules (from the user)
- **Every car gets the full 350Z treatment:** its own parts, working mirrors, a working interior and real-car performance. Don't stop at "it shows up". Use `ps2motortown/cars/350z.json` as the template spec and follow the per-car checklist below.
- **Keep this skill updated:** after any new step, fix or lesson, update this file in the same turn (and the MODLOG). The user asked for this to continue indefinitely.

## Per-car checklist (do ALL of these for every car)
1. **Spec:** copy `cars/350z.json` → `cars/<car>.json`. Set car/prefix/geometry/texture dirs, `display_name`, `cost`, `base_vehicle` (a Zino-like RWD car unless the real car is FWD/AWD; pick a base with the right drivetrain).
2. **Source data:** list the car's parts and texture hashes (texture names → hashes in the dumped `textures` folder). Map `texture_slots`: paint → Paint, black → Bottom, chrome → Trim (never Mirror), the car's own lamp textures → Tex_*, unknown → `default_slot` Bottom.
3. **Shape and surfaces:**
   - Body parts list (the KIT00 stock kit).
   - Doors including the front window glass.
   - Lamps with their own textures; drop dark lens layers.
   - `collision_boxes` sized to the body, starting about 14 cm above the ground.
   - Wheels with tyres (`slot_rename` tyre → Bottom); swap L/R if the rim face points inboard.
   - Verify a wireframe or shaded render matches the real car before building.
4. **Blueprint fit:**
   - **Wheel fitment (IMPORTANT, the user flagged it: the stock wheels were off too):** set `wheels.auto_arches: true`. ps_to_mt's `measure_arches` then measures each arch opening in the body and writes front_x/rear_x; check its printed "wheel arches: measured …" line on every build.
     - z = axle height − 8 for spring compression; `rear_z` = z + 2 for the Zino's longer rear springs.
     - After the first in-game look, compare front and rear wheels in a side screenshot and adjust rear_z / rear_half_track if they still differ.
   - Seats and `cockpit_camera` at the steering wheel's Y and the right height (no head through the roof).
   - `components` for RoomMirror, dome lights, headlight and blinker points inside the new body.
   - `strip_part_slots` (base car's body kit), `keep_body_materials: 1`.
   - `final_slot_names {Paint: Body_01, Glass: Window}`.
5. **Interior:**
   - `extract.SteeringWheel` (find the ring in a cockpit render; `align_x`).
   - `drop_boxes` for any static source parts the game supplies (rear-view mirror).
   - `dashboard.sockets` mapped from the dial art in the interior texture.
   - `texture_upscale` + `gauge_faces` for readable dials.
   - `uv_split` + `emissive_slots` for the backlight.
6. **Mirrors:**
   - SideMirror meshes = rear-facing glass only (`normal_filter` max −0.75, slot Mirror, `planar_uv {}`); housing → doors (Paint).
   - `mirror_sockets` aimed from the cockpit camera.
   - RoomMirror `component_rotations` aimed through the rear glass.
7. **Performance from the real car's specs** (look them up):
   - Custom engine: torque N·m, peak-power rpm, limiter, a torque curve that reproduces the rated hp, and an engine `sound` (V6Sport_02 for V6s).
   - Custom gearbox with the real ratios; the nearest FinalDriveRatio row.
   - Tyres/brakes/radiator matching the class AND allowed for the car's vehicle type (each part row has `VehicleTypes`; the Zino-based cars are "Small", so no BrakePad_Medium_*/MediumRadiator_*, which are truck-only and trigger the garage "Incompatible Parts" warning). Small-car choices: BrakePad_Small_02, SmallRadiator_110, PerformanceTire_46. `body_mass` = curb weight − parts mass.
   - Use the car's real drivetrain (base blueprint choice).
8. **Wheel part** (`wheel_part`; rim row) and add the car's key to `cars/ps_rims.json` vehicle_keys so the ProStreet rim pack is offered on it.
8b. **Body kits:** run `tools/add_body_kits.py cars/<car>.json` after the spec is final (it moves the stock bumpers, hood, skirts, fenders and wing out of Body into garage parts with the car's ProStreet alternatives). ALWAYS CHECK (the user asked for this):
    - **Wings:** the Body socket `RearWing` must sit on the trunk-lid top, with ProStreet wing meshes offset by −socket. Check BOTH our wings and the game's universal wings (Type-A…D) in game.
    - **Widebody:** must include the WIDEBODY shell via `drop_coincident_with` (rear half → W01 rear bumper, front half → W01 fenders). Render Body + Aero_RearBumper_KITW01 from the side and rear before building, and look for gaps or speckled z-fight bands.
    - **In game:** fit every wing and the full widebody once; check the dealer spot's explicit parts include the default kit slots.
    - **Before any big spec edit:** copy `cars/<car>.json` to `cars/<car>.before_<step>.json`. After any script that writes the spec, confirm it still loads with json.load.
9. **Dealer bay:** a new line in `dealers/spots.txt` with explicit parts (8th field) and a unique spot name → `rebuild_dealers.sh`.
10. **In-game check with the user:**
    - Look: exterior day and night, interior, gauges, mirrors in daylight.
    - Garage: paint.
    - F6 log: parts and engine actually fitted.
    - Driving.

## Fixed facts
- **Game:** `D:\SteamLibrary\steamapps\common\Motor Town`. UE 5.5.4, pak v11, encrypted index. The AES key is in `~/mt-work/aes.key` (local only; never print or publish it).
- **Mod loading:** the game loads `*_P.pak` from `MotorTown/Content/Paks`. Later alphabetical names win on conflicts.
- **Mappings:** `~/mt-work/MotorTown-current.usmap` (dumped with UE4SS). Re-dump it after game updates.
- **Unpacked game files:** `~/mt-work/unpacked/MotorTown/Content`. Fetch any single file with `repak -a $(cat ~/mt-work/aes.key) get <MotorTown-Windows.pak> <path> > out`.
- **Tools:**
  - `~/tools/repak/bin/repak.exe`
  - `~/tools/uassetgui/UAssetGUI.exe` (tojson/fromjson VER_UE5_5 MotorTown). Run it with cwd = its folder, from the regular Python `C:/Users/noust/AppData/Local/Programs/Python/Python313/python.exe`: the Store Python cannot see its mappings. The Store `python` has PIL.
  - `~/tools/mappatch-bin/mappatch.exe` (our UAssetAPI tool; needs `DOTNET_ROOT=C:\Users\noust\tools\dotnet8`).
- **Cooking project:** `C:/UE/Projects/MotorTown` (engine `C:/UE/UE_5.5`).
- **Motor Town frame:** cm, X forward, Y right, Z up, origin on the ground at the car centre. A raw OBJ (x,y,z) imports as UE (x,-y,z).

## Pipeline (scripts in `ps2motortown/tools`, per-car spec in `ps2motortown/cars/<car>.json`)
1. **Source meshes → OBJ:** run `python tools/ps_to_mt.py cars/<car>.json`. It writes OBJs per Motor Town mesh (Body, Door_L/R, SideMirror_L/R, Wheel_L/R), textures and `car.json`.
   - Spec keys:
     - `texture_slots` (source texture hash → slot), `default_slot`;
     - per-mesh `parts` (`offset`, `mirror`, `slot`), `slot_rename`, `drop_slots`;
     - `mesh_names`, `collision_boxes`, `sockets`.
   - Slots: Paint, Bottom, Trim, Glass, LightCase, HeadLight, TailLight, Mirror, and Tex_<name> (texture material instances).
2. **Build meshes in the FULL editor, hidden.** The editor subsystems are None in `-run=pythonscript` commandlets, so collision and UV calls silently do nothing there.
   ```
   PSCAR_BUILD_DIR=C:/Users/noust/mt-work/build/<CAR> PSCAR_QUIT=1 UnrealEditor.exe C:/UE/Projects/MotorTown/MotorTown.uproject -ExecutePythonScript="C:/UE/Projects/MotorTown/Scripts/build_car.py" -unattended -nop4 -nosplash -RenderOffscreen
   ```
   - Stand-in materials are created at the game's own paths and never packed.
   - Each old mesh is deleted before import.
   - Slot names lose the importer's "Mat" suffix.
   - UV layout: UV0 = textures, UV1 = side-planar decal UVs (M_Body reads them), UV2 = lightmap.
   - Collision boxes are written via `body_setup.agg_geom.import_text`.
3. **Game assets:** run `python313 (Git Bash: `py -3.13`) tools/make_mt_assets.py ~/mt-work/build/pak_<CAR> cars/<car>.json`. It clones the base car's blueprint (e.g. Zino) onto our meshes, then sets:
   - wheel/seat/camera positions;
   - `blueprint.components` moves (room mirror, dome lights, headlight/blinker points).
   It also builds:
   - `Vehicles_ProStreet` (a row copied from the base car; `strip_part_slots` drops the base car's body kit, `part_overrides` sets Wheel0-3; NotOptionalPartTypes is cleared), added to the `Vehicles` composite;
   - `Wheels_ProStreet` (rim part row, `wheel_part`), added to the `VehicleParts` composite. No user mod replaces either composite; the game re-merges parent tables at load.
4. **Cook:** `UnrealEditor-Cmd.exe <uproject> -run=cook -targetplatform=Windows -unversioned -cookall -unattended -nop4 -nosplash -nullrhi`
5. **Pack and install:** `python313 tools/pack_car.py cars/<car>.json --install` creates `<CAR>_P.pak`. The game locks paks while running: install once it closes.
6. **Dealer spot (permanent):** add a line to `ps2motortown/dealers/spots.txt`, then run `sh ps2motortown/dealers/rebuild_dealers.sh`.
   - It clones an existing VehicleParams-keyed MTDealerVehicleSpawnPoint in Jeju_World's PersistentLevel and repacks `PS_Dealers_P.pak` (umap+uexp only; the 9.7 GB ubulk stays in the base pak).
   - Re-run it after every game update.
   - The SOURCE spot (column 1) is only a template and must be VehicleParams-keyed. Many game spots are class-keyed (e.g. the Magis's `MTDealerVehicleSpawnPoint8_1`) and make mappatch fail, so always use `Seo-Gui-Po-PremiumDealership_1`; the position comes from the line itself.
   - To place a bay: confirm the space with the user's screenshot plus the F6 position/yaw. Don't infer a row from spot coordinates alone: nearby spots may sit behind walls (Supra v1 landed inside a building and kept spawning broken cars).
   - A bay next to an existing car = its location + N×300 cm along its right vector (yaw + 90; the viewer's left when facing the car's nose). Use the same yaw.
   - Bays used: 350Z = Seo-Gui-Po Premium west row bay 3 (9333,149584,-20890, yaw 155); Supra = Magis dealership lot, the parking bay beside the Magis (Magis + 300 cm along its right vector, yaw -105.5).

## Base car choice (Magis vs Zino)
- Pick the game car that resembles the source car (the user's tip: the Magis is Motor Town's Mk4 Supra). Check its blueprint layout first: extract `Cars/Models/<Base>/*`, then list components, mesh imports, sockets and the CDO paint settings.
- **Magis differences** (handled by spec keys):
  - **No door components:** doors, side windows and mirror housings go into Body.
  - **One local-space `SideMirror` mesh:** the right component is the same mesh at scale Y −1.
    - Spec mesh `SideMirror` = left glass (`normal_filter` max −0.75, slot Mirror, `recenter: true`, `planar_uv {}`). ps_to_mt records its centre in `recentered`.
    - `mirror_components {LeftSideMirror_GEN_VARIABLE: "SideMirror", RightSideMirror_GEN_VARIABLE: "SideMirror:mirror"}` puts the components there.
    - No mirror socket is needed; the game re-aims the capture at the component.
  - **Shared dashboard** (`/Game/Cars/Parts/Dashboard/Dashboard_01`): make_mt_assets repoints whatever DashboardMesh imports to the car's own gauge carrier.
  - **The Magis Dashboard component hangs off the Body socket `SteeringWheel`:** its CDO leaves DashboardAttachSocketName at the default, whereas the Zino sets None; DashboardMeshLocation (5,0,2) and Rotation (pitch −5) are offsets from that socket.
    - Spec `dashboard.parent_socket: "SteeringWheel"` converts the car-space dial sockets into that socket's frame (`to_parent_frame`, using the socket rot incl. the steering tilt), and make_mt_assets zeroes DashboardMeshLocation/Rotation.
    - Symptom when wrong: needles and hubs float outside the car, up and to the left.
  - **Room mirror:** the game re-aims the capture by reflecting the eye→mirror ray about the mirror mesh's facing, so the component rotation matters (rotation 0 on the Supra reflected up into the headliner: dark).
    - Aim it so the eye ray reflects to straight back, about 2° UP: r = (−1, 0, +0.035), n ∥ r − d, X = −n. Recompute whenever cockpit_camera changes. Fine-tune from screenshots: every 1° of reflected view ≈ 0.5° of mirror pitch. Supra (eye z 91): +2° up gave (3.9, 20.6) = wing across the bottom; final aim −1.7° (r_z −0.03) → (5.9, 20.6, 0) to look under the wing.
    - Through a hatch with a big rear wing, aiming level or lower shows mostly the wing and deck, which can be mistaken for "seeing its own bodywork".
  - **Paint slot is `Body`** (ColorSlots Body/Seat/Window): `final_slot_names {Paint: Body, Glass: Window}`. The Zino uses Body_01.
  - **Row part `RearWing=MagisStock`:** strip it. Springs 12/13 (rear_z = z+1); chassis 1120 kg; Body sockets include Exhaust_Right too.
- `default_engine: "/Game/Cars/Parts/Engine/<asset>"` sets the blueprint's default EngineData to any engine asset, e.g. More Tuning's 2JZ320HP for the Supra (420 N·m, 7000 rpm, with real 2JZ sound samples). The user asked to use More Tuning engines where they match the real car: accepted dependency on More Tuning.
- **Glow mask:** when the dial triangles are large (Supra: they span the whole dash face), cover the dash with `uv_split` and set `emissive_slots.<slot>.mask_from_gauges: true`. ps_to_mt writes `<tex>_GLOW.png` (black except the gauge-face circles), and M_Glow's separate "Glow Texture" param reads it.
- **Fortem base** (small roadster/coupe; used for the Elise, the user's pick). Same as the Magis except:
  - The mirror mesh is called **`LeftSideMirror`** (make_mt_assets' parts list includes it): spec mesh `LeftSideMirror` (recenter, planar_uv) + `mirror_components {LeftSideMirror_GEN_VARIABLE: "LeftSideMirror", RightSideMirror_GEN_VARIABLE: "LeftSideMirror:mirror"}`.
  - The colour slot for glass is `Windows` (`final_slot_names {Paint: Body, Glass: Windows}`).
  - Lamp/blinker components to move: `HeadLight_Left/Right`, `BlinkerLight_01/02`, **`TaliLight_01/02`** (the game's spelling), `RoomMirror`, `FrontDomeLightSlot`.
  - Dashboard_01 hangs off the Body socket `SteeringWheel` (DashboardMeshLocation (7,0,3), pitch −5) → `dashboard.parent_socket: "SteeringWheel"`.
  - Engine sound for a small I4: clone the game's `I4Sport_150HP` (row I4_150HP). Copy the asset into `~/mt-work/unpacked` first with `repak get` (make_engine clones from there).
- **Dealer bay placement:** ask the user to stand where the car should go, facing the direction its nose should point, and press F6 (it logs the player position and camera yaw to `MotorTown/Binaries/Win64/ue4ss/UE4SS.log`, line `[PSCar] player at (...) camera yaw ...`). If they stand at the bay entrance line, put the car centre ~2.5 m ahead along the yaw; z = ground ≈ player z − 90. Then add the spots.txt line and run rebuild_dealers.sh.

## Interior / first person
- **Steering wheel:** the game spins the mesh `/Game/Cars/Parts/SteeringWheels/<name>` around its local X axis, hub at the origin. The Zino's wheel is about 19.5 cm in radius and 6 cm thick in X. It is attached at the Body socket `SteeringWheel`.
  - Spec `extract.SteeringWheel = {from: Body, center, radius (Y-Z), x_range, socket, align_x}` moves the source car's own wheel triangles into that mesh. It centres them on the hub, stands the wheel upright (fits its tilt) and writes the socket location plus pitch = −tilt.
  - Find the centre by rendering the cockpit region (front view Y-Z); the wheel shows as a ring.
  - make_mt_assets swaps the blueprint's steering wheel import to the car's own. pack_car also packs `Cars/Parts/SteeringWheels/<car>.*`.
- **Base car's gauge pod:** it is a Dashboard component with `DashboardMesh` and `NiddleMesh` properties, not a plain StaticMesh. `blueprint.hide_meshes: [Dashboard, Niddle, SmallNiddle]` clears every object property pointing at those imports.
- **Working gauges:** MTDashboard (blueprint component "Dashboard") draws the dial faces itself (GaugeConfigs: W_Tachometer, W_MuscleGauge, W_FuelGauge, W_TempGauge) and turns needle meshes (Muscle_01 Niddle/SmallNiddle) at sockets `Niddle_RPM`, `Niddle_Speed`, `Niddle_Fuel`, `Niddle_Temp` on its DashboardMesh. The sockets are in car space; the Zino's use rot (0,-90,-64.06), a face tilted 26° up.
  - Spec `dashboard.sockets` makes ps_to_mt write a Dashboard mesh that is just a tiny hidden triangle carrying those sockets. make_mt_assets swaps the blueprint's Dashboard import to it.
  - Find the dial centres by locating them in the car's interior texture (render it with a UV grid). Then map each UV onto the cluster triangles (barycentric). Image row = 1 − v_json with the current UV convention.
  - Place each socket 0.4 cm proud along the panel normal. Roll = −90 + upward tilt (350Z panel leans 12° toward the driver → −102).
- **Working side mirrors:** Motor Town's side-mirror mesh is the reflective glass ONLY (one slot named `Mirror`, material M_Mirror). The SideMirror component (SideMirrorSocketName/SideMirrorSurfaceSocketName = `SideMirror_L/_R`) renders the reflection there via a socket on that mesh, whose X axis points away from the glass normal (Zino left: yaw −17).
  - Per-part `normal_filter {axis, min, max}` splits the source mirror: the rear-facing faces (normal X ≤ −0.75) become the SideMirror mesh with slot Mirror; the rest (the housing) goes onto the door with slot Paint.
  - `mirror_sockets {SideMirror_L: SideMirror_L, ...}` places each socket at the glass centroid. The ROTATION is aimed from the cockpit camera, like an adjusted real mirror: the eye ray must reflect to straight back, slightly outward (`mirror_outward` 0.15). Normal ∥ (reflected − incoming), socket X = −normal. Using the source glass's own normal (350Z left: 30° inward) made the mirror reflect the car's own flank. Aiming reproduced the Zino's own left value (−17.5°), which validates the method.
  - Test mirrors in daylight: at night a correct reflection is mostly black.
  - How the game does mirrors (logged with the [PSMirror] F6 inspector, a UE4SS mod in KoPDealer): each mirror component owns a SceneCaptureComponent2D `MirrorCapture` attached at the mirror mesh socket (room mirror socket `SideMirror`). There is no clip plane and no hidden actors. Every frame the game re-aims it and sets its FOV from the player camera (≈41° when you're in the car). It renders into a shared `BudgetRenderTarget`. M_Mirror samples it (texture param `DummyMirror`, U flipped; there is also M_Mirror_NonInvert).
  - If a mirror shows ONE flat colour, check the glass UVs (re-export with StaticMeshExporterOBJ and count distinct `vt`).
  - Pitfall: spec values like `planar_uv: {}` are falsy in Python, so test `is not None`.
- **Duplicate interior parts:** a source interior may model its own static rear-view mirror (or other parts the game supplies) that blocks the game's working one. Remove them with per-mesh `drop_boxes [[x0,y0,z0,x1,y1,z1]]` (drops triangles fully inside) and put the game component in its place. 350Z: the mirror box x12–30, y±18, z97–113; RoomMirror at (21,0,104).
  - Putting M_Mirror on the whole housing makes it glow white.
  - The glass needs UVs spanning 0..1 over its face: M_Mirror stretches the live capture over UV0. With the source car's UVs (a tiny region of a chrome texture) the glass shows one flat colour. Per-mesh `planar_uv {}` projects the glass flat: u along Y (1 at the −Y edge, `flip_u` to swap), v along Z (image top = v 1).
- **Room mirror:** it reflects through the rear glass, and a low hatch needs the mirror aimed further down than the Zino's. `blueprint.component_rotations {RoomMirror_GEN_VARIABLE: [pitch, yaw, roll]}`. 350Z: [10, 17, 0] (Zino 7.2/16.2/1.8).
- **Paintable at the garage:** the game paints the material slot NAMED `Body_01` (the Zino: Body, Door, all M_Body). Spec `final_slot_names {Paint: Body_01, Glass: Window}`; build_car also strips the importer's "Mat" suffix from every slot.
  - StaticMaterial structs must be rebuilt (`unreal.StaticMaterial(material_interface=..., material_slot_name=...)`) and set back. Editing them in place silently doesn't stick, and imported_material_slot_name is read-only.
- **Garage skins:** the blueprint CDO's `BodyMaterialList` is the skin list. Entry 0 = M_Body = "Paint #1", the colourable paint and the normal default. The Zino's other 35 entries are PolygonStreetRacer liveries mapped to Zino UVs, which come out scrambled on a converted body. `blueprint.keep_body_materials: 1` trims the list. `BodyColors` are the preset colour sets (Body_01, Interior_*, Seat_*), and `BodyMaterialNames`/`ColorSlots` name Body_01.
- **Readable gauge faces:** source-game dial art is tiny and dark, and its painted needles duplicate the live ones. Spec `texture_upscale {slot: 4}` + `gauge_faces {slot: [...]}` makes ps_to_mt upscale the texture and paint crisp faces (black face, white ticks/numbers, red zone) at each needle pivot. Angles follow MTDashboard (degrees clockwise from 3 o'clock; RPM/Speed 140→400, Fuel/Temp 210→330), with `labels` (E/F, C/H) and `captions` at 90° (the bottom gap).
  - Check the result with a crop of the texture before building.
  - Leave unit captions off the speedometer: the game may feed km/h or mph.
- **Per-car gauge style (2026-10-19, the user: "reference real world examples for the interiors instead of making them all the same"):** the generic black/white Arial faces were identical on every car. Spec `gauge_style` (merged into every gauge_faces entry; entries override) takes:
  - face_color, face_inner [colour, radius fraction], ring [colour, width fraction], ink, minor_ink, red_color, caption_color;
  - font_file (Windows font: segoeuib/seguisb Japanese and modern, bahnschrift = DIN for BMW/Porsche, framd = Franklin Gothic for classic American);
  - number_radius, tick_major/minor/outer, tick_w_major/minor;
  - **glow_color** (markings backlit in the car's light colour) or **glow_face** (white-faced dials: the face is backlit and the markings stay dark), plus glow_red.
  - With mask_from_gauges, the _GLOW texture is drawn in that backlight colour (cube roots, since M_Glow emits texture³ × Glow).
  - Use the NFS source dial art as the colour reference: it was drawn from the real cluster. Contact-sheet the source crops first.
  - White-faced cars use glow 1.5 instead of 3 so they don't look blown out by day.
  - Styles in use:
    - 350Z: amber on black.
    - Supra: white by day, orange at night.
    - Elise, R34, Viper, M3 GTR: white faces.
    - 997 Turbo, 993: black with DIN numbers.
    - Shelby: silver turbine.
    - Challenger, Chevelle: black with Franklin Gothic.
    - Chevelle: chrome rings.
  - Real redlines: 350Z 6.6, Supra 6.8, 997 Turbo 6.8, Shelby 6.0, Challenger 5.5.
- **Gauge needle ranges come from the blueprint, not the face (found 2026-10-19):** the Dashboard component's `GaugeConfigs` map (RPM/Speed/Fuel/Temp → MTDashboardGaugeConfig: NiddleMesh, NiddleMeshScale, MinValue, MaxValue, ValueScale, NiddleStart/EndDegree, WidgetClass) sets where the needle points. Every base stops RPM at 8 (×1000); Speed is 210 (Tuscan 180). Our faces drawn to 9k / 210 read wrong near the top.
  - Spec `gauge_ranges {RPM: {max}, Speed: {max}}` makes make_mt_assets set MaxValue. Keep the painted face's max equal to it.
  - **The user wants mph:** Speed `{max, value_scale: 1.609344}` sets ValueScale (needle value = raw / ValueScale, as RPM uses 1000; the game feeds km/h), and the speed face is painted in mph with an "MPH" caption. Numbers every 20 mph, or every 40 from 200 mph up.
  - Real US ranges (rpm×1000 / mph): 350Z 8/160, Supra 9/180, Elise 9/160, 997 Turbo 8/200, R34 9/160, Shelby 8/140, Challenger 8/150, Chevelle 8/140, Viper 7/220, M3 GTR 10/200, 993 8/180.
- **Per-car needles:** spec `needle_color` [r,g,b]. ps_to_mt make_needles writes Needle/SmallNeedle meshes, same size and frame as the game's Muscle_01 Niddle (+X from the pivot, 0.8 tail, 1.6 wide, 0.47 thick in +Z; ExtendedBounds origin (1.8,0,0.25) extent (2.6,0.8,0.23); small = half). Slot NeedleGlow is emissive with a solid Tex_<car>_NEEDLE. make_mt_assets repoints the blueprint's Niddle/SmallNiddle imports to Cars/Models/<car>/Needle and SmallNeedle.
- **Needle size per dial (round 3):** each base's GaugeConfigs NiddleMeshScale is a fixed 1.0 (Zino/Cora/Magis/Fortem) or 0.5/0.7 (Tuscan), whatever the car's dial size. Spec `needle_scales {RPM,Speed,Fuel,Temp}` = 0.85 × measured dial radius (cm, mapped through the dash triangles) / 4.39 (big needle) or / 2.195 (small); make_mt_assets writes them. `needle_width` (0.5) narrows our needle mesh. Measured radii are in ~/mt-work/dial_radii.json.
- **Dials cut by display strips (Elise):** gauge_faces `clip_below: <row>` restores the original texture below that row after painting.
- **Source models with their own 3D needles (993 RWB):** thin 4.5 cm strips sampling a colour swatch of the dial atlas show as "ghost" needles. Mesh option `drop_uv_boxes [{slot, uv: [u0,v0,u1,v1]}]` removes them (json v, before uv_split).
- **Dark MW tail lenses:** lamp kind `tail_red` = emissive pure red × saturate(R − max(G,B)) × (HeadLight 12 + BrakeLight 60), so dark-red "off" lens texels glow and chrome rims don't (M3 GTR).
- **Glowing gauges (backlight):**
  - Per-mesh spec `uv_split: [{from, to, box: [u0,row0,u1,row1]}]` moves triangles whose UVs fall in the cluster area of a texture onto their own slot (e.g. `Gauges`).
  - Spec `emissive_slots: {Gauges: {texture_slot, glow}}` makes build_car create our own material `/Game/Cars/Models/<car>/M_Glow`: base colour = texture, emissive = texture³ × Glow, so white/red markings glow while the grey bezel and black faces stay dark. Each slot gets an instance `MI_Glow_<slot>`.
  - Our own materials ARE shipped (anything under Cars/Models/<car> is packed; only the stand-ins under Cars/Materials are not). It cooks cleanly with UE 5.5.4.
  - The glow is always on, like a real dash: subtle by day, clear at night.
- **Lamps that light up:** the game drives light materials through scalar parameters named after the light: M_HeadLight → `HeadLight`, M_TailLight → `BrakeLight`, M_ReverseLight → `ReverseLight`, M_TurnSignalLight → `SideMarkerLight`. Its cars name the slots HeadLight / TailLight / BrakeLight / ReverseLight / LeftSignalLight / RightSignalLight.
  - Spec `lamp_slots {<lamp texture slot>: head|tail|reverse}` makes build_car create our own `M_Lamp_<Kind>`: base colour = lamp texture, emissive = texture × Σ(weight × parameter). Head: HeadLight×25; tail: HeadLight×3 + BrakeLight×18.
  - Plus `final_slot_names {<head slot>: HeadLight, <tail slot>: TailLight}`. (Plain textured lamps never glow; the game's own M_HeadLight renders flat white.)
  - CONFIRMED in game (Supra, 2026-10-18): headlights and taillights glow with our M_Lamp_* on slots named HeadLight/TailLight.
- **Body-coloured add-ons:** the source car's spoiler (and similar) may use the shared chrome code. Force the part's slot to Paint (`{"part": "SPOILER", "slot": "Paint"}`) so the garage paints it.
- **Seat height vs roof:** check the roof height above the seat (Supra roof 112 vs 350Z 117, sloping back). If the head pokes through, lower the seat (Supra z 8) and keep the cockpit camera where the dials are visible over the wheel hub (Supra 91; the hub hid the lower dial halves and needle pivots at 85).
- **Lamps:** source taillights are often a red inner graphic plus a dark semi-transparent lens (`*_GLASS_OFF`, alpha 170-255). M_Sketchfab_Base is opaque, so the lens draws black. Drop the lens slot (`drop_slots`) and keep the inner texture.
- **Lamps:** don't force the source car's light parts onto M_HeadLight/M_TailLight; they render as flat white. Map their own textures (e.g. `*_HEADLIGHT_ON`, `*_BRAKELIGHT_OFF`, `*_BRAKELIGHT_GLASS_OFF`), use Glass for clear covers and Mirror for chrome bowls whose texture wasn't exported. The trade-off is no emissive glow on the lamp meshes; the beam spotlights still work.
- **Driver position:** put the seat and cockpit camera at the steering wheel's Y.
- **Texture V:** ProStreet DAE UVs are top-left (D3D) and UE's OBJ import flips V itself, so write vt = v unflipped. With a wrong flip, symmetric textures (rims, badges) still look fine, but the window seals sampled the orange amber-lamp area of the MISC texture.

## ProStreet rim pack (aftermarket wheels as tuning-shop parts)
- **Source:** `CARS/GROUP01..08/GEOMETRY.BIN`, 96 designs (10/11/12/15/14/15/11/8), parts `GROUPgg_KITkk_WHEEL_TIRE_FRONT|REAR[_T0..T5]`. Every group's `TEXTURES.BIN` holds all 96 `GROUPgg_KITkk_WHEEL` textures. Export each with AssetDumper into `~/nfs-work/geo/ps_groupgg` and `~/nfs-work/tex/ps_groupgg`.
- **All ProStreet wheels share one frame and size:** radius 32.2 cm, the same as the stock 350Z wheel. Tyre = 0xE4CEA024 (→ Bottom); generic chrome = 0xBF30889B (→ Trim); plus the design's own texture.
  - Built exactly like a stock wheel: unmirrored + offset +11.5 = the `_R` asset, mirrored + offset −11.5 = `_L`.
- **`tools/ps_rims.py cars/ps_rims.json`** builds OBJs/textures plus `car.json` (for build_car, car = `PS_Rims`) and `rims.json` (rows) in `~/mt-work/build/PS_Rims`.
- **Tables:** give make_mt_assets the rim spec alongside the car specs: `make_mt_assets.py ~/mt-work/build/pak_PS_350Z cars/350z.json cars/ps_rims.json`. Specs with `kind: rims` add only Wheel rows (`add_rim`), with `VehicleKeys` = `vehicle_keys` so the rims are offered on ProStreet cars only (they're the wrong size on game cars), and `cost`.
  - Add each new ProStreet car's key to `ps_rims.json` vehicle_keys.
- **Pack:** `pack_car.py cars/ps_rims.json` → `PS_Rims_P.pak` (Cars/Models/PS_Rims MIs/textures + Cars/Parts/Wheels/PS_Rims_*, 864 files, 34 MB).
- **Names:** real names (e.g. "BBS LM", "Volk TE37", "KÖNIG Blatant") in `cars/ps_rim_names.json` (G01K01 → name; spec `names`).
  - Source: the ProStreet VLT unpack `~/nfs-work/ps_vlt/main/fe_attrib/frontend/part_fedata.yml` → `generic_wheel_group_gg` partData[0..n] HAL_ID (entry 0 = STOCK, then kit 1..n).
  - Those IDs index `LANGUAGES/English_Global.bin`: chunk 0x39000; at offset 8: NumStrings, HashTableOffset, StringTableOffset; entries (hash u32, offset u32) at 8+HT; strings at 8+ST+offset, NUL-terminated, Latin-1 (cp1252 fails on other entries).
  - The same method gives names for any ProStreet part.
- **Shared tables (DONE):** always run `make_mt_assets.py ~/mt-work/build/pak_PS_Common cars/350z.json cars/supra.json … cars/ps_rims.json` (EVERY car spec plus the rim spec). Then:
  - `pack_common.py` → `PS_Common_P.pak`: DataAsset tables/composites plus custom engines, gearboxes and curves.
  - `pack_car.py cars/<car>.json` → the car pak: its cooked meshes plus only its own blueprint from pak_PS_Common.

## ProStreet body kits as garage parts (like the rims)
- **Motor Town body kits:** AeroParts rows. PartType = slot: FrontBumper, RearBumper, Bonnet, SideSkirt, Fender, RearWing (also RearSpoiler, Roof, FrontSpoiler, Louvers, Trunk). Aero.Mesh is a static mesh in CAR space (Zino bumper at x +195, spoiler at x −193). We set bUseCustomSocket False (attach at the body origin).
- **ProStreet kits per car:** KIT00 (stock), KIT01/03/04/11 (bumpers, skirts, exhaust), KIT01–04 hoods, KITW01 widebody (bumpers, fenders, skirts), spoilers SPOILER / SPOILER_EVO / SPOILER_DRAG. All in car space; files `<CAR>_<KIT>_<PIECE>_A.dae`.
- **`tools/add_body_kits.py cars/<car>.json`:**
  - removes the stock pieces of those slots from Body;
  - adds meshes `Aero_<Slot>_<Kit>` (parts with a per-part `prefix`: RearBumper = BUMPER_REAR + _EXTRA + EXHAUST; skirts L+R; fenders L+R; wings forced to Paint);
  - writes `aero_parts` rows, default part_overrides (KIT00; the Supra wing via `stock_wing`) and `not_optional_part_types`.
- **make_mt_assets:** `make_aero_table` builds Aero_ProStreet (rows copied from a game row of the same PartType, VehicleKeys = the car, Cost 1500). `patch_composite_from` adds it as a second parent of our already-patched VehicleParts composite. part_overrides now ADD slots the base row lacks (e.g. FrontBumper on the Magis).
- **Rear wings:** Motor Town mounts RearWing parts on the Body socket `RearWing` regardless of bUseCustomSocket. The game's own universal wings (Type-A…D, other cars' wings) are modelled RELATIVE to that socket, so it must sit on the trunk-lid top (measure the highest Body paint z near the rear, |y| < 15: 350Z (−185,0,81), Supra (−200,0,86)).
  - Our car-space ProStreet wings get part `offset` = −socket.loc (add_body_kits does it from the spec socket).
  - History: socket at (−200,0,95) without the offset → our wings floated behind the car; socket at the origin → our wings fit but the universal wings sat under the car.
  - Bumpers, hoods, skirts and fenders attach at the origin and fit as-is.
- **Paintable parts:** a part row decides what gets painted.
  - `BodyMaterialNames` lists the mesh slots that take the BODY paint. Our wing rows copy Stella_RearWing_03 and set the key to the car's paint slot (Body / Body_01); with an empty list (our first RearWing template) wings stayed unpainted.
  - `ColorSlots` adds a per-part colour picker for a named slot (game rims: `Wheel_01`, e.g. the Civo).
  - Open item: the game's universal wings (Type-A…D) don't take paint on our cars (the user said skip for now; likely their BodyMaterialNames name a slot such as Rear_Wing_01 that the vehicle's paint setup doesn't cover).
  - Paintable rims: spec `paintable_texture_slots: [<rim tex slot>]` + `final_slot_names {<rim tex slot>: Wheel_01}`. build_car then parents those texture MIs to our `M_PaintTex` (texture × vector "Color", default white). Wheel rows (car rims and all 96 pack rims) get the Civo's ColorSlots with default white and display name "Rim". ps_rims does the slot part automatically.
- **Dealer spot:** append the new default slots to the explicit parts list and rename the spot.
- **measure_arches:** includes the `Aero_*_KIT00` meshes, since the fenders and bumpers left the body.
- **Owned cars:** parts saved before the kits existed have no bumpers or hood (those left the body). Fix at the garage (Workshop / restore normal parts) or buy fresh.
- **Kit numbers differ per car** (Elise: body KIT01/06/11, hoods KIT01/02/03/05). generic_body_as has only 4 names and generic_hood_as 4 (+ a duplicate), with no per-car lists, so the car's kits take the names in order: Elise KIT06 = Stratospeed Formula 5, hood KIT05 = Araxis Impact. Add new numbers to BODY_KITS/HOODS; unknown ones show as "Kit N".
- **Decoder:** English_Global.bin chunks are `id u32, size u32`; in each 0x39000 chunk the data starts with `NumStrings, HashTableOffset, StringTableOffset` (offsets from the data start); hash entries are `(hash u32, offset u32)` into the string table; Latin-1, NUL-terminated.
- **Render checks without numpy:** the system `python` has PIL (no numpy/matplotlib) and must run WITHOUT `-I` to see it. Draw OBJ triangles with ImageDraw (side X-Z, rear Y-Z, top X-Y); the OBJs are in the MT frame. Wings drawn at mesh + RearWing socket.
- **Real kit names** (in add_body_kits BODY_KITS/HOODS/WINGS), from part_fedata decoded with English_Global.bin (same method as the rims):
  - `generic_body_as` = Stock Autosculpt / Stratospeed Formula 4 / 5 / 7 → KIT01/03/04/11 in order;
  - `generic_hood_as` [1..4] = Araxis Sport / Sweeper / Blitz / Impact → hood KIT01..04;
  - `generic_widebody` = Stratospeed Widebody;
  - `generic_spoiler_evo` / `_drag` = Gentera Style 402 / 403.
  - ProStreet's car_kit.yml calls KIT01+ the KIT_TYPE_AUTOSCULPT kits.
- **Widebody:** `KITW01_WIDEBODY` is a WHOLE widened body shell, not flares. Adding it whole double-skins the car. Per-part `drop_coincident_with {part: BODY, prefix: <CAR>_KIT00, tol: 1}` keeps only the triangles that are off the stock body's SURFACE (sampled every ~1 cm; vertex-only matching left speckled z-fighting bands). `x_range` gives the rear half to the Widebody rear bumper and the front half to the Widebody fenders (add_body_kits does this automatically).
- Not done: the kit-specific BODY shells (KIT01_BODY…), roof scoops.
- **Spec safety:** never store non-JSON data (sets, caches) inside the spec. ps_to_mt writes the spec back, so a failed dump truncated both car specs. It now writes atomically (tmp + os.replace), and caches live in module globals. Keep a spec backup before big edits (`cars/<car>.before_kits.json` saved the day).

## Driving feel (real-car specs)
- **What sets it:** the vehicle row's Parts (Engine, Transmission, FinalDriveRatio, LSD0, Tire0-3, BrakePad0-3, CoolantRadiator), plus the blueprint Mesh `BodyInstance.MassInKgOverride` (chassis mass).
  - Total mass = chassis + each part's MassKg (engine ~190-310, gearbox ~100, rims 20 each, tyres 10 each).
  - The rear wheels carry `DifferentialComponentName`, so the Zino blueprint is RWD. Wheels also have SpringK, damping and BrakeRatio; the CDO has AirDragCoeff, AeroLift and AntiRollBars.
- **Engine asset** (MHEngineDataAsset, e.g. Cars/Parts/Engine/V6Sport_DOHC_200HP): EngineProperty.MaxTorque = N·m × 10000; MaxRPM; TorqueCurve = a CurveFloat whose time axis is rpm/MaxRPM and whose value is the torque fraction.
  - Peak hp = max over the curve of (fraction × MaxTorque/1e4 × rpm × 2π/60) / 745.7. This checks out exactly on the base V6 (201 hp).
- **Engine sound:** the engine asset's `EngineSoundData` import (MTEngineSoundDataAsset). The game has only three: V6Sport/V6Sport_02/EngineSoundData (the 400 hp V6), V6Sport/V6Sport_03/V6Sport_03_EngineSoundData (the 200 hp V6; distorted on the 350Z; V6Sport_02 was confirmed better by the user) and Truck/MidDuty_02. Engines without one (the small-block V8s) use the vehicle's default V8 sound. Set with the custom engine's `sound: "<package>.<object>"`.
- **Gearbox asset** (MTTransmissionDataAsset): Gears[] with Name R/N/1..n and GearRatio (reverse negative).
- **Final drive:** rows in FinalDriveRatio (e.g. "103" = 3.55).
- **Custom parts:** spec `custom_parts {engines: [{row, base_row, asset, base_asset, display_name, mass, cost, max_torque_nm, max_rpm, curve: [[t,v]...]}], transmissions: [{row, base_row, asset, base_asset, display_name, ratios: {R,1..6}}]}`.
  - make_mt_assets clones the engine asset, its torque curve (written with linear keys) and the gearbox asset under Cars/Parts/..., then adds their rows to Wheels_ProStreet (same row struct, already in the VehicleParts composite).
  - Set `part_overrides` for Engine/Transmission/FinalDriveRatio/Tire*/BrakePad*/CoolantRadiator, and `blueprint.body_mass`.
  - Don't depend on More Tuning rows: they vanish if that mod is removed.
- **Existing saves, and the dealer display car too:** vehicles keep the parts they first spawned with. That includes the dealer bay's display car, which is saved with the world and restored every session, so buying it "new" gives the old parts.
  - Diagnose with the KoPDealer F6 logger (Net_Parts, EngineComponent.EngineData).
  - Fix: give the spot explicit parts and a NEW actor name in spots.txt (8th field `Slot=PartKey,...`; mappatch copies the part-struct template from a game spot that has one, e.g. the Zydro), then `rebuild_dealers.sh`.
  - The blueprint's EngineComponent default EngineData is also repointed to the custom engine.
- **350Z reference:** VQ35DE 287 hp at 6200 rpm, 371 N·m at 4800, limiter 6800; curve [[.1,.62],[.35,.85],[.706,1],[.912,.888],[1,.78],[5,.15]]. CD009 gearbox: R -3.446, 3.794/2.324/1.624/1.271/1.000/0.794; final drive 103 (3.55); PerformanceTire_46; BrakePad_Small_02; SmallRadiator_110; chassis 1014 kg → 1440 total.

## Matching ProStreet's own performance (the user's choice for the Supra)
- **Source:** `~/nfs-work/ps_vlt/main/attributes/db/vehicle.yml`, record `<car>_track`. (pvehicle.yml lists `<car>` → vehicle presets; ecar.yml = visual setup, whose TireOffsets cross-check the arch positions.)
  - TORQUE: curve XValues 0..1 over MinX..MaxX rpm, YValues 0..1 over MinY..MaxY N·m (T = MinY + Y·(MaxY − MinY)).
  - `FORCED_INDUCTION` → forced_induction.yml (turbocharger: PeakPSI, BoostStartRPM as a fraction of MAX_RPM). Bake the boost in as T × (1 + PSI/14.7) from BoostStartRPM, ramped over about 800 rpm below it.
  - Also: MASS, FINAL_GEAR, GEAR_RATIO [R, N, 1..n], RED_LINE, MAX_RPM (→ MT MaxRPM), IDLE.
- **MT engine:** MaxTorque = the peak of the boosted curve; curve time = rpm/MAX_RPM, value = T/peak. Clone More Tuning's engine asset (copy it into ~/mt-work/unpacked first) to keep its recorded sound; make_engine repoints whatever CurveFloat the base imports.
- **Supra result:** 383 N·m at 3800, 296 hp, limiter 7600; V160 ratios with R 3.446; FD_3.31 (3.266); chassis 1064 → 1510 kg.
- Changing default parts means renaming the dealer spot (v3…) so a fresh car spawns. Owned cars keep their parts: swap at the garage.

## Lessons (each cost a round trip)
- **Widebody without fender pieces** (Elise): add_body_kits still makes a W01 Fender row from the shell's front half plus the KITW01 widened doors; `drop_coincident_with.parts` lists several reference parts (BODY + stock doors that live in Body). Symptom when missing: only the W01 bumpers in the garage, scraps behind the doors.
- **Mirror glass by triangle group:** when the normal filter grabs housing triangles (glass mesh comes out a long thin strip or the in-game mirror looks huge), list the source groups and use per-part `groups: [i]` for the glass and `skip_groups: [i]` on the housing. Elise: group 1 of SIDEMIRROR_LEFT (6 tris).
- **Never use slot `LightCase` (M_Glass_LightCase):** it renders solid WHITE in game (a stand-in that isn't really a game glass). Keep lamp covers on Glass; the user is fine with the window tint on them.
- **Turn signals (every car):** Motor Town flashes body slots named `LeftSignalLight` / `RightSignalLight` (game material M_TurnSignalLight reads scalar `TurnLight` for the flash and `SideMarkerLight` with the headlights; left = y < 0). Spec `signal_lamps` rules move triangles into `Signal_L<tag>` / `Signal_R<tag>` per mesh: `from` slot plus any of `box` (car space), `uv_box` (u0,row0,u1,row1; mod 1), `amber: true` (texels R>60, R>1.25G, G>0.35R, B<0.55G). Per tag add `lamp_slots {Signal_L_F: {kind: signal, texture_slot: <lens texture slot>}}` and `final_slot_names {Signal_L_F: LeftSignalLight}`. build_car's "signal" lamp material: base = lens texture, emissive = amber x (30 TurnLight + 1 SideMarkerLight). Find indicators with an amber-texel survey over all Tex_ triangles (front x>0 / rear x<0), then confirm in the textures.
  - 350Z: front = amber MISC lenses in the bumper corners, rear = BRAKELIGHT u 0.2-0.5 section. Supra: front = amber BADGING strip on the bumper, rear = amber tail-cluster texels (|y|>17). Elise: front = oval BADGING lens inboard of each headlight (bonnet + bumper) and amber MISC side markers, rear = inner round lamps (|y|<47, x<-178.5).
  - Rear signal lamps double as tail/brake lamps (the user: rear lights are brake lights too): lamp kind `signal_tail` = red (BrakeLight 18, HeadLight 3) + amber TurnLight flash (LAMP_PARAM_TINT). Unverified whether the game sets BrakeLight on the signal slots.
  - Open question (test in game): signal slots in aero meshes (bumpers/bonnets) and two same-named slots in one mesh may not flash.
- **Dashboard turn arrows / warning lights:** the game's upper MFD widget (W_UpperMFD_Transparent: Left/RightBlinker arrows, headlight, high beam, handbrake, low fuel, TCS, overheat, on a transparent background) renders onto Dashboard mesh faces named `DashboardUpperMFD` (material /Game/Cars/Materials/M_WidgetRender; build_car maps the slot). Game dashboards also have SpeedoMeter/TachoMeter/FuelGauge/TempGauge widget faces; we keep painted dials instead. Winding: converted meshes have geometric normal (json order) = facing; the strip was first written backwards and was culled (invisible). Spec `dashboard.mfd {anchor: [dial sockets], up, right, out, width, height}` adds a strip in the dial plane (tilt from the needle roll), converted into the parent socket frame when `parent_socket` is set. Elise: above the dials (up 5.4, 8x1.6 cm); 350Z: above the tach; Supra: above the speedo. Positions are first guesses: confirm in game.
- **Black "cutouts" round lamps = a ProStreet inner-panel material mapped to Bottom.** Elise `0xBEBC83C2` (only on HOOD and TRUNK: the panels' inner faces) is body colour in ProStreet; mapped to Paint the indicator pockets vanished. Compare with a ProStreet screenshot and check per-hash usage (part list + bounds) before mapping a hash to Bottom. The glass-plate tool below was the wrong fix (removed for the Elise).
- **Lamp recess without a cover:** `tools/lens_caps.py cars/<car>.json` fits a flat glass plate (slot Glass) over the lamp + recess-wall triangles per side (spec `lens_caps [{meshes, slots, box (|y|), lift, grow}]`) and writes it as Body `extra_triangles` (ps_to_mt appends raw triangles). Run it after a first ps_to_mt (it reads the mesh JSONs), then ps_to_mt again.
- **Light components (TaliLight/BlinkerLight/HeadLight):** always move all of them onto the car's own lamps, a few cm OUTSIDE the surface. Left at the base car's spots or inside the body they paint red/amber smears on the wrong panels (Elise rear). BlinkerLight_01/03 are RightBlinker (+y).
- **Badge textures are alpha cut-outs:** every car's `<CAR>_BADGING` (logos, lettering, the Elise's oval indicator lens) has transparent background; with an opaque material the background shows as dark squares (the Elise indicators looked like black parallelograms). Spec `masked_texture_slots: [Tex_<CAR>_BADGING]` → build_car parents those MIs to our M_TexMasked (alpha → opacity mask) and lamp slots showing them get M_Lamp_<Kind>_Masked. WHEEL textures also carry alpha (~97% "transparent") but it's a shading mask: never mask them. Survey: alpha<128 over >2% of the texture.
- **Light components hang off TaliLight:** BlinkerLight_03/04 and the ReverseLights sit RELATIVE to the TaliLight components, so moving TaliLight onto the car's tail lamps fixes all rear light sources. The Zino/Magis spots are 28-40 cm behind our cars (350Z/Supra brake light looked dead until moved). Always set TaliLight_01/02 in blueprint.components.
- **UV convention (cost two wrong turns):** ps_to_mt buckets, mesh JSON and OBJ all store the DAE UVs as-is; in game the texture ROW = 1 − v. Any texture lookup from those UVs uses row = 1 − v (uv_split, signal rules, gauge mapping). Don't read OBJ `vt` v as the row.
- **Gauge aspect:** the dash triangles can stretch the texture unevenly (Elise: 120.8 cm per u vs 196.9 cm per row, ratio 0.614), so round painted dials show as tall ovals. Measure cm-per-u / cm-per-row over the Gauges slot triangles and set `aspect` on each gauge_faces entry (drawn on a square canvas, squashed by aspect, pasted). Only apply where the user sees stretched dials: on the 350Z/Supra the faces then no longer fit the ProStreet bezels (they were tuned by eye already).
- **Extra-sharp small parts (steering wheel):** a part using a small patch of the 512 px interior stays soft even after x4. Spec `detail_textures [{mesh: SteeringWheel, from: Tex_<CAR>_INTERIOR, box: [u0,row0,u1,row1], to: Tex_<CAR>_SWHEEL, size: [2048,4096]}]`: ps_to_mt crops the source, runs Real-ESRGAN twice (x16), resizes, gives the mesh its own slot and remaps its UVs into the crop (row = 1 - v). Check the mesh's UV extent first.
- **Stance from the arch edge (don't guess in 3 cm steps):** histogram the outer Paint vertices above each axle (|y| > ~72, x = arch ±6) to get the arch-edge height, then set wheels.z so wheel z + tyre radius ≈ arch edge − a few cm for a stock gap. Shelby: arch 44, radius 32 → z 6 / rear 8 (from 24/26, the user: "pretty far up").
- **Ride height requests:** lower `wheels.z` / `rear_z` (the wheel mounts) raises the body; R34 went 24/26 → 20/22 → 17/19 on the user's two "a bit higher" requests.
- **Interior texture quality:** ProStreet interiors are 512 px. Spec `ai_upscale: [Tex_<CAR>_INTERIOR, _MISC, _BADGING, _ENGINE]` runs Real-ESRGAN x4plus (`~/tools/realesrgan/realesrgan-ncnn-vulkan.exe`, GPU, ~5 s, cached in ~/mt-work/ai_upscale_cache) → 2048 px, much sharper than Lanczos. build_car imports every texture with never_stream, lod_bias 0, mip gen Sharpen2. The user approved installing tools.
- **The car's own ProStreet engine sound (the user wants it, not a stand-in):**
  - Find it: caraudio.yml `<car>` → `ExhaustAudioNG` / `EngineAudioNG` → engineaudio_ng.yml `tmx_filename` (997tt: exhaust `car_042-exhaust.tmx` (por_911_a), engine `car_046-engine.tmx`). Files in `SOUND/ENGINE/`.
  - A TMX holds two `Gnsu20` granular blocks (split at the two "Gnsu" offsets; A = rising sweep, B = falling). Decode each with vgmstream (`~/tools/vgmstream/vgmstream-cli.exe`, r2117; EA-XAS ADPCM, 32/36 kHz mono). Header: minRPM, maxRPM (f32 at 8/12), 50, N, total samples, rate, then N+50 grain start samples. Each grain = one engine cycle: rpm = 120*rate/len.
  - `tools/gin_loops.py <block.gin> <block.wav> <prefix> 1600:idle 3500:mid 6500:high` builds seamless loops from the grains nearest each rpm (forward + backward, 24-sample crossfades) and prints the true recorded rpm of each.
  - `Scripts/import_sounds.py` (full editor; env PSCAR_SOUND_DIR, PSCAR_SOUND_DEST=/Game/Cars/Parts/Engine/Sound/<CAR>, run with `MSYS_NO_PATHCONV=1` or Git Bash turns /Game/... into a Windows path) imports them as looping SoundWaves.
  - Engine spec `sound_cue {cue_base: Cars/Parts/Engine/Sound/s58/SC_V8Engine, dir: <CAR>, pitch_rpm {idle, mid, high}}`: make_sound_cue clones More Tuning's S58 cue (RPM crossfade of idle/mid/high + RPM pitch modulators), repoints the waves and sets pitch = rpm/recorded rpm; make_engine swaps the engine's SoundCue import. pack_common also packs the cooked waves (Saved/Cooked/.../Engine/Sound/PS_*).
- **AWD (the user: build AWD cars AWD, never RWD):** Motor Town drive is per wheel (`DifferentialComponentName`, `LinkGearRatio -1` on the mirrored wheel). AWD game cars (Neo; Mitage/Muhan/Fox/EnfoGT/Raton) use DifferentialF/DifferentialR (+ centre). Spec `drivetrain: "awd"` → make_awd: the base's `Differential` (fed by Transmission) becomes the centre (LSDSlotName CenterLSD, index 1), new DifferentialF (FrontLSD, LinkGearRatio -1) and DifferentialR (RearLSD, index 2) = copies of its template export + SCS_Node (added to RootNodes/AllNodes and the CDO's dependencies) + class FObjectProperty; wheels 0/1 → F, 2/3 → R. Properties copied from the Neo (`~/mt-work/unpacked/.../Cars/Models/Neo`). The LSDSlotName text is a VehicleParts string-table entry: its TableId `/Game/DataAsset/StringTables/VehicleParts.VehicleParts` must be in the NameMap or UAssetGUI silently writes nothing (bisect by dropping changes).
- **Wings that carry their own engine lid (911):** every SPOILER* part includes the lid, so each wing row is complete and add_body_kits adds `UNIVERSAL_SPOILER_BASE` as "No Wing (Plain Engine Lid)". The game's universal wings show without a lid.
- **Layered dial clusters (911):** a flat back plate carries all dial art and separate raised dial faces (closer to the driver, own tilt) carry it again. `tools/uv_to_3d.py <mesh.json> <slot> u,row ...` lists every surface at a texture point: put needles on the FRONT-most face (per-dial tilt → per-socket roll). Fit gauge_faces to ProStreet's chrome bezels measured in a texture crop (centre, rx, ry → `aspect` = ry/rx).
- **Every car's Body must keep a `TailLight` slot.** With the 911's whole tail lamp moved into signal slots (no TailLight left) NO outside lamp worked in game (tail lights, front and rear blinkers), only the dash arrow: the game's lamp logic apparently needs TailLight.
- **Clear-lens indicators sharing one lamp face (911 tail):** the indicator is only a texture region on big triangles. Signal rule `copy: true, lift: 0.08` leaves the lamp in its slot (TailLight) and adds a copy lifted 0.8 mm along the normal into the signal slots; lamp kind `signal_overlay` = masked (opacity 2 x texture green², so only the clear section shows), amber TurnLight flash. (`signal_tail_tex` on the moved face is the version that broke the lamps.) Front: the bumper intake lamps (HEADLIGHT texture) by `box`.
- **Side mirrors on a Fortem base:** the components keep the Fortem's rotations (left yaw -11.85, right 20.71 with scale Y -1), which the recentred glass inherits. Don't guess: compute them. Take the glass normal (sum of the LeftSideMirror mesh's face normals, car space; for the right side mirror its Y because of scale Y -1), the desired normal n = unit(r - d) with d = eye→mirror and r = (-1, ±0.15 outward, -0.02), then search pitch/yaw (UE order: pitch in XZ, then yaw) so R·n_glass = n. 911: left (-8.4, 4.0, 0), right (-6.1, 7.8, 0). A ±7° guess made it worse (left saw sky, right saw the car).
  - Rotating the component also rotates the glass, which then cuts through the housing (the user saw "texture glitching through the mirror"). Bake the inverse into the glass: mesh option `counter_rotate {rot: [pitch, yaw, roll]}` (same values as the component). The right mirror needs a different counter-rotation, so give it its own mesh: spec mesh `RightSideMirror` (same source glass, `counter_rotate {rot: <right rotation>, mirror_frame: true}`, v = S R^-1 S g, a proper rotation so no winding swap) and `mirror_meshes {RightSideMirror_GEN_VARIABLE: RightSideMirror}` (make_mt_assets adds the Package + StaticMesh imports and repoints the component).
- **No turbo part in Motor Town:** engines have no boost property (EngineProperty = torque curve, inertia, MaxTorque, MaxRPM, friction, fuel, blip, afterfire), so a factory turbo lives in the torque curve. The user wants real-car power where ProStreet is low (911 Turbo: ~610 hp → MaxTorque scaled x1.513 to 797 N·m).
- **Vista base (the user's pick for the R34 Skyline):** like the Zino for paint (`Body_01`, `Window`), like the Magis for the dashboard (Dashboard_01 on the SteeringWheel socket; its DashboardMeshLocation (14,0,1) / pitch -15 get zeroed → `dashboard.parent_socket`). Door components LeftDoor/RightDoor (meshes Door_Left/Door_Right): give them the car's OWN doors as spec meshes `Door_Left` / `Door_Right` (DOOR_x + its front side window as Glass, `bbox_collision: true` → one box collision so the game can interact). Hiding them (hide_meshes) made the bought car impossible to get into. RHD: `blueprint.set_props {LeftDoor_GEN_VARIABLE: {DoorType: PassengerDoor}, RightDoor_GEN_VARIABLE: {DoorType: DriverDoor}}`.
  - The Vista's SteeringWheel component sets NO mesh, so the game shows its generic low-poly wheel (the user: "only use the interiors from ProStreet"). make_mt_assets now adds the /Game/Cars/Parts/SteeringWheels/<CAR> import and a StaticMesh property when the base has none.
  - Amber-texel signal rules can catch only a lamp's thin edge ring (R34 inner tail lamps: 47 edge-on tris, invisible flash). Check what a rule selected (y/z histogram of the slot) and use a `box` for the whole lamp when needed.
  - When a front indicator "doesn't glow", first ask which bumper is fitted: some ProStreet aftermarket bumpers have no lamp (R34, 2026-10-18).
  - Resolved: the R34's outside blinkers did get TurnLight (F6 log); the rear rule had caught only an edge ring. Earlier note kept for history:
  - Open (resolved): the R34's outside blinkers didn't flash (dash arrow did) although Body has TailLight + LeftSignalLight/RightSignalLight like the working cars; the Vista's BlinkerLight comps hang off HeadLight/TaliLight comps instead of Body. KoPDealer F6 now logs the driven ProStreet car's lamp slots with TurnLight/BrakeLight/HeadLight values (MIDs only). Never read raw struct properties like `Net_Parts` in UE4SS Lua: it crashed the game with an access violation inside UE4SS (pcall can't catch it); use UFunction calls only.
  - The Vista's skin list (BodyMaterialList, 38 entries) holds ONLY PolygonStreetRacer liveries, so keep_body_materials 1 kept a livery ("messed up paint"). `blueprint.body_material: /Game/Cars/Materials/Body/M_Body` adds the import and makes entry 0 the paintable M_Body. Check every new base's entry 0. One `SideMirror` mesh (right component scale Y -1, MirrorType SideRight) → mirror_components SideMirror / SideMirror:mirror, plus the computed rotations, counter_rotate and an own RightSideMirror mesh. Big kit list (Bonnet/Bumpers/Fenders/SideSkirt/RearWing _01.._04) is replaced by our KIT00 defaults.
- **Right-hand drive (JDM cars like the R34):** keep it authentic: DriverSeat at +y, PassengerSeat1 at -y, cockpit camera and SteeringWheel socket on +y, mirror aims computed from that eye. The seat interaction spheres are attached to the seats, so they move with them.
- **Rotated dial art (R34):** the cluster is drawn diagonally in the texture. Map u/row axes onto the dash with uv_to_3d (points 0.01 apart) to get the texture's in-plane rotation (R34: image "right" = 52.5° counter-clockwise from the dash's right), then `rotate` on each gauge_faces entry. Measure bezel centres from a zoomed crop before drawing; the first guess was off by 0.01 u. The cluster may be a few huge triangles: size `uv_split` to their full UV extent or the Gauges slot (glow) stays empty.
- **More Tuning engines that match the real car (the user points them out):** RB26DET276HP for the R34, 2JZ320HP for the Supra; real-car power when ProStreet's is lower (R34: factory 392 N·m / 280 PS).
- **Tuscan base (the user's pick for the '67 Shelby GT500):** Zino-like: own Dashboard in car space (DashboardAttachSocketName None → no parent_socket), mirror meshes SideMirror_L / SideMirror_R (mirror_sockets, aimed from the eye), no door components, 4 seats (PassengerSeat2/3 at the rear), paint Body_01 (+ Body_02 second colour), skin 0 = M_Body. Its SteeringWheel uses the shared GenCoupe wheel → our steering-wheel step replaces it. No Wheels row named "Tuscan": spec `base_wheel: Vista` for the rim row template. Cars with only a driver's mirror (real '67): hide the other with `hide_meshes ["SideMirror_R"]`.
- **Exact factory power (the user: "make sure to match the hp"):** take ProStreet's TORQUE shape and set max_torque_nm to the factory torque; check hp = T·rpm/7121 at the quoted rpm (Shelby: 569.4 N·m → 355 hp @ 5448).
- **Lamp slot names follow the BASE car's body:** the Tuscan's body uses `LeftTailLight` / `RightTailLight` (+ `Headlight`) and our plain TailLight didn't glow on the Shelby. Check the base Body's NameMap for its lamp slot names and give the car those (side split via a signal-style rule with its own tag, lamp kind `tail`), keeping a sliver as TailLight.
- **Painted stripes (Shelby Le Mans stripes are ProStreet vinyls, not in the body texture):** spec `stripes {from: Paint, to: Paint2, bands: [[5,29],[-29,-5]], max_abs_ny: 0.75}` cuts every paint triangle (body AND aero parts) along y-planes and moves the bands to slot Paint2 → final name `Body_02`, the base's second colour picker (Tuscan ColorSlots Body_01/Body_02).
- **Reusing a finished car as the template (the user: "use the Shelby we just made as the base"):** same base vehicle (Tuscan) and the same spec patterns (lamp names, stripes, red rear signals, arch-gap stance); only geometry, textures, measurements and performance change. Stance: keep the confirmed tyre-to-arch gap (Shelby arch 44 → z 6; Challenger arch 41/43 → z 3 / rear 7).
- **Side stripes (R/T strobe stripe):** `stripes` entries can be a list; `axis: 2` cuts z bands, `min_abs_ny: 0.6` keeps side-facing faces, `x_range` limits the length (Challenger z 62-69, x -175..230).
- **Rotated + stretched dial art:** combine `rotate` and `aspect` on gauge_faces (aspect is applied before the rotation). Challenger: art turned 90° (u → -z, row → -y), 126 vs 172 cm per unit → rotate 90, aspect 1.365 (stretch rows before rotating).
- **3-speed automatics:** clone the game's TQ4SpeedMuscle (row `302`) with transmission `drop_gears: ["4"]` (make_transmission removes the gear). The forklift 3-speed has three reverse gears: don't use it.
- **Red US rear turn signals (classic American cars):** lamp kind `signal_tail_red` (same as signal_tail, red TurnLight tint); outer tail-lamp segment as the blinker, inner stays TailLight.
- **Never end a part/asset/row name with `_<digits>`** (e.g. PS_SHELBY67_428): Unreal parses it as an FName number, the base name isn't in the NameMap and UAssetGUI silently writes nothing. Use PS_SHELBY67_FE428.
- **Gearbox mass:** gearbox rows cloned from a game row keep its mass (LP670: 130 kg). Set `mass` in custom_parts.transmissions (ours: 100) so the body_mass maths (ProStreet MASS − engine − gearbox − radiator − LSD − tyres − rims) holds.
- **Car flickers or vanishes at the dealer:** the body has no collision. Check that the cooked Body JSON has AggGeom/BoxElems.
- **Car looks like the base car:** the copied vehicle row's Parts fit the base car's body kit and rims over ours.
- **"Glass" or see-through body, blotchy paint:** the triangle winding is inverted. The OBJ faces must agree with the normals; ps_to_mt writes a, a+2, a+1.
- **Wheel component scale (game rims were "massive" on every port, 2026-10-19):** the game's wheel meshes are modelled ~50 cm in radius (Zino_L ExtendedBounds 49.8) and each car shrinks them with the Wheel0-3 RelativeScale3D (Zino 0.61, Tuscan 0.595, Fortem 0.62, Magis 0.647, Cora 0.665, Vista 0.7). make_mt_assets used to force scale 1, so game rims showed at ~50 cm. Now all ports use `WHEEL_MESH_SCALE` 0.6466 (32.2/49.8; spec `wheel_mesh_scale` overrides) and ps_to_mt enlarges every `Wheel_*` mesh by 1/scale (car stock wheels AND the PS/MW rim packs), so our wheels keep their size and game rims fit. Keep the two constants equal; any new wheel mesh must be named `Wheel_*`.
- **Wheels:** a Motor Town wheel mesh includes the tyre. The rim comes from a Wheel part row (Left/RightWheelMesh). If the rim face points inboard, swap the L/R meshes.
- **Character head through the roof:** the seats are at the base car's height. Also move RoomMirror and the dome light slots below the new roof.
- **Ride height:** springs (SpringLength 9/11) compress about 8 cm, so mount the wheels about 8 cm below the true axle height. The Zino's rear springs are 2 cm longer, so mount the rear 2 cm higher (`wheels.rear_z`), or the rear wheel hangs low in its arch.
- **Wheel fore/aft position (fitment):** don't guess `front_x`/`rear_x`. Measure the arch openings in the body mesh: for z bands 20–30 cm, find the largest gap in the outer-skin vertices (|y| > 78) around each axle, and use the gap centre. 350Z: front 136.2, rear −129.6 (the first guess of −132 sat 2.4 cm back and looked off). `rear_half_track` is available if the rear track differs. ProStreet front and rear wheel models are identical.
- **M_Gray (Trim) shows orange accents on some UVs:** use Bottom for black parts.
- **Never use M_Mirror (`Mirror` slot) for chrome:** it is the mirrors' reflection material and renders self-lit white, so trim, seams and mirror housings glowed at night. Use Trim (grey metal) or Bottom instead.
  - A source car often reuses one generic chrome texture code across parts (350Z: 0xBF30889B for both the mirror housings and the headlight bowls). Fix per mesh with `slot_rename`, e.g. SideMirror_* {Trim: Paint} for body-coloured housings.
- **Boot crash from the composite tables (2026-10-19, cost an afternoon):** patch_composite copies our parent tables' rows into the cooked VehicleParts / Vehicles composite, but rows carry object references as **import indices of their source package**. Copied raw, they pointed at unrelated imports of the composite. That stayed harmless until our tables had more imports than the composite (389 aero rows after the wing pack + MW parts): out-of-range indices then crashed the game ~10 s into boot (access violation at MotorTown-Win64-Shipping.exe+15d2015; mods only load after the in-game approval and a restart, so "it crashes every time after accepting mods"). Fix: `remap_imports()` re-creates each referenced import (with its outer chain) in the composite and rewrites the index. Bisect boot crashes per pak with the scratch `paktest.ps1` approach: CustomPak.ini `[CustomPakAccepted]` lines are `path|size|mtime as .NET UTC ticks (seconds precision)` and `[CustomPakBootSentinel]` disables mods after a crashed boot, so reset both.
- **UAssetGUI fromjson silently writes NOTHING when the JSON is invalid** (e.g. an FName value missing from the NameMap, such as new part keys in a row). make_mt_assets.fromjson now raises if the file wasn't (re)written, and make_table registers every part_overrides value. A stale earlier output hid this for hours.
- **Spec paths may use `~/`:** ps_to_mt expands geometry_dir/out_dir/texture_dir. Unexpanded, every part looked "missing" and meshes came out empty.
- **UAssetGUI tojson silently fails on huge maps:** use mappatch (UAssetAPI) instead. A round trip is byte-identical.
- **Outdated table mods crash the game:** "LowLevelFatalError ContainerHelpers.cpp:8" (invalid array size). Test each mod's assets: `mappatch info <uasset> <usmap>`, where raw>0 means outdated. FormulaUnlocked (Nov 2025) is outdated; Maja's Motor Works is a requirement of More Tuning, and More Tuning's tables are a superset of it.
- **Debugging in game:** the UE4SS mod `KoPDealer` (`ue4ss/Mods/KoPDealer/Scripts/main.lua`) is our swappable inspector; its output goes to `ue4ss/UE4SS.log`, and UE4SS mods load only on game start. Past versions are saved in `ps2motortown/dealers/KoPDealer_main_v*.lua`:
  - v1: dealer swap (F7)
  - v2: actor watcher (APPEAR/VANISH, position, velocity)
  - v3: mirror captures
  - current: F6 = each PS_350Z's Net_Parts plus engine data, torque, rpm and sound. Change the class name for other cars.
- **Reading game classes:** `python313 ~/mt-work/usmap.py`; `usmap.load(path)[ClassName]` = (super, [(prop, type)]). Example: MTEngineComponent.EngineData, MTVehicle.Net_Parts.

## Working with the user
- Begin replies with "Start here".
- Do the technical work yourself. Ask the user only to launch the game, take screenshots, log in to sites, or approve permission prompts.
- Their keyboard has no Insert key.
- Judge each fix from their screenshots. Render meshes offline when the in-game look is unclear: re-export from the editor with StaticMeshExporterOBJ.

## Side decals (stock vinyls) and widebody gaps (Challenger, 2026-10-18)
- **ProStreet stock vinyls aren't textures.** `CARS/<CAR>/VINYLS.BIN` only holds the vinyl UV template (`<CAR>_DEBUG`, left/right/top/front/rear planar projections). `CARS/VINYLS/LIVERYTEXTURES.BIN` holds full race liveries (`<CAR>_DRAG/SPEED/...`, 1024², exportable with AssetDumper). The manufacturer stripes (e.g. the '71 R/T strobe) are vector vinyls in `CARS/VINYLS/VINYLS.BIN`, which AssetDumper can't read. Recreate them from the user's ProStreet showroom screenshot.
- **Don't use a flat z band** (`stripes` axis 2) for a side stripe on a car whose beltline drops toward the front: the band slides off the fender top and shows as a thin sliver. `stripes` now takes `profile [[x, dz], ...]` (band shifted per x), but for anything shaped use decals.
- **Spec `decals`:** `[{from: Paint, to: Paint2, min_side_ny: 0.35, left: [polys], right: [polys]}]`. The polygons are in side view (x, z). left = y < 0, right = y > 0; keep them separate so lettering reads on both sides (mirror the glyph order). ps_to_mt cuts side-facing paint triangles along the edges of the polygons that overlap them (only edges near the triangle) and moves the inside pieces to Paint2 → Body_02 (the user's second colour). It runs on every mesh, aero kits included.
- Generate the polygons with a per-car script next to the spec: `cars/challenger71_strobe.py`. It holds the measured beltline, the line offsets and thicknesses, the kick, and italic block glyphs. Measure the beltline as the top of the side-facing paint (|ny| > 0.5) per 10 cm of x from the raw KIT00 BODY/FENDER/DOOR DAEs.
- **Widebody holes:** the W01 shell keeps only triangles that differ from the stock body plus doors, so shell triangles lying within ~1 cm of a stock door edge get dropped. The KIT00 skirt fills that strip on the stock car, but the shorter W01 skirt doesn't, so a hole shows behind the door bottom. Fix with spec `widebody_keep_boxes [[x0,y0,z0,x1,y1,z1], ...]` (both sides). add_body_kits puts it on the WIDEBODY shell's drop_coincident_with as `keep_boxes`, shell only, not the W01 doors. Find the hole by rendering Body + W01 rear/skirt in side view around the door rear bottom.
- **Cutter rule (stripes and decals):** when splitting a polygon by a plane or line, a vertex exactly on it (|f| < 1e-6) must go to BOTH pieces. Drop pieces that lie entirely on the line. Before this fix, an on-line vertex went to only one side, so the other piece lost a corner. The polygons kept their total area but turned degenerate, leaving visible gaps in the paint (the Challenger's widebody fender front between the stripe lines). After converting, check for zero-area triangles in the decaled meshes.
- **Decal line quality:** side projection stretches a band on the rounded shoulder under the window (normal |ny| < 0.85), so put pinstripes ≥3 cm below the side-paint top, where the panel is near vertical. Smooth the measured beltline (moving average over ±12 cm), ease kicks in with a parabola (KICK_R) instead of a corner, and sample the lines every 2 cm. Challenger final: thin 1.4 cm, gap 1.7, thick 3.4; R/T ×1.45, stepped down toward the back (DROP 0.42), lines ending into the letters.
- **Front signals per bumper:** check EVERY front bumper kit for amber lamp texels (sample the texture colour at each triangle's UV centroid). Lamps sit at different heights per kit: the Challenger widebody's is at z 0-5, while stock is at 15-25. Some aftermarket bumpers (Challenger KIT08/09, R34) have no lamp at all; tell the user so it isn't reported as a bug.

## Chevelle SS 454 '70 (Tuscan, from the Challenger spec, 2026-10-18)
- **Cloning a finished car:** take the current spec (all later fixes) but the Body parts list from `<car>.before_kits.json`. Drop aero meshes/aero_parts/aero part_overrides/decals/stripes/widebody_keep_boxes, rename the prefix, and re-map only the car's own texture hashes (the shared ProStreet hashes — paint 0x65FF171E, the Bottom/Trim codes — are the same on every car). Then re-measure everything that depends on geometry before add_body_kits.
- **Re-measure list:** mirror glass group (Chevelle group 2, rear-facing chrome hash, nx −1; Challenger was 3); seat offsets (relative to the steering wheel and the floor height: interior-texture faces with nz > 0.7 under the driver); steering ring (front-view render of BASE, x 0–60); dash dials (texture crop → uv_to_3d, points 0.01 apart for the axes); room-mirror drop box (interior-textured faces at x 0–40, |y| < 16, z 85–112); lamps (front-view render in texture colours); arch edges; trunk top; exhaust tips.
- The ProStreet `DRIVER` part is in its own local frame (identical in every car), so it can't place seats.
- **Signal rule `cuts: [[axis, value], ...]`** splits the source slot along planes before the box test. Use it when a lamp face is a few big triangles (Chevelle tail lamp: outer half |y| > 74.6 → red US blinker, 66–74.6 → Left/RightTailLight, |y| < 66 sliver stays TailLight).
- **Amber surveys catch emblems:** the red/orange "SS 454" fender emblem (BADGING) passed the amber test. Check the position against the real car before turning a hit into a blinker. Bumper chrome can sit inside a corner box: print the texel colour of the triangles a rule caught.
- **Chevelle values:** LS6 450 bhp @ 5600 / 678 N·m @ 3600, MaxRPM 6500, More Tuning 81bb sound, Muncie M22 (R −2.26, 2.20/1.64/1.27/1.00), FD row "104" = 3.73 (FinalDriveRatio rows: 101 2.73, 102 3.08, FD_3.31, 103 3.55, 104 3.73, 105 4.00, 112 4.11, 111 4.27). Dials: tach u .1465/row .111, speedo .2305/.108 (rotate 0, aspect 1.42, roll −99 for a panel normal z −0.157); fuel/temp in the two blank rings right of the clock. Stance z 7 / rear 9 (arch edges 44 / 44.2, kept the Challenger's gaps). body_mass 1174 (ProStreet MASS 1600).
- **Steering wheel invisible in game = no Body socket `SteeringWheel`.** The Chevelle clone dropped it from sockets.Body, and extract only updated an existing socket. ps_to_mt now adds the socket when it's missing. After converting, check that `sockets.Body` has SteeringWheel at the printed pivot.
- **Stripes `meshes: [prefixes]`** limits an entry to some meshes (Chevelle hood stripes → Aero_Bonnet, trunk stripes → Body). Without it, bumper tops inside x_range got stripes. Chevelle '70 SS stripes: two 21 cm bands at |y| 6–27 on top of the hood dome (|y| < 30) and on the trunk lid, max_abs_ny 0.75, on Body_02.
- **Decals `projection: "top"`** (bonnet/trunk stripes): `polys` in top view (x, y), serving both sides; triangles with nz ≥ `min_up_nz` (0.2) are cut; `meshes` prefixes limit it (Body + Aero_Bonnet). Use it instead of `stripes` when the stripes have outlines or shaped ends. Generator `cars/chevelle_stripes.py`: per-side stripe quads plus pinstripe rings built from per-edge offset strips (gap 1.2, width 0.6). Chevelle (traced from ProStreet): stripes |y| 5.4–43; hood x 82 → 230 inner / 217 outer (the pointed nose, 8 cm back); trunk −178 → −236.
- **Top-view render checks:** draw only faces with nz > 0.05, sorted by centroid z. Otherwise underside panels paint over the stripes and fake a gap.
- **Flickering chrome lips (Chevelle wheel arches):** trim facing mostly down (normal y ≈ 0.58), tucked under an overhanging panel, sits in its shadow and looks patchy in game, even though the mesh is continuous, correctly wound, not covered and not duplicated (check all four before blaming lighting). Spec `surface_tweaks [{from: <slot>, box: [x0,|y|0,z0,x1,|y|1,z1], lift: 0.25, normal_blend: 0.6}]` lifts those triangles outward along ±y and turns their shading normals outward. Chevelle: both arch rings, MISC.

## Viper SRT-10 (Tuscan, from the Shelby spec, 2026-10-18)
- **Using a More Tuning engine as-is (the user: "we do not need to add an engine"):** `part_overrides.Engine` = the More Tuning row (V10ACR = "Dodge V10 645HP"; V10ACRt = "Dodge V10 Tuned 720HP") plus `default_engine: /Game/Cars/Parts/Engine/V10ACR`, and `custom_parts.engines: []`. Find rows and labels in More Tuning's `DataAsset/VehicleParts/Engines` (repak get from qxZap_MoreTuning_P.pak → tojson → search the row JSON for the label). Read power from the engine asset: MaxTorque/1e4 N·m, MaxRPM, its TorqueCurve keys (V10ACR uses the game's TorqueCurve_V12 → 1009 N·m peak, ~635 hp at 6400). The car then depends on More Tuning (accepted).
- **Two-seat car on the 4-seat Tuscan:** put PassengerSeat2/3 on the front seats.
- **Side exhausts:** Exhaust_Left/Right sockets at the side pipes, yaw ∓90.
- **Mirror glass with a dark backing copy** (Viper groups 2 = 027FF2DC and 3 = MISC, same surface): glass = group 3; skip both on the housing.
- **Front signal inside the headlamp texture:** a signal rule with `uv_box` on the HEADLIGHT_ON slot (Viper amber block u .04–.245, rows 0–.47). Find the block by scanning the texture for amber texels.
- **Low flared arches:** the outer fender lip (|y| ≈ 90) sits beside the tyre, below its top. The arch-gap rule then gives a high mount (Viper z 20.5 / rear 25 from lips 57.3 / 59.7). Confirm in game first.
- Viper values: T56 R −2.9, 2.66/1.78/1.30/1.00/0.74/0.50, FD row 102 (3.08 ≈ 3.07), body_mass 983 (MASS 1542). Dials: tach (.4761,.9204), speedo (.5945,.951), fuel (.3797,.940), all roll −69.9 (panel nz .343); temp in the centre stack (.7715,.0983) roll −76.2. Steering wheel (−18.4,−39.1,63.8) r 16.5; eye (−78,−39,87); room mirror (−4,0,95) aim (3.7,13.9).
- **Full-length stripes (Viper):** use `stripes` (y bands, max_abs_ny 0.6, no meshes filter) when they wrap the vertical nose and tail; top-projected decals skip vertical faces. Scale stripe widths from a known object in the screenshot (US licence plate 30.5 cm), not the silhouette, which perspective distorts.
- **Wider / staggered wheels (Viper 275 F / 345 R):** per-part `scale [sx, sy, sz]` in ps_to_mt scales about the part origin + offset. With the wheel offset ±11 the outer face stays fixed and the tyre grows inward. Spec meshes `Wheel_RL` / `Wheel_RR` (WHEEL_TIRE_REAR, scale y 1.45; mesh_names → `<CAR>_REAR_R` / `_L`, same L/R swap) plus `rear_wheel_meshes: true`: add_rim fills the wheel row's `RearLeftWheelMesh` / `RearRightWheelMesh` (fields every Wheel row has), so one rim part shows different rears. pack_car already packs Wheels/<car>_*. Track: outer face = half_track + 11; put it ~1.5 cm inside the fender lip (Viper lips 91.9 / 95.4 → half_track 79.5 / rear 83).
- **Traction:** the base game's best car tyre is PerformanceTire_46. More Tuning adds PerformanceTire_30 (Street), _25 (SuperStreet), _15 (Sport Performance), DragTire (Track), DragTireStrip, RallyTire, Sideway (drift). They're rows in More Tuning's VehicleParts0. Viper: PerformanceTire_15 on all four (the user wanted a lot more grip for More Tuning's 1009 N·m V10).
- Changing default parts → rename the dealer spot (Viper v1 → v2) so the display car respawns with them.

## NFS Most Wanted (2005) / Most Wanted Rework IV → Motor Town (started 2026-10-18)
- **Source:** the user's install `D:\SSD GANG\Need for Speed - Most Wanted Rework IV` (fan overhaul of MW 2005; ~115 drivable cars in CARS/<CAR>/GEOMETRY.BIN, TEXTURES.BIN, VINYLS.BIN). Same Black Box engine family as ProStreet, so the pipeline carries over. Personal use only (Rework includes community models); never publish.
- **Export:** `AssetDumper.exe export <BIN> -g MostWanted -o <dir>` works for GEOMETRY, TEXTURES and VINYLS.
- **Scale:** MW DAEs are 10× larger than ProStreet's. Spec `source_scale: 100` (ProStreet default 1000); ps_to_mt.build sets the module PS_SCALE from it. Scripts calling P.to_mt directly must set `P.PS_SCALE = 100.0`.
- **Part names differ:** file prefix is just the car (`BMWM3GTR_<PART>_A.dae`). Stock parts are `KIT00_BODY` (whole body incl. bumpers), `BASE`, `KIT00_HOOD`, `KIT00_INTERIOR`, `KIT00_ATTACHMENTn`, `KIT00_FRONT_WINDOW` / `REAR_WINDOW` / `FRONT_LEFT_WINDOW`…, `KIT00_LEFT_HEADLIGHT(_GLASS)` and `KIT00_LEFT_BRAKELIGHT(_GLASS)` (these "LEFT" parts hold BOTH sides on the M3 GTR), `KIT00_LEFT_SIDE_MIRROR` (both sides), `KIT00_SPOILER`, `KIT00_FRONT_TIRE` (tyre + rim), `KIT00_FRONT_BRAKE`, `KIT00_DRIVER`. Body kits are WHOLE bodies `KIT01_BODY … KIT06_BODY` (→ the widebody-style drop_coincident approach). `STYLEnn_*` are aftermarket hoods/spoilers/rims/lights; `DAMAGE0_*` and `DECAL_*` are ignored.
- **ATTACHMENTn meanings vary per car; render them.** M3 GTR: 0/1 = seats, 2 = the 3D steering wheel, 4 = rear add-on, 9 = long body add-on.
- **Texture names in the dump can be misleading:** the M3 GTR interior atlas is `0x5CC81B3D_*_DRIVER.dds`, while `*_INTERIOR.dds` is a different variant. Map by hash after looking at each texture. Material hashes shared with ProStreet: 0x7B220DDF (window glass), 0xD195BE56 (rear glass), 0xCC772AFB, 0xBF30889B (chrome), 0x4E8CF857 (driver).
- **Interiors:** every car has KIT00_INTERIOR plus an interior atlas with dials and a wheel. Detail varies widely (M3 GTR 564 interior tris; Rework-upgraded cars 1–7k).
- **Performance:** unpack GLOBAL attributes.bin / gameplay.bin / FE_ATTRIB.bin with `~/tools/attribulator/patched/Attribulator.CLI.exe unpack -i <dir> -o ~/nfs-work/mw_vlt -p MOST_WANTED -f yml`.
  - engine.yml `<car>`: TORQUE = 9 values in lb-ft (the 997S peak 295 = real), evenly spaced idle → MAX_RPM; also RED_LINE.
  - transmission.yml: GEAR_RATIO [R, N, 1..n], FINAL_GEAR.
  - pvehicle.yml: MASS, plus the engineaudio CollectionKey → engineaudio.yml Filename_GinsuAccel / GinsuDecel (.gin in SOUND/ENGINE, same granular format as ProStreet → gin_loops.py), MinRPM / MaxRPM.
  - M3 GTR: 283 lb-ft peak, ~412 hp @ 9500 (redline 8500), 6-speed 3.40/2.085/1.50/1.25/1.09/0.91, R 3.79, FD 3.85, 1350 kg, wheelbase 2.725, sound GIN_AC_BMW(.gin/_DCL).
- **Vinyls are textures** in MW (VINYLS.BIN → hundreds of per-car masks and liveries), unlike ProStreet's vector vinyls.
- **MW body kits: `tools/add_body_kits_mw.py cars/<spec>.json`** (back up the spec first; spec `mw_kits {front_split, rear_split}`). Every whole body KITnn_BODY is cut by x planes. FrontBumper = x > front_split (ahead of the front arch), RearBumper = x < rear_split. SideSkirt (kits ≥ 01) = the middle minus whatever lies on KIT00_BODY (drop_coincident_with). Body keeps KIT00_BODY's middle via x_range. Bonnet = KIT00_HOOD + every STYLEnn_HOOD. RearWing = KIT00_SPOILER (stock) + STYLEnn_SPOILER(_CF), offset −RearWing socket. M3 GTR: splits 196 / −150 → 44 parts (7 bodies, 19 hoods, 3 wings).
- **Renders:** `tools/render_car.py <build_dir> <out.png> [mesh,list]` draws side/front/rear in texture colours (KIT00 aero by default). It doesn't apply the RearWing socket, so wings don't show.
- **MW lamps (M3 GTR):** the headlamp texture's right third (u .67–1) is the amber corner indicator (uv_box). The tail atlas has the outer lamps' round turn section at rows .37–.59 (u .5–1 → `signal_tail`), the upper outer lamp at rows .05–.37 and the inner lid lamps at rows .57–.8 → Left/RightTailLight, and the third brake light stays TailLight. The BRAKELIGHT part's group 1 is a flat lens layer: skip it.
- **MW wheels:** KIT00_FRONT_TIRE = rim (r 25) + tyre (r 33) on one rim texture; same y layout as ProStreet (−23..0), so the offset ±11 convention works. Mirror glass = LEFT_SIDE_MIRROR group 1 (both sides): split per side with mesh drop_boxes on y.
- **MW sound:** `vgmstream-cli -o x.wav GIN_x.gin`, then `gin_loops.py` as for ProStreet. Pick rpms inside the header range (M3 GTR 2659–8672 → 2600/4800/6600 → recorded 2695/4790/6650). pack_common now also packs Engine/Sound/MW_*. The M3 GTR import also brought in the full GIN wav: harmless.
- **Rework-added models can be laid out differently (993 RWB):** most geometry is in BASE (17.5k tris) and KIT00_INTERIOR (20k), with few KIT00_* parts. Some part files lack the car prefix (`KIT00_RIGHT_HEADLIGHT_A.dae`), and car names may start with digits. List the files before assuming the M3 GTR layout; split BASE by texture/region (groups, boxes) instead of by part name.
- **993 RWB (Rework model, misnamed parts):** render every part on its own before mapping. BASE = shell + headlamps; KIT00_BODY = RWB flares/sills (bumpers stay in BASE, so the MW kit bodies are only subtle variants); KIT00_HOOD = the REAR engine lid with the ducktail (the Bonnet slot on rear-engined cars); KIT00_FRONT_WINDOW = the 20k-tri cockpit + all glass; KIT00_REAR_WINDOW = the tail bar; `KIT00_RIGHT_HEADLIGHT_A.dae` (no car prefix → copy it to `993RWB_KIT00_RIGHT_HEADLIGHT_A.dae`) = window seals. Mirror glass = BASE group 4.
- **Additive MW decal atlases (993 crest/RWB atlas 0x3B904E9A, fully opaque, black = no effect):** drawn opaque they turn panels black. Spec `overlay_textures {hash: {base: Paint, slot: Tex_<X>_DECALS, parts: [...], lift: 0.05}}`: those groups render as the base slot plus a lifted copy in a masked overlay slot. `alpha_from_luma: [slot]` makes write_textures derive opacity from brightness. Add the slot to masked_texture_slots and texture_sources, plus a dummy texture_slots entry so it gets exported. Outside the listed parts (seals, interior) map the hash to Bottom. render_car.py honours alpha.
- **Lamp lens material without a car texture (993 0x02B52399):** it samples the car's lamp atlas at runtime. Map it to that atlas (0x9C85D2CC = unlit; 0xD63299CE = lit-brake copy) and split the lamps by position boxes: front bumper indicators, fender repeaters, outer tail-bar ends = amber signals (Euro); the bar's inner sections = Left/RightTailLight; the centre reflector (left half only, `_X`) = the TailLight sliver; the headlamps keep the atlas slot = HeadLight.
- **Gauges in reverse:** when the dial art is scattered in an atlas, find the pod centres in a front render, read the UV of the front-most face under each (barycentric), mark them on the texture, then pick the true dial centres in the art and map them back with uv_to_3d. 993: speedo (.234,.254), tach (.771,.23), fuel (.156,.68), oil temp (.518,.60); ~15 cm per texture unit, upright, roll −77.5. The atlas also textures the whole interior, so uv_split covers most of it (dark texels don't glow).
- **Engine sound choice:** Rework gives the 993 RWB `hon_s2k_b` (a Honda S2000 sound!). Use the period-correct GIN_964 (air-cooled flat-6) instead. Its range is 3470–9471, so cut loops inside it (3550/5300/7300); a target below the range picks a stray grain (660 rpm).
- 993 values: MW torque ×1.05 (induction HIGH_BOOST) → 566.6 N·m peak, ~400 hp at 7500; gears R 3.35, 3.82/2.05/1.41/1.12/0.92/0.75, FD_3.31 (MW 3.38); 1295 kg → body_mass 849; wheels radius 38.4, z 10/14, half_track 73.7 / rear 80.3, rears ×1.25 wide; wheel pivot (26.9,−30.6,67.9) (6404-tri wheel); eye (−32,−30.6,93); room mirror (18,0,106) aim (7.4,15.5); kit splits 158 / −146 → 35 parts.
- **Engine loops MUST be named exactly `idle.wav` / `mid.wav` / `high.wav`.** make_sound_cue only swaps the S58 cue's folder path, so the wave names have to match the S58 ones. gin_loops' `<prefix>_idle.wav` names imported as-is made the M3 GTR and 993 RWB silent in game. Copy the loops to idle/mid/high in a separate import folder, and import only those three (not the full GIN wav).
- **M3 GTR first in-game feedback (2026-10-18), and the fixes:**
  - Headlamp blinker lit the whole lamp: the housing (124 tris) samples a single texel column at u .98–.99, inside the "amber third" uv_box. Restrict uv_box to u .67–.975 plus a position box on the outer corner (|y| 58–80) → 37 tris/side. Check what a uv_box catches per group (u histogram by position) before building.
  - Tail blinker = only the white/clear sections of the outer (quarter) lamps: a signal rule with `copy: true, lift 0.08` on the outer lamps + lamp kind `signal_overlay` (masked by texture green²). All tail lamps stay Left/RightTailLight.
  - "Car looks outlined on each panel": the MW panel-seam strips 0xCC772AFB were mapped Bottom (black). Map them to Paint on MW cars.
  - Sports-car stance: the user wants the tyres tucked close under the arches (gap ~1 cm, not the muscle-car 3–5 cm): M3 GTR z 20 / rear 22 (arches 52.9/53.1, r 33).
  - Steering wheel hid the dials: extract option `socket_offset [dx,dy,dz]` moves the mount (M3 −6 cm z) and the eye went up 2 cm (101). Check the sightline eye → dial centre clears the rim top at the wheel's x.
  - Dealer rows: line cars up from an existing bay: loc + N×350 cm along its right vector (yaw + 90), same yaw (M3 v2, 993 next to the Viper).
- **Choose the base by lamp logic too (round-2 feedback):** the Tuscan's tail slots LeftTailLight/RightTailLight double as blinkers (US style: the whole tail lamp flashed on the European M3), and plain TailLight doesn't glow there. European cars → a base with separate TailLight + Left/RightSignalLight:
  - **Cora** (the user's pick for the M3 GTR): body slots TailLight, Left/RightSignalLight, TailSideMarkerLight, ReverseLight, Body_01, Window; no door components; a shared `SideMirror` mesh with Left/RightSideMirror components (right at scale Y −1) → spec mesh `SideMirror` (recenter, counter_rotate) + `RightSideMirror` + mirror_components/mirror_meshes; Dashboard_01 on the SteeringWheel socket (DashboardMeshLocation (10,0,2.5), pitch −10) → `dashboard.parent_socket`; wheels at z 33 on 9 cm springs front AND rear (no +2 rear); no Wheels row → base_wheel Vista.
  - **Fortem** (the user's pick for the 993 RWB, as for the 997): Paint→Body, Glass→Windows; mesh `LeftSideMirror`; 2 seats; RWD unless drivetrain awd.
  - Zino works too (TailLight + signals) but needs door meshes: mesh option `keep_boxes` carves Door_L/R from a one-piece body (+ the same boxes in Body drop_boxes, bbox_collision). Not used in the end.
- **`tools/fortem_mirror_aim.py <spec> <part> <group> [scale]`** computes the left/right component rotations for shared-mesh mirrors (Fortem/Magis/Cora). It reproduces the 997's −8.4/4.0 and −6.1/7.8 (the right yaw sign flips under scale Y −1). Use the same values for counter_rotate.
- **Stance reference per base** (tyre top above the arch-lip line at rest, i.e. z + r − arch): Zino 350Z +1.9; Fortem 997 +3.8 front / +4.9 rear; Tuscan muscle cars −4.8…−6 (higher). For a lower sports stance add ~1 cm.
- **Other round-2 fixes:**
  - extract `scale` (the M3 wheel ×1.12: MW wheels read small) and `socket_offset`;
  - the MFD strip above the dials (up +5.5, 6×1.5 cm) when the wheel hides the lower area;
  - user-picked More Tuning sound = drop sound_cue and keep base_asset (S58);
  - 993 wheels ×0.87 (MW's r 38.4 looked huge → 33.4);
  - the 993's dial glass layer 0xC2184967 (gauge art + alpha) covered the faces: drop it (texture_slots → a slot in drop_slots);
  - the headlamp cover 0x7AB9C92B (a 4×4 flat colour) is glass, not trim;
  - front indicators: uv_box to the amber block only;
  - **`slot_boxes [{from, to, box}]`** moves a slot's triangles in a box to another slot without a side split (993: the whole tail bar → Lamp_Tail = TailLight).
- **`tools/ue_build.sh <BUILD>`** wraps the hidden-editor mesh build and retries the sporadic exit 127 (the editor never launched; empty log). It hit the Chevelle and the M3 when the build ran right after another command in a chain. Always check the exit code before cooking.
- **MW rim pack: `tools/mw_rims.py cars/mw_rims.json`** (kind rims, car MW_Rims). CARS/WHEELS = 41 branded designs (5Zigen, ADR, BBS, Enkei, Konig, Lowenhart, OZ, Racing Hart, Roja, Volk) × 17–20". It uses the 18" files. Same wheel frame as ProStreet (tyre 0xE4CEA024, r 32, y −22.4..0, offset ±11.5); textures by hash (Tex_MWR_<design>). The ps_to_mt part path is prefix_part_lod, so prefix = design, part = "18_25" (an empty prefix gives "_name" → empty meshes). Add cars/mw_rims.json to the make_mt_assets list and pack it with pack_car.
- **Shared packs exported to ~/nfs-work/packs:** PS SPOILER (591 parts, KITnn types incl. HATCH), PS ROOFSCOOP (5 kits), PS EXHAUST (tips: Motor Town has no exhaust part type → skipped), MW SPOILER / _CARRERA / _HATCH / _PORSCHES (STYLEnn + _CF carbon), MW ROOF (scoops STYLEnn, _DUAL, _OFFSET, _CF), MW WHEELS. All are modelled around their own mount point (spoilers z≈0 base, scoops origin at the front edge). Motor Town's AeroParts include PartType Roof (car-space, origin attach), RearSpoiler, RearWing (mounted at the Body socket RearWing).
- **Universal NFS wing pack: `tools/aero_pack.py cars/nfs_wings.json`** (kind aero_pack, car NFS_Wings). Sources: PS SPOILER base parts (^SPOILER_KITnn_(HATCH|SMALL|MEDIUM|LARGE)$, 48) + MW SPOILER (^SPOILER_STYLEnn(_CF)?$, 165). One mesh per wing, RearWing rows mounted at each car's RearWing socket (no car rebuild needed), VehicleKeys = all ported cars, BodyMaterialNames key = pack paint_slot (Body_01: cars whose paint slot is "Body" (Fortem: Elise, 997, 993) may not paint them, as with the game's universal wings). make_mt_assets now takes aero packs: rows may carry `vehicle_keys` and `socket` (bUseCustomSocket + CustomSocketName); kind aero_pack is skipped for blueprints/vehicle rows.
  - Pack materials: on PS spoilers 0xBF30889B is the PAINT (not chrome), 0x721AFF7C / 0x027FF2DC dark, 0x48A68363 trim. On MW: 0xE9B62482 paint, 0x721AFF7C carbon fibre (rendered dark for now), 0x1B049702 black, 0xBF30889B trim. MW ROOF DAEs name materials in text ("BODY", "CARBONFIBRE_BODY", "BODY_PLAINNOTHING").
- **Roof scoops (to do):** Roof parts attach at the car origin in car space. Options: a Body socket "RoofScoop" per car + row socket (one mesh per scoop; needs every car rebuilt, so test on one car first), or per-car offset meshes.
- **MW vinyls/liveries as garage skins:** each car's VINYLS.BIN holds per-car liveries: the 15 Blacklist racers, BODYnn, FLAME/STRIPE/TRIBAL sets, national flags, CE01–03, model ones (BMW_24, MOTOGTR), each a colour layer with alpha plus a `_MASK`, and a `DEBUG` layout template (LEFT band upside-down / TOP / RIGHT / FRONT / REAR). On original MW models the paint UV0 IS that layout: test by rendering DEBUG through the paint UV0 (sides red/purple, top green). The 993 RWB Rework model fails this test, so it gets no vinyls. Its vinyls also live in another folder (911GT2993RWB).
  - Spec `skins {dir, pick: [names], labels}`: ps_to_mt write_skins picks the file with real alpha (colour layer vs its mask share truncated names) → textures/SKIN_<name>.png, car.json "skins".
  - build_car makes `M_VinylBody` (base = lerp(Color, vinyl.rgb, vinyl.a); Color/Metallic/Roughness = M_Body's own parameter names, so the chosen paint shows under the vinyl) and MI_SKIN_<name>. make_mt_assets add_skins appends MTVehicleBodyMaterial entries {Material, SlotMaterials, bUseForAIVehicle} to the CDO's BodyMaterialList, creating it (entry 0 = /Game/Cars/Materials/Body/M_Body) on bases without one (the Cora has none). M3 GTR: 20 skins. Unverified in game: whether the game feeds Color to a non-M_Body skin.
- **ProStreet liveries (to check):** CARS/VINYLS/LIVERYTEXTURES.BIN holds per-car race liveries; test whether the ProStreet paint UV0 matches the car's VINYLS.BIN DEBUG layout, as on MW.
- **REQUIRED before installing any kit / garage part: the texture-glitch check** (the user asked for this on every future part):
  - Run `tools/render_kits.py <build_dir> <out.png> kit:<CODE>` (or a mesh list). It draws depth-buffered 3/4 + side views with backfaces culled. Magenta marks where two different meshes' surfaces lie within 0.4 cm of each other (in-game flicker), and it prints a zfight %.
  - Compare against `kit:KIT00`; stock ProStreet runs ~0.03–0.7%. Also look for dark "Bottom" shards and holes at the seams.
  - MW kits on ProStreet ports measured 0.4–5.9% before the fix. Cause: the MW kit shells repeat the body sides and panel edges a few mm to cm off the ProStreet surface, because the models are near copies, not identical.
  - Fix (ps_to_mt part options, all set by add_mw_parts). Distance-only trimming left ragged seams where the MW surface drifts off the ProStreet one (the Supra drifts up to 9 cm), so:
    - `keep_nearest {prefix, parts (all ProStreet stock pieces except BASE), replaced (the slot's own stock parts), proud 2.5, far 6, lamp_clear 8}`. Each piece of the MW kit shell is given to the nearest ProStreet part and kept if that part is one being replaced, or if it stands > proud cm out (lips, flares). Pieces further than far from every part are kept only when OUTSIDE the car (sd ≥ 0). The MW shell's inner walls and undersides were the black bands showing through every seam. Over lamps, a piece is dropped only when it lies directly over the lamp (lateral ≤ 1.5 cm), so bumper-mounted lamps don't leave holes. Cuts then follow the ProStreet seams.
    - `fill_gaps {far, edge, drop_far}` on a ProStreet part that follows the MW part in the same mesh: keeps only the pieces the MW surface built so far doesn't cover. Skirts (far 8) fill the strip between a low MW sill and the ProStreet door bottom. Bumpers (far 4, drop_far) fill MW openings, never past the kit.
    - `refine_drop 4` (split mixed triangles down to ~1.5 cm), `x_clip` (straight cuts at x_range) and mesh `min_island 150` cm².
  - Check renders: the front-3/4 and rear-3/4 close-ups matter more than the zfight %. Ragged seams and dark bands don't show up in that number.
- **NFS Carbon as the fitment reference for MW (Rework IV) kits** (user tip: Rework IV ports Carbon cars such as the R34):
  - Carbon Remastered is at `C:/Program Files (x86)/needforspeed/Need For Speed Carbon Remastered`. Use each car's `geometry.bin.bak` (the original; the remaster's GEOMETRY.BIN fails to export), copy it to `~/nfs-work/nfsc_src/<CAR>/GEOMETRY.BIN`, and export with `AssetDumper export -g Carbon` into `~/nfs-work/db/nfsc/<CAR>/geo`.
  - The 8 overlapping cars are exported. Carbon kits are separate `KITnn_FRONT_BUMPER / REAR_BUMPER / SKIRT` plus `KITWnn_BODY` widebodies (with doors).
  - Every Rework MW `KITnn_BODY` = the Carbon KIT00 base body (identical, same space; median 0.47 cm = sampling noise) + that kit's pieces merged. Some MW kits are exact Carbon kits (Supra MW13 = Carbon 1, MW14 = Carbon 4, MW02–05 bodies = KITW02–05).
  - add_mw_parts (when the Carbon export exists) splits each MW kit shell:
    - `drop_coincident_with` the Carbon base parts (tol 0.5);
    - ps_to_mt `slot_label {pieces: Carbon KIT00 FRONT_BUMPER / REAR_BUMPER / SKIRT, keep}` (nearest Carbon stock piece), so the split lands on the original seams;
    - each slot gets its own fit (`mw_parts.<CAR>.carbon_slot_fit`): the Carbon stock piece onto the ProStreet stock piece. Skirts fit only on the shared x stretch, since the Carbon skirt also runs under the arches. Hoods use the KIT00_HOOD → HOOD fit.
  - Still applied: `keep_nearest` (with `tuck 1`: pieces 1–6 cm behind a ProStreet panel are kept, which closes seams), `fill_gaps`, and skirts `z_max` = arch tops.
  - Kit meshes are `double_sided` (a reversed copy of each triangle), because single-sided panels were see-through from low angles.
  - MW rear bumpers carry the ProStreet exhaust with `align_to_grille`: each tip set goes to the nearest grille opening (sideways and height only); a duplicate set for an already-used opening is hidden.
- **Widebodies must work as the panel's skin** (user standard): the body's wheel-arch zones ([[x, z, wheel r + 24, half_track − 30]] per axle, `spec.arch_zones`) are cut out of the Body and put in the mandatory Fender slot.
  - ProStreet ports: add_mw_parts adds them to Aero_Fender_KIT00 and the KITW widebody (WIDEBODY zones-keep, trimmed against the stock skirts with keep_nearest `keep_far`, and the stock BODY `fill_gaps` for holes).
  - MW-native cars: `tools/add_arch_fenders.py`.
  - MW kits whose shell is > 25% off the stock body inside the zones get a "Kit N Widebody" Fender row. Their bumpers and skirts drop the zones.
  - ps_to_mt part options:
    - `zones {mode keep|drop, list}` cuts exactly on the zone surface (after splitting to ~4 cm);
    - `blend {prefix, parts, zones, band 15, max 10}` morphs the skin onto the stock surface near the zone edge, so there is no step;
    - `drop_coincident_with.also` adds extra references under other prefixes.
  - add_mw_parts keeps the original ProStreet meshes in `spec.ps_meshes` and rebuilds from them on each run (repeat runs used to lose parts).
- **MW exhaust tips:** the local AssetDumper logs solid position markers to stderr (`MARKER <solid> <hash> x y z`). Dumps live in `~/nfs-work/markers/<CAR>.markers`.
  - Tip hashes are 0xBCF8A18B / 0xBD7CF15E (one per tip, per kit). The Carbon `EXHAUST_STYLE01_LEVEL1` tip goes on each, in the rear-bumper fit.
  - Side exits are turned with xform `rot_z` ±90.
  - render_kits only uses meshes listed in car.json.
- **Paintable rims, check the MI parent:** a paintable texture slot's MI must have the car's `M_PaintTex` as parent, or painting swaps in a flat M_Body MID (the glitched chrome look).
  - build_car's `set_material_instance_parent` on an EXISTING MI doesn't dirty the package, so `save_loaded_asset` skipped it. The PS rims and the PS car wheels stayed on M_Sketchfab_Base for weeks.
  - Now build_car uses `EAL.save_asset(path, only_if_is_dirty=False)`, and ue_build.sh runs `Scripts/fix_rim_parents.py` (PSCAR_ONLY=<build>) after every build.
  - Rims also need `DecalableMaterialSlotNames [Wheel_01]` (MP paint, like Maja's Wheel Works). A car wheel model whose tyre shares the rim texture gets mesh `radius_slot {r, slot: Bottom, from: [rim slot]}`, or the tyre takes the rim colour (white).
- **Other mods that replace a composite parent table** (Maja's Wheel Works replaces DataAsset/VehicleParts/Wheels): the game rejected our VehicleParts composite and loaded the vanilla one, so every kit vanished while the car paks were fine.
  - Fix: build the client tables on a base that includes that mod's table. `make_mt_assets` defaults to MT_BASE=~/mt-work/unpacked_maja (client extract + Maja's Wheels).
  - Verify at the main menu with the KoPCarCheck TblCheck probe: VehicleParts rows (2349 with ours) and 20 parents incl. Wheels_ProStreet/Aero_ProStreet. Check both with and without the mod.
- **Engine tuning (ProStreet style):**
  - `make_mt_assets.make_tuning_table` → `Tuning_ProStreet` (TUNING_PARTS: Turbocharger rows = boost, Intake rows = cams; templates in VehicleParts0; VehicleKeys = our cars).
  - `engine_tunes()` adds Street/Race/Pro tunes of each car's engine (ENGINE_TUNES) to the custom part rows. An engine from another mod (Viper V10ACR) is cloned with `curve: None` and `torque_scale`.
  - A new car gets all of this automatically. More Tuning's own turbos and intakes stay separate.
- **Base-car body parts left as defaults:** the vehicle row copied from the base keeps the base's default parts for slots our car doesn't fill. The Cora gave the M3 its Fender and Headlight parts, which floated as extra headlights, vents and fender strips. After make_mt_assets, list each row's parts that aren't ours or generic, and add those slots to `strip_part_slots`.
- **MW boss liveries on ProStreet ports** (`tools/transfer_livery.py <spec> <MW CAR> <vinyl> <r,g,b> <out.png>`):
  - The ProStreet livery layout is UV0 of the shared car-paint material 0x65FF171E only (other Paint-slot materials such as 0xBEBC83C2 have stretched UVs). Rasterise it in image space (V = 1 - v).
  - Map each texel to the nearest same-facing MW KIT00 BODY/HOOD paint triangle (placed with spec mw_parts xform), then sample the vinyl at that MW UV0. Coverage = the _MASK; MW colour-layer alpha is half scale (0x80 = opaque).
  - The output is opaque body colour plus vinyl, listed under spec `skins.baked {name: png}` with labels.
  - Boss colours: GLOBALB presets → part hashes (bStringHash) → the car-part table:
    - chunk 0x34604: 14-byte records, data at +4, attr-table index u16 at +6, hash at +10;
    - 0x3460C: u16 count + u16 attribute indices;
    - 0x34605: 8-byte key/value pairs, keys bStringHash RED/GREEN/BLUE/GLOSS.
    - Vic = navy (0, 16, 59); JV = (160, 60, 60).
  - Rework IV VINYLS.BIN are compressed TPKs; the DataOffsetStruct trailer is TextureInfo with ImageSize at -156+56.
- **Skin asset names must be alphanumeric** (write_skins strips them): the BMW_24 livery made MI_SKIN_BMW_24, an FName ending in _<digits>, and UAssetGUI silently refused to write the blueprint (it stopped the whole table run).

## Car database + fast path (2026-10-19)
- **`tools/nfs_db.py [ps|mw|all] [CAR...]`** → `db/cars.json` + `db/cars.md`, one record per drivable car of both games. Exports are cached in ~/nfs-work/db/<game>/<CAR>/{geo,tex,vin}, so later steps never re-export. Each record holds:
  - stock_parts, kits, styles, unprefixed parts;
  - tris (body / interior / base), bbox, wheel_radius;
  - materials (hash, use count, texture name) and paint_guess;
  - textures by hash; lamp and interior textures;
  - vinyl_check (share of side faces whose paint UV0 lands on the right DEBUG colour: > 0.4 = liveries fit) and vinyl_count;
  - performance: PS from vehicle.yml <car>_track (torque_nm, gears, FD, mass, rpm); MW via pvehicle → engine/transmission/engineaudio (torque_lbft, peak_hp_est, gin_accel).
- **`tools/make_spec.py <game:CAR> <base> <out.json> [CAR_KEY]`** bootstraps a spec from the record and the finished spec on that base (TEMPLATES: Cora→mw_m3gtr, Fortem→mw_993rwb, Tuscan→challenger71, Zino→350z, Vista→skyline, Magis→supra). It fills the shared hash table + the car's textures by role (texture_sources by hash), Body parts, wheels, engine/gearbox/FD/body_mass, and a TODO list of the measured steps.
- **Fast path for a new car:**
  1. make_spec;
  2. ps_to_mt + render_car → fix the texture map and parts;
  3. steering wheel / dials / lamps / mirrors (fortem_mirror_aim) / seats;
  4. stance via the per-base reference;
  5. add_body_kits(_mw);
  6. skins if vinyl_check is OK;
  7. ue_build.sh + make_mt_assets over ALL specs + packs (ps_rims, mw_rims, nfs_wings) → cook → pack_car + pack_common → dealer bay.

## Most Wanted parts on ProStreet-ported cars (2026-10-19)
- **The Rework IV models of cars ProStreet also has are near-copies in the same space**: MW <CAR>_KIT00_BODY at source_scale 100 matches the ProStreet KIT00 body (scale 1000) within ~0.6 cm, with no transform needed. That holds for SUPRA, VIPER, 350Z, ELISE, 997TT, SKYLINE, MUSTANGSHLBYO and CHEVELLE. So MW kits bolt straight onto our ProStreet ports.
- **`tools/add_mw_parts.py cars/<ps>.json <MWCAR> [--fit-only]`** fits the MW body onto the ProStreet one, starting from identity with trimmed one-way ICP, scale clamped to ±3%. It stores the result in spec `mw_parts[<MWCAR>]`, then adds rows tagged `"mw": true` (a re-run replaces them), labelled "Most Wanted …":
  - FrontBumper / RearBumper: KITnn_BODY cut at the ProStreet stock bumper's inner x edge, minus anything lying on any non-aero ProStreet part (`drop_coincident_with`, tol 1.5). The rear keeps the ProStreet EXHAUST.
  - SideSkirt: kit n>0 between the cuts, minus the MW stock body.
  - Bonnet: KIT00_HOOD + STYLEnn_HOOD (+ STYLEnn_ATTACHMENTn).
  - RearWing: the car's own KIT00/STYLE/ALT/NEW_STYLE spoilers, with xform t shifted by -RearWing socket.
  - Meshes are named `Aero_<Slot>_MW<code>`.
- **Converter support (ps_to_mt.py `load_src`)**: per-part `geo` (another export dir), `src_scale` and `xform {s,t}` (MT = s·MT_src + t). These work on parts and on `drop_coincident_with` references. Spec `texture_dirs {slot: dir}` gives a texture slot its own folder (`tex_dir()`).
- **MW material names**: look them up in ~/nfs-work/mwglobal_tex/textures (an AssetDumper export of GLOBAL/GLOBALB.LZC via ~/nfs-work/mw_globalb.bin) and in the car's own textures.
  - `<CAR>_SKINn` (bin hash: SKIN1 = paint, SKIN2 = +1, SKIN3 = +2), BODY_*, and DOORLINE → Paint.
  - CARBONFIBRE 0x721AFF7C, GRILL_01/02, INTERCOOLER and RADIATOR → Tex_MWG_* (GRILL_01 masked).
  - CHROME / ALUMIN → Trim.
  - CARBOTTOM, WINDOW_MASK, LICENSEPLATE, RUBBER, SOLIDGREY → Bottom.
  - The MW Viper's materials carry NAMES (BODY_TOP, CARBONFIBRE_BODY…), not hashes.
- **Not portable as parts**: MW SUPRA STYLEnn_HEADLIGHT / BRAKELIGHT lamp styles. Lamps belong to the Body lamp slots.
- MW kit bumpers have no ProStreet side markers / bumper signals.

## AssetDumper (local NFS-ModTools build) fixes for Rework IV
- **Geometry routing**: ChunkManager routes 0x80134001 at top level for MW, as a pack.
- **Split packs**: MostWantedSolidListReader.PostRead reads objects at the 0x134004 table offsets when the pack holds only the header. This covers 360MODENA, 9974S, BMWM3, CORVETTE, INTEGRATYPER, MAZDA3SPORT and SUPRA.
- **Guards**:
  - SolidReader skips materials whose vertex buffer is empty; this was the divide-by-zero on the CORVETTE.
  - Every object read is wrapped in try/catch, so one bad object (a null vertex buffer, on the SLR) is skipped with a stderr note instead of killing the car. CORVETTE skips 2 objects, SLR 3.
- **Texture packs**:
  - 0xB3300001 (NFS-TexEd compressed TPK; SUPRA) is routed to Version2Tpk.
  - Chunk walkers (ProcessOpen, ReadSubChunks, Version2Tpk.ReadChunks) stop at junk or loose JDLZ after the last chunk. This fixed VIPER, BMWM3, CLIO and MONARO.
  - COBRA and VIPER92 keep their textures in GLOBALB.
- **Cars that stay limited**:
  - SKYLINE32R's GEOMETRY.BIN actually holds the MONARO.
  - BEARCAT is a cop/traffic-style model: its body exists only as DAMAGE parts.
  - CAYENNE has no body in the Rework files.
- **Build**: `DOTNET_ROOT=~/tools/dotnet8 dotnet publish AssetDumper/AssetDumper.csproj -c Release -r win-x86 --self-contained -p:PublishSingleFile=true -o ~/tools/assetdumper-x86-new`, then copy over ~/tools/assetdumper-x86 (LZCompressLib.dll needed). The original build is kept in ~/tools/assetdumper-x86-old.
- **nfs_db.py needs Pillow**: run it with `python` (3.13 store build), not `py -3.13`.

## Interiors follow the real car (user rule, 2026-10-19)
- Build each car's interior from real reference photos of that exact car and model year: dash shape, gauge cluster (count, positions, dial ranges), steering wheel, seats, console. Don't reuse a shared base layout.
- The base vehicle (Cora/Fortem/Tuscan…) supplies only the blueprint and its functional sockets. Place the dials and the dashboard to match the reference; the NFS interior mesh and textures are the starting point.
- Pending: revisit the existing ports' interiors against reference photos.

## Vehicle spawn menu (testing tool)
- `C:\Users\noust\OneDrive\Documents\claude\mt-spawner` is an F8 in-game menu (version.dll overlay + UE4SS Lua `MTSpawner`). It spawns any Vehicles row through `MotorTownPlayerController:ServerSpawnVehicle`, for the host or an admin only. Useful for testing ports without a dealer bay.
- The game's classes are MotorTownPlayerController / MotorTownPlayerState (bIsHost, bIsAdmin) / MotorTownGameState (Net_Admins).
- Our pak rows join the Vehicles table only after the user accepts the launch mod-consent dialog.

## Tuning, F8 menu tools, NFS dealership, server (2026-10-22..24)
- **Adjustable PSI turbo:** garage part `PS_Turbo_Adjustable` + 102 hidden (`bIsHidden`) rows `PS_Boost_<psi*10>psi` (1-51.5 psi) in Tuning_ProStreet. Row names must not END in digits (FName splits the number off and UAssetGUI silently writes nothing). Curve `psi_turbo()` in make_mt_assets: TorqueMultiplier 1+0.08*psi (~1600 hp 2JZ at 50 psi), BaseTorque keeps 60% of the gain, light turbine (AR ~1, 20-28 kg, IPM 0.99, like More Tuning) - big laggy turbines never spool. The F8 Tuning tab swaps the part with `ServerUpdateVehiclePart(LastVehicle, 7, {ID, Key})` then `OnRep_Parts()` so the engine picks it up; PSI isn't saved across rejoin.
- **F8 menu facts:** while driving, `pc.Pawn` IS the MTVehicle. `Cheat_*` functions do nothing in shipping: time = `MTSunSky_C.SolarTime` + `pc:ClientSetTimeOfDay(h, speed, day)`, weather = `ClientSetWeatherIndex(0 sunny|1 rain, 1)`. XP: `ClientAddExp(why, levelType 0-6, exp, FText)`; money: `ServerSetMoney` / `ClientAddMoney`; money is not a readable property (HUD `MTMoneyWidget.MoneyTextBlock` text is). Never run game calls from `ExecuteWithDelay`'s thread (crash) - queue them to the game-thread tick. Never poll `Net_Parts` in the background (crashed the garage menu); read it on demand.
- **NFS dealership (map patch):** `mappatch transplant` copies whole world-partition cells' actors (a game showroom) into Jeju_World's persistent level, rotated/moved as a group (`dealers/nfs_dealership/showroom.txt`, built by `rebuild_dealers.sh`). Place by the building's WALL footprint (not the whole cell bbox). Use the FULL mappings `~/mt-work/MotorTown-full.usmap` (UE4SS `DumpUSMAP()` on the local server once the world loaded): with the plain usmap, blueprint-struct actors are RawExports and silently missing (spotlights, vendors, lifts). Server build: `PLATFORM=server` + `MAPPATCH_SKIP_MID=1` (saved MaterialInstanceDynamic subobjects crash the WindowsServer build: "Serial size mismatch"). Always test-start the local server copy (inject.py) before uploading a map patch. Survey a real dealer's layout in game with KoPDealer F9 (`survey.txt`).
- **Bisect:** the "Enable UE4SS" startup option only drops a UE4SS proxy `version.dll`; it hangs the server at start (no UE4SS.log) even with the experimental UE4SS installed - support says it isn't ready yet. Keep it Disabled; server-side mods (MTAdminServer) wait on it.
- **Friend's updates:** the user's friend also builds/updates the modpack and server. Run `tools/sync_from_server.sh --pull` before uploading anything; friend's `zzKitFix_*` paks override our MW kit meshes (load last).
