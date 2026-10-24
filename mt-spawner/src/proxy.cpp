// version.dll proxy: modules loaded by MotorTown-Win64-Shipping.exe import VERSION.dll, so Windows loads this DLL from the
// game's Win64 folder. Every export jumps straight to the real system version.dll, so signatures
// don't matter here. On load we start the overlay.
#include <windows.h>

#include "log.h"
#include "overlay.h"

#define VERSION_EXPORTS(X)                                                                         \
    X(GetFileVersionInfoA) X(GetFileVersionInfoByHandle) X(GetFileVersionInfoExA)                  \
    X(GetFileVersionInfoExW) X(GetFileVersionInfoSizeA) X(GetFileVersionInfoSizeExA)               \
    X(GetFileVersionInfoSizeExW) X(GetFileVersionInfoSizeW) X(GetFileVersionInfoW) X(VerFindFileA) \
    X(VerFindFileW) X(VerInstallFileA) X(VerInstallFileW) X(VerLanguageNameA) X(VerLanguageNameW)  \
    X(VerQueryValueA) X(VerQueryValueW)

// One pointer per export, filled before anything can call them (DllMain runs first).
#define DECLARE_PTR(name) extern "C" void* real_##name = nullptr;
VERSION_EXPORTS(DECLARE_PTR)

// Naked stubs: tail-jump through the pointer, leaving every argument register untouched.
#define DEFINE_STUB(name) \
    extern "C" __attribute__((naked)) void proxy_##name() { __asm__("jmp *real_" #name "(%rip)"); }
VERSION_EXPORTS(DEFINE_STUB)

namespace {

void LoadReal() {
    wchar_t path[MAX_PATH];
    GetSystemDirectoryW(path, MAX_PATH);
    lstrcatW(path, L"\\version.dll");
    HMODULE real = LoadLibraryW(path);
#define RESOLVE(name) real_##name = real ? (void*)GetProcAddress(real, #name) : nullptr;
    VERSION_EXPORTS(RESOLVE)
}

BOOL CALLBACK FindOurWindow(HWND h, LPARAM found) {
    DWORD pid = 0;
    GetWindowThreadProcessId(h, &pid);
    if (pid == GetCurrentProcessId() && IsWindowVisible(h)) {
        *(bool*)found = true;
        return FALSE;
    }
    return TRUE;
}

DWORD WINAPI Boot(LPVOID) {
    Log("MT Spawner v0.1.0 starting");
    for (int i = 0; i < 600; ++i) {  // wait up to 2 minutes for the game window
        bool found = false;
        EnumWindows(FindOurWindow, (LPARAM)&found);
        if (found) break;
        Sleep(200);
    }
    overlay::Install();
    return 0;
}

}  // namespace

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID) {
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        LoadReal();
        wchar_t exe[MAX_PATH];
        GetModuleFileNameW(nullptr, exe, MAX_PATH);
        const wchar_t* name = wcsrchr(exe, L'\\');
        if (name && lstrcmpiW(name + 1, L"MotorTown-Win64-Shipping.exe") == 0)
            CloseHandle(CreateThread(nullptr, 0, Boot, nullptr, 0, nullptr));
    }
    return TRUE;
}
