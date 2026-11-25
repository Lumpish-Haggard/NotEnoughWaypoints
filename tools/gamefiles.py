"""
gamefiles.py - read the game's level and story files (as LSLib converts them) into the
plain records that tools/.cache holds. No game files are needed to import or test it:
extract_game_data.py finds and converts the files, this module only reads them.

Level files (.lsx)
  Every placed object is a <node id="GameObjects"> with its attributes, a Transform
  (Position, RotationQuat, Scale) and, depending on the kind:
    * triggers: a volume, either a box ("Extents", the full size), a prism
      ("Points", x/z corners, and "Height") or a sphere ("Radius");
    * decals: "Dimensions", the box the decal is projected in;
    * level templates: the template that names a sub-level (SubLevelName in the root
      templates), placed with this transform;
    * tile constructions: walls, floors and trims built from tiles, each tile with its
      own "Translate", "Rotate" (a 3x3 matrix written row by row) or "QRotate" (a
      quaternion), "Scale" (uniform) and "ScaleZ" (length stretch along local x), in
      level coordinates.

Sub-levels
  The game builds most places from sub-levels: the Guildhall, Rivington's streets, the
  goblin camp and the Emerald Grove are each one, placed into the main level by a level
  template. Their objects are stored relative to the template's origin; place() turns them
  into world coordinates. A template whose StartingLoaded is False is loaded later by the
  story (the Grove's lockdown barrier, a burnt-out version of a place); its objects are
  marked "later".

Story goals (.txt)
  story() collects what the game's story does with waypoints and travel: every lock and
  unlock of a waypoint (and of a whole group), the danger zones (no travel out while
  active), the blocked waypoint zones (no waypoints at all) and the safe bubbles; a
  fingerprint of the game's waypoint rules (_Waypoints), and the waypoints Sovereign Glut
  follows the party between. After a game patch, build_waypoints.py compares these with
  what they were when the waypoints were last checked (story_baseline.json).
"""
from __future__ import annotations

import hashlib
import math
import re
import xml.etree.ElementTree as ET

from waypoints import canonical, quat_mul, rotate

ROUND = 3


# ------------------------------------------------------------------------ geometry

def matrix_to_quat(m):
    """A rotation matrix (rows) as the (x, y, z, w) quaternion the game stores."""
    (m00, m01, m02), (m10, m11, m12), (m20, m21, m22) = m
    trace = m00 + m11 + m22
    if trace > 0:
        s = math.sqrt(trace + 1.0) * 2
        q = ((m21 - m12) / s, (m02 - m20) / s, (m10 - m01) / s, 0.25 * s)
    elif m00 > m11 and m00 > m22:
        s = math.sqrt(1.0 + m00 - m11 - m22) * 2
        q = (0.25 * s, (m01 + m10) / s, (m02 + m20) / s, (m21 - m12) / s)
    elif m11 > m22:
        s = math.sqrt(1.0 + m11 - m00 - m22) * 2
        q = ((m01 + m10) / s, 0.25 * s, (m12 + m21) / s, (m02 - m20) / s)
    else:
        s = math.sqrt(1.0 + m22 - m00 - m11) * 2
        q = ((m02 + m20) / s, (m12 + m21) / s, 0.25 * s, (m10 - m01) / s)
    n = math.sqrt(sum(v * v for v in q)) or 1.0
    return canonical(tuple(v / n for v in q))


def place(placement, pos, rot=(0.0, 0.0, 0.0, 1.0), scale=1.0):
    """World position, rotation and scale of something given in a placed template's frame.

    placement: (position, rotation, scale) of the level template in the main level."""
    ppos, prot, pscale = placement
    p = rotate(prot, tuple(v * pscale for v in pos))
    return (tuple(a + b for a, b in zip(ppos, p)),
            canonical(quat_mul(prot, rot)),
            pscale * scale)


def rounded(values, places=ROUND):
    return [round(v, places) + 0.0 for v in values]


# ------------------------------------------------------------------------- LSX

def _attrs(node):
    """The direct <attribute> children of a node: {id: value} (TranslatedStrings give their handle)."""
    return {a.get("id"): a.get("value", a.get("handle")) for a in node.findall("attribute")}


def _floats(text):
    return [float(v) for v in text.split()]


def _child(node, node_id):
    children = node.find("children")
    if children is None:
        return None
    for c in children.findall("node"):
        if c.get("id") == node_id:
            return c
    return None


def _children(node, node_id):
    children = node.find("children")
    return [] if children is None else [c for c in children.findall("node") if c.get("id") == node_id]


def game_objects(path):
    """Every <node id="GameObjects"> of an LSX file, one at a time (large files stay small in memory)."""
    for _event, elem in ET.iterparse(path, events=("end",)):
        if elem.tag == "node" and elem.get("id") == "GameObjects":
            yield elem
            elem.clear()


def read_object(node, kind, scope):
    """One placed object as a cache record, in its own level's coordinates, or None if it has no position."""
    a = _attrs(node)
    transform = _child(node, "Transform")
    if transform is None or "MapKey" not in a:
        return None
    t = _attrs(transform)
    if "Position" not in t:
        return None
    rec = {
        "name": a.get("Name", ""),
        "key": a["MapKey"],
        "tpl": a.get("TemplateName", ""),
        "kind": kind,
        "scope": scope,
        "pos": _floats(t["Position"]),
        "rot": _floats(t.get("RotationQuat", "0 0 0 1")),
    }
    scale = float(t.get("Scale", "1") or 1)
    if abs(scale - 1.0) > 1e-6:
        rec["scale"] = scale
    if kind == "Triggers":
        shape = trigger_shape(node, a)
        if shape:
            rec["shape"] = shape
    elif kind == "Decals" and "Dimensions" in a:
        rec["dims"] = _floats(a["Dimensions"])
    elif kind == "LevelTemplates" and "StartingLoaded" in a:
        rec["loaded"] = a["StartingLoaded"] == "True"
    return rec


def trigger_shape(node, a=None):
    """The volume of a trigger: {"box": [x, y, z]} (full size), {"poly": [[x, z], ...], "h": height},
    {"sphere": radius}, or None for a point (a place scripts send characters to, an arrival point)."""
    a = a if a is not None else _attrs(node)
    if "Extents" in a:
        return {"box": rounded(_floats(a["Extents"]))}
    points = [_floats(_attrs(p)["Object"]) for p in _children(node, "Points")]
    if points:
        return {"poly": [rounded(p) for p in points], "h": round(float(a.get("Height", "0") or 0), ROUND)}
    if "Radius" in a:
        return {"sphere": round(float(a["Radius"]), ROUND)}
    return None


class Tile(tuple):
    """One tile of a tile construction: position, rotation, scale, length stretch, walk on, walk through,
    stretchable, no decals, tile GUID."""
    __slots__ = ()
    pos = property(lambda self: self[0])
    rot = property(lambda self: self[1])
    scale = property(lambda self: self[2])
    scale_z = property(lambda self: self[3])
    walk_on = property(lambda self: self[4])
    walk_through = property(lambda self: self[5])
    stretch = property(lambda self: self[6])
    no_decal = property(lambda self: self[7])
    guid = property(lambda self: self[8])


def read_tiles(node):
    """The tiles of one tile construction, in level coordinates."""
    no_decal = _attrs(node).get("RecieveDecal") == "False"
    out = []
    for tile in node.iter("node"):
        if tile.get("id") != "tile":
            continue
        a = _attrs(tile)
        if "Translate" not in a:
            continue
        if "QRotate" in a:
            q = _floats(a["QRotate"])
            n = math.sqrt(sum(v * v for v in q)) or 1.0
            rot = canonical(tuple(v / n for v in q))
        else:
            m = _floats(a.get("Rotate", "1 0 0 0 1 0 0 0 1"))
            rot = matrix_to_quat((m[0:3], m[3:6], m[6:9]))
        out.append(Tile((_floats(a["Translate"]), rot,
                         float(a.get("Scale", "1") or 1), float(a.get("ScaleZ", "1") or 1),
                         a.get("WalkOn") == "True", a.get("WalkThrough") == "True",
                         a.get("Stretchable") == "True", no_decal, a.get("tile", ""))))
    return out


def tile_record(name, tile, pos=None, rot=None, scale=None, ext=None, visual=None):
    """A tile as the cache keeps it: construction name, position, rotation, scale, length stretch, flags,
    extent, visual name."""
    rec = {"c": name, "pos": rounded(pos if pos is not None else tile.pos),
           "rot": rounded(rot if rot is not None else tile.rot, 5)}
    scale = tile.scale if scale is None else scale
    if abs(scale - 1.0) > 1e-6:
        rec["scale"] = round(scale, ROUND)
    if abs(tile.scale_z - 1.0) > 1e-6:
        rec["sz"] = round(tile.scale_z, ROUND)
    if tile.walk_on:
        rec["walk"] = 1
    if tile.walk_through:
        rec["thru"] = 1
    if tile.stretch:
        rec["stretch"] = 1
    if tile.no_decal:
        rec["nodecal"] = 1
    if ext:
        rec["ext"] = ext
    if visual:
        rec["v"] = visual
    return rec


def root_templates(path):
    """Every root template of a file: {GUID: {"type", "name", "visual", "parent"}}, and for level
    templates also "sub" (the sub-level they place) and "loaded" (False if the story loads it later)."""
    out = {}
    for node in game_objects(path):
        a = _attrs(node)
        if "MapKey" not in a:
            continue
        rec = {"type": a.get("Type", ""), "name": a.get("Name", ""),
               "visual": a.get("VisualTemplate", "") or "", "parent": a.get("ParentTemplateId", "") or ""}
        if rec["type"] == "LevelTemplate" and a.get("SubLevelName"):
            rec["sub"] = a["SubLevelName"]
            rec["loaded"] = a.get("StartingLoaded", "True") == "True"
        out[a["MapKey"]] = rec
    return out


def level_templates(path):
    """The level templates of a root template file: {template GUID: {"name", "sub", "loaded"}}."""
    return {k: {"name": v["name"], "sub": v["sub"], "loaded": v["loaded"]}
            for k, v in root_templates(path).items() if "sub" in v}


def visual_of(template, templates):
    """The visual a template is drawn with, inherited from its parents when it has none of its own."""
    seen = set()
    while template and template not in seen:
        seen.add(template)
        rec = templates.get(template)
        if not rec:
            return ""
        if rec.get("visual"):
            return rec["visual"]
        template = rec.get("parent", "")
    return ""


def bank(path):
    """From a resource bank: the bounds of every visual ({ID: [min x, y, z, max x, y, z]}, in the visual's
    own frame), the visual of every tile of its tile sets ({tile GUID: visual ID}), and the name of every
    visual ({ID: Name})."""
    bounds, tiles, names = {}, {}, {}
    region = None
    for event, elem in ET.iterparse(path, events=("start", "end")):
        if event == "start":
            if elem.tag == "region":
                region = elem.get("id")
            continue
        if elem.tag != "node":
            continue
        node_id = elem.get("id")
        if region == "TileSetBank" and node_id == "Tile":
            a = _attrs(elem)
            if a.get("TileGUID") and a.get("VisualGUID"):
                tiles[a["TileGUID"]] = a["VisualGUID"]
        elif node_id == "Resource":
            if region == "VisualBank":
                a = _attrs(elem)
                if "ID" in a:
                    if "BoundsMin" in a and "BoundsMax" in a:
                        bounds[a["ID"]] = rounded(_floats(a["BoundsMin"]) + _floats(a["BoundsMax"]))
                    if a.get("Name"):
                        names[a["ID"]] = a["Name"]
            elem.clear()
    return bounds, tiles, names


def placed(rec, placement, via, sub, later):
    """A sub-level object record moved into the main level."""
    pos, rot, scale = place(placement, rec["pos"], rec["rot"], rec.get("scale", 1.0))
    out = dict(rec)
    out["pos"] = rounded(pos)
    out["rot"] = rounded(rot, 5)
    if abs(scale - 1.0) > 1e-6:
        out["scale"] = round(scale, ROUND)
    else:
        out.pop("scale", None)
    out["via"] = via
    out["sub"] = sub
    if later:
        out["later"] = True
    return out


# ------------------------------------------------------------------------ story

_GUID = r"(?:\w*?_)?([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
RX_WAYPOINT_CALL = re.compile(
    r'\b(PROC_LockWaypoint|PROC_LockWaypointForAll|PROC_UnlockWaypoint|PROC_UnlockWaypointForAll'
    r'|PROC_LockAllGroupWaypoints|PROC_UnlockAllGroupWaypoints)\(\s*"(\w+)"')
RX_LOCK_ALL = re.compile(r"\bPROC_LockAllUnlockedWaypoints\(\s*\)")
RX_DANGER = re.compile(r'^[ \t]*(NOT\s+)?DB_DangerZone\(\s*(?:\(TRIGGER\))?\s*' + _GUID + r'\s*,\s*"(\w*)"\s*\)\s*;', re.M)
RX_BLOCKED = re.compile(r'^[ \t]*(NOT\s+)?DB_BlockedWaypointZone\(\s*(?:\(TRIGGER\))?\s*' + _GUID + r'\s*\)\s*;', re.M)
RX_SAFE = re.compile(r'^[ \t]*(NOT\s+)?DB_DangerZone_SafeBubble\(\s*(?:\(TRIGGER\))?\s*' + _GUID + r'\s*\)\s*;', re.M)
RX_UNDERDARK = re.compile(r'^[ \t]*DB_UND_BroodingSpovereign_UnderdarkWaypoints\(\s*"(\w+)"\s*\)\s*;', re.M)
WATCHED_GOALS = ("_Waypoints",)   # the game's waypoint rules (Shared): any change to them needs a look
RX_LINE_COMMENT = re.compile(r"//.*$", re.M)
RX_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)


def strip_comments(text):
    """Osiris code without its comments, with the line numbers kept."""
    text = RX_BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return RX_LINE_COMMENT.sub("", text)


def fingerprint(code):
    """A short fingerprint of Osiris code that changes only when the code does: comments and spacing
    are left out."""
    return hashlib.sha256(" ".join(strip_comments(code).split()).encode("utf-8")).hexdigest()[:16]


def story(goals):
    """What the story does with waypoints and travel.

    goals: iterable of (module, goal name, text). Returns
      {"waypoints": {id: [call]}, "groups": {group: [call]}, "all": [call],
       "zones": {trigger GUID: [{"type": "danger"|"blocked"|"safe", "id", "goal", "module", "line", "removed"}]},
       "rules": {goal: fingerprint} for the goals in WATCHED_GOALS, "underdark": [waypoint id]}
    where a call is {"call", "goal", "module", "line", "listener"}: listener is True when the
    line declares a rule that runs whenever the story makes that call (PROC ... THEN), not a call."""
    out = {"waypoints": {}, "groups": {}, "all": [], "zones": {}, "rules": {}, "underdark": []}
    for module, goal, text in goals:
        code = strip_comments(text)
        if goal in WATCHED_GOALS:
            out["rules"][goal] = fingerprint(text)
        out["underdark"] += RX_UNDERDARK.findall(code)
        code_lines = code.splitlines()
        for i, line in enumerate(code_lines):
            previous = next((code_lines[j].strip() for j in range(i - 1, -1, -1) if code_lines[j].strip()), "")
            listener = previous == "PROC"
            for call, arg in RX_WAYPOINT_CALL.findall(line):
                entry = {"call": call, "goal": goal, "module": module, "line": i + 1, "listener": listener}
                if call in ("PROC_LockAllGroupWaypoints", "PROC_UnlockAllGroupWaypoints"):
                    out["groups"].setdefault(arg, []).append(entry)
                else:
                    out["waypoints"].setdefault(arg, []).append(entry)
            if RX_LOCK_ALL.search(line):
                out["all"].append({"call": "PROC_LockAllUnlockedWaypoints", "goal": goal, "module": module,
                                   "line": i + 1, "listener": listener})
        for rx, kind in ((RX_DANGER, "danger"), (RX_BLOCKED, "blocked"), (RX_SAFE, "safe")):
            for m in rx.finditer(code):
                line = code.count("\n", 0, m.start()) + 1
                zone_id = m.group(3) if kind == "danger" else ""
                out["zones"].setdefault(m.group(2), []).append({
                    "type": kind, "id": zone_id, "goal": goal, "module": module, "line": line,
                    "removed": bool(m.group(1))})
    out["underdark"] = sorted(set(out["underdark"]))
    return out
