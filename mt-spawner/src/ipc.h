#pragma once
#include <map>
#include <string>
#include <vector>

// The menu talks to the RVTrainer UE4SS Lua mod through two small files in %LOCALAPPDATA%\RVTrainer:
//   cmd.txt   written here: one "seq<TAB>command<TAB>arg..." line per command not yet acknowledged
//   state.txt written by Lua: "key=value" lines, including ack=<last seq handled>
namespace ipc {
void Init();
void Send(const std::string& cmd, const std::vector<std::string>& args = {});
std::map<std::string, std::string> State();  // cached, re-read at most every 200 ms
bool Connected();                              // Lua wrote state within the last 3 seconds
}  // namespace ipc
