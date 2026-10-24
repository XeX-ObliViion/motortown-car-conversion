#pragma once

namespace overlay {
// Hooks IDXGISwapChain::Present/ResizeBuffers and ID3D12CommandQueue::ExecuteCommandLists, plus the
// cursor and raw-input calls Unreal uses.
bool Install();
bool MenuOpen();
const char* ToggleKeyName();  // e.g. "F8", from the ini
}  // namespace overlay

// menu.cpp: drawn between ImGui::NewFrame and ImGui::Render; MenuTick runs every frame.
void DrawMenu(bool* open);
void MenuTick();
bool HudWanted();  // a driving-style popup is showing: draw a frame even with the menu closed
void DrawHud();
