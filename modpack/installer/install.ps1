# NFS Car Pack installer: ships inside each pack zip and installs THAT version.
# manifest.json (written by make_modpack.sh) lists the pack's paks and F8-menu files with SHA-256. The installer finds
# Motor Town through Steam, copies only files that differ, moves our paks that are no longer in the pack to
# NFS_removed_paks (never deletes; other mods are untouched), and adds MTSpawner to an existing UE4SS mods.txt
# instead of replacing it.
$ErrorActionPreference = "Stop"
$Here = Split-Path -Parent $MyInvocation.MyCommand.Path      # "NFS Car Pack\Install" folder
$Pack = Split-Path -Parent $Here                              # the extracted "NFS Car Pack" folder
$OurPrefixes = @("PS_", "MW_", "HEAT_", "NFS_", "zzKitFix_", "ZZZZZ_FreeBuildings")

function Find-Game {
    if ($env:NFS_GAME_DIR) { return $env:NFS_GAME_DIR }      # override (testing / unusual installs)
    $steam = (Get-ItemProperty "HKCU:\Software\Valve\Steam" -ErrorAction SilentlyContinue).SteamPath
    $libs = @()
    if ($steam) {
        $libs += $steam
        $vdf = Join-Path $steam "steamapps\libraryfolders.vdf"
        if (Test-Path $vdf) {
            foreach ($m in [regex]::Matches((Get-Content $vdf -Raw), '"path"\s+"([^"]+)"')) { $libs += $m.Groups[1].Value -replace "\\\\", "\" }
        }
    }
    foreach ($l in $libs) {
        $g = Join-Path $l "steamapps\common\Motor Town"
        if (Test-Path (Join-Path $g "MotorTown")) { return $g }
    }
    Write-Host "Motor Town was not found through Steam."
    $g = Read-Host "Paste the Motor Town folder (the one that contains MotorTown)"
    if (-not (Test-Path (Join-Path $g "MotorTown"))) { throw "That folder does not contain MotorTown." }
    return $g
}

try {
    $man = Get-Content (Join-Path $Here "manifest.json") -Raw | ConvertFrom-Json
    Write-Host "NFS Car Pack $($man.version): $($man.files.Count) files"
    $game = Find-Game
    Write-Host "Motor Town: $game"
    while (Get-Process "MotorTown-Win64-Shipping" -ErrorAction SilentlyContinue) {
        Write-Host "Motor Town is running - close it to install (checking again in 5 s)..."; Start-Sleep 5
    }
    $paks = Join-Path $game "MotorTown\Content\Paks"
    $win64 = Join-Path $game "MotorTown\Binaries\Win64"
    $copied = 0
    foreach ($f in $man.files) {
        $src = Join-Path $Pack ($f.src -replace "/", "\")
        if ($f.dest -eq "Win64/ue4ss/Mods/mods.txt") {
            $dst = Join-Path $win64 "ue4ss\Mods\mods.txt"
            if (Test-Path $dst) {      # someone else's UE4SS setup: just enable our mod
                if (-not (Select-String -Path $dst -Pattern "^\s*MTSpawner\s*:" -Quiet)) {
                    $t = Get-Content $dst -Raw; Set-Content $dst ("MTSpawner : 1`r`n" + $t) -Encoding ASCII
                    Write-Host "Enabled MTSpawner in your UE4SS mods.txt"
                }
                continue
            }
        }
        if ($f.dest -eq "Win64/version.dll") {   # qxZap's Plugin Loader owns version.dll: keep it, our menu runs as its plugin
            $cur = Join-Path $win64 "version.dll"
            if ((Test-Path $cur) -and ([System.Text.Encoding]::GetEncoding(28591).GetString([System.IO.File]::ReadAllBytes($cur)).Contains("mt_plugin_*.dll"))) {
                continue
            }
        }
        $root = if ($f.dest.StartsWith("Paks/")) { $paks } else { $win64 }
        $dst = Join-Path $root ($f.dest.Substring($f.dest.IndexOf("/") + 1) -replace "/", "\")
        if ((Test-Path $dst) -and (Get-Item $dst).Length -eq $f.size -and
            (Get-FileHash $dst -Algorithm SHA256).Hash.ToLower() -eq $f.sha256) { continue }
        if (-not (Test-Path $src)) { throw "Missing from the pack folder: $($f.src). Extract the whole zip first." }
        New-Item -ItemType Directory -Force (Split-Path $dst) | Out-Null
        Copy-Item $src $dst -Force
        Write-Host "Installed $($f.dest)"
        $copied++
    }
    # our paks that are not in this version (renamed / retired): move aside, never delete
    $keep = @{}; foreach ($f in $man.files) { if ($f.dest.StartsWith("Paks/")) { $keep[$f.dest.Substring(5)] = 1 } }
    $bak = Join-Path $game "NFS_removed_paks"
    foreach ($p in Get-ChildItem $paks -Filter "*_P.pak") {
        if ($keep[$p.Name] -or -not ($OurPrefixes | Where-Object { $p.Name.StartsWith($_) })) { continue }
        New-Item -ItemType Directory -Force $bak | Out-Null
        Move-Item $p.FullName (Join-Path $bak $p.Name) -Force
        Write-Host "Retired $($p.Name) (moved to NFS_removed_paks)"
    }
    if ($copied) { Write-Host "`nDone: $copied file(s) installed. Start Motor Town, click ALLOW, then restart it once." }
    else { Write-Host "`nAlready up to date." }
    Write-Host "Still needed once (from Nexus, see README): More Tuning; recommended: Maja's Motor Works + Wheel Works."
} catch {
    Write-Host "`nINSTALL FAILED: $($_.Exception.Message)"
}
Read-Host "`nPress Enter to close" | Out-Null
