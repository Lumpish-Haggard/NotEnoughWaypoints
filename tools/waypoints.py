"""
waypoints.py - the waypoint list (waypoints.json), its geometry and its checks.

Shared by build_waypoints.py (generates the mod files, checks the list) and
survey.py (finds good places for new waypoints).

What a waypoint looks like in the game
  The game's waypoint "shrine" (Helper_Waypoint_A) is an invisible object: it is what
  players use and what unlocks the waypoint. What they see is a rock next to it, with
  the rune (a decal) projected onto the rock's face. Larian builds each one by hand.

  This mod copies one of them exactly: the Blighted Village waypoint (S_FOR_WaypointShrine).
  It stands on flat ground and is upright, so the same arrangement fits on any flat floor:
    * the invisible shrine, turned so that its front (local -z) faces the arrival point;
    * the boulder (NAT_Rock_Boulder_B at 1.2 scale), from the shrine's plane to 2.3 m behind it;
    * the rune, 1.5 m up, just inside the boulder's face;
    * the arrival point, a teleport trigger on free floor in front, about 2 m away.
  The boulder comes in several colours that share one mesh, so any of them fits.
"""
from __future__ import annotations

import json
import math
import os
import re

from navgrid import CELL, NavGrid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MOD = "NotEnoughWaypoints"
DATA_FILE = os.path.join(ROOT, "waypoints.json")
CACHE = os.path.join(ROOT, "tools", ".cache")

SHRINE_TEMPLATE = "2dab7df1-7914-4748-b329-b4fe8b60fcc9"   # Helper_Waypoint_A: the invisible waypoint object
TRIGGER_TEMPLATE = "f7bd7465-b0ec-45b3-81f6-6f01d6c68c48"  # TeleportTrigger: the arrival point
POINT_TRIGGER_TEMPLATE = "15111ce4-12fc-4757-bb81-7c2c212e141a"  # PointTrigger: where scripts send characters
DECAL_TEMPLATES = {
    "dark": "4aa6eeee-3d1b-45fc-8397-ad149db8c581",   # DCL_Waypoint_Dark_A (Acts 1 and 2, underground)
    "light": "fe811f3b-9c1e-43be-ba99-58628f614584",  # DCL_Waypoint_Light_A (Baldur's Gate streets)
}
ROCK_TEMPLATES = {                                    # all NAT_Rock_Boulder_B.GR2, different materials
    "grey": "99179bdb-43f3-4fa4-a40e-46c2101d3426",       # NAT_Rock_Boulder_B_Grey
    "grey_wet": "2a42f82d-2f63-4ffd-b7a7-cd31b31abb40",   # NAT_Rock_Boulder_B_Grey_Wet
    "grey_moss": "64e75246-41fb-4759-8e16-43b3e8a20c7b",  # NAT_Rock_Boulder_B_Grey_Moss (the Blighted Village one)
    "brown": "65f0089c-75c2-4ab3-a738-52fc782f0185",      # NAT_Rock_Boulder_B_Brown
    "brown_moss": "a11cf629-3d5d-4526-a19c-1e7b6378ee11",  # NAT_Rock_Boulder_B_Brown_Moss
}

# The Blighted Village arrangement, relative to the invisible shrine (x across, y up, z behind;
# the arrival point lies on the -z side). Measured from the game files: S_FOR_WaypointShrine,
# S_FOR_WaypointShrine_geo and S_FOR_WaypointShrine_DCL in WLD_Main_A.
SHRINE_ABOVE_FLOOR = 0.026
ROCK_OFFSET = (0.1715, 1.0096, 0.5984)
ROCK_ROTATION = (0.216247, 0.178869, -0.699633, 0.657082)
ROCK_SCALE = 1.2
DECAL_OFFSET = (0.0097, 1.5108, 0.1736)
DECAL_ROTATION = (-0.707052, 0.008834, 0.008834, 0.707051)
DECAL_DIMENSIONS = (3.0, 0.6, 3.0)   # the game's instance makes the decal shallower than its template (3 1 3)

# The boulder in that arrangement, measured on its mesh (shrine frame, metres):
ROCK_FOOTPRINT = (-1.5, 1.5, 0.0, 2.05)    # x from, x to, z from, z to: where it rests on the floor
ROCK_BODY = (-1.55, 1.75, -0.1, 2.35)      # x from, x to, z from, z to: everything above the floor
ROCK_HEIGHT = 3.2                          # top, above the shrine
ROCK_DEPTH = 0.71                          # bottom, below the shrine (it is set this far into the floor)
ROCK_FRONT = (-1.5, 1.5, 0.0, 0.5)         # the strip where the boulder meets the floor in front
FLOOR_DROP = 0.25                          # floor under the boulder may be this much lower than its front...
FLOOR_RISE = 1.0                           # ...and this much higher (it then sits in a rise, like the game's rocks)

# The story groups waypoints by act; the game locks a whole group when the story leaves it.
GROUP_OF_LEVEL = {
    "WLD_Main_A": "Act1",
    "CRE_Main_A": "Act1b",
    "SCL_Main_A": "Act2",
    "BGO_Main_A": "Act3",
    "CTY_Main_A": "Act3b",
}

RE_ID = re.compile(r"^NEW_WAYP_[A-Z]{3}_[A-Za-z0-9]+$")
RE_GUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
RE_HANDLE = re.compile(r"^h[0-9a-f]{8}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{4}g[0-9a-f]{12}$")
PARTS = ("shrine", "trigger", "decal", "rock")


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


def canonical(q):
    """The same rotation with w >= 0, as the game files write it."""
    return tuple(-v for v in q) if q[3] < 0 else tuple(q)


def facing_yaw(shrine, trigger) -> float:
    """Yaw that turns the shrine's front (its local -z side) towards the arrival point."""
    dx, dz = trigger[0] - shrine[0], trigger[2] - shrine[2]
    return round(math.degrees(math.atan2(-dx, -dz)), 2)


def shrine_yaw(wp) -> float:
    s = wp["shrine"]
    return float(s["yaw"]) if "yaw" in s else facing_yaw(s["position"], wp["trigger"]["position"])


def place(shrine_position, yaw, offset, rotation=None):
    """World position (and rotation) of a part given in the shrine's frame."""
    q = quat_yaw(yaw)
    d = rotate(q, offset)
    position = tuple(p + o for p, o in zip(shrine_position, d))
    return position, (canonical(quat_mul(q, rotation)) if rotation else None)


def decal_transform(shrine_position, yaw: float):
    return place(shrine_position, yaw, DECAL_OFFSET, DECAL_ROTATION)


def rock_transform(shrine_position, yaw: float):
    return place(shrine_position, yaw, ROCK_OFFSET, ROCK_ROTATION)


def front(yaw: float):
    """Unit x/z vector the shrine's front faces."""
    r = math.radians(yaw)
    return (-math.sin(r), -math.cos(r))


def to_world(shrine_position, yaw, x, z):
    """x/z of a point given in the shrine's frame (x across, z behind)."""
    p = rotate(quat_yaw(yaw), (x, 0.0, z))
    return shrine_position[0] + p[0], shrine_position[2] + p[2]


def area(shrine_position, yaw, box, step=0.25):
    """World x/z sample points of a rectangle given in the shrine's frame."""
    x0, x1, z0, z1 = box
    points = []
    x = x0
    while x <= x1 + 1e-6:
        z = z0
        while z <= z1 + 1e-6:
            points.append(to_world(shrine_position, yaw, x, z))
            z += step
        x += step
    return points


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
    return {part: "S_%s_%s" % (wp["id"], part.capitalize()) for part in PARTS}


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
        for part in PARTS:
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
            if part in ("shrine", "trigger"):
                pos = obj.get("position")
                if isinstance(pos, list) and len(pos) == 3 and all(isinstance(v, (int, float)) for v in pos):
                    positions += 1
                else:
                    out.append("%s: %s.position must be [x, y, z]" % (where, part))
        if wp.get("decal", {}).get("style") not in DECAL_TEMPLATES:
            out.append("%s: decal.style must be one of %s" % (where, ", ".join(DECAL_TEMPLATES)))
        if wp.get("rock", {}).get("style") not in ROCK_TEMPLATES:
            out.append("%s: rock.style must be one of %s" % (where, ", ".join(ROCK_TEMPLATES)))
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

    def inside(self, objects, shrine, yaw, box, margin, height=(-1.0, ROCK_HEIGHT)):
        """Objects within `margin` of a rectangle given in the shrine's frame, between the given heights."""
        q = quat_yaw(-yaw)
        found = []
        for o in objects:
            dy = o["pos"][1] - shrine[1]
            if not height[0] <= dy <= height[1]:
                continue
            x, _, z = rotate(q, (o["pos"][0] - shrine[0], 0.0, o["pos"][2] - shrine[2]))
            if box[0] - margin <= x <= box[1] + margin and box[2] - margin <= z <= box[3] + margin:
                found.append(o)
        return found


def vanilla_waypoints(cache: str = CACHE) -> list[dict]:
    path = os.path.join(cache, "vanilla_waypoints.json")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# ------------------------------------------------------------------ placement checks

def rock_base(level: Level, shrine, yaw, near):
    """The floor where the boulder meets it in front: the lowest free floor along its front edge."""
    heights = [level.floor(x, z, near, 0.6) for x, z in area(shrine, yaw, ROCK_FRONT)]
    heights = [h for h in heights if h is not None]
    return min(heights) if heights else None


def check_placement(level: Level, wp) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one waypoint, measured against the game's navigation grid."""
    errors, warnings = [], []
    shrine = wp["shrine"]["position"]
    trigger = wp["trigger"]["position"]
    yaw = shrine_yaw(wp)
    tag = wp["id"]
    base = shrine[1] - SHRINE_ABOVE_FLOOR   # the floor the arrangement was made for

    # The arrival point: on free floor, with room around it for the whole party.
    floor = level.floor(trigger[0], trigger[2], trigger[1], 1.0)
    if floor is None:
        errors.append("%s: no free floor under the arrival point" % tag)
        return errors, warnings
    if abs(trigger[1] - floor) > 0.15:
        errors.append("%s: the arrival point is %+.2f m from the floor (%.2f)" % (tag, trigger[1] - floor, floor))
    tight = sum(1 for dz in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2)
                if level.floor(trigger[0] + dx * CELL, trigger[2] + dz * CELL, floor, 0.4) is None)
    if tight:
        errors.append("%s: %d of the 25 floor cells within 1 m of the arrival point are blocked" % (tag, tight))

    # The boulder rests on free floor. Where the floor rises behind it, it sinks in further (as the game's
    # own rocks do on slopes); where the floor drops away, it would float, so that is not allowed.
    front_floor = rock_base(level, shrine, yaw, base)
    if front_floor is None or abs(front_floor - base) > 0.1:
        errors.append("%s: the shrine is not at the floor in front of the boulder (%s)" % (
            tag, "no floor there" if front_floor is None else "%.2f, shrine floor %.2f" % (front_floor, base)))
    heights, missing = [], 0
    for x, z in area(shrine, yaw, ROCK_FOOTPRINT):
        h = level.floor(x, z, base + 0.4, 0.7)
        if h is None:
            missing += 1
        else:
            heights.append(h)
    if missing:
        errors.append("%s: %d of %d points under the boulder are not free floor (a wall, furniture or a drop)" % (
            tag, missing, missing + len(heights)))
    if heights:
        low, high = min(heights), max(heights)
        if low < base - FLOOR_DROP or high > base + FLOOR_RISE:
            errors.append("%s: the floor under the boulder runs from %+.2f to %+.2f m around its base" % (tag, low - base, high - base))
    # Headroom: where the boulder or the party stands on a floor, no second floor (a balcony,
    # an upper storey) may run through it higher up.
    for x, z in area(shrine, yaw, ROCK_BODY, 0.5) + [(trigger[0], trigger[2])]:
        hs = [h for h, _flags in level.grid.surfaces(x, z)]
        ground = [h for h in hs if base - FLOOR_DROP - 0.1 <= h <= base + FLOOR_RISE]
        above = [h for h in hs if ground and min(ground) + 1.5 < h < base + ROCK_HEIGHT + 0.3]
        if above:
            errors.append("%s: another floor %.1f m above the waypoint (a balcony or upper storey)" % (tag, above[0] - base))
            break

    # The front must look at the arrival point, with walkable floor in between.
    fx, fz = front(yaw)
    dx, dz = trigger[0] - shrine[0], trigger[2] - shrine[2]
    dist = math.hypot(dx, dz)
    if dist and (fx * dx + fz * dz) / dist < 0.5:
        warnings.append("%s: the rune does not face the arrival point" % tag)
    steps = max(2, int(dist / 0.25))
    for k in range(1, steps):
        t = k / steps
        if level.floor(shrine[0] + dx * t, shrine[2] + dz * t, floor, 0.5) is None:
            errors.append("%s: something blocks the way between the arrival point and the boulder" % tag)
            break

    # Nothing of the game's in the way: characters, items and props in or near the boulder or the arrival point.
    for o in level.inside(level.solid, shrine, yaw, ROCK_BODY, 0.75):
        errors.append("%s: the boulder would touch %s" % (tag, o["name"]))
    for o in level.near(level.solid, trigger[0], trigger[1], trigger[2], 1.5):
        errors.append("%s: the arrival point is %.1f m from %s" % (tag, math.dist(o["pos"], trigger), o["name"]))
    for o in level.inside(level.points, shrine, yaw, ROCK_BODY, 0.5):
        warnings.append("%s: the boulder stands on a point scripts send characters to (%s)" % (tag, o["name"]))
    return errors, warnings
