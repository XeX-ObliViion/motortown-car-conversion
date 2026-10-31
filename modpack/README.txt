NFS CAR PACK FOR MOTOR TOWN (for Obliv's server)
=================================================

What's inside
-------------
14 cars from Need for Speed ProStreet and Most Wanted, all with full body kits,
liveries, real gauges (mph) and their own engines:

  Nissan 350Z, Toyota Supra, Lotus Elise, Porsche 911 Turbo (997), Nissan Skyline GT-R R34,
  Shelby GT500 '67, Dodge Challenger R/T '71, Chevrolet Chevelle SS 454, Dodge Viper SRT-10,
  BMW M3 GTR (Most Wanted), Porsche 911 GT2 993 RWB (Most Wanted),
  Toyota Supra (Most Wanted), Dodge Viper SRT-10 (Most Wanted), Lotus Elise (Most Wanted)

The Most Wanted versions use their own Most Wanted bodies, so all their Most Wanted kits fit properly.

Plus: the ProStreet rim pack (96 rims), the Most Wanted rim pack (41 rims) and the NFS wing pack.
The ProStreet cars are sold at the NFS dealership at the Ara drag strip (and a few other dealer spots);
the Most Wanted cars at the "MOST WANTED" dealership (see the map icon).


Install (5 minutes)
-------------------
1. Close Motor Town.

2. Copy EVERY .pak file from this folder into:
      ...\Steam\steamapps\common\Motor Town\MotorTown\Content\Paks
   (In Steam: right-click Motor Town > Manage > Browse local files, then open MotorTown\Content\Paks.
    The game's own MotorTown-Windows.pak is already in there.)

3. Also install these two mods from Nexus Mods (free; our cars use their engine sounds):
   - More Tuning (by qxZap):            https://www.nexusmods.com/motortownbehindthewheel/mods/18
   - More Tuning - No Limits (optional): https://www.nexusmods.com/motortownbehindthewheel/mods/49
   Recommended, to match the server:
   - Maja's Motor Works:                https://www.nexusmods.com/motortownbehindthewheel/mods/9
   - Maja's Wheel Works (makes the game's own rims paintable; pick the "Unlocked Wheels" pak):
                                        https://www.nexusmods.com/motortownbehindthewheel/mods/68
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
When there's a new version, close the game, replace the old .pak files with the new ones, then start the
game, allow the mods again and restart once. If body kits are missing after that, restart one more time.
Update of 31 Oct 2026: new MW Lotus Elise (MW_ELISE_P is new), working reverse lights on the MW Supra
and MW Elise. Replace every .pak.
Update of 30 Oct 2026: new MOST WANTED dealership, MW Supra + MW Viper, the NFS dealership now faces the drag strip
and its lights work. Replace every .pak (MW_SUPRA_P and MW_VIPER_P are new).
Update of 29 Oct 2026: the kit-fix files were renamed (zzKitFix_A_50_P.pak ... plus zzKitFix_E_Viper_99_P.pak).
Delete the old zzKitFix_A_P.pak, zzKitFix_B_P.pak, zzKitFix_C_P.pak, zzKitFix_D_P.pak and zzKitFix_E_Viper_P.pak
from your Paks folder if you have them.


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

These are fan conversions for private play with friends. Please don't re-upload them anywhere.
