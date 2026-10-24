#include "log.h"
#include <windows.h>
#include <cstdarg>
#include <cstdio>
#include <deque>
#include <mutex>

static std::mutex g_mu;
static std::deque<std::string> g_lines;
static FILE* g_file;

void Log(const char* fmt, ...) {
    char buf[2048];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);

    std::lock_guard<std::mutex> lock(g_mu);
    if (!g_file) {
        char path[MAX_PATH];
        GetModuleFileNameA(nullptr, path, MAX_PATH);
        if (char* slash = strrchr(path, '\\')) strcpy(slash + 1, "mt_spawner.log");
        g_file = fopen(path, "w");
    }
    if (g_file) {
        fprintf(g_file, "%s\n", buf);
        fflush(g_file);
    }
    g_lines.emplace_back(buf);
    while (g_lines.size() > 400) g_lines.pop_front();
}

std::vector<std::string> LogTail(size_t max_lines) {
    std::lock_guard<std::mutex> lock(g_mu);
    size_t start = g_lines.size() > max_lines ? g_lines.size() - max_lines : 0;
    return {g_lines.begin() + start, g_lines.end()};
}

void LogClear() {
    std::lock_guard<std::mutex> lock(g_mu);
    g_lines.clear();
}
