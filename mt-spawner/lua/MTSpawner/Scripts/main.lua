-- MTSpawner: the game-side half of the Motor Town vehicle spawn menu.
-- The overlay (version.dll) writes commands to %LOCALAPPDATA%\MTSpawner\cmd.txt; this mod runs them on the game
-- thread and writes state.txt (status) and vehicles.txt (every row of the game's Vehicles table) back.
-- Spawning uses the game's own MotorTownPlayerController:ServerSpawnVehicle, so spawned vehicles are real,
-- replicated to everyone and saved like any other. Only the host or a server admin may spawn.

local VERSION = "0.9.8"
local DIR = (os.getenv("LOCALAPPDATA") or ".") .. "\\MTSpawner\\"
local CMD_FILE, STATE_FILE, LIST_FILE = DIR .. "cmd.txt", DIR .. "state.txt", DIR .. "vehicles.txt"

local last_seq = nil      -- nil until leftovers from a previous session have been skipped
local message = "ready"
local list_written = false
local list_n, list_check = 0, 0  -- rows written; the table grows once mods are allowed and a world loads
local pending = nil       -- {key, at, deadline}: checks a spawn really produced a vehicle

-- Delayed work runs from the game-thread tick, never from ExecuteWithDelay's own thread: a delayed teleport called
-- from there crashed the game (2026-10-23).
local later_tasks = {}
local function later(seconds, fn) later_tasks[#later_tasks + 1] = { at = os.clock() + seconds, fn = fn } end
local function run_due_tasks()
    local now, keep, due = os.clock(), {}, {}
    for _, t in ipairs(later_tasks) do if now >= t.at then due[#due + 1] = t else keep[#keep + 1] = t end end
    later_tasks = keep
    for _, t in ipairs(due) do pcall(t.fn) end
end

local function log(fmt, ...) print(string.format("[MTSpawner] " .. fmt .. "\n", ...)) end
local function valid(o) return o ~= nil and o:IsValid() end

local function local_controller()
    local pcs = FindAllOf("MotorTownPlayerController")
    if not pcs then return nil end
    for _, pc in ipairs(pcs) do
        if valid(pc) and pc:IsLocalController() then return pc end
    end
    return nil
end

local function str(v)
    -- array elements arrive wrapped (RemoteUnrealParam); unwrap with :get() until ToString works
    for _ = 1, 3 do
        if type(v) ~= "userdata" then break end
        local ok, s = pcall(function() return v:ToString() end)
        if ok and type(s) == "string" and not s:find("RemoteUnrealParam") then return s end
        local okg, g = pcall(function() return v:get() end)
        if not okg or g == nil or g == v then break end
        v = g
    end
    return tostring(v)
end

-- Host = owns the world (single player or listen server); admin = in the server's admin list.
local function rights(pc)
    if not pc then return false, false end
    local host, admin = false, false
    pcall(function() host = pc:HasAuthority() end)
    pcall(function()
        local ps = pc.PlayerState
        if valid(ps) then
            if ps.bIsHost then host = true end
            if ps.bIsAdmin then admin = true end
        end
    end)
    return host, admin
end

local function write_list()
    local dt = StaticFindObject("/Game/DataAsset/Vehicles/Vehicles.Vehicles")
    local lib = StaticFindObject("/Script/Engine.Default__DataTableFunctionLibrary")
    if not (valid(dt) and valid(lib)) then return false end
    local names = {}
    local out = {}
    local ok = pcall(function() lib:GetDataTableRowNames(dt, out) end)
    if not ok then return false end
    local arr = out
    pcall(function() if out.get then arr = out:get() end end)
    local ok2 = pcall(function() arr:ForEach(function(_, v) names[#names + 1] = str(v) end) end)
    if not ok2 and type(arr) == "table" then
        for _, v in pairs(arr) do names[#names + 1] = str(v) end
    end
    if #names == 0 or names[1]:find("RemoteUnrealParam") or names[1]:find("^userdata") then
        log("vehicle row names unreadable (%s)", tostring(names[1])); return false
    end
    local f = io.open(LIST_FILE .. ".tmp", "w")
    if not f then return false end
    f:write(table.concat(names, "\n"), "\n")
    f:close()
    os.remove(LIST_FILE)
    os.rename(LIST_FILE .. ".tmp", LIST_FILE)
    if #names ~= list_n then log("wrote %d vehicle rows", #names) end
    list_n = #names
    return true
end

local function view_of(pc)
    -- where the player is and which way the camera faces
    local pawn = pc.Pawn
    if not valid(pawn) then return nil end
    local loc = pawn:K2_GetActorLocation()
    local yaw = 0
    pcall(function() yaw = pc:GetControlRotation().Yaw end)
    return { X = loc.X, Y = loc.Y, Z = loc.Z }, yaw
end

local function to_absolute(pc, loc)
    -- Motor Town takes absolute (origin-rebased) locations; convert in case the world origin has moved
    local gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
    local out = loc
    pcall(function()
        local r = gs:RebaseLocalOriginOntoZero(pc, loc)
        if r and r.X then out = { X = r.X, Y = r.Y, Z = r.Z } end
    end)
    return out
end

-- spawn attempts: on a dedicated server the game rejects drop points that overlap anything ("Space already
-- occupied"), and the client's origin rebasing can differ from the server's: retry higher / with the raw location
-- Game 0.7.20 changed some RPC signatures (ServerResetVehicleAt gained a 6th parameter). Read a UFunction's parameter
-- list at runtime, log it once, and build calls from it instead of hard-coding argument counts.
local SIG_LOGGED = {}
local function params_of(path)
    local f = StaticFindObject(path)
    if not (f and f:IsValid()) then log("sig %s: not found", path); return nil end
    local list = {}
    f:ForEachProperty(function(p)
        local e = { name = p:GetFName():ToString(), type = p:GetClass():GetFName():ToString() }
        if e.type == "StructProperty" then
            pcall(function()
                local fs = {}
                p:GetStruct():ForEachProperty(function(q)
                    fs[#fs + 1] = q:GetFName():ToString() .. ":" .. q:GetClass():GetFName():ToString()
                end)
                e.fields = table.concat(fs, ",")
            end)
        end
        list[#list + 1] = e
    end)
    if not SIG_LOGGED[path] then
        SIG_LOGGED[path] = true
        local parts = {}
        for _, e in ipairs(list) do parts[#parts + 1] = e.name .. ":" .. e.type .. (e.fields and ("{" .. e.fields .. "}") or "") end
        log("sig %s: %s", path, table.concat(parts, " "))
    end
    return list
end


local ATTEMPTS = {
    { z = 60,  extra = 0, rebase = true },
    { z = 180, extra = 0, rebase = false },
    { z = 300, extra = 5, rebase = true },
}
local function spawn(key, dist, use_cheat, attempt)
    attempt = attempt or 1
    local A = ATTEMPTS[attempt]
    local pc = local_controller()
    if not pc then message = "not in a game"; return end
    local host, admin = rights(pc)
    if not (host or admin) then message = "only the host or an admin can spawn vehicles"; return end
    local loc, yaw = view_of(pc)
    if not loc then message = "no player pawn yet"; return end
    dist = tonumber(dist) or 8
    local d = dist + A.extra
    local r = math.rad(yaw)
    local at = { X = loc.X + math.cos(r) * d * 100, Y = loc.Y + math.sin(r) * d * 100, Z = loc.Z + A.z }
    if use_cheat == "1" then
        local ok, err = pcall(function() pc:Cheat_AddVehicle(FName(key)) end)
        message = ok and ("Cheat_AddVehicle " .. key) or ("Cheat_AddVehicle failed: " .. tostring(err))
        log("%s", message)
        return
    end
    if admin and not host then
        -- dedicated server (0.7.20): a client's ServerSpawnVehicle is dropped, so the server mod spawns it
        local abs = A.rebase and to_absolute(pc, at) or at
        local ok, err = pcall(function()
            pc:ServerCommand(string.format("mta spawn %s %.1f %.1f %.1f %.1f", key, abs.X, abs.Y, abs.Z, yaw + 90))
        end)
        message = ok and string.format("asked the server to spawn %s %.0f m ahead (try %d)...", key, d, attempt)
            or ("spawn failed: " .. tostring(err))
        if ok then pending = { key = key, at = at, deadline = os.clock() + 4, dist = dist, attempt = attempt } end
        log("%s", message)
        return
    end
    local params = {
        VehicleKey = FName(key),
        AbsoluteLocation = A.rebase and to_absolute(pc, at) or at,
        Rotation = { Pitch = 0, Yaw = yaw + 90, Roll = 0 },   -- side-on, so it doesn't spawn nose-into you
        bResetOnSpawn = true,
        bResetIfCollide = true,
        bForceSimulate = true,
    }
    params_of("/Script/MotorTown.MotorTownPlayerController:ServerSpawnVehicle")   -- logs the 0.7.20 parameter struct once
    local ok, err = pcall(function() pc:ServerSpawnVehicle(params) end)
    if ok then
        message = string.format("spawning %s %.0f m ahead (try %d)...", key, d, attempt)
        pending = { key = key, at = at, deadline = os.clock() + 3, dist = dist, attempt = attempt }
    else
        message = "spawn failed: " .. tostring(err)
    end
    log("%s", message)
end

local function nearest_vehicle(pc, max_m)
    local loc = view_of(pc)
    if not loc then return nil end
    local best, bd = nil, (max_m or 15) * 100
    for _, v in ipairs(FindAllOf("MTVehicle") or {}) do
        if valid(v) then
            local ok, p = pcall(function() return v:K2_GetActorLocation() end)
            if ok then
                local d = math.sqrt((p.X - loc.X) ^ 2 + (p.Y - loc.Y) ^ 2 + (p.Z - loc.Z) ^ 2)
                if d < bd then best, bd = v, d end
            end
        end
    end
    return best, bd
end

local function despawn_nearest()
    local pc = local_controller()
    if not pc then message = "not in a game"; return end
    local host, admin = rights(pc)
    if not (host or admin) then message = "only the host or an admin can remove vehicles"; return end
    local v, d = nearest_vehicle(pc, 15)
    if not v then message = "no vehicle within 15 m"; return end
    local name = v:GetFullName()
    local ok, err = pcall(function() pc:ServerDespawnVehicle(v, 0) end)
    message = ok and string.format("removed %s (%.0f m away)", name:match("([%w_]+)_C") or name, d / 100)
        or ("remove failed: " .. tostring(err))
    log("%s", message)
end

-- Adjustable turbo: the garage sells PS_Turbo_Adjustable; the Tuning tab then swaps the Turbocharger part to one of
-- the hidden PS_Boost_<psi*10>psi rows (1.0 - 51.5 psi, 0.5 steps). Net_Parts is read field by field (ForEach + get),
-- which was safe in the server test; the swap goes through the game's own ServerUpdateVehiclePart, so the server
-- checks ownership as for any garage change.
local TURBO_SLOT = 7   -- EMTVehiclePartSlot::Turbocharger
local turbo = { key = "", id = nil, psi = 0 }   -- what the player's current car has fitted
local tuning_open = false   -- the menu says when its Tuning tab is visible

-- only the car being driven right now (the controller possesses it): LastVehicle can point at a car the game has
-- already freed, and reading its Net_Parts crashed the game when F8 opened (2026-10-27)
local TURBO_VEHICLE_CLASS
local function driven_vehicle(pc)
    local pawn = pc and pc.Pawn
    if not valid(pawn) then return nil end
    TURBO_VEHICLE_CLASS = TURBO_VEHICLE_CLASS or StaticFindObject("/Script/MotorTown.MTVehicle")
    local ok, is_vehicle = pcall(function() return pawn:IsA(TURBO_VEHICLE_CLASS) end)
    return (ok and is_vehicle) and pawn or nil
end

local function read_turbo(pc)
    local t = { key = "", id = nil, psi = 0 }
    local v = driven_vehicle(pc)
    if not v then return t end
    pcall(function()
        v.Net_Parts:ForEach(function(_, e)
            local p = e:get()
            if p.Slot == TURBO_SLOT then t.key = p.Key:ToString(); t.id = p.ID end
        end)
    end)
    local n = t.key:match("^PS_Boost_(%d+)psi$")
    if n then t.psi = tonumber(n) / 10 elseif t.key == "PS_Turbo_Adjustable" then t.psi = 10 end
    return t
end

local function set_boost(psi)
    local pc = local_controller()
    if not pc then message = "not in a game"; return end
    local v = driven_vehicle(pc)
    if not v then message = "get in your car first"; return end
    local t = read_turbo(pc)
    if t.psi == 0 then message = "fit the ProStreet Adjustable Turbo in the garage first"; return end
    psi = math.floor((tonumber(psi) or 10) * 2 + 0.5) / 2
    psi = math.max(1, math.min(51.5, psi))
    local key = string.format("PS_Boost_%03dpsi", math.floor(psi * 10 + 0.5))
    local ok, err = pcall(function()
        pc:ServerUpdateVehiclePart(v, TURBO_SLOT, { ID = t.id or 0, Key = FName(key), Slot = TURBO_SLOT, Damage = 0 })
    end)
    message = ok and string.format("boost set to %g psi", psi) or ("boost change failed: " .. tostring(err))
    log("%s (%s)", message, key)
    if not ok then return end
    -- The part list changed but the engine kept its old turbo (no felt difference, 2026-10-22): rebuild the car's
    -- parts the way a client does when the list replicates. On a host (single player / listen) OnRep never fires
    -- by itself; on a dedicated server it fires on the client anyway, so calling it again is harmless.
    later(0.6, function()
        local okr, e = pcall(function()
            if valid(v) then v:OnRep_Parts() end
        end)
        log("parts refresh %s %s", okr and "ok" or "failed", okr and "" or tostring(e))
    end)
end

-- Admin tab (host or server admin only). Everything goes through the game's own server functions, so the server
-- applies its usual admin checks:
--   teleport self / with car: ServerTeleportCharacter / ServerTeleportVehicle (absolute locations)
--   bring a player's car:      ServerTeleportVehicle on the car they own that is nearest to them
--   repair / refuel / flip:    ServerSetVehiclePartDamage 0 per part, ServerSetFuel to capacity, ServerResetVehicleAt
--   despawn a player's cars:   ServerDespawnVehicle on every car whose Net_OwnerPlayerState is theirs
--   time / weather:            Cheat_* when hosting; on a dedicated server ServerCommand("mta ...") for the
--                              MTAdminServer server mod, which runs the same cheats on the server
local admin_open = false   -- the menu says when its Admin tab is visible; the player list is only written then
local PLAYERS_FILE = DIR .. "players.txt"

local function require_admin()
    local pc = local_controller()
    if not pc then message = "not in a game"; return nil end
    local host, admin = rights(pc)
    if not (host or admin) then message = "only the host or an admin can do that"; return nil end
    return pc, host
end

local function player_name(ps)
    local n = ""
    pcall(function() n = ps:GetPlayerName():ToString() end)
    if n == "" then pcall(function() n = ps.PlayerNamePrivate:ToString() end) end
    return n
end

local function players()
    local out = {}
    for _, ps in ipairs(FindAllOf("MotorTownPlayerState") or {}) do
        if valid(ps) then
            local n = player_name(ps)
            if n ~= "" then out[#out + 1] = { name = n, ps = ps } end
        end
    end
    table.sort(out, function(a, b) return a.name:lower() < b.name:lower() end)
    return out
end

local function find_player(name)
    for _, p in ipairs(players()) do if p.name == name then return p.ps end end
    message = "player " .. tostring(name) .. " not found"
    return nil
end

local function write_players()
    local pc = local_controller()
    local me = pc and pc.PlayerState
    local lines = {}
    for _, p in ipairs(players()) do
        local adm = false
        pcall(function() adm = p.ps.bIsAdmin end)
        lines[#lines + 1] = p.name .. ((valid(me) and p.ps:GetAddress() == me:GetAddress()) and "\t(you)" or "\t") .. (adm and "\tadmin" or "\t")
    end
    local f = io.open(PLAYERS_FILE .. ".tmp", "w")
    if not f then return end
    f:write(table.concat(lines, "\n"), "\n")
    f:close()
    os.remove(PLAYERS_FILE)
    os.rename(PLAYERS_FILE .. ".tmp", PLAYERS_FILE)
end

local function vec(v) return { X = v.X, Y = v.Y, Z = v.Z } end

-- the car the player is driving or sitting in (nil when on foot). While driving, the controller possesses the
-- vehicle itself, so the pawn has no seat (the first version only checked the seat and never took the car along).
local VEHICLE_CLASS
local function seated_vehicle(pc)
    local pawn = pc.Pawn
    if not valid(pawn) then return nil end
    VEHICLE_CLASS = VEHICLE_CLASS or StaticFindObject("/Script/MotorTown.MTVehicle")
    local is_vehicle = false
    pcall(function() is_vehicle = pawn:IsA(VEHICLE_CLASS) end)
    if is_vehicle then return pawn end
    local seated = false
    pcall(function() seated = valid(pawn.Net_Seat) end)
    if seated and valid(pc.LastVehicle) then return pc.LastVehicle end
    local driving = false
    pcall(function() driving = valid(pc.LastVehicle) and pc.LastVehicle.Net_MovementOwnerPC:GetAddress() == pc:GetAddress() end)
    if driving then return pc.LastVehicle end
    return nil
end

local function teleport_to(pc, abs, with_car, yaw_override)
    local v = with_car == "1" and seated_vehicle(pc) or nil
    local ok, err
    if v then
        -- ServerTeleportVehicle left the car where it was in single player (2026-10-23); the game's own vehicle
        -- reset moves car and driver together, so use that, with the teleport as a fallback
        ok, err = pcall(function()
            local gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
            local loc = abs
            pcall(function() local r = gs:RebaseZeroOriginOntoLocal(pc, abs); if r and r.X then loc = { X = r.X, Y = r.Y, Z = r.Z } end end)
            local yaw = 0
            pcall(function() yaw = v:K2_GetActorRotation().Yaw end)
            yaw = yaw_override or yaw
            pc:ServerResetVehicleAt(v, loc, { Pitch = 0, Yaw = yaw, Roll = 0 }, false, true)
        end)
        if not ok then ok, err = pcall(function() pc:ServerTeleportVehicle(v, abs) end) end
    else
        ok, err = pcall(function() pc:ServerTeleportCharacter(abs, false, false) end)
    end
    return ok, err, v ~= nil
end

local function tp_player(name, with_car)
    local pc = require_admin(); if not pc then return end
    local ps = find_player(name); if not ps then return end
    local loc = vec(ps.Location)
    local abs = { X = loc.X + 300, Y = loc.Y, Z = loc.Z + 150 }   -- beside them, not inside them
    local ok, err, car = teleport_to(pc, abs, with_car)
    message = ok and string.format("teleported %sto %s", car and "with your car " or "", name) or ("teleport failed: " .. tostring(err))
    log("%s (%.0f %.0f %.0f)", message, abs.X, abs.Y, abs.Z)
end

-- ground height under an absolute X/Y, by a straight-down line trace in local (rebased) coordinates
local function ground_z(pc, abs, top_z)
    local gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
    local ks = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    local z
    pcall(function()
        local top = { X = abs.X, Y = abs.Y, Z = top_z or 300000 }
        local bottom = { X = abs.X, Y = abs.Y, Z = -100000 }
        local lt, lb = top, bottom
        pcall(function() lt = gs:RebaseZeroOriginOntoLocal(pc, top); lb = gs:RebaseZeroOriginOntoLocal(pc, bottom) end)
        local hit = {}
        -- ignore our own car / character: while held in the air above the target the trace would hit them first
        local ignore = {}
        pcall(function() if valid(pc.Pawn) then ignore[#ignore + 1] = pc.Pawn end end)
        pcall(function() if valid(pc.LastVehicle) then ignore[#ignore + 1] = pc.LastVehicle end end)
        if ks:LineTraceSingle(pc, lt, lb, 0, false, ignore, 0, hit, true, { R = 0, G = 0, B = 0, A = 0 }, { R = 0, G = 0, B = 0, A = 0 }, 0) then
            local p = hit.ImpactPoint or hit.Location
            if p then
                local back = gs:RebaseLocalOriginOntoZero(pc, { X = p.X, Y = p.Y, Z = p.Z })
                z = back.Z
            end
        end
    end)
    return z
end

-- Far away the ground isn't loaded yet, so neither the trace nor the waypoint height can be trusted (the waypoint
-- height put players under the map, 2026-10-23). Teleport 300 m above the waypoint, then keep tracing every half
-- second while the terrain streams in, and drop onto the ground as soon as it is there.
local tp_generation = 0
-- Long teleports: the destination's ground streams in a few seconds after you arrive, and until it does the car falls
-- through the world (user report 2026-10-31). So hold the car at the target point - re-placing it every 0.5 s, which
-- also zeroes its fall - until a downward trace finds the ground, then set it down 2 m above it and call done().
-- top_z limits the trace start (pickup points: just above the point, so refinery tanks / roofs aren't hit).
-- A spot where the whole rig fits: the pickup marker's own centre can be inside a loading bay, so the truck or its
-- trailer landed in a wall or on equipment and was wrecked at once (user report 2026-10-31). Try the marker and rings
-- 10 / 20 m around it, facing the current way or the marker's way, and take the first where traces over the rig's
-- footprint (5 m ahead to 18 m behind, 1.5 m each side) all hit ground at about the same height, near the marker's.
local function clear_spot(pc, abs, top_z, yaws, near_z)
    local best, best_spread
    for _, r in ipairs({ 0, 1000, 2000 }) do
        for k = 0, (r == 0 and 0 or 7) do
            local a = k * math.pi / 4
            local cx, cy = abs.X + r * math.cos(a), abs.Y + r * math.sin(a)
            for _, yaw in ipairs(yaws) do
                local fx, fy = math.cos(math.rad(yaw)), math.sin(math.rad(yaw))
                local lo, hi, ok = 1e9, -1e9, true
                for _, o in ipairs({ { 500, 0 }, { 0, 150 }, { 0, -150 }, { -900, 0 }, { -1800, 150 }, { -1800, -150 } }) do
                    local z = ground_z(pc, { X = cx + o[1] * fx - o[2] * fy, Y = cy + o[1] * fy + o[2] * fx }, top_z)
                    if not z then ok = false; break end
                    lo, hi = math.min(lo, z), math.max(hi, z)
                end
                if ok and math.abs(hi - near_z) < 400 then
                    if hi - lo < 60 then return { X = cx, Y = cy, Z = hi + 150 }, yaw end
                    if not best_spread or hi - lo < best_spread then best, best_spread = { { X = cx, Y = cy, Z = hi + 200 }, yaw }, hi - lo end
                end
            end
        end
    end
    if best then return best[1], best[2] end
end

local function teleport_settled(pc, abs, with_car, top_z, done, spot)
    tp_generation = tp_generation + 1
    local gen, tries = tp_generation, 0
    local function step()
        if gen ~= tp_generation then return end   -- a newer teleport took over
        tries = tries + 1
        local z = ground_z(pc, abs, top_z)
        if z then
            local dest, yaw = { X = abs.X, Y = abs.Y, Z = z + 200 }, nil
            if spot then
                local d, y = spot(z)
                if d then dest, yaw = d, y end
            end
            pcall(teleport_to, pc, dest, with_car, yaw)
            log("ground found after %.1f s: %.0f -> %.0f %.0f %.0f", tries * 0.5, z, dest.X, dest.Y, dest.Z)
            if done then later(1.5, function() if gen == tp_generation then done(true) end end) end
        elseif tries < 60 then
            pcall(teleport_to, pc, abs, with_car)
            later(0.5, step)
        else
            message = "the ground there didn't load - you may need to drive a bit"
            if done then done(false) end
        end
    end
    local ok, err = teleport_to(pc, abs, with_car)
    if not ok then message = "teleport failed: " .. tostring(err); log("%s", message); return false end
    later(0.5, step)
    return true
end
local function tp_waypoint(with_car)
    local pc = require_admin(); if not pc then return end
    local d
    pcall(function() d = vec(pc.PlayerState.CustomDestinationAbsoluteLocation) end)
    if not d or (d.X == 0 and d.Y == 0) then message = "set a waypoint on the map first"; return end
    local z = ground_z(pc, d)
    local abs = { X = d.X, Y = d.Y, Z = z and (z + 200) or (d.Z + 30000) }
    message = "teleporting to your waypoint..."
    teleport_settled(pc, abs, with_car, nil, function(ok) if ok then message = "teleported to your waypoint" end end)
end

-- the car a player owns that is nearest to them (their current car, normally)
local function players_car(ps)
    local loc = vec(ps.Location)
    local best, bd
    for _, v in ipairs(FindAllOf("MTVehicle") or {}) do
        local mine = false
        pcall(function() mine = valid(v.Net_OwnerPlayerState) and v.Net_OwnerPlayerState:GetAddress() == ps:GetAddress() end)
        if mine then
            local d = math.huge
            pcall(function()
                local pc = local_controller()
                local p = to_absolute(pc, v:K2_GetActorLocation())
                d = (p.X - loc.X) ^ 2 + (p.Y - loc.Y) ^ 2 + (p.Z - loc.Z) ^ 2
            end)
            if not bd or d < bd then best, bd = v, d end
        end
    end
    return best
end

local function bring_car(name)
    local pc = require_admin(); if not pc then return end
    local ps = find_player(name); if not ps then return end
    local v = players_car(ps)
    if not v then message = name .. " has no car out"; return end
    local loc, yaw = view_of(pc)
    if not loc then message = "no player pawn yet"; return end
    local r = math.rad(yaw)
    local at = to_absolute(pc, { X = loc.X + math.cos(r) * 800, Y = loc.Y + math.sin(r) * 800, Z = loc.Z + 150 })
    local ok, err = pcall(function() pc:ServerTeleportVehicle(v, at) end)
    message = ok and ("brought " .. name .. "'s car to you") or ("bring failed: " .. tostring(err))
    log("%s", message)
end

local function my_car(pc)
    local v = seated_vehicle(pc) or pc.LastVehicle
    if not valid(v) then message = "get in a car first"; return nil end
    return v
end

local function repair()
    local pc = require_admin(); if not pc then return end
    local v = my_car(pc); if not v then return end
    local slots = {}
    pcall(function() v.Net_Parts:ForEach(function(_, e) slots[#slots + 1] = e:get().Slot end) end)
    local n = 0
    for _, s in ipairs(slots) do
        if pcall(function() pc:ServerSetVehiclePartDamage(v, s, 0.0) end) then n = n + 1 end
    end
    message = string.format("repaired %d parts", n)
    log("%s", message)
end

-- after a cargo teleport: undo any knock the landing gave the truck
local function repair_quiet(pc)
    local v = seated_vehicle(pc); if not v then return end
    pcall(function() v.Net_Parts:ForEach(function(_, e) local slot = e:get().Slot; pcall(function() pc:ServerSetVehiclePartDamage(v, slot, 0.0) end) end) end)
end

local function refuel()
    local pc = require_admin(); if not pc then return end
    local v = my_car(pc); if not v then return end
    local cap = 100
    pcall(function() cap = v.FuelTankCapacityInLiter end)
    local ok, err = pcall(function() pc:ServerSetFuel(v, cap) end)
    message = ok and string.format("refuelled (%.0f L)", cap) or ("refuel failed: " .. tostring(err))
    log("%s", message)
end


local function flip()
    local pc = require_admin(); if not pc then return end
    local v = my_car(pc); if not v then return end
    local ok, err = pcall(function()
        local p = v:K2_GetActorLocation()
        local yaw = v:K2_GetActorRotation().Yaw
        local at, rot = { X = p.X, Y = p.Y, Z = p.Z + 150 }, { Pitch = 0, Yaw = yaw, Roll = 0 }
        local sig = params_of("/Script/MotorTown.MotorTownPlayerController:ServerResetVehicleAt") or {}
        local args, nstruct = {}, 0
        for _, e in ipairs(sig) do   -- by type: vehicle, location, rotation, then defaults (bools false)
            if e.type == "ObjectProperty" then args[#args + 1] = v
            elseif e.type == "StructProperty" then
                nstruct = nstruct + 1
                args[#args + 1] = (e.name:find("Rot") or nstruct == 2) and rot or at
            elseif e.type == "BoolProperty" then args[#args + 1] = false
            elseif e.type == "NameProperty" then args[#args + 1] = FName("None")
            else args[#args + 1] = 0 end
        end
        if #args == 0 then args = { v, at, rot, false, false } end
        pc:ServerResetVehicleAt(table.unpack(args))
    end)
    message = ok and "car flipped upright" or ("flip failed: " .. tostring(err))
    log("%s", message)
end

local function despawn_player(name)
    local pc = require_admin(); if not pc then return end
    local ps = find_player(name); if not ps then return end
    local n = 0
    for _, v in ipairs(FindAllOf("MTVehicle") or {}) do
        local theirs = false
        pcall(function() theirs = valid(v.Net_OwnerPlayerState) and v.Net_OwnerPlayerState:GetAddress() == ps:GetAddress() end)
        if theirs and pcall(function() pc:ServerDespawnVehicle(v, 0) end) then n = n + 1 end
    end
    message = string.format("despawned %d of %s's cars", n, name)
    log("%s", message)
end

-- Diagnostics for time/weather (the cheats did nothing in single player, 2026-10-23): log the plain number/bool/name
-- fields of the world's time and weather actors, so the next version can set the right one.
local world_dumped = false
local function dump_world_state()
    if world_dumped then return end
    world_dumped = true
    for _, cls in ipairs({ "MTTimeOfDayConfig", "MTWeatherConfig", "MTSunSky_C", "MotorTownGameState" }) do
        for _, o in ipairs(FindAllOf(cls) or {}) do
            local fields = {}
            pcall(function()
                local c = o:GetClass()
                while c and c:IsValid() do
                    c:ForEachProperty(function(prop)
                        local n = prop:GetFName():ToString()
                        local t = prop:GetClass():GetFName():ToString()
                        if (t == "FloatProperty" or t == "DoubleProperty" or t == "IntProperty" or t == "BoolProperty"
                            or t == "ByteProperty" or t == "EnumProperty") and (n:find("Time") or n:find("Day") or n:find("Speed")
                            or n:find("Weather") or n:find("Rain") or n:find("Sun") or n:find("Hour") or n:find("Cloud")) then
                            local okv, v = pcall(function() return o[n] end)
                            fields[#fields + 1] = n .. "=" .. (okv and tostring(v) or "?")
                        end
                    end)
                    c = c:GetSuperStruct()
                    if c and c:GetFName():ToString() == "Actor" then break end
                end
            end)
            log("world %s %s: %s", cls, o:GetFName():ToString(), table.concat(fields, " "))
        end
    end
end

-- Time is MTSunSky.SolarTime (hours, 0-24) and the server pushes it to players with ClientSetTimeOfDay(hours, speed,
-- day); weather is ClientSetWeatherIndex(0 sunny / 1 rain, 1 = snap). The Cheat_* functions do nothing in the
-- shipping game (2026-10-23). Calling the client functions on our own controller changes the world for us: the
-- whole world when hosting; on a dedicated server only our own view, until the server mod can run.
local time_speed = 48   -- game seconds per real second (30-minute days); remembered between buttons
local function sunsky()
    for _, o in ipairs(FindAllOf("MTSunSky_C") or {}) do if valid(o) then return o end end
end
local function world_cmd(what, arg)
    local pc, host = require_admin(); if not pc then return end
    pcall(dump_world_state)
    local sky = sunsky()
    local hour, day = 12, 1
    pcall(function() hour = sky.SolarTime; day = sky.Day end)
    local ok, err = pcall(function()
        if what == "time" then
            hour = tonumber(arg) or 12
            pc:ClientSetTimeOfDay(hour, time_speed, day)
            if valid(sky) then sky.SolarTime = hour end
        elseif what == "timespeed" then
            local x = tonumber(arg) or 1
            time_speed = x == 0 and 0 or 48 * x
            pc:ClientSetTimeOfDay(hour, time_speed, day)
        elseif what == "sunny" then pc:ClientSetWeatherIndex(0, 1)
        elseif what == "rain" then pc:ClientSetWeatherIndex(1, 1) end
    end)
    if not host then
        pcall(function() pc:ServerCommand("mta " .. what .. (arg and (" " .. arg) or "")) end)   -- for the server mod
    end
    local now = "?"
    pcall(function() now = string.format("%.2f", sunsky().SolarTime) end)
    message = ok and string.format("%s %s done (clock now %s h)%s", what, arg or "", now, host and "" or " - only you see it on a server")
        or ("failed: " .. tostring(err))
    log("%s", message)
end

-- Driving-style XP (ProStreet style). While you drive your own car, drifts, top speed, air and near misses build a
-- combo; the multiplier grows with each different kind of trick in the chain. 2.5 s without a trick banks it as XP
-- in the chosen level (Racer by default) through the game's own ClientAddExp; a crash (sudden big speed loss)
-- loses it. The overlay shows the combo as a popup (hud= / hud2= in state.txt).
local LEVEL_NAMES = { [0] = "Driver", "Taxi", "Bus", "Truck", "Racer", "Wrecker", "Police" }   -- EMTCharacterLevelType
local style = { enabled = true, level = 4, mult = 1.0 }
local combo = { points = 0, kinds = {}, last_trick = 0, label = "" }
local hud, hud2, hud2_until = "", "", 0
local last_speed, air_time = 0, 0
local near_cooldown = {}

local function ftext(s)
    local ok, t = pcall(function() return FText(s) end)
    return ok and t or nil
end

local function add_exp(pc, level, amount, why)
    local ok, err = pcall(function() pc:ClientAddExp(why, level, amount, ftext(why)) end)
    log("exp +%d %s (%s): %s", amount, LEVEL_NAMES[level] or tostring(level), why, ok and "ok" or tostring(err))
    return ok, err
end

local function kinds_count()
    local n = 0
    for _ in pairs(combo.kinds) do n = n + 1 end
    return n
end

local function trick(kind, pts)
    combo.points = combo.points + pts
    combo.kinds[kind] = true
    combo.last_trick = os.clock()
    combo.label = kind
end

local function bank(pc)
    local m = math.max(1, kinds_count())
    local exp = math.floor(combo.points * m * style.mult / 10)
    if exp > 0 then
        add_exp(pc, style.level, exp, "NFS style")
        hud2 = string.format("+%d XP  %s", exp, LEVEL_NAMES[style.level] or "")
        hud2_until = os.clock() + 3
    end
    combo = { points = 0, kinds = {}, last_trick = 0, label = "" }
end

local function airborne(v)
    local ks = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    local hit = false
    pcall(function()
        local p = v:K2_GetActorLocation()
        local h = {}
        hit = ks:LineTraceSingle(v, { X = p.X, Y = p.Y, Z = p.Z + 50 }, { X = p.X, Y = p.Y, Z = p.Z - 150 }, 0, false, {}, 0, h, true,
            { R = 0, G = 0, B = 0, A = 0 }, { R = 0, G = 0, B = 0, A = 0 }, 0)
    end)
    return not hit
end

local function style_tick(dt)
    if not style.enabled then hud = ""; return end
    local pc = local_controller()
    local v = pc and seated_vehicle(pc)
    if not v then
        if combo.points > 0 then bank(pc) end
        hud = ""; last_speed = 0; return
    end
    local vel, fwd
    if not pcall(function() vel = v:GetVelocity(); fwd = v:GetActorForwardVector() end) then return end
    local speed = math.sqrt(vel.X ^ 2 + vel.Y ^ 2) * 0.036   -- cm/s -> km/h (horizontal)
    local now = os.clock()

    -- crash: lost more than 35 km/h in one tick while a combo was running
    if combo.points > 0 and last_speed - speed > 35 then
        hud2 = "CRASHED - combo lost"; hud2_until = now + 2.5
        combo = { points = 0, kinds = {}, last_trick = 0, label = "" }
    end
    last_speed = speed

    -- drift: angle between where the car points and where it is going
    if speed > 35 then
        local hv = math.sqrt(vel.X ^ 2 + vel.Y ^ 2)
        local hf = math.sqrt(fwd.X ^ 2 + fwd.Y ^ 2)
        local cos = (vel.X * fwd.X + vel.Y * fwd.Y) / (hv * hf)
        local angle = math.deg(math.acos(math.max(-1, math.min(1, cos))))
        if angle > 12 and angle < 100 then trick("DRIFT", angle * speed / 40 * dt * 10) end
    end
    -- speed
    if speed > 180 then trick("SPEED", (50 + (speed - 180) * 5) * dt) end
    -- air
    if speed > 30 and airborne(v) then
        air_time = air_time + dt
        if air_time > 0.4 then trick("AIR", 300 * dt) end
    else
        air_time = 0
    end
    -- near miss: another vehicle passing within ~1 m of the car's side at speed
    if speed > 70 then
        local p = v:K2_GetActorLocation()
        for _, o in ipairs(FindAllOf("MTVehicle") or {}) do
            if valid(o) and o:GetAddress() ~= v:GetAddress() then
                local okp, q = pcall(function() return o:K2_GetActorLocation() end)
                if okp then
                    local d = math.sqrt((p.X - q.X) ^ 2 + (p.Y - q.Y) ^ 2 + (p.Z - q.Z) ^ 2)
                    local key = o:GetAddress()
                    if d < 330 and d > 200 and (near_cooldown[key] or 0) < now then
                        near_cooldown[key] = now + 3
                        trick("NEAR MISS", 250)
                    end
                end
            end
        end
    end

    if combo.points > 0 and now - combo.last_trick > 2.5 then bank(pc) end
    if combo.points > 0 then
        hud = string.format("%s  x%d   %d", combo.label, math.max(1, kinds_count()), math.floor(combo.points * style.mult))
    else
        hud = ""
    end
    if now > hud2_until then hud2 = "" end
end

-- Admin: add XP to yourself in any level
local function admin_xp(level, amount)
    local pc = require_admin(); if not pc then return end
    level, amount = tonumber(level) or 4, math.floor(tonumber(amount) or 0)
    if amount <= 0 then message = "enter an XP amount"; return end
    local ok, err = add_exp(pc, level, amount, "Admin")
    message = ok and string.format("added %d XP to %s", amount, LEVEL_NAMES[level] or "?") or ("XP failed: " .. tostring(err))
end

-- Admin: money. Money isn't a readable property (it lives in the game's native player data), so the menu sets an
-- exact amount (ServerSetMoney) or adds / removes (ClientAddMoney, the call the server uses to pay players).
-- Another player's money needs the server mod (ServerCommand "mta money ..."), since only the server can reach them.
local function admin_money(target, mode, amount)
    local pc, host = require_admin(); if not pc then return end
    amount = math.floor(tonumber(amount) or 0)
    local me = ""
    pcall(function() me = player_name(pc.PlayerState) end)
    if target ~= "" and target ~= me then
        local ok, err = pcall(function() pc:ServerCommand(string.format("mta money %s %d %s", mode, amount, target)) end)
        message = ok and string.format("asked the server to %s %d for %s (needs the server mod)", mode, amount, target)
            or ("money failed: " .. tostring(err))
        log("%s", message)
        return
    end
    local ok, err = pcall(function()
        if mode == "set" then pc:ServerSetMoney(amount)
        else pc:ClientAddMoney(amount, "Admin", ftext("Admin"), true, "", "") end
    end)
    message = ok and (mode == "set" and string.format("money set to %d", amount) or string.format("%s %d money", amount >= 0 and "added" or "removed", math.abs(amount)))
        or ("money failed: " .. tostring(err))
    log("%s", message)
end

-- log only: what each job paid (to check the economy pak against real payments)
pcall(function()
    RegisterHook("/Script/MotorTown.MotorTownPlayerController:ClientAddMoneyAndExp", function(ctx, context, money, level)
        local m, lt, cx = "?", "?", "?"
        pcall(function() m = money:get() end)
        pcall(function() lt = level:get() end)
        pcall(function() cx = context:get():ToString() end)
        log("job paid: %s $%s level %s", tostring(cx), tostring(m), tostring(lt))
    end)
end)

-- Admin: give or take admin rights (the game's own ServerAddAdmin / ServerRemoveAdmin; the server checks that the
-- caller is an admin, and removing another admin needs bAllowAdminToRemoveAdmin in the server config)
local function set_admin(name, on)
    local pc = require_admin(); if not pc then return end
    local ps = find_player(name); if not ps then return end
    local ok, err
    if on == "1" then
        ok, err = pcall(function() pc:ServerAddAdmin(ps, false) end)
    else
        local id
        pcall(function() id = ps.UniqueId:ToString() end)
        if not id or id == "" then pcall(function() id = ps:GetUniqueNetIdString() end) end
        if not id or id == "" then message = "couldn't read " .. name .. "'s player id; remove them in the server config"; return end
        ok, err = pcall(function() pc:ServerRemoveAdmin(id) end)
    end
    message = ok and string.format("%s admin %s", on == "1" and "made" or "removed", name) or ("admin change failed: " .. tostring(err))
    log("%s", message)
end

-- Admin: companies / corporations. The game state's Net_CompanySystem holds the companies this client knows about
-- (on a server: the ones the server syncs to you). Its property names aren't in our dumps, so the company array is
-- found by shape: an array of structs with Guid + Money + Settings fields. Changes go through the game's own RPCs
-- (ServerAddCompanyMoney, ServerAdd/RemoveCompanyVehicleSlot); the server decides whether an admin may use them.
-- companies.txt: index<TAB>name<TAB>owner<TAB>money<TAB>added slots<TAB>corp
local COMPANIES_FILE = DIR .. "companies.txt"
-- On a client the companies arrive on the player controller (Companies = ones you're in, Net_CompaniesBase = every
-- company / corporation on the server); the company system's Server_Companies is filled only where the game is the
-- server. Money is an MTShadowedInt64 (BaseValue = the amount).
local function companies()
    local out, seen = {}, {}
    local function add(arr)
        pcall(function()
            arr:ForEach(function(_, e)
                pcall(function()
                    local co = e:get()
                    local g = co.Guid
                    local k = string.format("%d.%d.%d.%d", g.A, g.B, g.C, g.D)
                    if seen[k] then return end
                    seen[k] = true
                    local name, owner, money = "", "", nil
                    pcall(function() name = co.Settings.Name:ToString() end)
                    pcall(function() owner = co.OwnerCharacterName:ToString() end)
                    pcall(function() money = co.Money.BaseValue end)
                    out[#out + 1] = { guid = { A = g.A, B = g.B, C = g.C, D = g.D }, name = name, owner = owner,
                        money = money, slots = co.AddedVehicleSlots, corp = co.bIsCorporation }
                end)
            end)
        end)
    end
    local pc = local_controller()
    if pc then add(pc.Companies); add(pc.Net_CompaniesBase) end
    pcall(function() add(FindFirstOf("MotorTownGameState").Net_CompanySystem.Server_Companies) end)
    return out
end
local function write_companies()
    local lines = {}
    for i, c in ipairs(companies()) do
        lines[#lines + 1] = string.format("%d\t%s\t%s\t%s\t%s\t%s", i, c.name ~= "" and c.name or "(unnamed)", c.owner,
            c.money and string.format("%.0f", c.money) or "?", tostring(c.slots or 0), c.corp and "corp" or "")
    end
    local f = io.open(COMPANIES_FILE .. ".tmp", "w")
    if not f then return end
    f:write(table.concat(lines, "\n"), "\n")
    f:close()
    os.remove(COMPANIES_FILE)
    os.rename(COMPANIES_FILE .. ".tmp", COMPANIES_FILE)
end
local function company_cmd(what, idx, amount)
    local pc = require_admin(); if not pc then return end
    local c = companies()[tonumber(idx) or 0]
    if not c then message = "company not found (refresh the list)"; return end
    local ok, err
    if what == "money" then
        amount = math.floor(tonumber(amount) or 0)
        ok, err = pcall(function() pc:ServerAddCompanyMoney(c.guid, 0, amount, 0, "Admin", "") end)
        message = ok and string.format("asked the server to %s $%d %s %s", amount >= 0 and "add" or "remove", math.abs(amount),
            amount >= 0 and "to" or "from", c.name) or ("company money failed: " .. tostring(err))
    elseif what == "slot_add" then
        ok, err = pcall(function() pc:ServerAddCompanyVehicleSlot(c.guid) end)
        message = ok and ("asked for one more vehicle slot for " .. c.name) or ("slot failed: " .. tostring(err))
    elseif what == "slot_remove" then
        ok, err = pcall(function() pc:ServerRemoveCompanyVehicleSlot(c.guid) end)
        message = ok and ("asked to remove a vehicle slot from " .. c.name) or ("slot failed: " .. tostring(err))
    end
    log("%s", message)
    later(1.5, write_companies)   -- the server's change arrives by replication
end

-- Admin: construction. A building under construction is an MTBuilding with a Construction actor; it is finished by
-- delivering each step's materials (cargo) to its delivery point, and the server then raises Net_BuildingStep. There
-- is no client RPC for delivering or finishing, so "Finish next step" only works where this game IS the server
-- (single player / hosting): it raises the step the way the server would and replicates it.
-- construction.txt: one line "key<TAB>step<TAB>distance m<TAB>delivered (Material xCount, ...)" for the nearest site
local CONSTRUCTION_FILE = DIR .. "construction.txt"
local function nearest_site(pc)
    local me = pc.Pawn:K2_GetActorLocation()
    local best, bd
    for _, b in ipairs(FindAllOf("MTBuilding") or {}) do
        pcall(function()
            if not (valid(b) and valid(b.Construction)) then return end
            local l = b:K2_GetActorLocation()
            local d = math.sqrt((l.X - me.X) ^ 2 + (l.Y - me.Y) ^ 2) / 100
            if d < 150 and (not bd or d < bd) then best, bd = b, d end
        end)
    end
    return best, bd
end
local function write_construction()
    local line = ""
    pcall(function()
        local pc = local_controller()
        local b, d = nearest_site(pc)
        if not b then return end
        local mats = {}
        pcall(function()
            b.Net_DeliveredMaterials:ForEach(function(_, e)
                local m = e:get()
                mats[#mats + 1] = m.MaterialKey:ToString() .. " x" .. tostring(m.Count)
            end)
        end)
        line = string.format("%s\t%d\t%.0f\t%s", b.Net_BuildingKey:ToString(), b.Net_BuildingStep, d, table.concat(mats, ", "))
    end)
    local f = io.open(CONSTRUCTION_FILE, "w")
    if f then f:write(line, "\n"); f:close() end
end
local function finish_step()
    local pc, host = require_admin(); if not pc then return end
    if not host then message = "finishing construction only works in your own world for now (the server decides)"; return end
    local b = nearest_site(pc)
    if not b then message = "no construction site within 150 m"; return end
    local ok, err = pcall(function()
        b.Net_BuildingStep = b.Net_BuildingStep + 1
        b:OnRep_BuildingStep()
        pcall(function() b:MulticastSpawnConstructionSmokes() end)
    end)
    message = ok and ("construction advanced to step " .. tostring(b.Net_BuildingStep)) or ("finish failed: " .. tostring(err))
    log("%s", message)
    later(1, write_construction)
end

-- Admin: cargo. Every job on the map is an MTDelivery in the game state's Net_DeliverySystem.Deliveries (ID, cargo,
-- count, sender / receiver points). Loading goes through the game's own ServerAcceptDelivery(ID, true, cargo space),
-- the call the job screen makes, so the server spawns real cargo that pays and counts for construction as usual.
-- The server may insist that you are at the pickup point: "Go to pickup" teleports you (and your car) there first.
-- cargo.txt: id<TAB>cargo<TAB>count<TAB>from<TAB>to<TAB>distance km (nearest first, at most 500)
local CARGO_FILE = DIR .. "cargo.txt"
-- a point's map name: "Plastic Factory 2" (DeliveryPointName text + number), else its mission name, else the actor
-- name without the _C_UAID_... suffix
local function point_name(p)
    if not valid(p) then return "?" end
    local n = ""
    pcall(function()
        n = p.DeliveryPointName.Name:ToString()
        local num = p.DeliveryPointName.Number
        if n ~= "" and num and num > 0 then n = n .. " " .. num end
    end)
    if n == "" then pcall(function() n = p.MissionPointName:ToString() end) end
    if n == "" then pcall(function() n = p:GetFName():ToString():gsub("_C_UAID.*", ""):gsub("_", " ") end) end
    return n
end
local function deliveries()
    local out = {}
    local ok, err = pcall(function()
        -- never touch the job's own SenderPoint / ReceiverPoint pointers: on a client they can be stale, and reading
        -- one crashed the game (access violation, 2026-10-31). Match the live delivery-point actors by guid instead.
        local function gk(g) return string.format("%d.%d.%d.%d", g.A, g.B, g.C, g.D) end
        local points = {}
        for _, pt in ipairs(FindAllOf("MTDeliveryPoint") or {}) do
            pcall(function() if valid(pt) then points[gk(pt.DeliveryPointGuid)] = pt end end)
        end
        local ds = FindFirstOf("MotorTownGameState").Net_DeliverySystem
        ds.Deliveries:ForEach(function(_, e)
            pcall(function()
                local d = e:get()
                out[#out + 1] = { id = d.ID, key = d.CargoKey:ToString(), n = d.NumCargos,
                    from = points[gk(d.SenderPointGuid)], to = points[gk(d.ReceiverPointGuid)] }
            end)
        end)
    end)
    if not ok then log("deliveries unreadable: %s", tostring(err)) end
    return out
end
-- construction sites all share one name, so a drop-off at a building under construction is labelled with the
-- building and its owner ("Construction Site: LargeGarage_01 (you)"), and every job shows how far its drop-off is
-- from you, so the one for your own site is the one ~0 km away
local function site_owners()
    local names, mine = {}, ""
    pcall(function() mine = local_controller().PlayerState.UniqueId:ToString() end)
    for _, p in ipairs(players()) do pcall(function() names[p.ps.UniqueId:ToString()] = p.name end) end
    local sites = {}
    for _, b in ipairs(FindAllOf("MTBuilding") or {}) do
        pcall(function()
            if not (valid(b) and valid(b.Construction)) then return end
            local id = b.Net_OwnerUniqueNetId:ToString()
            sites[#sites + 1] = { at = b:K2_GetActorLocation(), key = b.Net_BuildingKey:ToString(),
                owner = (id ~= "" and id == mine) and "you" or (names[id] or "someone offline") }
        end)
    end
    return sites
end
local function drop_name(p, sites)
    local n = point_name(p)
    pcall(function()
        local l = p:K2_GetActorLocation()
        for _, st in ipairs(sites) do
            if (st.at.X - l.X) ^ 2 + (st.at.Y - l.Y) ^ 2 < 6000 * 6000 then n = n .. ": " .. st.key .. " (" .. st.owner .. ")"; return end
        end
    end)
    return n
end
local function km(p, me)
    local d = -1
    pcall(function()
        local l = p:K2_GetActorLocation()
        d = math.sqrt((l.X - me.X) ^ 2 + (l.Y - me.Y) ^ 2) / 100000
    end)
    return d
end
local function write_cargo()
    local pc = local_controller()
    local me = pc and view_of(pc)
    local sites = site_owners()
    local rows = {}
    for _, d in ipairs(deliveries()) do rows[#rows + 1] = { d = d, dist = km(d.from, me), drop = km(d.to, me) } end
    table.sort(rows, function(a, b) return a.dist < b.dist end)
    local lines = {}
    for i = 1, math.min(#rows, 500) do
        local r = rows[i]
        lines[#lines + 1] = string.format("%d\t%s\t%d\t%s\t%s\t%.1f\t%.1f", r.d.id, r.d.key, r.d.n, point_name(r.d.from),
            drop_name(r.d.to, sites), r.dist, r.drop)
    end
    local f = io.open(CARGO_FILE .. ".tmp", "w")
    if not f then return end
    f:write(table.concat(lines, "\n"), "\n")
    f:close()
    os.remove(CARGO_FILE)
    os.rename(CARGO_FILE .. ".tmp", CARGO_FILE)
    message = string.format("%d cargo jobs on the map", #rows)
end
-- the cargo space to fill: a trailer hitched near you first, else your own vehicle's bed
local function my_cargo_space(pc)
    local car = seated_vehicle(pc) or pc.LastVehicle
    local me = view_of(pc)
    local best, best_d
    for _, c in ipairs(FindAllOf("MTVehicleCargoSpaceComponent") or {}) do
        pcall(function()
            if not (valid(c) and c.bCanLoadCargo) then return end
            local owner = c:GetOwner()
            local l = owner:K2_GetActorLocation()
            local d = math.sqrt((l.X - me.X) ^ 2 + (l.Y - me.Y) ^ 2)
            local is_car = valid(car) and owner:GetAddress() == car:GetAddress()
            if d > 3000 and not is_car then return end
            local score = is_car and d + 2000 or d   -- a trailer behind you beats the truck's own bed
            if not best_d or score < best_d then best, best_d = c, score end
        end)
    end
    return best
end
local function pickup_of(id)
    for _, d in ipairs(deliveries()) do if tostring(d.id) == id then return d end end
    message = "that job is gone (refresh)"
end
-- load the picked job only, all of its units: ServerAcceptDelivery hands out one cargo per call (user test on the
-- server 2026-11-02: one call per job loaded 1 of every order at the mill instead of the 4 planks one site needed), so
-- call it again for the same job until its count is used up, the job is gone, or the trailer stops taking more.
local function job_count(id)
    for _, d in ipairs(deliveries()) do if d.id == id then return d.n end end
    return 0
end
local function load_many(pc, job, done)
    if not my_cargo_space(pc) then message = "no truck or trailer with cargo space near you"; return end
    local want, n, stalls = math.max(1, job.n or 1), 0, 0
    local function step(k)
        local left = job_count(job.id)
        if n >= want or left <= 0 or stalls >= 2 or k > want + 4 then
            message = string.format("loaded %d of %d %s at %s", n, want, job.key, point_name(job.from)); log("%s", message)
            if done then done(n) end
            return
        end
        local space = my_cargo_space(pc)
        local before = left
        if space then pcall(function() pc:ServerAcceptDelivery(job.id, k == 1, space) end) end
        message = string.format("loading %s %d / %d...", job.key, n + 1, want)
        later(0.6, function()
            if job_count(job.id) < before then n = n + 1; stalls = 0 else stalls = stalls + 1 end
            step(k + 1)
        end)
    end
    step(1)
end
-- strap everything on the cargo space (the game's own ServerStrapCargo, as the strap button does) so the load stays
-- put through the teleport back (user 2026-11-02: cargo fell off the trailer on the return jump)
local function cargo_on(space)
    local out = {}
    pcall(function() space.Cargos:ForEach(function(_, e) local c = e:get(); if valid(c) then out[#out + 1] = c end end) end)
    if #out > 0 then return out end
    pcall(function()
        local owner = space:GetOwner(); local o = owner:K2_GetActorLocation()
        for _, c in ipairs(FindAllOf("MTCargo") or {}) do
            pcall(function()
                if not valid(c) then return end
                local parent = nil
                pcall(function() parent = c:GetAttachParentActor() end)
                local l = c:K2_GetActorLocation()
                local near = (l.X - o.X) ^ 2 + (l.Y - o.Y) ^ 2 < 900 * 900 and math.abs(l.Z - o.Z) < 400
                if (valid(parent) and parent:GetAddress() == owner:GetAddress()) or near then out[#out + 1] = c end
            end)
        end
    end)
    return out
end
local function strap_all(pc)
    local space = my_cargo_space(pc); if not space then return 0 end
    local n = 0
    for _, c in ipairs(cargo_on(space)) do
        if pcall(function() pc:ServerStrapCargo(c) end) then n = n + 1 end
    end
    log("strapped %d cargo", n)
    return n
end
local function cargo_load(id)
    local pc = require_admin(); if not pc then return end
    local job = pickup_of(id); if not job then return end
    load_many(pc, job, function() later(1.5, function() strap_all(pc) end) end)
end
-- the server only loads a job into a vehicle at its pickup point (user test 2026-10-31: loading from a distance gave
-- an error), so: teleport there with the car (a hitched trailer follows), load once it has settled, then bring the
-- car back to where it started
local function to_pickup(pc, job, done)
    if not valid(job.from) then message = "that job's pickup isn't known to your game"; return false end
    local l = job.from:K2_GetActorLocation()
    local abs = to_absolute(pc, { X = l.X, Y = l.Y, Z = l.Z + 300 })
    local yaws = {}
    pcall(function() yaws[#yaws + 1] = seated_vehicle(pc):K2_GetActorRotation().Yaw end)
    pcall(function() local y = job.from:K2_GetActorRotation().Yaw; yaws[#yaws + 1] = y; yaws[#yaws + 1] = y + 180 end)
    if #yaws == 0 then yaws[1] = 0 end
    message = "going to " .. point_name(job.from) .. "..."
    -- trace from 8 m above the marker only: higher, canopies and pipe racks over the bay count as ground
    local top = abs.Z + 500
    return teleport_settled(pc, abs, "1", top, function(ok)
        if ok then repair_quiet(pc) end
        if done then done(ok) end
    end, function(z) return clear_spot(pc, abs, top, yaws, z) end)
end
local function cargo_fetch(id)
    local pc = require_admin(); if not pc then return end
    if not seated_vehicle(pc) then message = "get in your truck first"; return end
    local job = pickup_of(id); if not job then return end
    local here = view_of(pc)
    local home = to_absolute(pc, { X = here.X, Y = here.Y, Z = here.Z + 150 })
    to_pickup(pc, job, function(ok)
        if not ok then return end
        later(1.5, function()   -- let the trailer settle
            load_many(pc, job, function(n)
                later(1.5, function()   -- let the loaded cargo settle on the bed, then strap it down
                    local st = strap_all(pc)
                    later(1.5, function()
                        teleport_settled(pc, home, "1", home.Z + 1500, function(back)
                            if back then repair_quiet(pc) end
                            message = back and string.format("back; loaded %d %s, strapped %d", n, job.key, st) or message
                        end)
                    end)
                end)
            end)
        end)
    end)
end
local function cargo_goto(id)
    local pc = require_admin(); if not pc then return end
    local job = pickup_of(id); if not job then return end
    to_pickup(pc, job, function(ok) if ok then message = "at the pickup: " .. point_name(job.from) .. " (now press Load here)" end end)
end

local function run(line)
    local parts = {}
    for p in (line .. "\t"):gmatch("([^\t]*)\t") do parts[#parts + 1] = p end
    local cmd = parts[2]
    log("cmd %s %s", tostring(cmd), tostring(parts[3]))
    if cmd == "spawn" then spawn(parts[3], parts[4], parts[5])
    elseif cmd == "despawn_nearest" then despawn_nearest()
    elseif cmd == "boost" then set_boost(parts[3])
    elseif cmd == "tuning_tab" then
        tuning_open = parts[3] == "1"
        if tuning_open then turbo = read_turbo(local_controller()) end
    elseif cmd == "admin_tab" then
        admin_open = parts[3] == "1"
        if admin_open then write_players(); write_companies(); write_construction() end
    elseif cmd == "companies_refresh" then write_companies(); write_construction(); message = "lists refreshed"
    elseif cmd == "company" then company_cmd(parts[3], parts[4], parts[5])
    elseif cmd == "finish_step" then finish_step()
    elseif cmd == "cargo_refresh" then write_cargo()
    elseif cmd == "cargo_load" then cargo_load(parts[3])
    elseif cmd == "cargo_goto" then cargo_goto(parts[3])
    elseif cmd == "cargo_fetch" then cargo_fetch(parts[3])
    elseif cmd == "tp_player" then tp_player(parts[3], parts[4])
    elseif cmd == "tp_waypoint" then tp_waypoint(parts[3])
    elseif cmd == "bring_car" then bring_car(parts[3])
    elseif cmd == "repair" then repair()
    elseif cmd == "refuel" then refuel()
    elseif cmd == "flip" then flip()
    elseif cmd == "despawn_player" then despawn_player(parts[3])
    elseif cmd == "world" then world_cmd(parts[3], parts[4])
    elseif cmd == "style" then
        style.enabled = parts[3] ~= "0"
        style.level = tonumber(parts[4]) or style.level
        style.mult = tonumber(parts[5]) or style.mult
        message = string.format("style XP %s (%s, x%g)", style.enabled and "on" or "off", LEVEL_NAMES[style.level] or "?", style.mult)
    elseif cmd == "xp" then admin_xp(parts[3], parts[4])
    elseif cmd == "money" then admin_money(parts[3] or "", parts[4], parts[5])
    elseif cmd == "set_admin" then set_admin(parts[3], parts[4])
    elseif cmd == "refresh_list" then list_written = write_list(); message = list_written and "vehicle list refreshed" or "vehicle list not available yet"
    else message = "unknown command " .. tostring(cmd) end
end

local function read_commands()
    local f = io.open(CMD_FILE, "r")
    if not f then return {} end
    local out = {}
    for line in f:lines() do
        local seq = math.tointeger(tonumber(line:match("^(%d+)\t")))
        if seq then out[#out + 1] = { seq = seq, line = line } end
    end
    f:close()
    table.sort(out, function(x, y) return x.seq < y.seq end)
    return out
end

local function write_state()
    local pc = local_controller()
    local host, admin = rights(pc)
    local in_game = pc and valid(pc.Pawn) or false
    local s = {
        "ack=" .. tostring(last_seq or 0),
        "version=" .. VERSION,
        "in_game=" .. (in_game and 1 or 0),
        "host=" .. (host and 1 or 0),
        "admin=" .. (admin and 1 or 0),
        "list=" .. (list_written and 1 or 0),
        "list_n=" .. list_n,
        "turbo=" .. turbo.key,
        "psi=" .. string.format("%g", turbo.psi),
        "tuning=" .. (tuning_open and 1 or 0),
        "admin_tab=" .. (admin_open and 1 or 0),
        "hud=" .. hud,
        "hud2=" .. hud2,
        "style=" .. (style.enabled and 1 or 0),
        "style_level=" .. style.level,
        "style_mult=" .. string.format("%g", style.mult),
        "message=" .. message:gsub("[\r\n]", " "),
    }
    local tmp = STATE_FILE .. ".tmp"
    local f = io.open(tmp, "w")
    if not f then return end
    f:write(table.concat(s, "\n"), "\n")
    f:close()
    os.remove(STATE_FILE)
    os.rename(tmp, STATE_FILE)
end

-- Don't touch the game while it is still starting up: polling from the first second (FindAllOf, DataTable reads)
-- crashed Motor Town at boot (access violation in the engine, 2026-10-19). Start after 30 s, and only read the
-- vehicle table once a player controller exists.
local busy = false
local function tick()
    if busy then return false end
    busy = true
    ExecuteInGameThread(function()
        local ok, err = pcall(function()
            list_check = list_check + 1
            if local_controller() and (not list_written or list_check % 240 == 0) then   -- every ~60 s in a session
                list_written = write_list() or list_written
            end
            local cmds = read_commands()
            if last_seq == nil then
                last_seq = cmds[#cmds] and cmds[#cmds].seq or 0
            end
            for _, c in ipairs(cmds) do
                if c.seq > last_seq then
                    last_seq = c.seq
                    run(c.line)
                end
            end
            if pending then
                local pc = local_controller()
                local found = false
                for _, v in ipairs(FindAllOf("MTVehicle") or {}) do
                    local okp, p = pcall(function() return v:K2_GetActorLocation() end)
                    if okp and (p.X - pending.at.X) ^ 2 + (p.Y - pending.at.Y) ^ 2 < 600 * 600 then found = true break end
                end
                if found then
                    message = "spawned " .. pending.key .. " (try " .. pending.attempt .. ")"; log("%s", message); pending = nil
                elseif os.clock() > pending.deadline then
                    local p_ = pending; pending = nil
                    if p_.attempt < #ATTEMPTS then
                        log("nothing appeared for %s on try %d, retrying", p_.key, p_.attempt)
                        spawn(p_.key, p_.dist, "0", p_.attempt + 1)
                    else
                        message = "nothing appeared for " .. p_.key .. " - move to open flat ground and try again"
                        log("%s", message)
                        -- diagnosis: which of the mod car's packages fails to load? (class first, then its parts)
                        local k = p_.key
                        local m = "/Game/Cars/Models/" .. k .. "/"
                        local paths = { m .. k .. "." .. k .. "_C", m .. "Body.Body", m .. "Dashboard.Dashboard",
                                m .. "SideMirror_Left.SideMirror_Left", m .. "Tailgate.Tailgate",
                                "/Game/Cars/Parts/SteeringWheels/" .. k .. "." .. k,
                                "/Game/Cars/Parts/Wheels/" .. k .. "_L." .. k .. "_L",
                                "/Game/Cars/Parts/Engine/Sound/" .. k .. "/SC_" .. k .. ".SC_" .. k,
                                -- controls from a pak that works (Diablo spawns at its dealer)
                                "/Game/Cars/Models/MW_DIABLOSV/Body.Body", "/Game/Cars/Models/MW_DIABLOSV/MW_DIABLOSV.MW_DIABLOSV_C" }
                        ExecuteInGameThread(function()   -- LoadAsset only works on the game thread
                            for _, path in ipairs(paths) do
                                local okl, a = pcall(function() return LoadAsset(path) end)
                                log("diag load %s: ok=%s valid=%s", path, tostring(okl), tostring(okl and a ~= nil and a:IsValid()))
                            end
                        end)
                    end
                end
            end
            -- only while the Tuning tab is open: reading Net_Parts in the background crashed the game when the
            -- garage's performance menu was opened (2026-10-22), so never poll it otherwise
            if tuning_open and list_check % 8 == 0 then turbo = read_turbo(local_controller()) end   -- every 2 s
            if admin_open and list_check % 8 == 0 then write_players() end
            run_due_tasks()
            pcall(style_tick, 0.25)
            write_state()
        end)
        if not ok then log("loop error: %s", tostring(err)) end
        busy = false
    end)
    return false
end
ExecuteWithDelay(30000, function()
    log("starting command loop")
    LoopAsync(250, tick)
end)

log("v%s loaded; commands from %s", VERSION, CMD_FILE)
