// User-set hotkeys for menu actions (Hotkeys tab). Bindings live in mt_spawner.ini [Hotkeys] as
// <action id>=<combo>, e.g. repair=CTRL+R, spawn:PS_SUPRA=F6. A combo is optional CTRL/SHIFT/ALT plus one key.
// Keys fire from the Present hook every frame, also while the menu is closed, only when the game window is in
// front and ImGui isn't taking text. The Lua mod still checks host/admin rights for each command.
#include <windows.h>

#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#include "hotkey.h"
#include "imgui.h"
#include "ipc.h"
#include "log.h"
#include "overlay.h"

namespace {

struct Action { std::string id, label, cmd; std::vector<std::string> args; };
struct Binding { int vk = 0; bool ctrl = false, shift = false, alt = false; bool down = false; };

std::vector<Action> g_actions;
std::vector<Binding> g_binds;
int g_capturing = -1;         // index being set, -2 = the menu toggle key
bool g_loaded;
std::string g_ini;

const std::vector<Action>& BaseActions() {
    static const std::vector<Action> a = {
        {"repair", "Repair my car", "repair", {}},
        {"refuel", "Refuel my car", "refuel", {}},
        {"flip", "Flip my car upright", "flip", {}},
        {"tp_waypoint_car", "Teleport to map waypoint (with car)", "tp_waypoint", {"1"}},
        {"tp_waypoint", "Teleport to map waypoint (on foot)", "tp_waypoint", {"0"}},
        {"despawn_nearest", "Remove nearest vehicle", "despawn_nearest", {}},
        {"time_freeze", "Freeze time", "world", {"timespeed", "0"}},
        {"time_normal", "Normal time speed", "world", {"timespeed", "1"}},
        {"time_fast", "Fast time (10x)", "world", {"timespeed", "10"}},
        {"sunny", "Weather: sunny", "world", {"sunny"}},
        {"rain", "Weather: rain", "world", {"rain"}},
    };
    return a;
}

std::string KeyName(int vk) {
    if (vk >= 'A' && vk <= 'Z') return std::string(1, (char)vk);
    if (vk >= '0' && vk <= '9') return std::string(1, (char)vk);
    if (vk >= VK_F1 && vk <= VK_F24) return "F" + std::to_string(vk - VK_F1 + 1);
    if (vk >= VK_NUMPAD0 && vk <= VK_NUMPAD9) return "NUMPAD" + std::to_string(vk - VK_NUMPAD0);
    struct { int vk; const char* n; } names[] = {
        {VK_HOME, "HOME"}, {VK_END, "END"}, {VK_DELETE, "DELETE"}, {VK_PRIOR, "PAGEUP"}, {VK_NEXT, "PAGEDOWN"},
        {VK_INSERT, "INSERT"}, {VK_PAUSE, "PAUSE"}, {VK_SCROLL, "SCROLLLOCK"}, {VK_OEM_3, "TILDE"},
    };
    for (auto& n : names)
        if (n.vk == vk) return n.n;
    char b[8];
    snprintf(b, sizeof b, "0x%02X", vk);
    return b;
}

std::string ComboName(const Binding& b) {
    if (!b.vk) return "";
    return std::string(b.ctrl ? "CTRL+" : "") + (b.shift ? "SHIFT+" : "") + (b.alt ? "ALT+" : "") + KeyName(b.vk);
}

Binding ParseCombo(std::string s) {
    Binding b;
    for (auto& c : s) c = (char)toupper((unsigned char)c);
    size_t p;
    while ((p = s.find('+')) != std::string::npos && p + 1 < s.size()) {
        std::string m = s.substr(0, p);
        if (m == "CTRL") b.ctrl = true; else if (m == "SHIFT") b.shift = true; else if (m == "ALT") b.alt = true;
        s = s.substr(p + 1);
    }
    b.vk = hotkey::Parse(s);
    return b;
}

void Load() {
    g_loaded = true;
    char path[MAX_PATH];
    GetModuleFileNameA(nullptr, path, MAX_PATH);
    if (char* slash = strrchr(path, '\\')) strcpy(slash + 1, "mt_spawner.ini");
    g_ini = path;
    g_actions = BaseActions();
    // spawn bindings are saved as spawn:<vehicle key>
    std::vector<char> keys(32768);
    DWORD n = GetPrivateProfileStringA("Hotkeys", nullptr, "", keys.data(), (DWORD)keys.size(), g_ini.c_str());
    for (DWORD i = 0; i < n;) {
        std::string k = keys.data() + i;
        i += (DWORD)k.size() + 1;
        if (k.rfind("spawn:", 0) == 0) g_actions.push_back({k, "Spawn " + k.substr(6), "spawn", {k.substr(6), "8", "0"}});
    }
    g_binds.assign(g_actions.size(), {});
    for (size_t i = 0; i < g_actions.size(); ++i) {
        char buf[64];
        GetPrivateProfileStringA("Hotkeys", g_actions[i].id.c_str(), "", buf, sizeof buf, g_ini.c_str());
        g_binds[i] = ParseCombo(buf);
    }
}

void Save(size_t i) {
    std::string v = ComboName(g_binds[i]);
    WritePrivateProfileStringA("Hotkeys", g_actions[i].id.c_str(), v.empty() ? nullptr : v.c_str(), g_ini.c_str());
}

bool Mod(int vk) { return (GetAsyncKeyState(vk) & 0x8000) != 0; }

// one fresh key press for the capture: any key except mouse buttons and the modifiers themselves
int CaptureKey() {
    static bool held[256];
    int hit = 0;
    for (int vk = 0x08; vk <= 0xFE; ++vk) {
        if (vk == VK_SHIFT || vk == VK_CONTROL || vk == VK_MENU || (vk >= VK_LSHIFT && vk <= VK_RMENU) ||
            vk == VK_LWIN || vk == VK_RWIN)
            continue;
        bool d = Mod(vk);
        if (d && !held[vk] && !hit) hit = vk;
        held[vk] = d;
    }
    return hit;
}

}  // namespace

// every frame, menu open or not
void HotkeysTick() {
    if (!g_loaded) Load();
    if (!overlay::MenuOpen()) g_capturing = -1;   // menu closed mid-capture
    if (g_capturing != -1) return;  // the next press is being captured, don't fire anything
    HWND fg = GetForegroundWindow();
    DWORD pid = 0;
    GetWindowThreadProcessId(fg, &pid);
    bool game_front = pid == GetCurrentProcessId();
    bool typing = overlay::MenuOpen() && ImGui::GetCurrentContext() && ImGui::GetIO().WantTextInput;
    bool ctrl = Mod(VK_CONTROL), shift = Mod(VK_SHIFT), alt = Mod(VK_MENU);
    for (size_t i = 0; i < g_binds.size(); ++i) {
        Binding& b = g_binds[i];
        if (!b.vk) continue;
        bool d = Mod(b.vk);
        if (d && !b.down && game_front && !typing && b.ctrl == ctrl && b.shift == shift && b.alt == alt) {
            ipc::Send(g_actions[i].cmd, g_actions[i].args);
            Log("[hotkeys] %s -> %s", ComboName(b).c_str(), g_actions[i].id.c_str());
        }
        b.down = d;
    }
}

void DrawHotkeysTab(const std::string& selected_key, const std::string& selected_name) {
    if (!g_loaded) Load();
    if (g_capturing != -1) {
        int vk = CaptureKey();
        if (vk == VK_ESCAPE) g_capturing = -1;
        else if (vk) {
            if (g_capturing == -2) {
                overlay::SetToggleKey(vk, KeyName(vk).c_str());
            } else {
                Binding& b = g_binds[g_capturing];
                b = {vk, Mod(VK_CONTROL), Mod(VK_SHIFT), Mod(VK_MENU), true};   // down: don't fire on this press
                Save(g_capturing);
            }
            g_capturing = -1;
        }
    } else {
        CaptureKey();   // keep the held-state current so the click that starts a capture isn't taken as the key
    }

    ImGui::TextWrapped("Click Set, then press a key (hold Ctrl / Shift / Alt for a combo). Esc cancels. "
                       "Hotkeys work with the menu closed. Admin actions still need host or admin rights.");
    ImGui::TextDisabled("Pick keys the game doesn't use, or both will happen.");
    ImGui::Separator();

    auto row = [](const char* label, const std::string& combo, int idx, bool clearable) {
        ImGui::PushID(idx);
        ImGui::AlignTextToFramePadding();
        ImGui::TextUnformatted(label);
        ImGui::SameLine(ImGui::GetFontSize() * 18);
        bool cap = g_capturing == idx;
        ImGui::SetNextItemWidth(ImGui::GetFontSize() * 9);
        ImGui::TextColored(cap ? ImVec4(1, 0.8f, 0.3f, 1) : ImVec4(0.6f, 0.9f, 1, 1), "%s",
                           cap ? "press a key..." : (combo.empty() ? "-" : combo.c_str()));
        ImGui::SameLine(ImGui::GetFontSize() * 27);
        if (ImGui::SmallButton("Set")) g_capturing = idx;
        bool cleared = false;
        if (clearable) {
            ImGui::SameLine();
            cleared = ImGui::SmallButton("Clear");
        }
        ImGui::PopID();
        return cleared;
    };

    row("Open / close this menu", overlay::ToggleKeyName(), -2, false);
    ImGui::Separator();
    for (size_t i = 0; i < g_actions.size(); ++i) {
        if (row(g_actions[i].label.c_str(), ComboName(g_binds[i]), (int)i, true)) {
            g_binds[i] = {};
            Save(i);
            if (g_actions[i].cmd == "spawn") {   // a cleared spawn binding disappears from the list
                g_actions.erase(g_actions.begin() + i);
                g_binds.erase(g_binds.begin() + i);
                break;
            }
        }
    }
    ImGui::Separator();
    ImGui::BeginDisabled(selected_key.empty());
    std::string btn = selected_key.empty() ? std::string("Add a spawn hotkey (select a vehicle in Spawner first)")
                                           : "Add a spawn hotkey for " + selected_name;
    if (ImGui::Button(btn.c_str())) {
        std::string id = "spawn:" + selected_key;
        int found = -1;
        for (size_t i = 0; i < g_actions.size(); ++i)
            if (g_actions[i].id == id) found = (int)i;
        if (found < 0) {
            g_actions.push_back({id, "Spawn " + selected_name, "spawn", {selected_key, "8", "0"}});
            g_binds.push_back({});
            found = (int)g_actions.size() - 1;
        }
        g_capturing = found;
    }
    ImGui::EndDisabled();
}
