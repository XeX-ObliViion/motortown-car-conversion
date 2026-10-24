#pragma once
#include <string>
#include <vector>

// Writes to sr3r_trainer.log next to the game exe and keeps the last lines for the in-game console.
void Log(const char* fmt, ...);
std::vector<std::string> LogTail(size_t max_lines);
void LogClear();
