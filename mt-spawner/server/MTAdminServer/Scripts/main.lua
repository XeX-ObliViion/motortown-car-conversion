-- MTAdminServer: server-side half of the F8 menu's Admin tab (time and weather on a dedicated server).
-- The menu sends ServerCommand("mta <what> [arg]"); this hook runs on the server, checks that the sender is an
-- admin (PlayerState.bIsAdmin) and runs the game's own cheat on the server, which replicates to every player.
local VERSION = "0.2.0"
local function log(fmt, ...) print(string.format("[MTAdminServer] " .. fmt .. "\n", ...)) end

local function find_pc(name)
    for _, p in ipairs(FindAllOf("MotorTownPlayerController") or {}) do
        local n = ""
        pcall(function() n = p.PlayerState:GetPlayerName():ToString() end)
        if n == name then return p end
    end
end

local function handle(pc, cmd)
    local mode, amount, target = cmd:match("^mta%s+money%s+(%S+)%s+(%-?%d+)%s+(.+)$")
    if mode then
        local admin = false
        pcall(function() admin = pc.PlayerState.bIsAdmin end)
        if not admin then log("refused %s (not admin)", cmd); return end
        local t = find_pc(target)
        if not t then log("money: player %s not found", target); return end
        local ok, err = pcall(function()
            if mode == "set" then t:ServerSetMoney(tonumber(amount))
            else t:ClientAddMoney(tonumber(amount), "Admin", FText("Admin"), true, "", "") end
        end)
        log("money %s %s for %s: %s", mode, amount, target, ok and "ok" or tostring(err))
        return
    end
    local what, arg = cmd:match("^mta%s+(%S+)%s*(%S*)")
    if not what then return end
    local admin = false
    pcall(function() admin = pc.PlayerState.bIsAdmin end)
    local who = "?"
    pcall(function() who = pc.PlayerState:GetPlayerName():ToString() end)
    if not admin then log("refused %s from %s (not admin)", cmd, who); return end
    local ok, err = pcall(function()
        if what == "time" then pc:Cheat_TimeOfDay(tonumber(arg) or 12)
        elseif what == "timespeed" then pc:Cheat_TimeOfDaySpeed(tonumber(arg) or 1)
        elseif what == "sunny" then pc:Cheat_Sunny()
        elseif what == "rain" then pc:Cheat_Rain()
        else error("unknown command") end
    end)
    log("%s %s from %s: %s", what, arg, who, ok and "ok" or tostring(err))
end

-- the controller class isn't loaded yet when mods start: retry until the hook registers
local function try_hook()
    local f = StaticFindObject("/Script/MotorTown.MotorTownPlayerController:ServerCommand")
    if not (f and f:IsValid()) then return false end
    local ok, err = pcall(function()
        RegisterHook("/Script/MotorTown.MotorTownPlayerController:ServerCommand", function(ctx, command)
            local pc, cmd = ctx:get(), ""
            pcall(function() cmd = command:get():ToString() end)
            if cmd:sub(1, 4) == "mta " then
                ExecuteInGameThread(function() pcall(handle, pc, cmd) end)
            end
        end)
    end)
    log("hook %s", ok and "registered" or ("failed: " .. tostring(err)))
    return true
end
log("v%s loaded", VERSION)
LoopAsync(2000, function() return try_hook() end)
