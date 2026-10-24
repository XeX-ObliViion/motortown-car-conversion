#include "ipc.h"
#include "log.h"

#include <windows.h>

#include <cstdio>
#include <deque>
#include <mutex>

namespace ipc {
namespace {

std::mutex g_mu;
std::wstring g_dir;
struct Cmd { long long seq; std::string line; };
std::deque<Cmd> g_pending;
long long g_next_seq;
std::map<std::string, std::string> g_state;
ULONGLONG g_state_read_at;
FILETIME g_state_mtime;
bool g_connected;

std::wstring Path(const wchar_t* name) { return g_dir + L"\\" + name; }

void WriteCommands() {  // under g_mu
    std::string body;
    for (auto& c : g_pending) body += c.line + "\n";
    std::wstring tmp = Path(L"cmd.tmp");
    FILE* f = _wfopen(tmp.c_str(), L"wb");
    if (!f) return;
    fwrite(body.data(), 1, body.size(), f);
    fclose(f);
    MoveFileExW(tmp.c_str(), Path(L"cmd.txt").c_str(), MOVEFILE_REPLACE_EXISTING);
}

void ReadState() {  // under g_mu
    std::wstring p = Path(L"state.txt");
    WIN32_FILE_ATTRIBUTE_DATA a;
    if (!GetFileAttributesExW(p.c_str(), GetFileExInfoStandard, &a)) {
        g_connected = false;
        return;
    }
    FILETIME now;
    GetSystemTimeAsFileTime(&now);
    ULARGE_INTEGER n{{now.dwLowDateTime, now.dwHighDateTime}}, m{{a.ftLastWriteTime.dwLowDateTime, a.ftLastWriteTime.dwHighDateTime}};
    g_connected = n.QuadPart - m.QuadPart < 3ULL * 10000000ULL;
    if (CompareFileTime(&a.ftLastWriteTime, &g_state_mtime) == 0) return;
    g_state_mtime = a.ftLastWriteTime;

    FILE* f = _wfopen(p.c_str(), L"rb");
    if (!f) return;
    std::map<std::string, std::string> s;
    char line[1024];
    while (fgets(line, sizeof line, f)) {
        std::string l = line;
        while (!l.empty() && (l.back() == '\n' || l.back() == '\r')) l.pop_back();
        size_t eq = l.find('=');
        if (eq != std::string::npos) s[l.substr(0, eq)] = l.substr(eq + 1);
    }
    fclose(f);
    if (s.empty()) return;  // caught it mid-write; keep the previous state
    g_state = std::move(s);

    long long ack = atoll(g_state["ack"].c_str());
    bool changed = false;
    while (!g_pending.empty() && g_pending.front().seq <= ack) {
        g_pending.pop_front();
        changed = true;
    }
    if (changed) WriteCommands();
}

}  // namespace

void Init() {
    wchar_t buf[MAX_PATH];
    GetEnvironmentVariableW(L"LOCALAPPDATA", buf, MAX_PATH);
    g_dir = std::wstring(buf) + L"\\MTSpawner";
    CreateDirectoryW(g_dir.c_str(), nullptr);
    // Sequence numbers only need to grow across restarts of the game; time does that.
    g_next_seq = (long long)GetTickCount64() + (long long)time(nullptr) * 1000;
    std::lock_guard<std::mutex> lock(g_mu);
    WriteCommands();
    Log("[ipc] using %ls", g_dir.c_str());
}

void Send(const std::string& cmd, const std::vector<std::string>& args) {
    std::lock_guard<std::mutex> lock(g_mu);
    long long seq = ++g_next_seq;
    std::string line = std::to_string(seq) + "\t" + cmd;
    for (auto& a : args) {
        std::string clean = a;
        for (char& c : clean)
            if (c == '\t' || c == '\n' || c == '\r') c = ' ';
        line += "\t" + clean;
    }
    if (g_pending.size() > 200) g_pending.pop_front();
    g_pending.push_back({seq, line});
    WriteCommands();
}

std::map<std::string, std::string> State() {
    std::lock_guard<std::mutex> lock(g_mu);
    ULONGLONG now = GetTickCount64();
    if (now - g_state_read_at > 200) {
        g_state_read_at = now;
        ReadState();
    }
    return g_state;
}

bool Connected() {
    State();
    std::lock_guard<std::mutex> lock(g_mu);
    return g_connected;
}

}  // namespace ipc
