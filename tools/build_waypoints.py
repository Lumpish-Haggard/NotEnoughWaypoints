"""
build_waypoints.py - check waypoints.json and generate the mod files from it.

What it writes (all from waypoints.json; never edit these by hand)
  Mods/NotEnoughWaypoints/Globals/<level>/Items/<guid>.lsx      the shrines (invisible; what players use)
  Mods/NotEnoughWaypoints/Globals/<level>/Triggers/<guid>.lsx   the arrival points
  Mods/NotEnoughWaypoints/Levels/<level>/Scenery/<guid>.lsx     the boulders
  Mods/NotEnoughWaypoints/Levels/<level>/Decals/<guid>.lsx      the runes on the boulders
  Mods/NotEnoughWaypoints/Story/RawFiles/Goals/NotEnoughWaypoints.txt
  Mods/NotEnoughWaypoints/Localization/Waypointshrines.lsx      waypoint id -> name handle
  Localization/English/NotEnoughWaypoints.xml                   the English names
pack.ps1 converts the .lsx files to .lsf and the .xml to .loca when it builds the pak.

What it checks
  * waypoints.json: ids, names, GUIDs and handles well formed and unique, the act group
    that goes with the level, the arrival point at a sensible distance from the shrine
  * meta.lsx: folder, UUID and version (--version X.Y.Z: that the mod is version X.Y.Z.0
    and that CHANGELOG.md has a section for it)
  * with the game cache (tools/extract_game_data.py): every waypoint against the game's
    navigation grid and the objects the game places nearby (flat free floor under the boulder
    and the arrival point, room for the party, nothing in the way, no floor overhead),
    and no clash with the game's own waypoint ids, names or object GUIDs

Usage:
  python tools/build_waypoints.py                  # check, then write the files
  python tools/build_waypoints.py --check          # check only, and that the files are up to date (CI)
  python tools/build_waypoints.py --check --version 1.0.0
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waypoints import (CACHE, DATA_FILE, DECAL_DIMENSIONS, DECAL_TEMPLATES, MOD, ROCK_SCALE, ROCK_TEMPLATES,  # noqa: E402
                       ROOT, SHRINE_TEMPLATE, TRIGGER_TEMPLATE, Level, check_placement, decal_transform, load, num,
                       object_names, problems, quat_yaw, rock_transform, shrine_yaw, vanilla_waypoints, PARTS)

MOD_DIR = os.path.join(ROOT, "Mods", MOD)
GENERATED_DIRS = [os.path.join(MOD_DIR, "Globals"), os.path.join(MOD_DIR, "Levels")]
GOAL = os.path.join(MOD_DIR, "Story", "RawFiles", "Goals", MOD + ".txt")
KEYS = os.path.join(MOD_DIR, "Localization", "Waypointshrines.lsx")
LOCA = os.path.join(ROOT, "Localization", "English", MOD + ".xml")
META = os.path.join(MOD_DIR, "meta.lsx")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

# The headers the game's own files of these kinds carry (LSLib reads them when converting to .lsf).
LEVEL_HEADER = '<version major="4" minor="0" revision="9" build="0" lslib_meta="v1,bswap_guids,lsf_adjacency" />'
KEYS_HEADER = '<version major="4" minor="0" revision="9" build="319" lslib_meta="v1,bswap_guids,lsf_keys_adjacency" />'


# --------------------------------------------------------------------- generation

def vec(values, places):
    return " ".join(num(v, places) for v in values)


def game_object(level, guid, name, template, kind, position, rotation, extra=(), children_before=(), scale=1):
    """One placed object, in the layout of the game's own level files."""
    attrs = list(extra) + [
        ("Flag", "int32", "1"),
    ]
    if kind in ("item", "trigger"):
        attrs.append(("IsGlobal", "bool", "True"))
    attrs += [
        ("LevelName", "FixedString", level),
        ("MapKey", "FixedString", guid),
        ("Name", "LSString", name),
        ("TemplateName", "FixedString", template),
        ("Type", "FixedString", kind),
    ]
    if kind == "trigger":
        attrs.append(("Zoom", "bool", "True"))
    attrs.sort(key=lambda a: a[0])
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<save>", "\t" + LEVEL_HEADER,
             '\t<region id="Templates">', '\t\t<node id="Templates">', "\t\t\t<children>",
             '\t\t\t\t<node id="GameObjects">']
    lines += ['\t\t\t\t\t<attribute id="%s" type="%s" value="%s" />' % a for a in attrs]
    lines.append("\t\t\t\t\t<children>")
    lines += ["\t\t\t\t\t\t" + c for c in children_before]
    lines += [
        '\t\t\t\t\t\t<node id="LayerList">',
        "\t\t\t\t\t\t\t<children>",
        '\t\t\t\t\t\t\t\t<node id="Layers">',
        "\t\t\t\t\t\t\t\t\t<children>",
        '\t\t\t\t\t\t\t\t\t\t<node id="Object">',
        '\t\t\t\t\t\t\t\t\t\t\t<attribute id="MapKey" type="FixedString" value="%s" />' % level,
        "\t\t\t\t\t\t\t\t\t\t</node>",
        "\t\t\t\t\t\t\t\t\t</children>",
        "\t\t\t\t\t\t\t\t</node>",
        "\t\t\t\t\t\t\t</children>",
        "\t\t\t\t\t\t</node>",
        '\t\t\t\t\t\t<node id="Transform">',
        '\t\t\t\t\t\t\t<attribute id="Position" type="fvec3" value="%s" />' % vec(position, 3),
        '\t\t\t\t\t\t\t<attribute id="RotationQuat" type="fvec4" value="%s" />' % vec(rotation, 7),
        '\t\t\t\t\t\t\t<attribute id="Scale" type="float" value="%s" />' % num(scale, 3),
        "\t\t\t\t\t\t</node>",
        "\t\t\t\t\t</children>",
        "\t\t\t\t</node>",
        "\t\t\t</children>",
        "\t\t</node>",
        "\t</region>",
        "</save>",
    ]
    return "\n".join(lines) + "\n"


def level_files(wp):
    level = wp["level"]
    names = object_names(wp)
    yaw = shrine_yaw(wp)
    shrine = wp["shrine"]["position"]
    decal_pos, decal_rot = decal_transform(shrine, yaw)
    rock_pos, rock_rot = rock_transform(shrine, yaw)
    return {
        os.path.join(MOD_DIR, "Globals", level, "Items", wp["shrine"]["guid"] + ".lsx"):
            game_object(level, wp["shrine"]["guid"], names["shrine"], SHRINE_TEMPLATE, "item", shrine, quat_yaw(yaw)),
        os.path.join(MOD_DIR, "Globals", level, "Triggers", wp["trigger"]["guid"] + ".lsx"):
            game_object(level, wp["trigger"]["guid"], names["trigger"], TRIGGER_TEMPLATE, "trigger",
                        wp["trigger"]["position"], (0, 0, 0, 1), extra=[("Angle", "float", "-1")],
                        children_before=['<node id="FadeChildren" />']),
        os.path.join(MOD_DIR, "Levels", level, "Decals", wp["decal"]["guid"] + ".lsx"):
            game_object(level, wp["decal"]["guid"], names["decal"], DECAL_TEMPLATES[wp["decal"]["style"]], "decal",
                        decal_pos, decal_rot, extra=[("Dimensions", "fvec3", vec(DECAL_DIMENSIONS, 3))]),
        os.path.join(MOD_DIR, "Levels", level, "Scenery", wp["rock"]["guid"] + ".lsx"):
            game_object(level, wp["rock"]["guid"], names["rock"], ROCK_TEMPLATES[wp["rock"]["style"]], "scenery",
                        rock_pos, rock_rot, scale=ROCK_SCALE),
    }


def ref(kind, wp, part):
    return "(%s)%s_%s" % (kind, object_names(wp)[part], wp[part]["guid"])


def goal(waypoints):
    out = [
        "Version 1",
        "SubGoalCombiner SGC_AND",
        "INITSECTION",
        "// Generated by tools/build_waypoints.py from waypoints.json: edit that, not this file.",
        "//",
        "// DB_WaypointInfo(group, id, shrine, arrival point) is how the game declares its own",
        "// waypoints (Shared: _Waypoints.txt). The shrine is the invisible object players use;",
        "// what they see is the boulder behind it, with the rune on its face.",
        "//",
        "// The game's rules do the rest: they register a",
        "// waypoint for the map, unlock it when a player comes near the shrine or uses it, and",
        "// lock every waypoint of a group when the story leaves that act.",
        "",
    ]
    for wp in waypoints:
        out.append("// %s. %s" % (wp["name"], wp.get("where", "")))
        out.append('DB_WaypointInfo("%s","%s",%s,%s);' % (wp["group"], wp["id"], ref("ITEM", wp, "shrine"), ref("TRIGGER", wp, "trigger")))
        out.append('DB_NEW_WAYP_Waypoint("%s");' % wp["id"])
        out.append("")
    underdark = [wp for wp in waypoints if wp.get("underdark")]
    if underdark:
        out += [
            "// Sovereign Glut can only follow the party between Underdark waypoints, and the game",
            "// keeps the list of those (Act1_UND_MyconidCircle_BroodingMyconid.txt). These are in the Underdark too.",
        ]
        out += ['DB_UND_BroodingSpovereign_UnderdarkWaypoints("%s");' % wp["id"] for wp in underdark]
        out.append("")
    out += [
        "KBSECTION",
        "//REGION Register for the map",
        "// This goal has no parent, so it starts as soon as the story does, also in a save that",
        "// was made without the mod. Depending on the order in which goals start, that can be",
        "// before the game's _Waypoints goal is running, and its rule only registers a waypoint",
        "// when the DB_WaypointInfo fact is added. Registering once more when gameplay starts",
        "// covers both orders.",
        "IF",
        "LevelGameplayStarted(_, _)",
        "AND",
        "NOT DB_NEW_WAYP_Registered(1)",
        "THEN",
        "DB_NEW_WAYP_Registered(1);",
        "PROC_NEW_WAYP_Register();",
        "",
        "PROC",
        "PROC_NEW_WAYP_Register()",
        "AND",
        "DB_NEW_WAYP_Waypoint(_ID)",
        "AND",
        "DB_WaypointInfo(_, _ID, _Item, _)",
        "THEN",
        "RegisterWaypoint(_ID, _Item);",
        "//END_REGION",
        "",
    ]
    locked = [wp for wp in waypoints if wp.get("lockWith")]
    if locked:
        out += [
            "//REGION Locked together with the game's own waypoints",
            "// Where the story locks one of its waypoints (the Emerald Grove when the druids seal it),",
            "// a waypoint of this mod in the same place is locked at the same moment.",
        ]
        for wp in locked:
            out += ["PROC", 'PROC_LockWaypointForAll("%s")' % wp["lockWith"], "THEN",
                    'PROC_LockWaypointForAll("%s");' % wp["id"], ""]
        out.append("//END_REGION")
    out += ["EXITSECTION", "", "ENDEXITSECTION", ""]
    return "\n".join(out)


def name_keys(waypoints):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<save>", "\t" + KEYS_HEADER,
             '\t<region id="TranslatedStringKeys">', '\t\t<node id="TranslatedStringKeys">', "\t\t\t<children>"]
    for wp in waypoints:
        lines += [
            '\t\t\t\t<node id="TranslatedStringKey">',
            '\t\t\t\t\t<attribute id="Content" type="TranslatedString" handle="%s" version="1" />' % wp["handle"],
            '\t\t\t\t\t<attribute id="ExtraData" type="LSString" value="" />',
            '\t\t\t\t\t<attribute id="Speaker" type="FixedString" value="" />',
            '\t\t\t\t\t<attribute id="Stub" type="bool" value="True" />',
            '\t\t\t\t\t<attribute id="UUID" type="FixedString" value="%s" />' % wp["id"],
            "\t\t\t\t</node>",
        ]
    lines += ["\t\t\t</children>", "\t\t</node>", "\t</region>", "</save>"]
    return "\n".join(lines) + "\n"


def english(waypoints):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<contentList>"]
    lines += ['\t<content contentuid="%s" version="1">%s</content>' % (wp["handle"], wp["name"]) for wp in waypoints]
    lines.append("</contentList>")
    return "\n".join(lines) + "\n"


def all_files(waypoints):
    files = {}
    for wp in waypoints:
        files.update(level_files(wp))
    files[GOAL] = goal(waypoints)
    files[KEYS] = name_keys(waypoints)
    files[LOCA] = english(waypoints)
    return files


# ------------------------------------------------------------------------- checks

def version_of(v64: int) -> str:
    return "%d.%d.%d.%d" % (v64 >> 55, (v64 >> 47) & 0xFF, (v64 >> 31) & 0xFFFF, v64 & 0x7FFFFFFF)


def check_meta(errors, version=None):
    try:
        root = ET.parse(META).getroot()
    except (OSError, ET.ParseError) as e:
        errors.append("meta.lsx: %s" % e)
        return
    info = {}
    for node in root.iter("node"):
        if node.get("id") == "ModuleInfo":
            info = {a.get("id"): a.get("value") for a in node.findall("attribute")}
            publish = [a.get("value") for n in node.iter("node") if n.get("id") == "PublishVersion"
                       for a in n.findall("attribute") if a.get("id") == "Version64"]
            break
    else:
        errors.append("meta.lsx: no ModuleInfo")
        return
    if info.get("Folder") != MOD:
        errors.append("meta.lsx: Folder is '%s', expected '%s'" % (info.get("Folder"), MOD))
    if not re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", info.get("UUID", "")):
        errors.append("meta.lsx: UUID is not a GUID")
    try:
        v64 = int(info.get("Version64", ""))
    except ValueError:
        errors.append("meta.lsx: Version64 is not a number")
        return
    if publish and publish[0] != info.get("Version64"):
        errors.append("meta.lsx: the two Version64 values differ")
    if version:
        if version_of(v64) != version + ".0":
            errors.append("meta.lsx is version %s, not %s.0" % (version_of(v64), version))
        text = open(CHANGELOG, encoding="utf-8").read() if os.path.exists(CHANGELOG) else ""
        if not re.search(r"^## \[%s\]" % re.escape(version), text, re.M):
            errors.append("CHANGELOG.md has no section for %s" % version)


def check_game(waypoints, errors, warnings):
    """Checks against the game files; skipped (with a note) when the cache is missing."""
    vanilla = vanilla_waypoints()
    if vanilla:
        ids = {v["id"] for v in vanilla}
        names = {v["name"].lower(): v["id"] for v in vanilla if v["name"]}
        for wp in waypoints:
            if wp["id"] in ids:
                errors.append("%s: the game already has a waypoint with this id" % wp["id"])
            if wp["name"].lower() in names:
                errors.append("%s: the game's %s is also called '%s'" % (wp["id"], names[wp["name"].lower()], wp["name"]))
            if wp.get("lockWith") and wp["lockWith"] not in ids:
                errors.append("%s: lockWith %s is not one of the game's waypoints" % (wp["id"], wp["lockWith"]))
    else:
        warnings.append("no tools/.cache/vanilla_waypoints.json: the game's own waypoints were not compared")
    checked = 0
    for level in sorted({wp["level"] for wp in waypoints}):
        if not Level.available(level):
            warnings.append("%s is not in the game cache: its waypoints were not checked against the game "
                            "(run tools/extract_game_data.py)" % level)
            continue
        lv = Level(level)
        keys = {o["key"] for o in lv.objects}
        for wp in [w for w in waypoints if w["level"] == level]:
            for part in PARTS:
                if wp[part]["guid"] in keys:
                    errors.append("%s: %s.guid is already used by the game" % (wp["id"], part))
            e, w = check_placement(lv, wp)
            errors += e
            warnings += w
            checked += 1
    return checked


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="only check, and fail if the generated files are out of date")
    ap.add_argument("--version", default=None, help="also check that the mod is version X.Y.Z (release builds)")
    args = ap.parse_args()

    data = load(DATA_FILE)
    errors = problems(data)
    warnings = []
    check_meta(errors, args.version[1:] if args.version and args.version.startswith("v") else args.version)
    if errors:
        for e in errors:
            print("ERROR  " + e)
        return 1
    waypoints = data["waypoints"]
    checked = check_game(waypoints, errors, warnings)

    files = all_files(waypoints)
    existing = set()
    for d in GENERATED_DIRS:
        for dirpath, _, names in os.walk(d):
            existing.update(os.path.join(dirpath, n) for n in names)
    stale = sorted(existing - set(files))
    changed = []
    for path, text in sorted(files.items()):
        try:
            with open(path, encoding="utf-8", newline="") as fh:
                current = fh.read().replace("\r\n", "\n")
        except FileNotFoundError:
            current = None
        if current != text:
            changed.append(path)

    for w in warnings:
        print("WARN   " + w)
    for e in errors:
        print("ERROR  " + e)
    if errors:
        return 1

    rel = lambda p: os.path.relpath(p, ROOT).replace("\\", "/")  # noqa: E731
    if args.check:
        for p in changed:
            print("ERROR  %s is out of date: run python tools/build_waypoints.py" % rel(p))
        for p in stale:
            print("ERROR  %s is not generated from waypoints.json: delete it or run python tools/build_waypoints.py" % rel(p))
        if changed or stale:
            return 1
    else:
        for p in stale:
            os.remove(p)
            print("removed  " + rel(p))
        for p in changed:
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(files[p])
            print("wrote    " + rel(p))
        for d in GENERATED_DIRS:  # drop folders emptied by a removed waypoint
            for dirpath, _, _ in os.walk(d, topdown=False):
                if dirpath != d and not os.listdir(dirpath):
                    os.rmdir(dirpath)
    print("%d waypoints OK (%d checked against the game files, cache: %s)." % (
        len(waypoints), checked, "yes" if os.path.isdir(CACHE) else "no"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
