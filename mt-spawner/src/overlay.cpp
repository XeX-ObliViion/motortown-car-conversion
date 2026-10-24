#include "overlay.h"
#include "hotkey.h"
#include "log.h"

#include <windows.h>
#include <d3d12.h>
#include <dxgi1_4.h>
#include <MinHook.h>

#include <atomic>
#include <string>
#include <vector>

#include "imgui.h"
#include "imgui_impl_dx12.h"
#include "imgui_impl_win32.h"

extern IMGUI_IMPL_API LRESULT ImGui_ImplWin32_WndProcHandler(HWND, UINT, WPARAM, LPARAM);

namespace overlay {
namespace {

using present_t = HRESULT(__stdcall*)(IDXGISwapChain3*, UINT, UINT);
using resize_t = HRESULT(__stdcall*)(IDXGISwapChain3*, UINT, UINT, UINT, DXGI_FORMAT, UINT);
using resize1_t = HRESULT(__stdcall*)(IDXGISwapChain3*, UINT, UINT, UINT, DXGI_FORMAT, UINT, const UINT*, IUnknown* const*);
using exec_t = void(__stdcall*)(ID3D12CommandQueue*, UINT, ID3D12CommandList* const*);
using setcursorpos_t = BOOL(WINAPI*)(int, int);
using clipcursor_t = BOOL(WINAPI*)(const RECT*);

present_t o_present;
resize_t o_resize;
resize1_t o_resize1;
exec_t o_exec;
setcursorpos_t o_setcursorpos;
clipcursor_t o_clipcursor;

struct Frame {
    ID3D12CommandAllocator* alloc = nullptr;
    ID3D12Resource* back = nullptr;
    D3D12_CPU_DESCRIPTOR_HANDLE rtv{};
    UINT64 fence_value = 0;
};

IDXGISwapChain3* g_sc;   // swap chain the frames were built for (not AddRef'd: identity check only)

HWND g_hwnd;
WNDPROC g_wndproc;
ID3D12Device* g_dev;
std::atomic<ID3D12CommandQueue*> g_queue{nullptr};
ID3D12DescriptorHeap* g_rtv_heap;
ID3D12DescriptorHeap* g_srv_heap;
ID3D12GraphicsCommandList* g_list;
ID3D12Fence* g_fence;
HANDLE g_fence_event;
UINT64 g_fence_next = 1;
std::vector<Frame> g_frames;
DXGI_FORMAT g_format;
bool g_imgui_ready, g_frames_ready, g_failed;
std::atomic<bool> g_open{false};
bool g_toggle_down;

int g_toggle_key = VK_F8;
std::string g_toggle_name = "F8";

void WaitFrame(Frame& f) {
    if (f.fence_value && g_fence->GetCompletedValue() < f.fence_value) {
        g_fence->SetEventOnCompletion(f.fence_value, g_fence_event);
        WaitForSingleObject(g_fence_event, 1000);
    }
}

void ReleaseFrames() {
    for (auto& f : g_frames) {
        WaitFrame(f);
        if (f.alloc) f.alloc->Release();
    }
    g_frames.clear();
    if (g_rtv_heap) { g_rtv_heap->Release(); g_rtv_heap = nullptr; }
    g_frames_ready = false;
}

bool CreateFrames(IDXGISwapChain3* sc) {
    DXGI_SWAP_CHAIN_DESC d;
    sc->GetDesc(&d);
    UINT n = d.BufferCount;
    g_format = d.BufferDesc.Format;
    D3D12_DESCRIPTOR_HEAP_DESC hd{D3D12_DESCRIPTOR_HEAP_TYPE_RTV, n, D3D12_DESCRIPTOR_HEAP_FLAG_NONE, 0};
    if (FAILED(g_dev->CreateDescriptorHeap(&hd, IID_PPV_ARGS(&g_rtv_heap)))) return false;
    UINT step = g_dev->GetDescriptorHandleIncrementSize(D3D12_DESCRIPTOR_HEAP_TYPE_RTV);
    D3D12_CPU_DESCRIPTOR_HANDLE h = g_rtv_heap->GetCPUDescriptorHandleForHeapStart();
    g_frames.resize(n);
    for (UINT i = 0; i < n; ++i) {
        Frame& f = g_frames[i];
        if (FAILED(g_dev->CreateCommandAllocator(D3D12_COMMAND_LIST_TYPE_DIRECT, IID_PPV_ARGS(&f.alloc)))) return false;
        // No back-buffer reference is kept between frames: holding them blocked Unreal from rebuilding its swap
        // chain while a save loaded, which it reported as "Out of video memory" (2026-10-19).
        f.rtv = h;
        h.ptr += step;
    }
    if (!g_list) {
        if (FAILED(g_dev->CreateCommandList(0, D3D12_COMMAND_LIST_TYPE_DIRECT, g_frames[0].alloc, nullptr, IID_PPV_ARGS(&g_list))))
            return false;
        g_list->Close();
    }
    g_frames_ready = true;
    g_sc = sc;
    return true;
}

bool IsInputMsg(UINT m) {
    return (m >= WM_MOUSEFIRST && m <= WM_MOUSELAST) || (m >= WM_KEYFIRST && m <= WM_KEYLAST) ||
           m == WM_INPUT || m == WM_CHAR || m == WM_SETCURSOR;
}

LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    if (g_open) {
        ImGui_ImplWin32_WndProcHandler(h, m, w, l);
        if (IsInputMsg(m)) return m == WM_INPUT ? DefWindowProcW(h, m, w, l) : 0;
    }
    return CallWindowProcW(g_wndproc, h, m, w, l);
}

void SetOpen(bool open) {
    g_open = open;
    ImGui::GetIO().MouseDrawCursor = open;
    // with the menu closed ImGui still draws the driving-style popup; keep it away from the game's cursor
    if (open) ImGui::GetIO().ConfigFlags &= ~ImGuiConfigFlags_NoMouseCursorChange;
    else ImGui::GetIO().ConfigFlags |= ImGuiConfigFlags_NoMouseCursorChange;
    if (open) {
        o_clipcursor(nullptr);
        RECT r;
        GetClientRect(g_hwnd, &r);
        POINT c{(r.right - r.left) / 2, (r.bottom - r.top) / 2};
        ClientToScreen(g_hwnd, &c);
        o_setcursorpos(c.x, c.y);
    } else {
        // Unreal re-captures the mouse on the next click into the viewport.
    }
}

void SrvAlloc(ImGui_ImplDX12_InitInfo*, D3D12_CPU_DESCRIPTOR_HANDLE* cpu, D3D12_GPU_DESCRIPTOR_HANDLE* gpu) {
    // ImGui only needs one SRV (the font atlas).
    *cpu = g_srv_heap->GetCPUDescriptorHandleForHeapStart();
    *gpu = g_srv_heap->GetGPUDescriptorHandleForHeapStart();
}
void SrvFree(ImGui_ImplDX12_InitInfo*, D3D12_CPU_DESCRIPTOR_HANDLE, D3D12_GPU_DESCRIPTOR_HANDLE) {}

bool InitImGui(IDXGISwapChain3* sc) {
    if (FAILED(sc->GetDevice(IID_PPV_ARGS(&g_dev)))) return false;
    DXGI_SWAP_CHAIN_DESC d;
    sc->GetDesc(&d);
    g_hwnd = d.OutputWindow;

    D3D12_DESCRIPTOR_HEAP_DESC sd{D3D12_DESCRIPTOR_HEAP_TYPE_CBV_SRV_UAV, 1, D3D12_DESCRIPTOR_HEAP_FLAG_SHADER_VISIBLE, 0};
    if (FAILED(g_dev->CreateDescriptorHeap(&sd, IID_PPV_ARGS(&g_srv_heap)))) return false;
    if (FAILED(g_dev->CreateFence(0, D3D12_FENCE_FLAG_NONE, IID_PPV_ARGS(&g_fence)))) return false;
    g_fence_event = CreateEventW(nullptr, FALSE, FALSE, nullptr);
    if (!CreateFrames(sc)) return false;

    ImGui::CreateContext();
    ImGuiIO& io = ImGui::GetIO();
    io.IniFilename = nullptr;
    io.ConfigFlags |= ImGuiConfigFlags_NavEnableKeyboard;
    float scale = d.BufferDesc.Height >= 1080 ? d.BufferDesc.Height / 1080.0f : 1.0f;
    ImFontConfig fc;
    fc.SizePixels = 15.0f * scale;
    io.Fonts->AddFontDefault(&fc);
    ImGui::StyleColorsDark();
    ImGuiStyle& st = ImGui::GetStyle();
    st.WindowRounding = 6;
    st.FrameRounding = 4;
    st.GrabRounding = 4;
    // Desert-road orange.
    ImVec4 a(0.85f, 0.45f, 0.12f, 1.0f), ah(0.95f, 0.56f, 0.20f, 1.0f);
    st.Colors[ImGuiCol_TitleBgActive] = ImVec4(0.55f, 0.28f, 0.07f, 1.0f);
    st.Colors[ImGuiCol_Header] = ImVec4(a.x, a.y, a.z, 0.45f);
    st.Colors[ImGuiCol_HeaderHovered] = ImVec4(ah.x, ah.y, ah.z, 0.75f);
    st.Colors[ImGuiCol_Button] = ImVec4(a.x, a.y, a.z, 0.55f);
    st.Colors[ImGuiCol_ButtonHovered] = ah;
    st.Colors[ImGuiCol_CheckMark] = ImVec4(1.0f, 0.78f, 0.45f, 1.0f);
    st.Colors[ImGuiCol_SliderGrab] = a;
    st.Colors[ImGuiCol_Tab] = ImVec4(0.45f, 0.24f, 0.08f, 0.86f);
    st.Colors[ImGuiCol_TabSelected] = a;
    st.Colors[ImGuiCol_TabHovered] = ah;
    st.ScaleAllSizes(scale);

    ImGui_ImplWin32_Init(g_hwnd);
    ImGui_ImplDX12_InitInfo info{};
    info.Device = g_dev;
    info.CommandQueue = g_queue;
    info.NumFramesInFlight = (int)g_frames.size();
    info.RTVFormat = g_format;
    info.DSVFormat = DXGI_FORMAT_UNKNOWN;
    info.SrvDescriptorHeap = g_srv_heap;
    info.SrvDescriptorAllocFn = SrvAlloc;
    info.SrvDescriptorFreeFn = SrvFree;
    if (!ImGui_ImplDX12_Init(&info)) return false;
    g_wndproc = (WNDPROC)SetWindowLongPtrW(g_hwnd, GWLP_WNDPROC, (LONG_PTR)WndProc);
    Log("[overlay] ImGui DX12 ready, %ux%u, %u buffers, format %d. Toggle: %s", d.BufferDesc.Width,
        d.BufferDesc.Height, d.BufferCount, (int)g_format, g_toggle_name.c_str());
    return true;
}

void Render(IDXGISwapChain3* sc) {
    if (g_frames_ready && sc != g_sc) ReleaseFrames();   // the game made a new swap chain
    if (!g_frames_ready && !CreateFrames(sc)) return;
    UINT idx = sc->GetCurrentBackBufferIndex();
    if (idx >= g_frames.size()) { ReleaseFrames(); return; }
    Frame& f = g_frames[idx];
    ID3D12Resource* back = nullptr;
    if (FAILED(sc->GetBuffer(idx, IID_PPV_ARGS(&back)))) return;
    g_dev->CreateRenderTargetView(back, nullptr, f.rtv);   // view the buffer in its own format
    WaitFrame(f);
    f.alloc->Reset();
    g_list->Reset(f.alloc, nullptr);

    D3D12_RESOURCE_BARRIER b{};
    b.Type = D3D12_RESOURCE_BARRIER_TYPE_TRANSITION;
    b.Transition.pResource = back;
    b.Transition.Subresource = D3D12_RESOURCE_BARRIER_ALL_SUBRESOURCES;
    b.Transition.StateBefore = D3D12_RESOURCE_STATE_PRESENT;
    b.Transition.StateAfter = D3D12_RESOURCE_STATE_RENDER_TARGET;
    g_list->ResourceBarrier(1, &b);
    g_list->OMSetRenderTargets(1, &f.rtv, FALSE, nullptr);
    g_list->SetDescriptorHeaps(1, &g_srv_heap);
    ImGui_ImplDX12_RenderDrawData(ImGui::GetDrawData(), g_list);
    std::swap(b.Transition.StateBefore, b.Transition.StateAfter);
    g_list->ResourceBarrier(1, &b);
    g_list->Close();

    ID3D12CommandList* lists[] = {g_list};
    ID3D12CommandQueue* q = g_queue;
    o_exec(q, 1, lists);
    f.fence_value = g_fence_next++;
    q->Signal(g_fence, f.fence_value);
    back->Release();   // the swap chain owns it; we only borrowed it for this frame
}

HRESULT __stdcall hk_present(IDXGISwapChain3* sc, UINT sync, UINT flags) {
    bool pressed = (GetAsyncKeyState(g_toggle_key) & 0x8000) != 0;
    if (!g_imgui_ready && !g_failed && g_queue && ((pressed && !g_toggle_down) || HudWanted())) {
        // nothing is created in the game's renderer until the player first opens the menu
        g_imgui_ready = InitImGui(sc);
        if (g_imgui_ready && !g_open) ImGui::GetIO().ConfigFlags |= ImGuiConfigFlags_NoMouseCursorChange;
        if (!g_imgui_ready) {
            g_failed = true;
            Log("[overlay] DX12 ImGui init failed; menu disabled");
        }
    }
    if (g_imgui_ready) {
        bool down = (GetAsyncKeyState(g_toggle_key) & 0x8000) != 0;
        if (down && !g_toggle_down && GetForegroundWindow() == g_hwnd) SetOpen(!g_open);
        g_toggle_down = down;

        MenuTick();
        if (g_open || HudWanted()) {
            ImGui_ImplDX12_NewFrame();
            ImGui_ImplWin32_NewFrame();
            ImGui::NewFrame();
            if (g_open) {
                bool open = true;
                DrawMenu(&open);
                if (!open) SetOpen(false);
            }
            DrawHud();
            ImGui::Render();
            Render(sc);
        }
    }
    return o_present(sc, sync, flags);
}

HRESULT __stdcall hk_resize(IDXGISwapChain3* sc, UINT n, UINT w, UINT h, DXGI_FORMAT fmt, UINT fl) {
    if (g_imgui_ready) ReleaseFrames();  // back buffers must be released before the resize
    return o_resize(sc, n, w, h, fmt, fl);
}

HRESULT __stdcall hk_resize1(IDXGISwapChain3* sc, UINT n, UINT w, UINT h, DXGI_FORMAT fmt, UINT fl,
                             const UINT* masks, IUnknown* const* queues) {
    if (g_imgui_ready) ReleaseFrames();
    return o_resize1(sc, n, w, h, fmt, fl, masks, queues);
}

void __stdcall hk_exec(ID3D12CommandQueue* q, UINT n, ID3D12CommandList* const* lists) {
    // Remember the game's direct queue: our draw must go to the queue that owns the swap chain.
    if (!g_queue && q->GetDesc().Type == D3D12_COMMAND_LIST_TYPE_DIRECT) g_queue = q;
    o_exec(q, n, lists);
}

BOOL WINAPI hk_setcursorpos(int x, int y) { return g_open ? TRUE : o_setcursorpos(x, y); }
BOOL WINAPI hk_clipcursor(const RECT* r) { return g_open ? TRUE : o_clipcursor(r); }

bool GetVtables(void** present, void** resize, void** resize1, void** exec) {
    HMODULE d3d12 = GetModuleHandleW(L"d3d12.dll");
    HMODULE dxgi = GetModuleHandleW(L"dxgi.dll");
    if (!d3d12 || !dxgi) return false;
    auto create_device = (PFN_D3D12_CREATE_DEVICE)GetProcAddress(d3d12, "D3D12CreateDevice");
    auto create_factory = (HRESULT(WINAPI*)(REFIID, void**))GetProcAddress(dxgi, "CreateDXGIFactory1");
    if (!create_device || !create_factory) return false;

    WNDCLASSEXW wc{sizeof wc, CS_CLASSDC, DefWindowProcW, 0, 0, GetModuleHandleW(nullptr),
                   nullptr, nullptr, nullptr, nullptr, L"mt_spawner_dummy", nullptr};
    RegisterClassExW(&wc);
    HWND hwnd = CreateWindowW(wc.lpszClassName, L"", WS_OVERLAPPEDWINDOW, 0, 0, 100, 100, nullptr, nullptr,
                              wc.hInstance, nullptr);
    bool ok = false;
    ID3D12Device* dev = nullptr;
    ID3D12CommandQueue* q = nullptr;
    IDXGIFactory4* fac = nullptr;
    IDXGISwapChain1* sc = nullptr;
    if (SUCCEEDED(create_device(nullptr, D3D_FEATURE_LEVEL_11_0, IID_PPV_ARGS(&dev)))) {
        D3D12_COMMAND_QUEUE_DESC qd{};
        qd.Type = D3D12_COMMAND_LIST_TYPE_DIRECT;
        if (SUCCEEDED(dev->CreateCommandQueue(&qd, IID_PPV_ARGS(&q))) &&
            SUCCEEDED(create_factory(IID_PPV_ARGS(&fac)))) {
            DXGI_SWAP_CHAIN_DESC1 sd{};
            sd.BufferCount = 2;
            sd.Width = 100;
            sd.Height = 100;
            sd.Format = DXGI_FORMAT_R8G8B8A8_UNORM;
            sd.BufferUsage = DXGI_USAGE_RENDER_TARGET_OUTPUT;
            sd.SwapEffect = DXGI_SWAP_EFFECT_FLIP_DISCARD;
            sd.SampleDesc.Count = 1;
            if (SUCCEEDED(fac->CreateSwapChainForHwnd(q, hwnd, &sd, nullptr, nullptr, &sc))) {
                *present = (*(void***)sc)[8];
                *resize = (*(void***)sc)[13];
                *resize1 = (*(void***)sc)[39];  // IDXGISwapChain3::ResizeBuffers1
                *exec = (*(void***)q)[10];
                ok = true;
            }
        }
    }
    if (sc) sc->Release();
    if (fac) fac->Release();
    if (q) q->Release();
    if (dev) dev->Release();
    DestroyWindow(hwnd);
    UnregisterClassW(wc.lpszClassName, wc.hInstance);
    return ok;
}

}  // namespace

bool Install() {
    g_toggle_key = hotkey::Load("mt_spawner.ini", "F8", &g_toggle_name);
    if (MH_Initialize() != MH_OK) {
        Log("[overlay] MH_Initialize failed");
        return false;
    }
    // d3d12.dll is loaded by Unreal's RHI shortly after the window appears.
    for (int i = 0; i < 100 && !GetModuleHandleW(L"d3d12.dll"); ++i) Sleep(100);
    void *present = nullptr, *resize = nullptr, *resize1 = nullptr, *exec = nullptr;
    if (!GetVtables(&present, &resize, &resize1, &exec)) {
        Log("[overlay] could not build a dummy D3D12 swap chain (is the game running on DX11? use the default DX12)");
        return false;
    }
    bool ok = MH_CreateHook(present, (void*)hk_present, (void**)&o_present) == MH_OK &&
              MH_CreateHook(resize, (void*)hk_resize, (void**)&o_resize) == MH_OK &&
              MH_CreateHook(resize1, (void*)hk_resize1, (void**)&o_resize1) == MH_OK &&
              MH_CreateHook(exec, (void*)hk_exec, (void**)&o_exec) == MH_OK &&
              MH_CreateHookApi(L"user32", "SetCursorPos", (void*)hk_setcursorpos, (void**)&o_setcursorpos) == MH_OK &&
              MH_CreateHookApi(L"user32", "ClipCursor", (void*)hk_clipcursor, (void**)&o_clipcursor) == MH_OK;
    if (!ok) {
        Log("[overlay] MH_CreateHook failed");
        return false;
    }
    MH_EnableHook(MH_ALL_HOOKS);
    Log("[overlay] DX12 hooks installed");
    return true;
}

bool MenuOpen() { return g_open; }
const char* ToggleKeyName() { return g_toggle_name.c_str(); }

}  // namespace overlay
