"""
waypoints.py - the waypoint list (waypoints.json), its geometry and its checks.

Shared by build_waypoints.py (generates the mod files, checks the list) and
survey.py (finds good places for new waypoints).

A waypoint is built the way the game builds its own (measured on all 38 of them):
  * the shrine stands upright, its rune face towards the arrival point;
  * the arrival point is a teleport trigger on free floor in front of it, about 2 m away;
  * the rune is a decal 1.5 m up the shrine, turned to lie flat on its face.
"""
from __future__ import annotations

import json
import math
import os
import re

from navgrid import BLOCKED, CELL, NavGrid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = "NotEnoughWaypoints"
DATA_FILE = os.path.join(ROOT, "waypoints.json")
CACHE = os.path.join(ROOT, "tools", ".cache")

SHRINE_TEMPLATE = "2dab7df1-7914-4748-b329-b4fe8b60fcc9"   # Helper_Waypoint_A, the game's waypoint shrine
TRIGGER_TEMPLATE = "f7bd7465-b0ec-45b3-81f6-6f01d6c68c48"  # TeleportTrigger, the arrival point
POINT_TRIGGER_TEMPLATE = "15111ce4-12fc-4757-bb81-7c2c212e141a"  # PointTrigger: where scripts send characters
DECAL_TEMPLATES = {
    "dark": "4aa6eeee-3d1b-45fc-8397-ad149db8c581",   # DCL_Waypoint_Dark_A (Acts 1 and 2, underground)
    "light": "fe811f3b-9c1e-43be-ba99-58628f614584",  # DCL_Waypoint_Light_A (Baldur's Gate streets)
}
DECAL_HEIGHT = 1.5                                   # metres up the shrine
DECAL_TILT = (-math.sqrt(0.5), 0.0, 0.0, math.sqrt(0.5))  # -90 degrees about the shrine's x axis

# The story groups waypoints by act; the game locks a whole group when the story leaves it.
GROUP_OF_LEVEL = {
    "WLD_Main_A": "Act1",
    "CRE_Main_A": "Act1b",
    "SCL_Main_A": "Act2",
    "BGO_Main_A": "Act3",
    "CTY_Main_A": "Act3b",
}

# Shrine footprint (from the template's bounds: 2.4 m wide, 0.25 m deep, 3 m tall).
SHRINE_HALF_WIDTH = 1.2
SHRINE_HALF_DEPTH = 0.125
SHRINE_HEIGHT = 3.0
SINK = 0.05  # the shrine is set this far into the floor, so no gap shows under it

RE_ID = re.compile(r"^NEW_WAYP_[A-Z]{3}_[A-Za-z0-9]+$")
RE_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RE_HANDLE = re.compile(r"^h[0-9a-f]{8}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{12}$")


# ----------------------------------------------------------------------- geometry

def quat_yaw(degrees: float):
    """Rotation about the vertical axis, as the (x, y, z, w) quaternion the game stores."""
    half = math.radians(degrees) / 2
    return (0.0, math.sin(half), 0.0, math.cos(half))


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def rotate(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2 * (y * vz - z * vy)
    ty = 2 * (z * vx - x * vz)
    tz = 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty),
            vy + w * ty + (z * tx - x * tz),
            vz + w * tz + (x * ty - y * tx))


def facing_yaw(shrine, trigger) -> float:
    """Yaw that turns the shrine's rune face (its local -z side) towards the arrival point."""
    dx, dz = trigger[0] - shrine[0], trigger[2] - shrine[2]
    return round(math.degrees(math.atan2(-dx, -dz)), 2)


def shrine_yaw(wp) -> float:
    s = wp["shrine"]
    return float(s["yaw"]) if "yaw" in s else facing_yaw(s["position"], wp["trigger"]["position"])


def decal_transform(shrine_position, yaw: float):
    q = quat_yaw(yaw)
    up = rotate(q, (0.0, DECAL_HEIGHT, 0.0))
    position = tuple(p + u for p, u in zip(shrine_position, up))
    return position, quat_mul(q, DECAL_TILT)


def front(yaw: float):
    """Unit x/z vector of the rune face."""
    r = math.radians(yaw)
    return (-math.sin(r), -math.cos(r))


def num(v: float, places: int = 6) -> str:
    """A float the way the game files write them: no trailing zeros, no '-0'."""
    s = ("%." + str(places) + "f") % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------------------- data

def load(path: str = DATA_FILE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def object_names(wp) -> dict:
    return {"shrine": "S_%s_Shrine" % wp["id"], "trigger": "S_%s_Trigger" % wp["id"], "decal": "S_%s_Decal" % wp["id"]}


def problems(data: dict) -> list[str]:
    """Everything wrong with waypoints.json that can be seen without the game files."""
    out = []
    seen_ids, seen_names, seen_guids, seen_handles = set(), set(), set(), set()
    waypoints = data.get("waypoints")
    if not isinstance(waypoints, list) or not waypoints:
        return ["waypoints.json has no waypoints"]
    for i, wp in enumerate(waypoints):
        where = wp.get("id") or "waypoint #%d" % (i + 1)
        wid, name, level, group = wp.get("id", ""), wp.get("name", ""), wp.get("level", ""), wp.get("group", "")
        if not RE_ID.match(wid):
            out.append("%s: id must look like NEW_WAYP_<AREA>_<Name>, for example NEW_WAYP_DEN_Hollow" % where)
        if wid in seen_ids:
            out.append("%s: id used twice" % where)
        seen_ids.add(wid)
        if not name or len(name) > 40 or any(ord(c) < 32 or ord(c) > 126 for c in name):
            out.append("%s: name must be 1 to 40 plain ASCII characters" % where)
        if name.lower() in seen_names:
            out.append("%s: name '%s' used twice" % (where, name))
        seen_names.add(name.lower())
        if level not in GROUP_OF_LEVEL:
            out.append("%s: unknown level '%s' (known: %s)" % (where, level, ", ".join(GROUP_OF_LEVEL)))
        elif group != GROUP_OF_LEVEL[level]:
            out.append("%s: waypoints in %s belong to group '%s', not '%s'" % (where, level, GROUP_OF_LEVEL[level], group))
        handle = wp.get("handle", "")
        if not RE_HANDLE.match(handle):
            out.append("%s: handle must look like h1234abcdg1234g1234g1234g1234567890ab" % where)
        if handle in seen_handles:
            out.append("%s: handle used twice" % where)
        seen_handles.add(handle)
        positions = 0
        for part in ("shrine", "trigger", "decal"):
            obj = wp.get(part)
            if not isinstance(obj, dict):
                out.append("%s: missing '%s'" % (where, part))
                continue
            guid = obj.get("guid", "")
            if not RE_GUID.match(guid):
                out.append("%s: %s.guid is not a lower-case GUID" % (where, part))
            if guid in seen_guids:
                out.append("%s: %s.guid used twice" % (where, part))
            seen_guids.add(guid)
            if part != "decal":
                pos = obj.get("position")
                if isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos):
                    positions += 1
                else:
                    out.append("%s: %s.position must be [x, y, z]" % (where, part))
        if wp.get("decal", {}).get("style") not in DECAL_TEMPLATES:
            out.append("%s: decal.style must be one of %s" % (where, ", ".join(DECAL_TEMPLATES)))
        if "yaw" in wp.get("shrine", {}) and not isinstance(wp["shrine"]["yaw"], (int, float)):
            out.append("%s: shrine.yaw must be a number of degrees" % where)
        if wp.get("underdark") and group != "Act1":
            out.append("%s: only Act 1 waypoints can be Underdark waypoints" % where)
        lock = wp.get("lockWith")
        if lock is not None and not re.match(r"^WAYP_[A-Za-z0-9_]+$", str(lock)):
            out.append("%s: lockWith must be the id of one of the game's own waypoints" % where)
        if positions == 2:
            s, t = wp["shrine"]["position"], wp["trigger"]["position"]
            d = math.hypot(t[0] - s[0], t[2] - s[2])
            if not 1.0 <= d <= 4.5:
                out.append("%s: the arrival point is %.1f m from the shrine (the game uses 0.5 to 4.5 m)" % (where, d))
    return out


# ------------------------------------------------------------------ game file cache

class Level:
    """The cached data of one level: its navigation grid and the objects the game places in it."""

    def __init__(self, name: str, cache: str = CACHE):
        folder = os.path.join(cache, "levels", name)
        self.name = name
        self.grid = NavGrid(os.path.join(folder, "aigrid.data"))
        with open(os.path.join(folder, "objects.json"), encoding="utf-8") as fh:
            self.objects = json.load(fh)
        self.solid = [o for o in self.objects if o["kind"] in ("Characters", "Items", "Scenery")]
        self.points = [o for o in self.objects if o["kind"] == "Triggers" and o["tpl"] == POINT_TRIGGER_TEMPLATE]

    @staticmethod
    def available(name: str, cache: str = CACHE) -> bool:
        folder = os.path.join(cache, "levels", name)
        return os.path.exists(os.path.join(folder, "aigrid.data")) and os.path.exists(os.path.join(folder, "objects.json"))

    def floor(self, x, z, near, tolerance=2.0):
        return self.grid.floor(x, z, near, tolerance)

    def near(self, objects, x, y, z, radius, height=2.0):
        return [o for o in objects
                if abs(o["pos"][1] - y) <= height and math.hypot(o["pos"][0] - x, o["pos"][2] - z) <= radius]


def vanilla_waypoints(cache: str = CACHE) -> list[dict]:
    path = os.path.join(cache, "vanilla_waypoints.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ placement checks

def footprint(position, yaw, margin=0.0, step=0.25):
    """Sample points under the shrine (and `margin` metres around it)."""
    fx, fz = front(yaw)
    sx, sz = -fz, fx  # along the shrine's width
    half_w = SHRINE_HALF_WIDTH + margin
    half_d = SHRINE_HALF_DEPTH + margin
    points = []
    u = -half_w
    while u <= half_w + 1e-6:
        v = -half_d
        while v <= half_d + 1e-6:
            points.append((position[0] + sx * u + fx * v, position[2] + sz * u + fz * v))
            v += step
        u += step
    return points


def check_placement(level: Level, wp) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one waypoint, measured against the game's navigation grid."""
    errors, warnings = [], []
    shrine = wp["shrine"]["position"]
    trigger = wp["trigger"]["position"]
    yaw = shrine_yaw(wp)
    tag = wp["id"]

    # The arrival point: on free floor, with room around it for the whole party.
    floor = level.floor(trigger[0], trigger[2], trigger[1], 1.0)
    if floor is None:
        errors.append("%s: no free floor under the arrival point" % tag)
        return errors, warnings
    if abs(trigger[1] - floor) > 0.15:
        errors.append("%s: the arrival point is %+.2f m from the floor (%.2f)" % (tag, trigger[1] - floor, floor))
    tight = 0
    for dz in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            h = level.floor(trigger[0] + dx * CELL, trigger[2] + dz * CELL, floor, 0.4)
            if h is None:
                tight += 1
    if tight:
        errors.append("%s: %d of the 25 floor cells within 1 m of the arrival point are blocked" % (tag, tight))

    # The shrine: on flat free floor, not floating, not sunk, with nothing overhead.
    heights = []
    for x, z in footprint(shrine, yaw):
        h = level.floor(x, z, shrine[1] + SINK, 0.5)
        if h is None:
            errors.append("%s: part of the shrine stands on blocked floor or over a drop" % tag)
            break
        heights.append(h)
    if heights:
        low, high = min(heights), max(heights)
        if high - low > 0.3:
            errors.append("%s: the floor under the shrine varies by %.2f m" % (tag, high - low))
        if not low - 0.2 <= shrine[1] <= low + 0.02:
            errors.append("%s: the shrine base is at %.2f, the floor under it from %.2f to %.2f" % (tag, shrine[1], low, high))
    for x, z in ((shrine[0], shrine[2]), (trigger[0], trigger[2])):
        for h, _flags in level.grid.surfaces(x, z):
            if shrine[1] + 0.5 < h < shrine[1] + SHRINE_HEIGHT + 0.3:
                errors.append("%s: another floor %.1f m above the shrine (a balcony or upper storey)" % (tag, h - shrine[1]))
                break

    # The rune face must look at the arrival point, with walkable floor in between.
    fx, fz = front(yaw)
    dx, dz = trigger[0] - shrine[0], trigger[2] - shrine[2]
    dist = math.hypot(dx, dz)
    if dist and (fx * dx + fz * dz) / dist < 0.5:
        warnings.append("%s: the rune face does not look towards the arrival point" % tag)
    steps = max(2, int(dist / 0.25))
    for k in range(1, steps):
        t = k / steps
        x, z = shrine[0] + dx * t, shrine[2] + dz * t
        if math.hypot(x - shrine[0], z - shrine[2]) < 0.5:
            continue
        if level.floor(x, z, floor, 0.5) is None:
            errors.append("%s: something blocks the way between the arrival point and the shrine" % tag)
            break

    # Nothing of the game's in the way: characters, items and props near the shrine or the arrival point.
    for o in level.near(level.solid, shrine[0], shrine[1], shrine[2], SHRINE_HALF_WIDTH + 1.0):
        errors.append("%s: the shrine is %.1f m from %s" % (tag, math.dist(o["pos"], shrine), o["name"]))
    for o in level.near(level.solid, trigger[0], trigger[1], trigger[2], 1.5):
        errors.append("%s: the arrival point is %.1f m from %s" % (tag, math.dist(o["pos"], trigger), o["name"]))
    for o in level.near(level.points, shrine[0], shrine[1], shrine[2], SHRINE_HALF_WIDTH + 0.5):
        warnings.append("%s: the shrine stands on a point scripts send characters to (%s)" % (tag, o["name"]))
    return errors, warnings
