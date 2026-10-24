-- MTSpawner: the game-side half of the Motor Town vehicle spawn menu.
-- The overlay (version.dll) writes commands to %LOCALAPPDATA%\MTSpawner\cmd.txt; this mod runs them on the game
-- thread and writes state.txt (status) and vehicles.txt (every row of the game's Vehicles table) back.
-- Spawning uses the game's own MotorTownPlayerController:ServerSpawnVehicle, so spawned vehicles are real,
-- replicated to everyone and saved like any other. Only the host or a server admin may spawn.

local VERSION = "0.5.2"
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
    local params = {
        VehicleKey = FName(key),
        AbsoluteLocation = A.rebase and to_absolute(pc, at) or at,
        Rotation = { Pitch = 0, Yaw = yaw + 90, Roll = 0 },   -- side-on, so it doesn't spawn nose-into you
        bResetOnSpawn = true,
        bResetIfCollide = true,
        bForceSimulate = true,
    }
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

local function read_turbo(pc)
    local t = { key = "", id = nil, psi = 0 }
    local v = pc and pc.LastVehicle
    if not valid(v) then return t end
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
    local v = pc.LastVehicle
    if not valid(v) then message = "get in your car first"; return end
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

local function teleport_to(pc, abs, with_car)
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
local function ground_z(pc, abs)
    local gs = StaticFindObject("/Script/Engine.Default__GameplayStatics")
    local ks = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
    local z
    pcall(function()
        local top = { X = abs.X, Y = abs.Y, Z = 300000 }
        local bottom = { X = abs.X, Y = abs.Y, Z = -100000 }
        local lt, lb = top, bottom
        pcall(function() lt = gs:RebaseZeroOriginOntoLocal(pc, top); lb = gs:RebaseZeroOriginOntoLocal(pc, bottom) end)
        local hit = {}
        if ks:LineTraceSingle(pc, lt, lb, 0, false, {}, 0, hit, true, { R = 0, G = 0, B = 0, A = 0 }, { R = 0, G = 0, B = 0, A = 0 }, 0) then
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
local function tp_waypoint(with_car)
    local pc = require_admin(); if not pc then return end
    tp_generation = tp_generation + 1
    local gen = tp_generation
    local d
    pcall(function() d = vec(pc.PlayerState.CustomDestinationAbsoluteLocation) end)
    if not d or (d.X == 0 and d.Y == 0) then message = "set a waypoint on the map first"; return end
    local z = ground_z(pc, d)
    local abs = { X = d.X, Y = d.Y, Z = z and (z + 200) or (d.Z + 30000) }
    local ok, err, car = teleport_to(pc, abs, with_car)
    if not ok then message = "teleport failed: " .. tostring(err); log("%s", message); return end
    message = string.format("teleported %sto your waypoint%s", car and "with your car " or "", z and "" or " (finding the ground...)")
    log("%s (%.0f %.0f %.0f, ground %s, waypoint z %.0f)", message, abs.X, abs.Y, abs.Z, tostring(z), d.Z)
    if z then return end
    local tries = 0
    local function settle()
        if gen ~= tp_generation then return end   -- a newer teleport took over
        tries = tries + 1
        local z2 = ground_z(pc, d)
        if z2 then
            pcall(teleport_to, pc, { X = d.X, Y = d.Y, Z = z2 + 200 }, with_car)
            message = string.format("teleported %sto your waypoint", car and "with your car " or "")
            log("waypoint ground found after %.1f s: %.0f", tries * 0.5, z2)
        elseif tries < 40 then
            later(0.5, settle)
        else
            message = "waypoint ground didn't load - you may need to drive a bit"
            log("%s", message)
        end
    end
    later(0.5, settle)
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
        pc:ServerResetVehicleAt(v, { X = p.X, Y = p.Y, Z = p.Z + 150 }, { Pitch = 0, Yaw = yaw, Roll = 0 }, false, false)
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
        if admin_open then write_players() end
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
