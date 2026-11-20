NFS CAR PACK FOR MOTOR TOWN (for Obliv's server)
=================================================

What's inside
-------------
Over 30 cars from Need for Speed ProStreet, Most Wanted, Heat, Assetto Corsa and BeamNG, all with real gauges (mph) and
their own engines (the NFS cars also with full body kits and liveries):

  Nissan 350Z, Toyota Supra, Lotus Elise, Porsche 911 Turbo (997), Nissan Skyline GT-R R34,
  Shelby GT500 '67, Dodge Challenger R/T '71, Chevrolet Chevelle SS 454, Dodge Viper SRT-10,
  BMW M3 GTR (Most Wanted), Porsche 911 GT2 993 RWB (Most Wanted),
  Toyota Supra (Most Wanted), Dodge Viper SRT-10 (Most Wanted), Lotus Elise (Most Wanted),
  Nissan 350Z (Most Wanted), Porsche 911 Turbo 997 (Most Wanted), Lamborghini Diablo SV (Most Wanted),
  Nissan Skyline GT-R R34 (Most Wanted), Nissan Skyline GT-R R34 V-Spec (Heat, with 58 Heat kit parts),
  Mazda RX-7 Spirit R (Heat, with Heat's pop-up headlights, its own Heat engine sound and 86 Heat kit parts),
  Renault Clio V6 (Most Wanted), Chevrolet Corvette C6 (Most Wanted),
  Rockport PD4 police SUV (Most Wanted) - a police vehicle: needs the police licence, has siren + light bar
  Rockport PD1U unmarked cruiser (Most Wanted) - a police vehicle: hidden red/blue lights in the grille, visor, rear deck and bumper
  Toyota Supra and Lamborghini Gallardo Superleggera from the Assetto Corsa "8 Second Shootout" drag pack - they keep their
  drag tunes (Supra 2JZ ~1300 hp, Gallardo twin-turbo V10 AWD), stock turbo fitted, their own AC engine sounds
  Honda Civic EG (K20 swap, drag), Mazda RX-7 FD (rotary drag car with working pop-up headlights, wheelie bar and chute) and
  the 1320Video "Unicorn" Corvette C5 Z06 (twin-turbo LS, pop-up headlights, roll cage, chute) from the same AC drag pack
  Ferrari F40 and Chevrolet Silverado drag truck (Assetto Corsa), Porsche Cayman S (Most Wanted, 6 body kits and 60 liveries),
  Shelby GT350R and drag Shelby GT500 (BeamNG), Rockport PD5U police car (Most Wanted),
  Mazda RX-7 Savanna FC (Most Wanted, working pop-up headlights, 6 body kits and 60 liveries)

The Most Wanted versions use their own Most Wanted bodies, so all their Most Wanted kits fit properly.

Plus: the ProStreet rim pack (96 rims), the Most Wanted rim pack (41 rims) and the NFS wing pack.
The ProStreet cars are sold at the NFS dealership at the Ara drag strip (and a few other dealer spots);
the Most Wanted cars at the "MOST WANTED" dealership (see the map icon); the Diablo SV stands in the middle
of its showroom. The Rockport PD4 and the PD1U unmarked are at the police station car park. The Heat R34 stands on the lot
beside Seoguipo Luxury Cars. The ProStreet cars now have their own PROSTREET dealership at the Ara drag strip, and all
Assetto Corsa cars are at the ASSETTO CORSA dealership across the strip (see the map icons).


Install (5 minutes)
-------------------
1. Close Motor Town.

2. EASY WAY: extract the whole zip, then double-click "Install NFS Pack.cmd" in this folder. It finds Motor Town
   through Steam, installs the pack AND the F8 menu (step 3's F8 part), and on updates replaces only what changed and
   moves our old paks to NFS_removed_paks (your other mods are left alone). Then skip to step 3 for the Nexus mods.
   If Windows SmartScreen asks: "More info" > "Run anyway" (it is a plain text script).

   Manual way: copy EVERY .pak file from this folder into:
      ...\Steam\steamapps\common\Motor Town\MotorTown\Content\Paks
   (In Steam: right-click Motor Town > Manage > Browse local files, then open MotorTown\Content\Paks.
    The game's own MotorTown-Windows.pak is already in there.)

3. Game version 0.7.20: also install these mods from Nexus Mods (free). Use the 0.7.20 versions and delete
   the 0.7.19 ones (MajasMotorWorksV7.1-7.19, MajasMoWheelWorksV5.1-7.19, old qxZap_MoreTuning paks):
   REQUIRED (our cars and parts are registered through it, without it they do not show up):
   - DataTable Framework (by qxZap):    https://www.nexusmods.com/motortownbehindthewheel/mods/208
   - More Tuning 3.0 (by qxZap):        https://www.nexusmods.com/motortownbehindthewheel/mods/18
     (Files tab: take the 180 MB "qxZap_MoreTuningV3"; the small 191 KB one is only the server version)
   - Maja's Trailer Works V8 (7.20, needed by More Tuning 3.0):
                                        https://www.nexusmods.com/motortownbehindthewheel/mods/13
   Recommended, to match the server:
   - More Tuning - No Limits 3.0:       https://www.nexusmods.com/motortownbehindthewheel/mods/49
   - Maja's Wheel Works V6 (7.20; makes the game's own rims paintable; pick the "Unlocked Wheels" pak):
                                        https://www.nexusmods.com/motortownbehindthewheel/mods/68
   (Maja's Motor Works has no 0.7.20 version yet: leave it out until it is updated.)
   Optional, works with the pack (only on your own PC, the server doesn't need it):
   - ECU Tuning (by qxZap; engine tuning, pops/bangs, turbo flutter):  https://www.nexusmods.com/motortownbehindthewheel/mods/212
   - Suspension Tuning (by qxZap; big brakes, suspension geometry): https://www.nexusmods.com/motortownbehindthewheel/mods/213
     needs Plugin Loader (by qxZap):                                    https://www.nexusmods.com/motortownbehindthewheel/mods/209
     Install them AFTER this pack. The Plugin Loader replaces our F8 menu's version.dll; that's fine, the pack's
     installer also puts the F8 menu in the plugins folder, where the Plugin Loader starts it.
   Put their .pak files in the same Paks folder.

   F8 menu (Tuning tab for the adjustable turbo, plus the vehicle spawner for hosts/admins):
   copy EVERYTHING inside the "F8 Menu (copy into Win64)" folder into:
      ...\Steam\steamapps\common\Motor Town\MotorTown\Binaries\Win64
   (next to MotorTown-Win64-Shipping.exe). If Windows asks, choose Replace. In game press F8.
   If you already use UE4SS for other mods, only copy version.dll, mt_spawner.ini and
   ue4ss\Mods\MTSpawner, then add the line "MTSpawner : 1" to your ue4ss\Mods\mods.txt.

4. Start Motor Town. It asks whether to allow the mods: click ALLOW.
5. Restart Motor Town once. The mods only switch on after that restart.
6. Join the server.


Updating
--------
When there's a new version: close the game, extract the new zip and double-click "Install NFS Pack.cmd" (or replace
the old .pak files by hand), then start the game, allow the mods again and restart once. If body kits are missing after that, restart one more time.
Update of 20 Nov 2026: new Mazda RX-7 Savanna FC (MW_RX7FC_P - NEW pak: enable it in the game's mod list, then restart)
  with working pop-up headlights and backlit gauges. Most Wanted Supra: now has the Assetto Corsa Supra's full interior
  (right-hand drive), and its widebody kit 5 no longer has gaps at the hood/fender. The Cayman and RX-7 FC moved to their
  own spot. Cars you already own keep their old parts - buy a fresh one to see pop-ups / the new cabin.
Update of 19 Nov 2026 (3): F8 menu: "flip upright" works again on game 0.7.20. Suspension Tuning (qxZap) added to the optional list.
Update of 19 Nov 2026 (2): the F8 menu now also works alongside qxZap's Plugin Loader / ECU Tuning (see step 3, optional).
Update of 19 Nov 2026: new Ferrari F40 (AC_F40_P), Chevrolet Silverado drag truck (AC_SILVERADO_P) and Porsche Cayman S
from Most Wanted (MW_CAYMAN_P), all at the ASSETTO CORSA dealership for now. The Cayman comes with 6 Most Wanted body
kits, Most Wanted hoods and 60 Most Wanted liveries as paint options. FIX: the ProStreet turbos (Low / Medium / High and the
adjustable PSI turbo) all gave the same power since game 0.7.20; they now give their own boost again, which also brings the AC drag cars back up to their
rated power again. Both BeamNG Mustangs: the interior no longer glows with the headlights / brake lights.
NEW PAKS ON 0.7.20: the game asks before it loads a pak it hasn't seen before. If a new car doesn't show up, open the game's
mod list and enable AC_F40_P, AC_SILVERADO_P and MW_CAYMAN_P, then restart.
Update of 13 Nov 2026 (2): new Mazda RX-7 Spirit R from NFS Heat (HEAT_RX7_P), at the end of the PROSTREET row at the drag
strip: Heat pop-up headlights, Heat engine sound, 21 front bumpers, 22 side skirts, 10 wings, 25 fender sets, hoods, rear bumpers.
Update of 13 Nov 2026: three new Assetto Corsa drag cars: Honda Civic EG (AC_CIVICEG_P), Mazda RX-7 FD (AC_RX7FD_P, pop-up
headlights, wheelie bar, chute) and the 1320Video "Unicorn" Corvette C5 Z06 (AC_UNICORN_P). New dealerships at the Ara drag strip:
PROSTREET (the ProStreet cars) and ASSETTO CORSA (all AC cars) across the strip. Fixes: rear wheels show the right (wide) rear rims
on the AC cars, Viper and 993 RWB; no more leftover base-car hoods/bumpers/skirts on any car; Skyline R34 gauges and bonnet.
Cars you already own keep their old parts: buy the car again or swap the wheels/kit in the garage to get the fixes.
Update of 7 Nov 2026 (2): new Assetto Corsa drag cars: Toyota Supra (AC_SUPRA_P) and Lamborghini Gallardo
Superleggera UGR (AC_GALLARDO_P), side by side next to the Magis dealership. Both come with a stock turbo.

Update of 7 Nov 2026: new MW Rockport PD1U unmarked police car (MW_COPGHOST_P, police station car park); R34 brakes and
suspension visible behind the wheels; Clio B-pillar body colour.
Update of 6 Nov 2026 (2): MW Skyline R34 rebuilt from the Most Wanted Remaster model (new body, opening doors, real R34 gauges in mph,
GT-R wheel, Brembo brakes; kits 6-7 are gone); Rockport PD4 sits at real SUV height; Clio and 350Z B-pillars filled; Corvette cluster
clear; F8 menu shows every Most Wanted / Heat car by name (copy the new 'F8 Menu' folder too).
Update of 6 Nov 2026: Most Wanted cars now come from the MW Remaster: the Corvette gets the stock C6 interior (seats, dash,
door panels, no roll cage), the Elise its full interior, smooth mirrors and working right taillights, Supra and 350Z re-sourced.
Engine sounds: 6-7 Most Wanted recordings per car from idle to redline (Corvette, Clio, 911 Turbo, 350Z, Elise, Diablo, 993 RWB),
louder on every port; engines hold idle again (Elise stalled). Diablo SV is rear-wheel drive with the real front track;
Clio and 350Z blinkers in the right lenses; Corvette tail lamps all glow; PD4 sits at real SUV height.
Update of 2 Nov 2026: new MW Renault Clio V6 (MW_CLIO_P, with Most Wanted's own engine sound) and MW Corvette C6
(MW_CORVETTE_P) at the MOST WANTED dealership; real-car ride heights on every car incl. the Diablo SV (the stiffer springs had raised them);
MW Viper paint is one colour again; Most Wanted engine sounds on the MW 911 Turbo, 350Z, Elise, Corvette, Diablo and Clio; F8 cargo run loads the job's full amount and straps it before driving back.
Update of 1 Nov 2026 (2): new Heat R34 (HEAT_SKYLINE_P: Heat body, interior and kits); the Diablo SV is now built on
the Raton (seat, gauges, ride height); working mirrors on every Most Wanted car (MW Supra's passenger window fixed);
the MW R34 is AWD like the real car.
Update of 1 Nov 2026: stiffer Most Wanted-style suspension on every car, reworked Diablo SV interior,
Challenger Rallye dash, MW Skyline (MW_SKYLINE_P is new) and a fix for the Diablo/Skyline/997 missing from the dealers.
Update of 31 Oct 2026 (3): new MW Porsche 911 Turbo (MW_997TT_P), Diablo ride height + wheels, PD4 ride height
and bay, badge fixes on the MW 997/350Z/PD4, and the new installer (Install NFS Pack.cmd).
Update of 31 Oct 2026 (2): new MW Nissan 350Z, Lamborghini Diablo SV and Rockport PD4 police SUV
(MW_350Z_P, MW_DIABLOSV_P and MW_COPSUV_P are new). Replace every .pak.
Update of 31 Oct 2026: new MW Lotus Elise (MW_ELISE_P is new), working reverse lights on the MW Supra
and MW Elise. Replace every .pak.
Update of 30 Oct 2026: new MOST WANTED dealership, MW Supra + MW Viper, the NFS dealership now faces the drag strip
and its lights work. Replace every .pak (MW_SUPRA_P and MW_VIPER_P are new).
Update of 29 Oct 2026: the kit-fix files were renamed (zzKitFix_A_50_P.pak ... plus zzKitFix_E_Viper_99_P.pak).
Delete the old zzKitFix_A_P.pak, zzKitFix_B_P.pak, zzKitFix_C_P.pak, zzKitFix_D_P.pak and zzKitFix_E_Viper_P.pak
from your Paks folder if you have them.


Free buildings
--------------
ZZZZZ_FreeBuildings_P.pak: the depots and the large garage you build on your own land need no materials
(the server has it too).


Tuning parts
------------
At a garage, the NFS cars get ProStreet tuning: Low/Medium/High boost turbos, Street/Sport/Race cams, engine
tunes, and the "ProStreet Adjustable Turbo". Fit the adjustable turbo, get in the car, press F8 and open the
Tuning tab: pick the boost (1 - 51.5 psi) with the slider, the number box or a preset, then press Apply.


Problems?
---------
- Cars missing or no body kits: make sure every .pak from this folder is in the Paks folder, then
  allow and restart.
- Single-player saves: cars bought in an old save before an update may lose parts. Buy a fresh one.
- Uninstall: delete the PS_*, MW_*, NFS_* and zzKitFix_* .pak files from the Paks folder. For the F8 menu, delete
  version.dll, dwmapi.dll, mt_spawner.ini and the ue4ss folder from Win64.

Credits
-------
This pack depends on these mods. They are not included (their authors don't allow re-uploading), so please
download them from their Nexus pages and endorse them there:
  - qxZap:    DataTable Framework, More Tuning, More Tuning - No Limits
              https://www.nexusmods.com/motortownbehindthewheel/users/qxZap  (mods 208, 18, 49)
  - Majataka: Maja's Trailer Works, Maja's Wheel Works (and Maja's Motor Works)
              https://www.nexusmods.com/motortownbehindthewheel/mods/13 , /68 , /9
  - UE4SS (the F8 menu's loader): https://github.com/UE4SS-RE/RE-UE4SS
  - Our cars are converted from Need for Speed ProStreet, Most Wanted and Heat (EA), Assetto Corsa mods and the
    BeamNG.drive s550pewpiw mod: all rights stay with their creators.

These are fan conversions for private play with friends. Please don't re-upload them anywhere.
