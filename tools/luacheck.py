"""Syntax-check Lua files with Lua 5.4 (lupa; same version as UE4SS) without running them.
usage: luacheck.py <file.lua> [...]   exit 1 if any file fails"""
import sys
from lupa import lua54

lua = lua54.LuaRuntime()
check = lua.eval("function(src, name) local f, err = load(src, '=' .. name) return err end")
bad = 0
for p in sys.argv[1:]:
    err = check(open(p, encoding="utf-8", errors="replace").read(), p.replace("\\", "/").split("/")[-1])
    print(("FAIL " + err) if err else ("ok   " + p))
    bad += bool(err)
sys.exit(1 if bad else 0)
