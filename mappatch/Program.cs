// mappatch: inspect and patch Motor Town's persistent world map (Jeju_World) with UAssetAPI.
//   mappatch dump <map.umap> <mappings.usmap>
//   mappatch roundtrip <map.umap> <mappings.usmap> <out.umap>
//   mappatch clone <map.umap> <mappings.usmap> <out.umap> <spec.txt>
//     spec.txt lines: <source spot actor name> <new actor name> <vehicle row key> <x> <y> <z> <yaw> [Slot=PartKey,...]
//     Copies a dealer spot actor (and its subobjects) to a new place selling another vehicle row.
//   mappatch transplant <map.umap> <mappings.usmap> <out.umap> <cell.umap> <spec.txt>
//     Copies actors of a world-partition cell (e.g. a dealership showroom) into the persistent level, moved and rotated
//     as a group. spec: bbox x0 x1 y0 y1 / pivot x y z / target x y z yaw / skip <class regex> / prefix <name>.
//   mappatch label <map.umap> <mappings.usmap> <out.umap> <actor> <text0> [text1]   (map icon place-name texts)
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using UAssetAPI;
using UAssetAPI.ExportTypes;
using UAssetAPI.PropertyTypes.Objects;
using UAssetAPI.PropertyTypes.Structs;
using UAssetAPI.UnrealTypes;
using UAssetAPI.Unversioned;

static class P
{
    static string Cls(UAsset a, Export e) => e.ClassIndex.IsImport() ? e.ClassIndex.ToImport(a).ObjectName.ToString() : e.ClassIndex.IsExport() ? e.ClassIndex.ToExport(a).ObjectName.ToString() : "?";

    static string Val(UAsset a, PropertyData p, int depth = 0)
    {
        switch (p)
        {
            case ObjectPropertyData o: return o.Value.IsNull() ? "null" : o.Value.IsImport() ? "imp:" + o.Value.ToImport(a).ObjectName : "exp:" + (o.Value.Index - 1) + ":" + o.Value.ToExport(a).ObjectName;
            case SoftObjectPropertyData s: return "soft:" + s.Value.AssetPath.PackageName + "." + s.Value.AssetPath.AssetName;
            case NamePropertyData n: return "name:" + n.Value;
            case VectorPropertyData v: return $"({v.Value.X:F0},{v.Value.Y:F0},{v.Value.Z:F0})";
            case ArrayPropertyData ar: return "[" + string.Join(", ", ar.Value.Select(x => Val(a, x, depth + 1))) + "]";
            case StructPropertyData st: return st.StructType + "{" + string.Join(", ", st.Value.Select(x => x.Name + "=" + Val(a, x, depth + 1))) + "}";
            case StrPropertyData sp: return "\"" + (sp.Value?.Value ?? "") + "\"";
            case TextPropertyData tp: return "text:" + (tp.CultureInvariantString?.Value ?? tp.Value?.Value ?? "");
            default: try { return p.ToString(); } catch { return p.GetType().Name; }
        }
    }

    static PropertyData Remap(PropertyData p, Dictionary<int, int> map)
    {
        switch (p)
        {
            case ObjectPropertyData o when o.Value.IsExport() && map.ContainsKey(o.Value.Index):
                o.Value = new FPackageIndex(map[o.Value.Index]); break;
            case ArrayPropertyData ar:
                ar.Value = ar.Value.Select(x => Remap((PropertyData)x.Clone(), map)).ToArray(); break;
            case StructPropertyData st:
                st.Value = st.Value.Select(x => Remap((PropertyData)x.Clone(), map)).ToList(); break;
        }
        return p;
    }

    static List<FPackageIndex> RemapDeps(List<FPackageIndex> l, Dictionary<int, int> map) =>
        l.Select(x => x.IsExport() && map.ContainsKey(x.Index) ? new FPackageIndex(map[x.Index]) : x).ToList();

    static StructPropertyData FindPartTemplate(UAsset a)
    {
        foreach (var e in a.Exports.OfType<NormalExport>())
            foreach (var vp in e.Data.OfType<ArrayPropertyData>().Where(p => p.Name.ToString() == "VehicleParams"))
                foreach (var row in vp.Value.OfType<StructPropertyData>())
                    foreach (var pa in row.Value.OfType<ArrayPropertyData>().Where(p => p.Name.ToString() == "Parts" && p.Value.Length > 0))
                        return (StructPropertyData)pa.Value[0];
        return null;
    }

    static void Clone(UAsset a, LevelExport lvl, string src, string newName, string key, double x, double y, double z, double yaw, string parts)
    {
        int si = a.Exports.FindIndex(e => e.ObjectName.ToString() == src);
        if (si < 0) throw new Exception("no export named " + src);
        if (a.Exports.Any(e => e.ObjectName.ToString() == newName)) { Console.WriteLine(newName + " already there, skipped"); return; }
        // the actor and everything whose outer chain leads to it
        var group = new List<int> { si };
        for (bool grew = true; grew;)
        {
            grew = false;
            for (int i = 0; i < a.Exports.Count; i++)
                if (!group.Contains(i) && a.Exports[i].OuterIndex.IsExport() && group.Contains(a.Exports[i].OuterIndex.Index - 1)) { group.Add(i); grew = true; }
        }
        var map = new Dictionary<int, int>();   // FPackageIndex.Index (1-based) old -> new
        for (int k = 0; k < group.Count; k++) map[group[k] + 1] = a.Exports.Count + k + 1;
        foreach (int gi in group)
        {
            var e = (NormalExport)a.Exports[gi];
            var c = (NormalExport)e.Clone();
            c.Data = e.Data.Select(p => Remap((PropertyData)p.Clone(), map)).ToList();
            c.OuterIndex = c.OuterIndex.IsExport() && map.ContainsKey(c.OuterIndex.Index) ? new FPackageIndex(map[c.OuterIndex.Index]) : c.OuterIndex;
            c.SerializationBeforeSerializationDependencies = RemapDeps(e.SerializationBeforeSerializationDependencies, map);
            c.CreateBeforeSerializationDependencies = RemapDeps(e.CreateBeforeSerializationDependencies, map);
            c.SerializationBeforeCreateDependencies = RemapDeps(e.SerializationBeforeCreateDependencies, map);
            c.CreateBeforeCreateDependencies = RemapDeps(e.CreateBeforeCreateDependencies, map);
            if (gi == si) c.ObjectName = new FName(a, newName);
            a.Exports.Add(c);
            Console.WriteLine($"  cloned #{gi} {e.ObjectName} -> #{a.Exports.Count - 1} {c.ObjectName}");
        }
        // exports that must load the original before/after: depend on the copy the same way
        for (int i = 0; i < a.Exports.Count - group.Count; i++)
        {
            var e = a.Exports[i];
            foreach (var l in new[] { e.SerializationBeforeSerializationDependencies, e.CreateBeforeSerializationDependencies, e.SerializationBeforeCreateDependencies, e.CreateBeforeCreateDependencies })
                foreach (var kv in map)
                    if (l.Any(d => d.Index == kv.Key)) l.Add(new FPackageIndex(kv.Value));
        }
        lvl.Actors.Add(new FPackageIndex(map[si + 1]));
        // new settings on the copy
        var actor = (NormalExport)a.Exports[map[si + 1] - 1];
        // dealer spots get their vehicle row; other actors (e.g. a map icon, key "-") are only moved
        var vp = actor.Data.OfType<ArrayPropertyData>().FirstOrDefault(p => p.Name.ToString() == "VehicleParams");
        var row = vp != null ? (StructPropertyData)vp.Value[0] : null;
        if (vp != null) vp.Value = new PropertyData[] { row };
        foreach (var p in row?.Value ?? new List<PropertyData>())
        {
            if (p.Name.ToString() == "VehicleKey") ((NamePropertyData)p).Value = new FName(a, key);
            if (p.Name.ToString() == "Customizations" && p is ArrayPropertyData cu) cu.Value = new PropertyData[0];
            if (p.Name.ToString() == "Parts" && p is ArrayPropertyData pa)
            {
                // explicit parts (Slot=PartKey,...), like the game's own Zydro display; a template part struct is taken
                // from any dealer spot in the map that has one
                var list = new List<PropertyData>();
                if (!string.IsNullOrEmpty(parts))
                {
                    var tmpl = FindPartTemplate(a);
                    if (tmpl == null) throw new Exception("no dealer spot with a Parts entry to copy");
                    foreach (var kv in parts.Split(','))
                    {
                        var sp = kv.Split('=');
                        var part = (StructPropertyData)tmpl.Clone();
                        part.Name = new FName(a, list.Count.ToString());
                        foreach (var q in part.Value)
                        {
                            if (q is EnumPropertyData en)
                            {
                                string old = en.Value.ToString();
                                string prefix = old.Contains("::") ? old.Substring(0, old.IndexOf("::") + 2) : "";
                                en.Value = new FName(a, prefix + sp[0]);
                            }
                            if (q.Name.ToString() == "PartKey") ((NamePropertyData)q).Value = new FName(a, sp[1]);
                        }
                        list.Add(part);
                    }
                }
                pa.Value = list.ToArray();
            }
        }
        var root = actor.Data.OfType<ObjectPropertyData>().First(p => p.Name.ToString() == "RootComponent");
        var rc = (NormalExport)root.Value.ToExport(a);
        foreach (var p in rc.Data.OfType<StructPropertyData>())
        {
            if (p.Name.ToString() == "RelativeLocation") ((VectorPropertyData)p.Value[0]).Value = new FVector(x, y, z);
            if (p.Name.ToString() == "RelativeRotation") ((RotatorPropertyData)p.Value[0]).Value = new FRotator(0, yaw, 0);
        }
        Console.WriteLine($"spot {newName}: sells '{key}' at ({x},{y},{z}) yaw {yaw}");
    }


    // ---- transplant: copy actors from a world-partition cell into the persistent level ----
    static readonly HashSet<object> seen = new HashSet<object>(ReferenceEqualityComparer.Instance);

    // every FName carries an index into its own asset's name table: point them all at the map's table
    static void Rebind(object o, UAsset dst, int depth = 0)
    {
        if (o == null || depth > 40 || o is string || o.GetType().IsPrimitive || o.GetType().IsEnum || o is UAsset) return;
        if (!seen.Add(o)) return;
        if (o is System.Collections.IList list)
        {
            for (int i = 0; i < list.Count; i++)
            {
                if (list[i] is FName fn) list[i] = Re(fn, dst);
                else Rebind(list[i], dst, depth + 1);
            }
            return;
        }
        if (o is System.Collections.IDictionary) return;
        var t = o.GetType();
        if (t.Namespace == null || !t.Namespace.StartsWith("UAssetAPI")) return;
        for (var tt = t; tt != null && tt != typeof(object); tt = tt.BaseType)
            foreach (var f in tt.GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
            {
                if (f.FieldType == typeof(UAsset)) { f.SetValue(o, dst); continue; }
                if (f.FieldType == typeof(INameMap)) { if (f.GetValue(o) != null) f.SetValue(o, dst); continue; }
                var v = f.GetValue(o);
                if (v is FName fn) f.SetValue(o, Re(fn, dst));
                else if (v != null && !f.FieldType.IsPrimitive && !(v is string)) Rebind(v, dst, depth + 1);
            }
    }

    static FName Re(FName fn, UAsset dst)
    {
        if (fn == null || ReferenceEquals(fn.Asset, dst)) return fn;
        string v;
        try { v = fn.Value?.Value; } catch { return fn; }
        if (v == null) return fn;
        return new FName(dst, v, fn.Number);
    }

    static int ImportFor(UAsset src, UAsset dst, FPackageIndex si, Dictionary<int, int> cache)
    {
        if (!si.IsImport()) return 0;
        if (cache.TryGetValue(si.Index, out int got)) return got;
        var imp = si.ToImport(src);
        int outer = imp.OuterIndex.IsImport() ? ImportFor(src, dst, imp.OuterIndex, cache) : 0;
        string cp = imp.ClassPackage.Value.Value, cn = imp.ClassName.Value.Value, on = imp.ObjectName.Value.Value;
        for (int i = 0; i < dst.Imports.Count; i++)
        {
            var d = dst.Imports[i];
            if (d.ObjectName.Value.Value == on && d.ObjectName.Number == imp.ObjectName.Number && d.ClassName.Value.Value == cn
                && d.ClassPackage.Value.Value == cp && d.OuterIndex.Index == outer) { cache[si.Index] = -(i + 1); return -(i + 1); }
        }
        var ni = new Import(new FName(dst, cp), new FName(dst, cn), new FPackageIndex(outer), new FName(dst, on, imp.ObjectName.Number), imp.bImportOptional);
        try { if (imp.PackageName != null && imp.PackageName.Value != null) ni.PackageName = new FName(dst, imp.PackageName.Value.Value); } catch { }
        int idx = dst.AddImport(ni).Index;
        cache[si.Index] = idx;
        return idx;
    }

    static FPackageIndex MapIdx(UAsset src, UAsset dst, FPackageIndex p, Dictionary<int, int> exp, Dictionary<int, int> imp)
    {
        if (p == null || p.IsNull()) return p;
        if (p.IsExport()) return exp.TryGetValue(p.Index, out int e) ? new FPackageIndex(e) : new FPackageIndex(0);
        return new FPackageIndex(ImportFor(src, dst, p, imp));
    }

    static void RemapX(UAsset src, UAsset dst, PropertyData p, Dictionary<int, int> exp, Dictionary<int, int> imp)
    {
        switch (p)
        {
            case ObjectPropertyData o: o.Value = MapIdx(src, dst, o.Value, exp, imp); break;
            case ArrayPropertyData ar: foreach (var x in ar.Value) RemapX(src, dst, x, exp, imp); break;
            case StructPropertyData st: foreach (var x in st.Value) RemapX(src, dst, x, exp, imp); break;
            case MapPropertyData mp: foreach (var kv in mp.Value) { RemapX(src, dst, kv.Key, exp, imp); RemapX(src, dst, kv.Value, exp, imp); } break;
        }
    }

    static (double, double) Rot(double x, double y, double deg) { double r = deg * Math.PI / 180; return (x * Math.Cos(r) - y * Math.Sin(r), x * Math.Sin(r) + y * Math.Cos(r)); }

    static void Transplant(UAsset dst, LevelExport lvl, UAsset src, string specPath, string prefixOverride = null)
    {
        double x0 = -1e9, x1 = 1e9, y0 = -1e9, y1 = 1e9, px = 0, py = 0, pz = 0, tx = 0, ty = 0, tz = 0, tyaw = 0;
        var skip = new List<System.Text.RegularExpressions.Regex>(); string prefix = "NFSD_";
        var skipMesh = new List<System.Text.RegularExpressions.Regex>();
        foreach (var line in System.IO.File.ReadAllLines(specPath))
        {
            var f = line.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
            if (f.Length == 0 || f[0].StartsWith("#")) continue;
            if (f[0] == "bbox") { x0 = double.Parse(f[1]); x1 = double.Parse(f[2]); y0 = double.Parse(f[3]); y1 = double.Parse(f[4]); }
            if (f[0] == "pivot") { px = double.Parse(f[1]); py = double.Parse(f[2]); pz = double.Parse(f[3]); }
            if (f[0] == "target") { tx = double.Parse(f[1]); ty = double.Parse(f[2]); tz = double.Parse(f[3]); tyaw = double.Parse(f[4]); }
            if (f[0] == "skip") skip.Add(new System.Text.RegularExpressions.Regex(f[1]));
            if (f[0] == "prefix") prefix = f[1];
            if (f[0] == "skipmesh") skipMesh.Add(new System.Text.RegularExpressions.Regex(f[1]));
        }
        if (prefixOverride != null) prefix = prefixOverride;
        var srcLvl = src.Exports.OfType<LevelExport>().First();
        var imp = new Dictionary<int, int>();
        int lvlIdx = dst.Exports.IndexOf(lvl) + 1;
        int copied = 0;
        var classes = new Dictionary<string, int>();
        // pass 1: pick the actors, collect each with its subobjects
        var picked = new List<(int si, string cls, List<int> group, int rootIdx)>();
        foreach (var ai in srcLvl.Actors.Where(a => a != null && a.IsExport()).ToList())
        {
            int si = ai.Index - 1;
            var actor = src.Exports[si] as NormalExport;
            if (actor == null) continue;
            string cls = Cls(src, actor);
            if (skip.Any(r => r.IsMatch(cls))) continue;
            var rootP = actor.Data.OfType<ObjectPropertyData>().FirstOrDefault(p => p.Name.ToString() == "RootComponent");
            if (rootP == null || !rootP.Value.IsExport()) continue;
            var root = rootP.Value.ToExport(src) as NormalExport;
            var locP = root?.Data.OfType<StructPropertyData>().FirstOrDefault(p => p.Name.ToString() == "RelativeLocation");
            if (locP == null) continue;
            bool attached = root.Data.OfType<ObjectPropertyData>().Any(p => p.Name.ToString() == "AttachParent" && !p.Value.IsNull());
            var loc = ((VectorPropertyData)locP.Value[0]).Value;
            if (!attached && (loc.X < x0 || loc.X > x1 || loc.Y < y0 || loc.Y > y1)) continue;
            var meshP = root.Data.OfType<ObjectPropertyData>().FirstOrDefault(p => p.Name.ToString() == "StaticMesh");
            string meshName = meshP != null && meshP.Value.IsImport() ? meshP.Value.ToImport(src).ObjectName.ToString() : "";
            if (meshName != "" && skipMesh.Any(r => r.IsMatch(meshName))) continue;
            var group = new List<int> { si };
            for (bool grew = true; grew;)
            {
                grew = false;
                for (int i = 0; i < src.Exports.Count; i++)
                    if (!group.Contains(i) && src.Exports[i].OuterIndex.IsExport() && group.Contains(src.Exports[i].OuterIndex.Index - 1)) { group.Add(i); grew = true; }
            }
            if (group.Any(g => !(src.Exports[g] is NormalExport))) { Console.WriteLine($"  skipped {actor.ObjectName} ({cls}): non-property export inside"); continue; }
            // saved dynamic material instances don't round-trip on the server build ("Serial size mismatch", server
            // crash on load, 2026-10-23): server builds leave such actors out (MAPPATCH_SKIP_MID=1); the client loads them fine
            if (Environment.GetEnvironmentVariable("MAPPATCH_SKIP_MID") == "1" && group.Any(g => Cls(src, src.Exports[g]) == "MaterialInstanceDynamic")) { Console.WriteLine($"  skipped {actor.ObjectName} ({cls}): dynamic material inside"); continue; }
            picked.Add((si, cls, group, rootP.Value.Index));
        }
        // attached actors only come along when what they hang on comes too (repeat until stable)
        for (bool dropped = true; dropped;)
        {
            dropped = false;
            var have = new HashSet<int>(picked.SelectMany(p => p.group).Select(g => g + 1));
            for (int k = picked.Count - 1; k >= 0; k--)
            {
                var root = (NormalExport)src.Exports[picked[k].rootIdx - 1];
                var ap = root.Data.OfType<ObjectPropertyData>().FirstOrDefault(p => p.Name.ToString() == "AttachParent" && !p.Value.IsNull());
                if (ap != null && (!ap.Value.IsExport() || !have.Contains(ap.Value.Index))) { picked.RemoveAt(k); dropped = true; }
            }
        }
        // one export map for everything copied, so references between copied actors survive
        var exp = new Dictionary<int, int>();
        foreach (var pk in picked) foreach (int g in pk.group) exp[g + 1] = dst.Exports.Count + exp.Count + 1;
        // pass 2: copy
        foreach (var pk in picked)
        {
            int si = pk.si;
            foreach (int gi in pk.group)
            {
                var e = (NormalExport)src.Exports[gi];
                var c = (NormalExport)e.Clone();
                c.Data = e.Data.Select(p => (PropertyData)p.Clone()).ToList();
                seen.Clear();
                Rebind(c, dst);
                foreach (var p in c.Data) RemapX(src, dst, p, exp, imp);
                c.ClassIndex = MapIdx(src, dst, e.ClassIndex, exp, imp);
                c.SuperIndex = MapIdx(src, dst, e.SuperIndex, exp, imp);
                c.TemplateIndex = MapIdx(src, dst, e.TemplateIndex, exp, imp);
                c.OuterIndex = gi == si ? new FPackageIndex(lvlIdx) : MapIdx(src, dst, e.OuterIndex, exp, imp);
                Func<List<FPackageIndex>, List<FPackageIndex>> deps = l => l.Select(d => MapIdx(src, dst, d, exp, imp)).Where(d => !d.IsNull()).ToList();
                c.SerializationBeforeSerializationDependencies = deps(e.SerializationBeforeSerializationDependencies);
                c.CreateBeforeSerializationDependencies = deps(e.CreateBeforeSerializationDependencies);
                c.SerializationBeforeCreateDependencies = deps(e.SerializationBeforeCreateDependencies);
                c.CreateBeforeCreateDependencies = deps(e.CreateBeforeCreateDependencies);
                c.ObjectName = gi == si ? new FName(dst, prefix + e.ObjectName.Value.Value, e.ObjectName.Number) : new FName(dst, e.ObjectName.Value.Value, e.ObjectName.Number);
                if (dst.Exports.Count + 1 != exp[gi + 1]) throw new Exception("export index drift");
                dst.Exports.Add(c);
            }
            // move the root (attached roots are relative to their parent and stay as they are)
            var nroot = (NormalExport)dst.Exports[exp[pk.rootIdx] - 1];
            bool isAttached = nroot.Data.OfType<ObjectPropertyData>().Any(p => p.Name.ToString() == "AttachParent" && !p.Value.IsNull());
            if (!isAttached)
            {
                bool hasRot = false;
                foreach (var p in nroot.Data.OfType<StructPropertyData>())
                {
                    if (p.Name.ToString() == "RelativeLocation")
                    {
                        var v = ((VectorPropertyData)p.Value[0]).Value;
                        var (rx, ry) = Rot(v.X - px, v.Y - py, tyaw);
                        ((VectorPropertyData)p.Value[0]).Value = new FVector(tx + rx, ty + ry, tz + (v.Z - pz));
                    }
                    if (p.Name.ToString() == "RelativeRotation")
                    {
                        hasRot = true;
                        var r = ((RotatorPropertyData)p.Value[0]).Value;
                        ((RotatorPropertyData)p.Value[0]).Value = new FRotator(r.Pitch, r.Yaw + tyaw, r.Roll);
                    }
                }
                if (!hasRot && tyaw != 0)
                {
                    var rp = new StructPropertyData(new FName(dst, "RelativeRotation")) { StructType = new FName(dst, "Rotator"), SerializeNone = true,
                        Value = new List<PropertyData> { new RotatorPropertyData(new FName(dst, "RelativeRotation")) { Value = new FRotator(0, tyaw, 0) } } };
                    int at = nroot.Data.FindIndex(p => p.Name.ToString() == "RelativeLocation");
                    nroot.Data.Insert(at + 1, rp);
                }
            }
            lvl.Actors.Add(new FPackageIndex(exp[si + 1]));
            copied++;
            classes[pk.cls] = classes.TryGetValue(pk.cls, out int n) ? n + 1 : 1;
        }
        Console.WriteLine($"transplanted {copied} actors: " + string.Join(", ", classes.OrderByDescending(k => k.Value).Select(k => $"{k.Key} x{k.Value}")));
        Console.WriteLine($"map now has {dst.Exports.Count} exports, {dst.Imports.Count} imports");
    }

    static void Label(UAsset a, string actorName, string t0, string t1)
    {
        foreach (var e in a.Exports.OfType<NormalExport>())
        {
            if (!e.OuterIndex.IsExport() || e.OuterIndex.ToExport(a).ObjectName.ToString() != actorName) continue;
            var pn = e.Data.OfType<StructPropertyData>().FirstOrDefault(p => p.Name.ToString() == "PlaceNameTexts");
            if (pn == null) continue;
            var texts = pn.Value.OfType<ArrayPropertyData>().First(p => p.Name.ToString() == "Texts");
            string[] want = { t0, t1 };
            for (int i = 0; i < texts.Value.Length && i < 2; i++)
                if (want[i] != null && texts.Value[i] is TextPropertyData tp)
                {
                    tp.HistoryType = TextHistoryType.None;
                    tp.Namespace = null;
                    tp.Value = null;
                    tp.CultureInvariantString = new FString(want[i]);
                }
            Console.WriteLine($"label of {actorName}: {t0} / {t1}");
        }
    }

    static int Main(string[] args)
    {
        var sw = System.Diagnostics.Stopwatch.StartNew();
        var map = new Usmap(args[2]);
        var a = new UAsset(args[1], EngineVersion.VER_UE5_5, map);
        Console.WriteLine($"loaded {a.Exports.Count} exports in {sw.Elapsed.TotalSeconds:F0}s; raw={a.Exports.Count(e => e is RawExport)}");
        var lvl = a.Exports.OfType<LevelExport>().FirstOrDefault();
        Console.WriteLine("level actors: " + (lvl?.Actors.Count ?? -1));
        if (args[0] == "dump")
        {
            for (int i = 0; i < a.Exports.Count; i++)
            {
                var e = a.Exports[i];
                // optional 4th arg: regex on the export's class (default: dealer spawn points)
                var clsRe = args.Length > 3 ? args[3] : "^MTDealerVehicleSpawnPoint$";
                if (!System.Text.RegularExpressions.Regex.IsMatch(Cls(a, e) ?? "", clsRe)) continue;
                Console.WriteLine($"#{i} {e.ObjectName} [{Cls(a, e)}] outer={(e.OuterIndex.IsExport() ? e.OuterIndex.ToExport(a).ObjectName.ToString() : "-")} ({e.GetType().Name}, {e.SerialSize} bytes)");
                if (e is NormalExport ne)
                    foreach (var p in ne.Data)
                    {
                        var s = Val(a, p);
                        if (p.Name.ToString() == "RootComponent" && p is ObjectPropertyData ro && ro.Value.IsExport() && ro.Value.ToExport(a) is NormalExport rc)
                            s += " loc=" + string.Join(" ", rc.Data.Where(x => x.Name.ToString().StartsWith("Relative")).Select(x => x.Name + Val(a, x)));
                        Console.WriteLine($"   {p.Name} = {(s.Length > 600 ? s.Substring(0, 600) + "..." : s)}");
                    }
            }
        }
        if (args[0] == "clone")
        {
            foreach (var line in System.IO.File.ReadAllLines(args[4]))
            {
                var f = line.Split((char[])null, StringSplitOptions.RemoveEmptyEntries);
                if (f.Length < 7 || f[0].StartsWith("#")) continue;
                Clone(a, lvl, f[0], f[1], f[2], double.Parse(f[3]), double.Parse(f[4]), double.Parse(f[5]), double.Parse(f[6]), f.Length > 7 ? f[7] : null);
            }
            a.Write(args[3]);
            Console.WriteLine("wrote " + args[3] + "; level actors now " + lvl.Actors.Count);
        }
        if (args[0] == "transplant")
        {
            var cell = new UAsset(args[4], EngineVersion.VER_UE5_5, map);
            Transplant(a, lvl, cell, args[5], args.Length > 6 ? args[6] : null);
            a.Write(args[3]);
            Console.WriteLine("wrote " + args[3]);
        }
        if (args[0] == "label")
        {
            Label(a, args[4], args[5], args.Length > 6 ? args[6] : null);
            a.Write(args[3]);
            Console.WriteLine("wrote " + args[3]);
        }
        if (args[0] == "info")
        {
            var bf = System.Reflection.BindingFlags.NonPublic | System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public;
            foreach (var n in new[] { "BulkDataStartOffset", "DataResourceOffset", "PayloadTocOffset", "SectionSixOffset", "WorldTileInfoDataOffset" })
                Console.WriteLine(n + " = " + (typeof(UAsset).GetField(n, bf)?.GetValue(a) ?? "?"));
            Console.WriteLine("AdditionalFiles = " + (a.AdditionalFiles?.Length ?? -1));
            var dr = a.DataResources ?? new List<FObjectDataResource>();
            Console.WriteLine("DataResources = " + dr.Count);
            foreach (var g in dr.GroupBy(d => d.LegacyBulkDataFlags))
                Console.WriteLine($"  flags 0x{(uint)g.Key:X}: {g.Count()}  offsets {g.Min(d => d.SerialOffset)}..{g.Max(d => d.SerialOffset)}  dup {g.Min(d => d.DuplicateSerialOffset)}..{g.Max(d => d.DuplicateSerialOffset)}");
        }
        if (args[0] == "roundtrip")
        {
            a.Write(args[3]);
            Console.WriteLine("wrote " + args[3]);
        }
        return 0;
    }
}
