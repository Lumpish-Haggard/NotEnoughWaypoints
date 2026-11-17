"""
extract_game_data.py - read what the waypoint checks need out of your own Baldur's Gate 3
installation (nothing is downloaded, nothing of it is committed).

Uses LSLib's Divine.exe to extract, for every level that has (or will get) a waypoint:
  * the navigation grid (Levels/<level>/Ai/aigrid.data)   -> tools/.cache/levels/<level>/aigrid.data
  * every character, item, trigger, decal and prop the game
    places there                                          -> tools/.cache/levels/<level>/objects.json
and, for the whole game:
  * the game's own waypoints, with their English names     -> tools/.cache/vanilla_waypoints.json

Run it again after a game patch, then run build_waypoints.py to check the waypoints.

Usage:
  python tools/extract_game_data.py [--levels WLD_Main_A,SCL_Main_A] [--divine PATH\\TO\\Divine.exe] [--game PATH\\TO\\Baldurs Gate 3]

Without --levels it reads the levels used in waypoints.json. Both paths are auto-detected
(Steam libraries, GOG, Vortex / common LSLib folders) or can be given with the environment
variables DIVINE_PATH and BG3_PATH.
"""
from __future__ import annotations

import argparse
import glob
import html
import json
import os
import re
import shutil
import string
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waypoints import CACHE, DATA_FILE, GROUP_OF_LEVEL, load  # noqa: E402

GAME_FOLDER = "Baldurs Gate 3"
# Later modules override earlier ones. Honour adds objects for Honour mode only, so it is left out.
MODULES = ("Gustav", "GustavDev")
KINDS = ("Characters", "Items", "Triggers", "Decals", "Scenery", "LevelTemplates")


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


ATTR = re.compile(r'<attribute id="(\w+)" type="\w+" (?:value|handle)="([^"]*)"')


def index_objects(lsx_root, level):
    """Every placed object of one level, later modules overriding earlier ones (same MapKey)."""
    by_key = {}
    for module in MODULES:
        for scope in ("Globals", "Levels"):
            for kind in KINDS:
                path = os.path.join(lsx_root, "Mods", module, scope, level, kind, "_merged.lsx")
                if not os.path.exists(path):
                    continue
                text = open(path, encoding="utf-8-sig").read()
                for node in re.split(r'(?=<node id="GameObjects">)', text)[1:]:
                    attrs = dict(ATTR.findall(node.split("<children>", 1)[0]))
                    t = re.search(r'<node id="Transform">(.*?)</node>', node, re.S)
                    tr = dict(ATTR.findall(t.group(1))) if t else {}
                    if "Position" not in tr or "MapKey" not in attrs:
                        continue
                    by_key[attrs["MapKey"]] = {
                        "name": attrs.get("Name", ""),
                        "key": attrs["MapKey"],
                        "tpl": attrs.get("TemplateName", ""),
                        "kind": kind,
                        "scope": scope,
                        "pos": [round(float(v), 3) for v in tr["Position"].split()],
                        "rot": [round(float(v), 5) for v in tr.get("RotationQuat", "0 0 0 1").split()],
                    }
    return sorted(by_key.values(), key=lambda o: (o["kind"], o["name"], o["key"]))


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


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--levels", default=None, help="comma-separated level names (default: the levels in waypoints.json)")
    ap.add_argument("--divine", default=None, help="path to LSLib Divine.exe")
    ap.add_argument("--game", default=None, help="BG3 install folder (contains Data\\)")
    ap.add_argument("--cache", default=CACHE)
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
    if os.path.isdir(work):
        shutil.rmtree(work)
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

    names = "|".join(re.escape(lv) for lv in levels)
    expr = ("^Mods/[^/]+/(Globals|Levels)/(%s)/(%s)/_merged\\.lsf$" % (names, "|".join(KINDS))
            + "|^Mods/[^/]+/Levels/(%s)/Ai/aigrid\\.data$" % names
            + "|^Mods/[^/]+/Localization/Waypointshrines[^/]*\\.lsf$"
            + "|^Mods/[^/]+/Story/RawFiles/Goals/[^/]*Waypoints[^/]*\\.txt$")
    for pak in paks:
        print("Extracting from", os.path.basename(pak))
        divine(exe, "-a", "extract-package", "-s", pak, "-d", work, "-x", expr, "--use-regex")

    print("Converting level files (LSF -> LSX)...")
    lsx = os.path.join(cache, "work_lsx")
    if os.path.isdir(lsx):
        shutil.rmtree(lsx)
    divine(exe, "-a", "convert-resources", "-s", work, "-d", lsx, "-i", "lsf", "-o", "lsx")

    print("Reading the English waypoint names...")
    loca_dir = os.path.join(work, "loca")
    os.makedirs(loca_dir, exist_ok=True)
    divine(exe, "-a", "extract-single-file", "-s", os.path.join(data, "Localization", "English.pak"),
           "-d", os.path.join(loca_dir, "english.loca"), "-f", "Localization/English/english.loca")
    divine(exe, "-a", "convert-loca", "-s", os.path.join(loca_dir, "english.loca"), "-d", os.path.join(loca_dir, "english.xml"))
    text = open(os.path.join(loca_dir, "english.xml"), encoding="utf-8-sig").read()
    loca = {m.group(1): html.unescape(m.group(2)).strip()
            for m in re.finditer(r'<content contentuid="([^"]+)" version="\d+">(.*?)</content>', text, re.S)}

    # Goals are text: copy them next to the converted resources so both are read from one tree.
    for path in glob.glob(os.path.join(work, "Mods", "*", "Story", "RawFiles", "Goals", "*.txt")):
        dest = os.path.join(lsx, os.path.relpath(path, work))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(path, dest)
    rows = vanilla_waypoints(lsx, loca)
    with open(os.path.join(cache, "vanilla_waypoints.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump(rows, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(f"  {len(rows)} of the game's own waypoints")

    for lv in levels:
        folder = os.path.join(cache, "levels", lv)
        os.makedirs(folder, exist_ok=True)
        grid = None
        for module in reversed(MODULES):  # the newest module's grid is the one the game uses
            p = os.path.join(work, "Mods", module, "Levels", lv, "Ai", "aigrid.data")
            if os.path.exists(p):
                grid = p
                break
        if not grid:
            print(f"  {lv}: no navigation grid found, skipped")
            continue
        shutil.copy2(grid, os.path.join(folder, "aigrid.data"))
        objects = index_objects(lsx, lv)
        with open(os.path.join(folder, "objects.json"), "w", encoding="utf-8", newline="\n") as fh:
            json.dump(objects, fh, separators=(",", ":"))
        print(f"  {lv}: {len(objects)} objects, navigation grid from {os.path.relpath(grid, work)}")

    hotfix = [os.path.basename(p)[:-4] for p in paks if "ot" in os.path.basename(p).lower() and "ix" in os.path.basename(p).lower()]
    with open(os.path.join(cache, "manifest.json"), "w", encoding="utf-8", newline="\n") as fh:
        json.dump({"game": game, "packages": [os.path.basename(p) for p in paks], "latest_hotfix": hotfix[-1] if hotfix else None,
                   "levels": levels}, fh, indent=1)
        fh.write("\n")
    shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(lsx, ignore_errors=True)
    print("Done. Cache:", cache)


if __name__ == "__main__":
    main()
