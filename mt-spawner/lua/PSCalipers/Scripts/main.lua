-- PSCalipers: front brake calipers that steer with the wheel but do not spin with it.
-- Motor Town's wheel (MHWheelComponent) is one mesh that both steers and spins, so a caliper can't simply be part of
-- it. For each listed car this adds one StaticMeshComponent per front wheel on the body and, every frame, puts it at
-- the wheel's hub (body space) turned by the wheel's axle direction: steering yaw only, no spin.
-- Caliper meshes are modelled in hub space (origin = hub, car axes). Without this mod the car just has no front calipers.
local CARS = {
    AC_SUPRA_C = { FL = "/Game/Cars/Models/AC_SUPRA/CaliperFL.CaliperFL", FR = "/Game/Cars/Models/AC_SUPRA/CaliperFR.CaliperFR" },
}
local state = {}      -- vehicle full name -> {veh=, pairs={{wheel=, comp=}, ...}}
local SMC, WHEEL, KML
local UP = { X = 0.0, Y = 0.0, Z = 1.0 }

local function valid(o) return o ~= nil and o:IsValid() end
local function log(m) print("[PSCalipers] " .. m .. "\n") end

local function load_mesh(path)
    local m = StaticFindObject(path)
    if valid(m) then return m, "found" end
    local ok, r = pcall(LoadAsset, path)
    if ok and valid(r) then return r, "LoadAsset" end
    m = StaticFindObject(path)
    if valid(m) then return m, "found after LoadAsset" end
    return nil, "LoadAsset failed: " .. tostring(r)
end

local function setup(veh, cfg)
    local wheels = veh:K2_GetComponentsByClass(WHEEL)
    local out = {}
    for i = 1, #wheels do
        local w = wheels[i]:get()
        local l = w.RelativeLocation
        if l.X > 0 then   -- front axle (steered)
            local path = l.Y < 0 and cfg.FL or cfg.FR
            local mesh, how = load_mesh(path)
            if not mesh then
                log("caliper mesh not loaded: " .. path .. " (" .. how .. ")")
                goto continue
            end
            local tf = { Rotation = { X = 0.0, Y = 0.0, Z = 0.0, W = 1.0 }, Translation = { X = l.X, Y = l.Y, Z = l.Z }, Scale3D = { X = 1.0, Y = 1.0, Z = 1.0 } }
            local okc, c = pcall(function() return veh:AddComponentByClass(SMC, false, tf, false) end)
            if okc and valid(c) and mesh then
                c:SetStaticMesh(mesh)
                pcall(function() c:SetCollisionEnabled(0) end)   -- NoCollision: visual only
                out[#out + 1] = { wheel = w, comp = c }
                log("caliper " .. path .. " on " .. veh:GetFName():ToString() .. " (" .. how .. ")")
            else
                log(string.format("could not add caliper %s on %s: mesh=%s (%s) component=%s %s", path, veh:GetFName():ToString(),
                    tostring(mesh ~= nil), how, tostring(okc), okc and tostring(c ~= nil and c:IsValid()) or tostring(c)))
            end
        end
        ::continue::
    end
    return out
end

local function update(p)
    local w, c = p.wheel, p.comp
    local y = KML:GetRightVector(w.RelativeRotation)              -- axle direction in body space
    if y.Y < 0 then y = { X = -y.X, Y = -y.Y, Z = -y.Z } end      -- some wheels are flipped 180 deg: keep the axle pointing right
    local rot = KML:MakeRotFromYZ(y, UP)
    c:K2_SetRelativeLocationAndRotation(w.RelativeLocation, rot, false, {}, false)
end

local frame, errlogged = 0, false
local function scan()
    local seen = {}
    for cls, cfg in pairs(CARS) do
        for _, veh in ipairs(FindAllOf(cls) or {}) do
            if valid(veh) then
                local key = veh:GetFullName()
                if not key:find("Default__") then
                    seen[key] = true
                    local s = state[key]
                    if not s or not valid(s.veh) or (#s.pairs == 0 and s.tries < 5) then
                        local tries = s and s.tries or 0
                        state[key] = { veh = veh, pairs = setup(veh, cfg), tries = tries + 1 }
                    end
                end
            end
        end
    end
    for k in pairs(state) do if not seen[k] then state[k] = nil end end
end

local function tick()
    SMC = SMC or StaticFindObject("/Script/Engine.StaticMeshComponent")
    WHEEL = WHEEL or StaticFindObject("/Script/MotorTown.MHWheelComponent")
    KML = KML or StaticFindObject("/Script/Engine.Default__KismetMathLibrary")
    if not (valid(SMC) and valid(WHEEL) and valid(KML)) then return end
    if frame % 60 == 0 then scan() end   -- FindAllOf walks every object: once a second is plenty for spawns
    frame = frame + 1
    for _, s in pairs(state) do
        if valid(s.veh) then
            for _, p in ipairs(s.pairs) do
                if valid(p.wheel) and valid(p.comp) then
                    local ok, err = pcall(update, p)
                    if not ok and not errlogged then log("update error: " .. tostring(err)); errlogged = true end
                end
            end
        end
    end
end

LoopAsync(16, function()
    ExecuteInGameThread(function()
        local ok, err = pcall(tick)
        if not ok and not errlogged then log("tick error: " .. tostring(err)); errlogged = true end
    end)
    return false
end)
log("loaded")
