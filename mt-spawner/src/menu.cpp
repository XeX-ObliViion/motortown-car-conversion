// The in-game vehicle spawn menu. Game work is done by the MTSpawner Lua mod; we only send it commands.
#include <windows.h>

#include <algorithm>
#include <cfloat>
#include <cmath>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <map>
#include <set>
#include <string>
#include <vector>

#include "imgui.h"
#include "ipc.h"
#include "log.h"
#include "overlay.h"
#include "vehicles.h"

namespace {

using State = std::map<std::string, std::string>;

bool On(const State& s, const char* k) {
    auto it = s.find(k);
    return it != s.end() && it->second == "1";
}
std::string Get(const State& s, const char* k, const char* def = "") {
    auto it = s.find(k);
    return it == s.end() ? def : it->second;
}
std::string Lower(std::string s) {
    std::transform(s.begin(), s.end(), s.begin(), ::tolower);
    return s;
}

struct Entry { std::string key, name, category; bool hidden; };

const char* CategoryLabel(const std::string& c) {
    if (c == "Modded") return "Your ported cars";
    if (c == "Small") return "Cars";
    if (c == "SemiTractor") return "Semi tractors";
    if (c == "SemiTrailer") return "Semi trailers";
    if (c == "HeavyMachinery") return "Heavy machinery";
    return nullptr;
}

// The game's live Vehicles table (vehicles.txt from Lua) is the truth; names/categories come from vehicles.h.
std::vector<Entry> LoadEntries() {
    std::map<std::string, const VehicleInfo*> info;
    for (auto& v : kVehicles) info[v.key] = &v;
    std::vector<std::string> keys;
    wchar_t buf[MAX_PATH];
    GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH);
    std::wstring path = std::wstring(buf) + L"\\MTSpawner\\vehicles.txt";
    if (FILE* f = _wfopen(path.c_str(), L"rb")) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            std::string l = line;
            while (!l.empty() && (l.back() == '\n' || l.back() == '\r' || l.back() == ' ')) l.pop_back();
            if (!l.empty()) keys.push_back(l);
        }
        fclose(f);
    }
    if (keys.empty())
        for (auto& v : kVehicles) keys.push_back(v.key);
    std::vector<Entry> out;
    std::set<std::string> seen;
    for (auto& k : keys) {
        if (!seen.insert(k).second) continue;
        auto it = info.find(k);
        if (it != info.end())
            out.push_back({k, it->second->name, it->second->category, it->second->hidden});
        else if (k.rfind("PS_", 0) == 0 || k.rfind("MW_", 0) == 0)
            out.push_back({k, k, "Modded", false});
        else
            out.push_back({k, k, "Other", false});
    }
    auto rank = [](const std::string& c) { return c == "Modded" ? 0 : c == "Small" ? 1 : 2; };
    std::sort(out.begin(), out.end(), [&](const Entry& a, const Entry& b) {
        if (rank(a.category) != rank(b.category)) return rank(a.category) < rank(b.category);
        if (a.category != b.category) return a.category < b.category;
        return Lower(a.name) < Lower(b.name);
    });
    return out;
}

std::vector<Entry> g_entries;
std::string g_selected;
std::vector<std::string> g_recent;

bool g_dev_spawn;

void Spawn(const std::string& key, float dist) {
    char d[16];
    snprintf(d, sizeof d, "%.0f", dist);
    ipc::Send("spawn", {key, d, g_dev_spawn ? "1" : "0"});
    g_recent.erase(std::remove(g_recent.begin(), g_recent.end(), key), g_recent.end());
    g_recent.insert(g_recent.begin(), key);
    if (g_recent.size() > 8) g_recent.resize(8);
}

const Entry* Find(const std::string& key) {
    for (auto& e : g_entries)
        if (e.key == key) return &e;
    return nullptr;
}

bool tuning_sent;           // what Lua was last told about the Tuning tab
ULONGLONG g_menu_drawn_at;  // menu hidden (F8) = tab not visible either

// ProStreet-style popup for the driving-style combo (hud=) and the banked XP / crash line (hud2=), top centre.
bool HudWantedImpl() {
    if (!ipc::Connected()) return false;
    State s = ipc::State();
    return !Get(s, "hud").empty() || !Get(s, "hud2").empty();
}

void DrawHudImpl() {
    State s = ipc::State();
    std::string a = Get(s, "hud"), b = Get(s, "hud2");
    if (a.empty() && b.empty()) return;
    ImGuiIO& io = ImGui::GetIO();
    ImDrawList* dl = ImGui::GetForegroundDrawList();
    float big = io.DisplaySize.y * 0.045f, small = io.DisplaySize.y * 0.03f;
    float y = io.DisplaySize.y * 0.14f;
    auto line = [&](const std::string& t, float size, ImU32 col) {
        ImVec2 sz = ImGui::GetFont()->CalcTextSizeA(size, FLT_MAX, 0, t.c_str());
        ImVec2 at(io.DisplaySize.x * 0.5f - sz.x * 0.5f, y);
        dl->AddText(ImGui::GetFont(), size, ImVec2(at.x + 2, at.y + 2), IM_COL32(0, 0, 0, 200), t.c_str());
        dl->AddText(ImGui::GetFont(), size, at, col, t.c_str());
        y += sz.y + 4;
    };
    if (!a.empty()) line(a, big, IM_COL32(255, 200, 40, 255));
    if (!b.empty()) line(b, small, b.rfind("CRASHED", 0) == 0 ? IM_COL32(255, 80, 60, 255) : IM_COL32(120, 255, 140, 255));
}

const char* kLevels[] = {"Driver", "Taxi", "Bus", "Truck", "Racer", "Wrecker", "Police"};

// Admin tab (host / server admin): teleports, car tools, a player's cars, time and weather. Lua writes the player
// list (players.txt: name<TAB>(you)<TAB>admin) every 2 s while this tab is visible.
bool admin_sent;
struct Player { std::string name; bool me, admin; };
std::vector<Player> LoadPlayers() {
    std::vector<Player> out;
    wchar_t buf[MAX_PATH];
    GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH);
    std::wstring path = std::wstring(buf) + L"\\MTSpawner\\players.txt";
    if (FILE* f = _wfopen(path.c_str(), L"rb")) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            std::string l = line;
            while (!l.empty() && (l.back() == '\n' || l.back() == '\r')) l.pop_back();
            std::vector<std::string> f;
            for (size_t a = 0;;) {
                size_t b = l.find('\t', a);
                f.push_back(l.substr(a, b == std::string::npos ? std::string::npos : b - a));
                if (b == std::string::npos) break;
                a = b + 1;
            }
            if (!f[0].empty()) out.push_back({f[0], f.size() > 1 && f[1] == "(you)", f.size() > 2 && f[2] == "admin"});
        }
        fclose(f);
    }
    return out;
}

void DrawAdminTab(const State& s, bool can, bool host) {
    static std::vector<Player> players;
    static ULONGLONG loaded_at;
    static std::string target;
    static bool with_car = true;
    static float hour = 12.0f;
    static bool confirm_despawn;
    if (GetTickCount64() - loaded_at > 1000) {
        players = LoadPlayers();
        loaded_at = GetTickCount64();
    }
    if (!can) {
        ImGui::TextDisabled("Admin tools are only available to the host or a server admin, in a world.");
        return;
    }

    ImGui::SeparatorText("Players");
    ImGui::BeginChild("players", ImVec2(0, ImGui::GetTextLineHeightWithSpacing() * 5.5f), ImGuiChildFlags_Borders);
    for (auto& [name, me, adm] : players) {
        std::string label = name + (me ? "  (you)" : "") + (adm ? "  [admin]" : "");
        if (ImGui::Selectable(label.c_str(), target == name)) target = name;
    }
    if (players.empty()) ImGui::TextDisabled("Reading players...");
    ImGui::EndChild();
    bool picked = !target.empty() && std::any_of(players.begin(), players.end(), [&](auto& p) { return p.name == target; });
    bool target_admin = picked && std::any_of(players.begin(), players.end(), [&](auto& p) { return p.name == target && p.admin; });
    bool target_me = picked && std::any_of(players.begin(), players.end(), [&](auto& p) { return p.name == target && p.me; });
    ImGui::BeginDisabled(!picked || target_me);
    if (!target_admin) {
        if (ImGui::Button(("Make " + (picked ? target : std::string("player")) + " an admin").c_str())) ipc::Send("set_admin", {target, "1"});
    } else if (ImGui::Button(("Remove " + target + "'s admin").c_str())) {
        ipc::Send("set_admin", {target, "0"});
    }
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::TextDisabled("Admins with the F8 menu get this Admin tab too.");

    ImGui::SeparatorText("Teleport");
    ImGui::Checkbox("Take my car with me (when I'm in it)", &with_car);
    ImGui::BeginDisabled(!picked);
    if (ImGui::Button(("Teleport to " + (picked ? target : std::string("player"))).c_str()))
        ipc::Send("tp_player", {target, with_car ? "1" : "0"});
    ImGui::SameLine();
    if (ImGui::Button(("Bring " + (picked ? target + "'s" : std::string("their")) + " car to me").c_str()))
        ipc::Send("bring_car", {target});
    ImGui::EndDisabled();
    if (ImGui::Button("Teleport to my map waypoint")) ipc::Send("tp_waypoint", {with_car ? "1" : "0"});

    ImGui::SeparatorText("My car");
    if (ImGui::Button("Repair")) ipc::Send("repair");
    ImGui::SameLine();
    if (ImGui::Button("Refuel")) ipc::Send("refuel");
    ImGui::SameLine();
    if (ImGui::Button("Flip upright")) ipc::Send("flip");

    ImGui::SeparatorText("Player's cars");
    ImGui::BeginDisabled(!picked);
    if (!confirm_despawn) {
        if (ImGui::Button(("Despawn all of " + (picked ? target + "'s" : std::string("a player's")) + " cars").c_str()))
            confirm_despawn = true;
    } else {
        ImGui::TextColored(ImVec4(1, 0.6f, 0.4f, 1), "Despawn every car %s owns?", target.c_str());
        ImGui::SameLine();
        if (ImGui::Button("Yes, despawn")) {
            ipc::Send("despawn_player", {target});
            confirm_despawn = false;
        }
        ImGui::SameLine();
        if (ImGui::Button("Cancel")) confirm_despawn = false;
    }
    ImGui::EndDisabled();

    ImGui::SeparatorText("Time and weather");
    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 12);
    ImGui::SliderFloat("##hour", &hour, 0.0f, 24.0f, "%.1f h");
    ImGui::SameLine();
    char h[16];
    snprintf(h, sizeof h, "%.2f", hour);
    if (ImGui::Button("Set time")) ipc::Send("world", {"time", h});
    if (ImGui::Button("Freeze time")) ipc::Send("world", {"timespeed", "0"});
    ImGui::SameLine();
    if (ImGui::Button("Normal speed")) ipc::Send("world", {"timespeed", "1"});
    ImGui::SameLine();
    if (ImGui::Button("Fast (10x)")) ipc::Send("world", {"timespeed", "10"});
    if (ImGui::Button("Sunny")) ipc::Send("world", {"sunny"});
    ImGui::SameLine();
    if (ImGui::Button("Rain")) ipc::Send("world", {"rain"});
    if (!host) ImGui::TextDisabled("On a server, only you see time/weather changes for now.");

    ImGui::SeparatorText("Money");
    {
        static int money = 100000;
        bool other = picked && !target_me;
        std::string who = other ? target : std::string("me");
        ImGui::SetNextItemWidth(ImGui::GetFontSize() * 10);
        ImGui::InputInt("##money", &money, 1000, 100000);
        ImGui::SameLine();
        if (ImGui::Button(("Set " + who + " to this").c_str())) ipc::Send("money", {other ? target : "", "set", std::to_string(money)});
        ImGui::SameLine();
        if (ImGui::Button("Add")) ipc::Send("money", {other ? target : "", "add", std::to_string(money)});
        ImGui::SameLine();
        if (ImGui::Button("Remove")) ipc::Send("money", {other ? target : "", "add", std::to_string(-money)});
        ImGui::TextDisabled(other ? "Changing another player's money needs the server-side admin mod."
                                  : "Pick another player in the list above to change their money instead.");
    }

    ImGui::SeparatorText("XP");
    static int xp_level = 4;
    static int xp_amount = 1000;
    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 8);
    ImGui::Combo("##xplevel", &xp_level, kLevels, 7);
    ImGui::SameLine();
    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 8);
    ImGui::InputInt("##xpamount", &xp_amount, 100, 1000);
    xp_amount = std::max(0, xp_amount);
    ImGui::SameLine();
    if (ImGui::Button("Add XP to me")) ipc::Send("xp", {std::to_string(xp_level), std::to_string(xp_amount)});
    static float style_mult = 1.0f;
    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 12);
    if (ImGui::SliderFloat("Driving-style XP multiplier", &style_mult, 0.25f, 5.0f, "x%.2f")) {
        State st = ipc::State();
        ipc::Send("style", {Get(st, "style", "1"), Get(st, "style_level", "4"), std::to_string(style_mult)});
    }
}

// Tuning tab: the boost picker for the ProStreet Adjustable Turbo. Lua reports the fitted turbo (turbo=<row>,
// psi=<value>, 0 when it isn't the adjustable one); the picker stays locked until that part is fitted in a garage.
void DrawTuningTab(const State& s, bool connected, bool in_game) {
    static float psi = 10.0f;
    static std::string synced;
    std::string key = Get(s, "turbo");
    float fitted = (float)atof(Get(s, "psi", "0").c_str());
    if (!connected || !in_game) {
        ImGui::TextDisabled("Load into a world and get in your car.");
        return;
    }
    ImGui::SeparatorText("Driving-style XP");
    {
        bool on = Get(s, "style", "1") == "1";
        int level = std::clamp(atoi(Get(s, "style_level", "4").c_str()), 0, 6);
        bool changed = ImGui::Checkbox("Earn XP for drifts, speed, air and near misses", &on);
        ImGui::SetNextItemWidth(ImGui::GetFontSize() * 8);
        changed |= ImGui::Combo("XP goes to", &level, kLevels, 7);
        if (changed) ipc::Send("style", {on ? "1" : "0", std::to_string(level), Get(s, "style_mult", "1")});
        ImGui::TextDisabled("Chain different tricks for a bigger multiplier; a crash loses the combo.");
    }
    ImGui::SeparatorText("ProStreet Adjustable Turbo");
    if (fitted <= 0) {
        ImGui::TextWrapped("Locked. Buy and fit the \"ProStreet Adjustable Turbo\" (Turbocharger slot) on one of the NFS "
                           "cars at a garage, then come back here to set its boost.");
        ImGui::TextDisabled("Current car's turbo: %s", key.empty() ? "none" : key.c_str());
        return;
    }
    if (key != synced) {  // follow the fitted value whenever the part changes (other car, garage, last apply)
        psi = fitted;
        synced = key;
    }
    ImGui::Text("Fitted boost: %.1f psi", fitted);
    ImGui::SetNextItemWidth(-ImGui::GetFontSize() * 7);
    ImGui::SliderFloat("Boost##slider", &psi, 1.0f, 51.5f, "%.1f psi");
    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 9);
    ImGui::InputFloat("psi##input", &psi, 0.5f, 5.0f, "%.1f");
    psi = std::clamp(std::round(psi * 2.0f) / 2.0f, 1.0f, 51.5f);
    const float presets[] = {7.0f, 10.0f, 14.7f, 21.0f, 29.0f, 36.0f, 44.0f, 51.5f};
    for (int i = 0; i < 8; i++) {
        if (i) ImGui::SameLine();
        char b[16];
        snprintf(b, sizeof b, "%g##p%d", presets[i], i);
        if (ImGui::SmallButton(b)) psi = std::round(presets[i] * 2.0f) / 2.0f;
    }
    ImGui::TextDisabled("About +%.0f%% torque at full boost. More boost = more lag, heat and fuel use.", psi * 8.0f);
    char v[16];
    snprintf(v, sizeof v, "%.1f", psi);
    std::string btn = std::string("Apply ") + v + " psi";
    if (ImGui::Button(btn.c_str(), ImVec2(-1, 0))) ipc::Send("boost", {v});
    ImGui::TextDisabled("Works on cars you own. The change is saved like a garage part.");
    ImGui::TextDisabled("Use this tab outside the garage menus.");
}

}  // namespace

bool HudWanted() {
    MenuTick();  // starts the IPC if the menu hasn't been opened yet
    return HudWantedImpl();
}
void DrawHud() { DrawHudImpl(); }

void MenuTick() {
    static bool inited;
    if (!inited) {
        inited = true;
        ipc::Init();
    }
    if (tuning_sent && GetTickCount64() - g_menu_drawn_at > 500) {  // menu closed while on the Tuning tab
        ipc::Send("tuning_tab", {"0"});
        tuning_sent = false;
    }
    if (admin_sent && GetTickCount64() - g_menu_drawn_at > 500) {
        ipc::Send("admin_tab", {"0"});
        admin_sent = false;
    }
}

void DrawMenu(bool* open) {
    ImGuiIO& io = ImGui::GetIO();
    ImGui::SetNextWindowSize(ImVec2(io.DisplaySize.y * 0.62f, io.DisplaySize.y * 0.72f), ImGuiCond_FirstUseEver);
    ImGui::SetNextWindowPos(ImVec2(io.DisplaySize.x * 0.05f, io.DisplaySize.y * 0.12f), ImGuiCond_FirstUseEver);
    std::string title = std::string("Motor Town Menu") + "  |  " + overlay::ToggleKeyName() + " to hide###main";
    if (!ImGui::Begin(title.c_str(), open, ImGuiWindowFlags_NoCollapse)) {
        ImGui::End();
        return;
    }
    State s = ipc::State();
    bool connected = ipc::Connected();
    bool in_game = On(s, "in_game"), host = On(s, "host"), admin = On(s, "admin");
    static bool first = true;
    static std::string list_n;
    static ULONGLONG reload_at;
    if (first || Get(s, "list_n") != list_n || (reload_at && GetTickCount64() > reload_at)) {
        g_entries = LoadEntries();  // reload whenever the game's vehicle table changes size (mods load late)
        first = false;
        list_n = Get(s, "list_n");
        reload_at = 0;
    }

    if (!connected) {
        ImGui::TextColored(ImVec4(1, 0.45f, 0.4f, 1), "Waiting for the MTSpawner Lua mod...");
        ImGui::TextWrapped("Make sure ue4ss\\Mods\\MTSpawner is installed and listed in mods.txt.");
    } else if (!in_game) {
        ImGui::TextColored(ImVec4(1, 0.8f, 0.3f, 1), "Load into a world to spawn vehicles.");
    } else if (!host && !admin) {
        ImGui::TextColored(ImVec4(1, 0.45f, 0.4f, 1), "Spawning is only available to the host or a server admin (tuning works for everyone).");
    } else {
        ImGui::TextColored(ImVec4(0.5f, 1, 0.55f, 1), "%s", host ? "Host" : "Admin");
        ImGui::SameLine();
        ImGui::TextDisabled("|  %s", Get(s, "message").c_str());
    }
    bool can = connected && in_game && (host || admin);

    if (!ImGui::BeginTabBar("tabs")) {
        ImGui::End();
        return;
    }
    // Lua reads the car's parts only while this tab is visible (background reads crashed in the garage)
    g_menu_drawn_at = GetTickCount64();
    bool tuning_visible = ImGui::BeginTabItem("Tuning");
    if (tuning_visible != tuning_sent || (tuning_visible && connected && Get(s, "tuning") != "1")) {
        static ULONGLONG last_send;
        if (tuning_visible != tuning_sent || GetTickCount64() - last_send > 3000) {
            ipc::Send("tuning_tab", {tuning_visible ? "1" : "0"});
            last_send = GetTickCount64();
        }
        tuning_sent = tuning_visible;
    }
    if (tuning_visible) {
        DrawTuningTab(s, connected, in_game);
        ImGui::EndTabItem();
    }
    bool admin_visible = (host || admin) && ImGui::BeginTabItem("Admin");
    if (admin_visible != admin_sent) {
        ipc::Send("admin_tab", {admin_visible ? "1" : "0"});
        admin_sent = admin_visible;
    }
    if (admin_visible) {
        DrawAdminTab(s, can, host);
        ImGui::EndTabItem();
    }
    if (!ImGui::BeginTabItem("Spawner")) {
        ImGui::EndTabBar();
        ImGui::End();
        return;
    }
    static char filter[64];
    static float dist = 8.0f;
    static int cat = 0;  // 0 = all
    ImGui::SetNextItemWidth(-ImGui::GetFontSize() * 8.5f);
    ImGui::InputTextWithHint("##filter", "Search vehicles...", filter, sizeof filter);
    ImGui::SameLine();
    if (ImGui::Button("Refresh list")) {
        ipc::Send("refresh_list");
        reload_at = GetTickCount64() + 1500;  // after Lua rewrites vehicles.txt
    }

    std::vector<std::string> cats{"All"};
    for (auto& e : g_entries)
        if (std::find(cats.begin(), cats.end(), e.category) == cats.end()) cats.push_back(e.category);
    if (cat >= (int)cats.size()) cat = 0;
    for (int i = 0; i < (int)cats.size(); i++) {
        if (i) ImGui::SameLine();
        const char* lbl = i == 0 ? "All" : CategoryLabel(cats[i]);
        std::string l = (lbl ? lbl : cats[i].c_str()) + std::string("##c") + std::to_string(i);
        if (ImGui::RadioButton(l.c_str(), cat == i)) cat = i;
        if (ImGui::GetContentRegionAvail().x < ImGui::GetFontSize() * 8) ImGui::NewLine();
    }

    float footer = ImGui::GetFrameHeightWithSpacing() * 4.2f;
    ImGui::BeginChild("list", ImVec2(0, -footer), ImGuiChildFlags_Borders);
    std::string f = Lower(filter);
    std::string last_cat;
    for (auto& e : g_entries) {
        if (cat && e.category != cats[cat]) continue;
        if (!f.empty() && Lower(e.name).find(f) == std::string::npos && Lower(e.key).find(f) == std::string::npos) continue;
        if (e.category != last_cat) {
            last_cat = e.category;
            const char* lbl = CategoryLabel(e.category);
            ImGui::SeparatorText(lbl ? lbl : e.category.c_str());
        }
        std::string label = e.name + (e.name != e.key ? "  (" + e.key + ")" : "") + (e.hidden ? "  [hidden]" : "") + "##" + e.key;
        if (ImGui::Selectable(label.c_str(), g_selected == e.key, ImGuiSelectableFlags_AllowDoubleClick)) {
            g_selected = e.key;
            if (ImGui::IsMouseDoubleClicked(0) && can) Spawn(e.key, dist);
        }
    }
    ImGui::EndChild();

    ImGui::SetNextItemWidth(ImGui::GetFontSize() * 12);
    ImGui::SliderFloat("Distance ahead (m)", &dist, 4.0f, 30.0f, "%.0f");
    ImGui::SameLine();
    ImGui::Checkbox("Use developer spawn", &g_dev_spawn);
    if (ImGui::IsItemHovered())
        ImGui::SetTooltip("Spawns through the developers' AddVehicle cheat instead of the normal spawn request. "
                          "Only needed if the normal spawn doesn't produce a vehicle.");
    ImGui::BeginDisabled(!can || g_selected.empty());
    const Entry* sel = Find(g_selected);
    std::string btn = sel ? "Spawn " + sel->name : std::string("Spawn (pick a vehicle)");
    if (ImGui::Button(btn.c_str(), ImVec2(-ImGui::GetFontSize() * 11, 0))) Spawn(g_selected, dist);
    ImGui::EndDisabled();
    ImGui::SameLine();
    ImGui::BeginDisabled(!can);
    if (ImGui::Button("Remove nearest", ImVec2(-1, 0))) ipc::Send("despawn_nearest");
    if (ImGui::IsItemHovered(ImGuiHoveredFlags_AllowWhenDisabled))
        ImGui::SetTooltip("Removes the vehicle closest to you (within 15 m). Careful: it can be someone else's.");
    ImGui::EndDisabled();
    if (!g_recent.empty()) {
        ImGui::TextDisabled("Recent:");
        for (auto& k : g_recent) {
            ImGui::SameLine();
            const Entry* e = Find(k);
            ImGui::BeginDisabled(!can);
            if (ImGui::SmallButton(((e ? e->name : k) + "##r" + k).c_str())) Spawn(k, dist);
            ImGui::EndDisabled();
            if (ImGui::GetContentRegionAvail().x < ImGui::GetFontSize() * 10) ImGui::NewLine();
        }
    }
    ImGui::TextDisabled("Double-click a vehicle to spawn it in front of you.");
    ImGui::EndTabItem();
    ImGui::EndTabBar();
    ImGui::End();
}
