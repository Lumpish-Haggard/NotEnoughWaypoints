"""
extract_game_data.py - read what the waypoint checks need out of your own Baldur's Gate 3
installation (nothing is downloaded, nothing of it is committed).

Uses LSLib's Divine.exe to extract, for every level that has (or will get) a waypoint:
  * the navigation grid (Levels/<level>/Ai/aigrid.data)       -> tools/.cache/levels/<level>/aigrid.data
  * every character, item, trigger, decal and prop the game
    places there, including those of the sub-levels the level
    is built from (the Guildhall, Rivington's streets, the
    goblin camp, the Emerald Grove ...), in world coordinates -> tools/.cache/levels/<level>/objects.json
  * the tiles of its walls, floors and ceilings               -> tools/.cache/levels/<level>/tiles.json
and, for the whole game:
  * the game's own waypoints, with their English names         -> tools/.cache/vanilla_waypoints.json
  * what the story does with waypoints and travel: every lock
    and unlock, the danger zones and blocked waypoint zones    -> tools/.cache/story.json

Run it again after a game patch, then run build_waypoints.py to check the waypoints, and what
the story now does with what they follow (against story_baseline.json).

Usage:
  python tools/extract_game_data.py [--levels WLD_Main_A,SCL_Main_A] [--divine PATH\\TO\\Divine.exe] [--game PATH\\TO\\Baldurs Gate 3]

Without --levels it reads the levels used in waypoints.json. Both paths are auto-detected
(Steam libraries, GOG, Vortex / common LSLib folders) or can be given with the environment
variables DIVINE_PATH and BG3_PATH. --keep-work keeps the converted game files in
tools/.cache/work_lsx for a closer look.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import math
import os
import re
import shutil
import string
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gamefiles  # noqa: E402
from navgrid import NavGrid  # noqa: E402
from waypoints import CACHE, CACHE_VERSION, DATA_FILE, GROUP_OF_LEVEL, load  # noqa: E402

GAME_FOLDER = "Baldurs Gate 3"
# Later modules override earlier ones. Honour adds objects for Honour mode only, so it is left out.
MODULES = ("Gustav", "GustavDev")
TEMPLATE_MODULES = ("Shared", "SharedDev", "Gustav", "GustavDev", "GustavX")
KINDS = ("Characters", "Items", "Triggers", "Decals", "Scenery", "LevelTemplates", "TileConstructions")
OBJECT_KINDS = KINDS[:-1]
MAX_DEPTH = 4   # level templates inside sub-levels inside sub-levels ...


def windows_drives():
    if os.name != "nt":
        return []
    return [f"{d}:\\" for d in string.ascii_uppercase if os.path.exists(f"{d}:\\")]


def registry_value(root_name, key, value):
    if os.name != "nt":
        return None
    try:
        import winreg
        root = getattr(winreg, root_name)
        with winreg.OpenKey(root, key) as k:
            return winreg.QueryValueEx(k, value)[0]
    except OSError:
        return None


def steam_libraries():
    """Every Steam library folder, read from Steam's libraryfolders.vdf."""
    steam = registry_value("HKEY_CURRENT_USER", r"Software\Valve\Steam", "SteamPath") \
        or registry_value("HKEY_LOCAL_MACHINE", r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath") \
        or r"C:\Program Files (x86)\Steam"
    libraries = [steam]
    vdf = os.path.join(steam, "steamapps", "libraryfolders.vdf")
    if os.path.exists(vdf):
        text = open(vdf, encoding="utf-8", errors="replace").read()
        libraries += [p.replace("\\\\", "\\") for p in re.findall(r'"path"\s+"([^"]+)"', text)]
    return libraries


def game_candidates():
    env = os.environ.get("BG3_PATH")
    if env:
        yield env
    for lib in steam_libraries():
        yield os.path.join(lib, "steamapps", "common", GAME_FOLDER)
    gog = registry_value("HKEY_LOCAL_MACHINE", r"SOFTWARE\WOW6432Node\GOG.com\Games\1456460669", "path")
    if gog:
        yield gog
    for drive in windows_drives():
        yield os.path.join(drive, "GOG Games", GAME_FOLDER)
        yield os.path.join(drive, "SteamLibrary", "steamapps", "common", GAME_FOLDER)


def divine_candidates():
    env = os.environ.get("DIVINE_PATH")
    if env:
        yield env
    for name in ("Divine.exe", "divine"):
        hit = shutil.which(name)
        if hit:
            yield hit
    yield os.path.join(os.path.dirname(CACHE), "Divine.exe")
    patterns = []
    if os.environ.get("APPDATA"):
        patterns.append(os.path.join(os.environ["APPDATA"], "Vortex", "baldursgate3", "mods", "ExportTool*", "tools", "Divine.exe"))
    for drive in windows_drives():
        patterns += [
            os.path.join(drive, "Vortex Mods", "baldursgate3", "ExportTool*", "tools", "Divine.exe"),
            os.path.join(drive, "Tools", "ExportTool*", "Tools", "Divine.exe"),
            os.path.join(drive, "Tools", "LSLib", "Divine.exe"),
            os.path.join(drive, "Modding", "ExportTool*", "Tools", "Divine.exe"),
        ]
    for pattern in patterns:
        yield from sorted(glob.glob(pattern), reverse=True)  # newest ExportTool version first


def first_existing(candidates, predicate=os.path.exists):
    for c in candidates:
        if c and predicate(c):
            return c
    return None


def divine(exe, *args):
    cmd = [exe, "-g", "bg3", "-l", "warn", *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print(res.stdout[-2000:], res.stderr[-2000:])
        raise SystemExit(f"Divine failed: {' '.join(cmd)}")
    return res.stdout


def extract(exe, paks, work, expr):
    """Extract the files matching expr from every package, later packages overriding earlier ones."""
    for pak in paks:
        print("  from", os.path.basename(pak))
        divine(exe, "-a", "extract-package", "-s", pak, "-d", work, "-x", expr, "--use-regex")


def convert(exe, work, lsx):
    if os.path.isdir(lsx):
        shutil.rmtree(lsx)
    if os.path.isdir(work) and any(f.endswith(".lsf") for _, _, fs in os.walk(work) for f in fs):
        divine(exe, "-a", "convert-resources", "-s", work, "-d", lsx, "-i", "lsf", "-o", "lsx")


# ------------------------------------------------------------------------ levels

def read_level(lsx_roots, level, scopes=("Globals", "Levels")):
    """Objects and tile constructions of one (sub-)level in its own coordinates, later modules
    overriding earlier ones (same MapKey): (objects by key, [(construction name, tiles)])."""
    by_key, constructions = {}, {}
    for root in lsx_roots:
        for module in MODULES:
            for scope in scopes:
                for kind in KINDS:
                    path = os.path.join(root, "Mods", module, scope, level, kind, "_merged.lsx")
                    if not os.path.exists(path):
                        continue
                    for node in gamefiles.game_objects(path):
                        if kind == "TileConstructions":
                            a = {x.get("id"): x.get("value") for x in node.findall("attribute")}
                            if "MapKey" in a:
                                constructions[a["MapKey"]] = (a.get("Name", ""), gamefiles.read_tiles(node))
                            continue
                        rec = gamefiles.read_object(node, kind, scope)
                        if rec:
                            by_key[rec["key"]] = rec
    return by_key, list(constructions.values())


def sublevel_folders(lsx_roots, name):
    return [os.path.join(root, "Mods", m, "Levels", name) for root in lsx_roots for m in MODULES
            if os.path.isdir(os.path.join(root, "Mods", m, "Levels", name))]


class Extents:
    """How far things reach: the bounds of the visual each template and each tile is drawn with."""

    def __init__(self, roots, bounds, tile_visuals, visual_names=None):
        self.roots, self.bounds, self.tile_visuals = roots, bounds, tile_visuals
        self.visual_names = visual_names or {}

    def of_template(self, template):
        return self.bounds.get(gamefiles.visual_of(template, self.roots))

    def of_tile(self, tile):
        return self.bounds.get(self.tile_visuals.get(tile.guid, ""))

    def visual_of_tile(self, tile):
        return self.visual_names.get(self.tile_visuals.get(tile.guid, ""), "")


def build_level(level, lsx_roots, templates, sub_cache, grid=None, extents=None):
    """Every object and tile of a main level and of the sub-levels placed into it, in world coordinates."""
    main, constructions = read_level(lsx_roots, level)
    objects = list(main.values())
    ext = extents.of_tile if extents else (lambda tile: None)
    vname = extents.visual_of_tile if extents else (lambda tile: "")
    tiles = [gamefiles.tile_record(name, t, ext=ext(t), visual=vname(t)) for name, ts in constructions for t in ts]
    report = []
    missing = set()

    def add_placements(records, outer, via_prefix, later, depth):
        for rec in records:
            if rec["kind"] != "LevelTemplates":
                continue
            tpl = templates.get(rec["tpl"])
            if not tpl:
                continue
            rec["sub"] = tpl["sub"]
            loaded = rec.get("loaded", tpl["loaded"])
            if outer is None:
                placement = (tuple(rec["pos"]), tuple(rec["rot"]), rec.get("scale", 1.0))
            else:
                p, r, s = gamefiles.place(outer, rec["pos"], rec["rot"], rec.get("scale", 1.0))
                placement = (p, r, s)
            via = rec["name"] if not via_prefix else via_prefix + "/" + rec["name"]
            is_later = later or not loaded
            if tpl["sub"] not in sub_cache:
                missing.add(tpl["sub"])
                continue
            sub_objects, sub_constructions = sub_cache[tpl["sub"]]
            placed = [gamefiles.placed(o, placement, via, tpl["sub"], is_later) for o in sub_objects.values()]
            objects.extend(placed)
            for name, ts in sub_constructions:
                for tile in ts:
                    p, r, s = gamefiles.place(placement, tile.pos, tile.rot, tile.scale)
                    t = gamefiles.tile_record(name, tile, p, r, s, ext=ext(tile), visual=vname(tile))
                    t["via"] = via
                    if is_later:
                        t["later"] = True
                    tiles.append(t)
            report.append((via, tpl["sub"], is_later, placed))
            if depth < MAX_DEPTH:
                add_placements(list(sub_objects.values()), placement, via, is_later, depth + 1)

    add_placements(list(main.values()), None, "", False, 1)
    if extents:
        for o in objects:
            if o["kind"] in ("Items", "Scenery"):
                bounds = extents.of_template(o["tpl"])
                if bounds:
                    o["ext"] = bounds
    fit = placement_fit(grid, report) if grid else {}
    return objects, tiles, report, missing, fit


def placement_fit(grid, report):
    """How well each placed sub-level sits on the main level's navigation grid: the share of its
    characters and floor items that stand within 0.3 m of a surface. A sub-level placed with a
    wrong transform would float or sink everywhere."""
    out = {}
    for via, sub, later, placed in report:
        standing = [o for o in placed if o["kind"] in ("Characters", "Items")]
        if len(standing) < 5:
            continue
        hits = 0
        for o in standing:
            x, y, z = o["pos"]
            if any(abs(h - y) <= 0.3 for h, _flags in grid.surfaces(x, z)):
                hits += 1
        out[via] = (sub, len(standing), hits / len(standing), later)
    return out


def needed_sublevels(lsx_roots, levels, templates, known):
    """The sub-levels the given (sub-)levels place, that are not read yet."""
    out = set()
    for level in levels:
        for root in lsx_roots:
            for module in MODULES:
                for scope in ("Globals", "Levels"):
                    path = os.path.join(root, "Mods", module, scope, level, "LevelTemplates", "_merged.lsx")
                    if not os.path.exists(path):
                        continue
                    for node in gamefiles.game_objects(path):
                        a = {x.get("id"): x.get("value") for x in node.findall("attribute")}
                        tpl = templates.get(a.get("TemplateName", ""))
                        if tpl and tpl["sub"] not in known:
                            out.add(tpl["sub"])
    return out


# ------------------------------------------------------------------------- story

def vanilla_waypoints(work, loca):
    """DB_WaypointInfo facts of the game's story, with the waypoint names the map shows."""
    rx = re.compile(r'^\s*DB_WaypointInfo\(\s*"(\w+)"\s*,\s*"(\w+)"\s*,\s*(?:\(ITEM\))?\s*\w*?_?([0-9a-f]{8}-[0-9a-f-]{27})\s*,'
                    r'\s*(?:\(TRIGGER\))?\s*\w*?_?([0-9a-f]{8}-[0-9a-f-]{27})\s*\)\s*;', re.M)
    rows = {}
    for path in glob.glob(os.path.join(work, "Mods", "*", "Story", "RawFiles", "Goals", "*.txt")):
        for group, wid, item, trigger in rx.findall(open(path, encoding="utf-8", errors="replace").read()):
            rows[wid] = {"id": wid, "group": group, "item": item, "trigger": trigger, "name": ""}
    for path in glob.glob(os.path.join(work, "Mods", "*", "Localization", "Waypointshrines*.lsx")):
        text = open(path, encoding="utf-8-sig").read()
        for node in re.findall(r'<node id="TranslatedStringKey">(.*?)</node>', text, re.S):
            handle = re.search(r'id="Content" type="TranslatedString" handle="([^"]+)"', node)
            key = re.search(r'id="UUID" type="FixedString" value="([^"]+)"', node)
            if handle and key and key.group(1) in rows:
                rows[key.group(1)]["name"] = loca.get(handle.group(1), "")
    return sorted(rows.values(), key=lambda r: (r["group"], r["id"]))


def goals(work):
    for path in sorted(glob.glob(os.path.join(work, "Mods", "*", "Story", "RawFiles", "Goals", "*.txt"))):
        module = os.path.relpath(path, os.path.join(work, "Mods")).split(os.sep)[0]
        yield module, os.path.splitext(os.path.basename(path))[0], open(path, encoding="utf-8", errors="replace").read()


# -------------------------------------------------------------------------- main

def write_json(path, data, compact=False):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        if compact:
            json.dump(data, fh, separators=(",", ":"), ensure_ascii=False)
        else:
            json.dump(data, fh, indent=1, ensure_ascii=False)
        fh.write("\n")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default=None, help="comma-separated level names (default: the levels in waypoints.json)")
    ap.add_argument("--divine", default=None, help="path to LSLib Divine.exe")
    ap.add_argument("--game", default=None, help="BG3 install folder (contains Data\\)")
    ap.add_argument("--cache", default=CACHE)
    ap.add_argument("--keep-work", action="store_true", help="keep the converted game files (tools/.cache/work_lsx*)")
    args = ap.parse_args()

    if args.levels:
        levels = [lv.strip() for lv in args.levels.split(",") if lv.strip()]
    else:
        levels = sorted({wp["level"] for wp in load(DATA_FILE)["waypoints"]})
    for lv in levels:
        if not re.match(r"^[A-Za-z0-9_]+$", lv):
            sys.exit(f"Not a level name: {lv}")
        if lv not in GROUP_OF_LEVEL:
            print(f"Note: {lv} is not one of the main levels ({', '.join(GROUP_OF_LEVEL)}).")

    exe = args.divine or first_existing(divine_candidates())
    game = args.game or first_existing(game_candidates(), lambda p: os.path.isdir(os.path.join(p, "Data")))
    if not exe or not os.path.exists(exe):
        sys.exit("Divine.exe not found - pass --divine (it ships with LSLib / ExportTool).")
    if not game or not os.path.isdir(os.path.join(game, "Data")):
        sys.exit("BG3 install not found - pass --game.")
    data = os.path.join(game, "Data")
    cache = os.path.abspath(args.cache)
    work = os.path.join(cache, "work")
    lsx = os.path.join(cache, "work_lsx")
    for d in glob.glob(os.path.join(cache, "work*")):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(work)
    print("Divine:", exe)
    print("Game  :", game)
    print("Levels:", ", ".join(levels))

    # Load order matters: later packages override earlier ones, so hotfixes are
    # sorted numerically (Patch8_HotFix9 before Patch8_HotFix10).
    def natural_key(path):
        return [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", os.path.basename(path))]

    paks = [os.path.join(data, p + ".pak") for p in ("Shared", "Gustav", "GustavX")]
    hotfixes = {os.path.normcase(p): p for p in glob.glob(os.path.join(data, "Patch*_*ot*ix*.pak"))}
    paks += sorted(hotfixes.values(), key=natural_key)
    paks = [p for p in dict.fromkeys(paks) if os.path.exists(p)]

    # Pass 1: the main levels, the templates that name their sub-levels, the story and the names.
    names = "|".join(re.escape(lv) for lv in levels)
    expr = ("^Mods/[^/]+/(Globals|Levels)/(%s)/(%s)/_merged\\.lsf$" % (names, "|".join(KINDS))
            + "|^Mods/[^/]+/Levels/(%s)/Ai/aigrid\\.data$" % names
            + "|^Mods/[^/]+/Localization/Waypointshrines[^/]*\\.lsf$"
            + "|^Mods/[^/]+/Story/RawFiles/Goals/[^/]+\\.txt$"
            + "|^Public/(%s)/RootTemplates/_merged\\.lsf$" % "|".join(TEMPLATE_MODULES)
            + "|^Public/(%s)/Content/.*_merged\\.lsf$" % "|".join(TEMPLATE_MODULES))
    print("Extracting the levels, the templates, the visuals and the story...")
    extract(exe, paks, work, expr)
    print("Converting (LSF -> LSX)...")
    convert(exe, work, lsx)
    lsx_roots = [lsx]

    roots = {}
    for module in TEMPLATE_MODULES:
        path = os.path.join(lsx, "Public", module, "RootTemplates", "_merged.lsx")
        if os.path.exists(path):
            roots.update(gamefiles.root_templates(path))
    templates = {k: v for k, v in roots.items() if "sub" in v}
    print(f"  {len(roots)} root templates, {len(templates)} of them level templates")

    print("Reading how far things reach (the bounds of every visual and tile)...")
    bounds, tile_visuals, visual_names = {}, {}, {}
    for module in TEMPLATE_MODULES:
        for path in sorted(glob.glob(os.path.join(lsx, "Public", module, "Content", "**", "_merged.lsx"), recursive=True)):
            b, t, n = gamefiles.bank(path)
            bounds.update(b)
            tile_visuals.update(t)
            visual_names.update(n)
    extents = Extents(roots, bounds, tile_visuals, visual_names)
    print(f"  {len(bounds)} visuals, {len(tile_visuals)} tiles")

    # Pass 2 and on: the sub-levels those levels place, and the ones placed inside them.
    sub_cache = {}
    wanted = needed_sublevels(lsx_roots, levels, templates, set(levels))
    depth = 1
    while wanted and depth <= MAX_DEPTH:
        print(f"Extracting {len(wanted)} sub-levels (depth {depth})...")
        sub_work, sub_lsx = os.path.join(cache, f"work{depth}"), os.path.join(cache, f"work_lsx{depth}")
        os.makedirs(sub_work, exist_ok=True)
        names = "|".join(re.escape(s) for s in sorted(wanted))
        extract(exe, paks, sub_work, "^Mods/[^/]+/Levels/(%s)/(%s)/_merged\\.lsf$" % (names, "|".join(KINDS)))
        convert(exe, sub_work, sub_lsx)
        lsx_roots.append(sub_lsx)
        for sub in sorted(wanted):
            sub_cache[sub] = read_level(lsx_roots, sub, scopes=("Levels",))
        known = set(levels) | set(sub_cache)
        wanted = needed_sublevels(lsx_roots, sorted(sub_cache), templates, known)
        depth += 1

    print("Reading the English waypoint names...")
    loca_dir = os.path.join(work, "loca")
    os.makedirs(loca_dir, exist_ok=True)
    divine(exe, "-a", "extract-single-file", "-s", os.path.join(data, "Localization", "English.pak"),
           "-d", os.path.join(loca_dir, "english.loca"), "-f", "Localization/English/english.loca")
    divine(exe, "-a", "convert-loca", "-s", os.path.join(loca_dir, "english.loca"), "-d", os.path.join(loca_dir, "english.xml"))
    text = open(os.path.join(loca_dir, "english.xml"), encoding="utf-8-sig").read()
    loca = {m.group(1): html.unescape(m.group(2)).strip()
            for m in re.finditer(r'<content contentuid="([^"]+)" version="\d+">(.*?)</content>', text, re.S)}

    # Goals are text: read them from the extracted tree, next to the converted name keys.
    for path in glob.glob(os.path.join(work, "Mods", "*", "Story", "RawFiles", "Goals", "*.txt")):
        dest = os.path.join(lsx, os.path.relpath(path, work))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
    rows = vanilla_waypoints(lsx, loca)
    write_json(os.path.join(cache, "vanilla_waypoints.json"), rows)
    print(f"  {len(rows)} of the game's own waypoints")
    story = gamefiles.story(goals(lsx))
    write_json(os.path.join(cache, "story.json"), story)
    print("  story: %d waypoints and %d groups locked or unlocked somewhere, %d travel zones" % (
        len(story["waypoints"]), len(story["groups"]), len(story["zones"])))

    manifest_levels = {}
    for lv in levels:
        folder = os.path.join(cache, "levels", lv)
        os.makedirs(folder, exist_ok=True)
        grid_path = None
        for module in reversed(MODULES):  # the newest module's grid is the one the game uses
            p = os.path.join(work, "Mods", module, "Levels", lv, "Ai", "aigrid.data")
            if os.path.exists(p):
                grid_path = p
                break
        if not grid_path:
            print(f"  {lv}: no navigation grid found, skipped")
            continue
        shutil.copy2(grid_path, os.path.join(folder, "aigrid.data"))
        grid = NavGrid(grid_path)
        objects, tiles, report, missing, fit = build_level(lv, lsx_roots, templates, sub_cache, grid, extents)
        objects.sort(key=lambda o: (o["kind"], o.get("via", ""), o["name"], o["key"]))
        write_json(os.path.join(folder, "objects.json"), objects, compact=True)
        write_json(os.path.join(folder, "tiles.json"), tiles, compact=True)
        subs = sorted({sub for _via, sub, _later, _placed in report})
        solid = [o for o in objects if o["kind"] in ("Items", "Scenery")]
        print(f"  {lv}: {len(objects)} objects ({sum(1 for o in objects if 'via' in o)} from {len(subs)} sub-levels), "
              f"{len(tiles)} tiles, navigation grid from {os.path.relpath(grid_path, work)}")
        print(f"    extents known for {sum(1 for o in solid if 'ext' in o)} of {len(solid)} items and props, "
              f"{sum(1 for t in tiles if 'ext' in t)} of {len(tiles)} tiles")
        if missing:
            print(f"    placed but not found (no files): {', '.join(sorted(missing))}")
        poor = sorted((v, f) for v, f in fit.items() if f[2] < 0.5 and f[1] >= 10 and not f[3])
        for via, (sub, n, share, _later) in poor:
            print(f"    note: only {share:.0%} of the {n} characters and items of {via} ({sub}) stand on the floor")
        manifest_levels[lv] = {
            "objects": len(objects), "tiles": len(tiles), "sublevels": subs,
            "fit": {via: {"sub": f[0], "standing": f[1], "on_floor": round(f[2], 2), "later": f[3]} for via, f in sorted(fit.items())},
        }

    hotfix = [os.path.basename(p)[:-4] for p in paks if "ot" in os.path.basename(p).lower() and "ix" in os.path.basename(p).lower()]
    write_json(os.path.join(cache, "manifest.json"), {
        "version": CACHE_VERSION, "game": game, "packages": [os.path.basename(p) for p in paks],
        "latest_hotfix": hotfix[-1] if hotfix else None, "levels": manifest_levels})
    if not args.keep_work:
        for d in glob.glob(os.path.join(cache, "work*")):
            shutil.rmtree(d, ignore_errors=True)
    print("Done. Cache:", cache)


if __name__ == "__main__":
    main()
