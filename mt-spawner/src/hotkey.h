#pragma once
// Menu toggle key, read from an ini next to the game exe:
//   [Menu]
//   ToggleKey=F8
// Accepts F1-F24, A-Z, 0-9, HOME, END, DELETE, PAGEUP, PAGEDOWN, INSERT, PAUSE, SCROLLLOCK,
// NUMPAD0-NUMPAD9, TILDE, or a raw virtual-key code like 0x77. The file is created with the default
// the first time the game starts.
#include <windows.h>

#include <cctype>
#include <cstdlib>
#include <cstring>
#include <string>

namespace hotkey {

inline int Parse(std::string s) {
    for (auto& c : s) c = (char)toupper((unsigned char)c);
    if (s.size() == 1 && (isalnum((unsigned char)s[0]))) return s[0];
    if (s.size() >= 2 && s[0] == 'F' && isdigit((unsigned char)s[1])) {
        int n = atoi(s.c_str() + 1);
        if (n >= 1 && n <= 24) return VK_F1 + n - 1;
    }
    if (s.rfind("NUMPAD", 0) == 0 && s.size() == 7 && isdigit((unsigned char)s[6])) return VK_NUMPAD0 + (s[6] - '0');
    if (s.rfind("0X", 0) == 0) return (int)strtol(s.c_str() + 2, nullptr, 16);
    struct { const char* name; int vk; } names[] = {
        {"HOME", VK_HOME}, {"END", VK_END}, {"DELETE", VK_DELETE}, {"DEL", VK_DELETE},
        {"PAGEUP", VK_PRIOR}, {"PAGEDOWN", VK_NEXT}, {"INSERT", VK_INSERT}, {"PAUSE", VK_PAUSE},
        {"SCROLLLOCK", VK_SCROLL}, {"TILDE", VK_OEM_3}, {"~", VK_OEM_3}, {"`", VK_OEM_3},
    };
    for (auto& n : names)
        if (s == n.name) return n.vk;
    return 0;
}

// Returns the key and its display name; writes the ini with the default if it doesn't exist.
inline int Load(const char* ini_name, const char* default_key, std::string* display) {
    char path[MAX_PATH];
    GetModuleFileNameA(nullptr, path, MAX_PATH);
    if (char* slash = strrchr(path, '\\')) strcpy(slash + 1, ini_name);
    if (GetFileAttributesA(path) == INVALID_FILE_ATTRIBUTES) {
        WritePrivateProfileStringA("Menu", "ToggleKey", default_key, path);
    }
    char buf[64];
    GetPrivateProfileStringA("Menu", "ToggleKey", default_key, buf, sizeof buf, path);
    int vk = Parse(buf);
    if (!vk) {
        vk = Parse(default_key);
        strcpy(buf, default_key);
    }
    *display = buf;
    for (auto& c : *display) c = (char)toupper((unsigned char)c);
    return vk;
}

}  // namespace hotkey
