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
CACHE_VERSION = 3   # the layout extract_game_data.py writes: 2 added sub-levels, tiles, trigger volumes and
                    # story.json; 3 added how far items, props and tiles reach ("ext")

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

# The rune on a wall, the way the game does it in towns and buildings: nothing is added, the invisible
# shrine stands at the foot of a wall and the rune is drawn on the wall above it. The game's fifteen
# runes in these levels that have no rock of their own are all turned the same way relative to their
# shrine, to within a few degrees (WALL_DECAL_ROTATION), and sit about 1.5 m above it (the Lower City
# Central Wall: 1.497 m). Here the shrine stands on the wall's face,
# found from the bounds of the wall's tiles, and the rune's centre is 6 cm in front of the face, where
# the Moonrise Towers rune is in front of its wall (the one game rune whose wall the tools can measure),
# and at the same 0.9 scale as that rune, which keeps the bottom of its box 15 cm clear of the floor.
# The rune's box is 0.27 m deep: it takes in the face whether the game projects a decal from the middle
# of its box or inward from its front, and reaches at most 0.21 m into the wall, so a wall at least
# WALL_THICKNESS thick never shows the rune on its far side.
WALL_DECAL_OFFSET = (0.0, 1.497, -0.06)
WALL_DECAL_ROTATION = (-0.707107, 0.0, 0.0, 0.707107)
WALL_DECAL_DIMENSIONS = (3.0, 0.3, 3.0)
WALL_DECAL_SCALE = 0.9
WALL_FACE_TOLERANCE = 0.05                 # the wall's face may be this far off the shrine's plane, either way
WALL_THICKNESS = 0.3
WALL_ARRIVAL = 2.0                         # the arrival point stands this far out from the wall
WALL_RUNE = (-1.35, 1.35, 0.17, 2.87)      # across from, to, up from, to (above the floor): the rune's box on the wall
STYLES = ("boulder", "wall")

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


def wall_decal_transform(shrine_position, yaw: float):
    return place(shrine_position, yaw, WALL_DECAL_OFFSET, WALL_DECAL_ROTATION)


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


def add(a, b):
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def mul(a, k):
    return (a[0] * k, a[1] * k, a[2] * k)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def frame_box(origin, yaw, lo, hi):
    """A box given in a frame turned by `yaw` at `origin` (lo and hi its corners in that frame), as
    (centre, axes, half sizes) in the world."""
    q = quat_yaw(yaw)
    centre = add(origin, rotate(q, tuple((a + b) / 2 for a, b in zip(lo, hi))))
    axes = tuple(rotate(q, e) for e in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    return centre, axes, tuple((b - a) / 2 for a, b in zip(lo, hi))


def box(o):
    """The box an object or a tile fills in the world, from the bounds of the visual it is drawn with:
    (centre, axes, half sizes), or None when they are not known. A stretchable tile is stretched
    along its length only, so its scale applies to its x alone."""
    if "_box" in o:
        return o["_box"]
    ext = o.get("ext")
    if not ext:
        return None
    s = o.get("scale", 1.0)
    k = (s, 1.0, 1.0) if o.get("stretch") else (s, s, s)
    lo = tuple(v * f for v, f in zip(ext[:3], k))
    hi = tuple(v * f for v, f in zip(ext[3:], k))
    q = tuple(o["rot"])
    centre = add(o["pos"], rotate(q, tuple((a + b) / 2 for a, b in zip(lo, hi))))
    axes = tuple(rotate(q, e) for e in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    o["_box"] = (centre, axes, tuple(abs(b - a) / 2 for a, b in zip(lo, hi)))
    return o["_box"]


def boxes_overlap(a, b, margin=0.0) -> bool:
    """Whether two boxes (centre, axes, half sizes) come within `margin` of each other (separating axes)."""
    ca, aa, ha = a
    cb, ab, hb = b
    d = sub(cb, ca)
    for axis in list(aa) + list(ab) + [cross(x, y) for x in aa for y in ab]:
        n = math.sqrt(dot(axis, axis))
        if n < 1e-9:
            continue
        axis = mul(axis, 1 / n)
        ra = sum(abs(dot(aa[i], axis)) * ha[i] for i in range(3))
        rb = sum(abs(dot(ab[i], axis)) * hb[i] for i in range(3))
        if abs(dot(d, axis)) > ra + rb + margin:
            return False
    return True


def box_span(b, axis):
    """The stretch of a box along an axis: (lowest, highest) of dot(point, axis)."""
    c, axes, half = b
    r = sum(abs(dot(axes[i], axis)) * half[i] for i in range(3))
    m = dot(c, axis)
    return m - r, m + r


def point_in_box(b, p, margin=0.0) -> bool:
    c, axes, half = b
    d = sub(p, c)
    return all(abs(dot(d, axes[i])) <= half[i] + margin for i in range(3))


def num(v: float, places: int = 6) -> str:
    """A float the way the game files write them: no trailing zeros, no '-0'."""
    s = ("%." + str(places) + "f") % v
    s = s.rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


# --------------------------------------------------------------------------- data

def load(path: str = DATA_FILE) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def parts_of(wp) -> tuple:
    """The objects a waypoint is made of: a rune on a wall has no rock."""
    return PARTS[:3] if wp.get("style") == "wall" else PARTS


def object_names(wp) -> dict:
    return {part: "S_%s_%s" % (wp["id"], part.capitalize()) for part in parts_of(wp)}


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
        style = wp.get("style", "boulder")
        if style not in STYLES:
            out.append("%s: style must be one of %s" % (where, ", ".join(STYLES)))
        positions = 0
        for part in parts_of(wp):
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
        if style == "boulder" and wp.get("rock", {}).get("style") not in ROCK_TEMPLATES:
            out.append("%s: rock.style must be one of %s" % (where, ", ".join(ROCK_TEMPLATES)))
        if style == "wall" and "rock" in wp:
            out.append("%s: a rune on a wall has no rock (list a released rock's guid under retired)" % where)
        if "yaw" in wp.get("shrine", {}) and not isinstance(wp["shrine"]["yaw"], (int, float)):
            out.append("%s: shrine.yaw must be a number of degrees" % where)
        if style == "wall" and "yaw" not in wp.get("shrine", {}):
            out.append("%s: a rune on a wall needs shrine.yaw, the way the wall faces" % where)
        placement = wp.get("placement", 1)
        if not isinstance(placement, int) or isinstance(placement, bool) or placement < 1:
            out.append("%s: placement must be a whole number from 1 (raise it by one whenever a released "
                       "waypoint moves)" % where)
        accept = wp.get("accept", [])
        if not isinstance(accept, list) or not all(isinstance(a, str) and len(a) >= 8 for a in accept):
            out.append("%s: accept must be a list of check results (at least 8 characters of their text)" % where)
        retired = wp.get("retired", [])
        if not isinstance(retired, list):
            out.append("%s: retired must be a list of GUIDs" % where)
            retired = []
        for guid in retired:
            if not RE_GUID.match(str(guid)):
                out.append("%s: retired guid %s is not a lower-case GUID" % (where, guid))
            if guid in seen_guids:
                out.append("%s: retired guid %s used twice" % (where, guid))
            seen_guids.add(guid)
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

# Placed objects that are not there to be seen or bumped into: camera colliders and other helpers.
RE_HELPER = re.compile(r"^(CAM_|AI_|FX_|Helper|Dummy)|Invisible|Collider|Blocker_Nav", re.I)
# Things that lie flat on the floor or hang thin on a wall: a boulder on one looks odd, but nothing clips.
RE_FLAT = re.compile(r"Carpet|Rug|Puddle|Blood|Mat_|Leaves_Pile|Rubble_Flat|_Tile_|SpiderWeb|Cobweb", re.I)
# Pieces the floor itself is made of (a rock slab, a wooden platform): below floor level they are
# what the boulder stands on, not something in its way.
RE_FLOOR_PIECE = re.compile(r"Platform|Floor|Ground|Slab", re.I)
# Tiles that are a floor, a ceiling or a roof rather than a wall (walkable tiles are floors too).
RE_TILE_OVER = re.compile(r"Ceiling|Roof|Floor|Platform|Balcony", re.I)


def in_the_way(o, floor) -> bool:
    """For an object whose extent is not known: whether it can be in the way of something standing on
    `floor`, rather than lie flat on it, hang thin on a wall or be part of the floor itself."""
    if RE_FLAT.search(o["name"]):
        return False
    return not (RE_FLOOR_PIECE.search(o["name"]) and o["pos"][1] < floor - 0.15)


class Indexed(list):
    """A list of placed things (anything with "pos"), also sorted into 8 m squares for quick lookups."""
    SIZE = 8.0

    def __init__(self, items=()):
        super().__init__(items)
        self._cells = {}
        for it in self:
            key = (math.floor(it["pos"][0] / self.SIZE), math.floor(it["pos"][2] / self.SIZE))
            self._cells.setdefault(key, []).append(it)

    def around(self, x, z, radius):
        """Everything in the squares that a circle of `radius` around x/z touches (a superset of the circle)."""
        cx, cz = math.floor(x / self.SIZE), math.floor(z / self.SIZE)
        r = int(math.ceil(radius / self.SIZE))
        out = []
        for i in range(cx - r, cx + r + 1):
            for j in range(cz - r, cz + r + 1):
                out.extend(self._cells.get((i, j), ()))
        return out


class BoxIndex:
    """Placed things sorted into 8 m squares by the whole area their box covers, so that a lookup returns
    everything whose box can reach a region however far away its own position is (a 16 m beam, a long
    wall). Things whose extent is not known count with `pad` metres around their position."""
    SIZE = 8.0

    HUGE = 32.0   # things that reach further than this (a backdrop, a whole cliff) are kept in one list

    def __init__(self, items=(), pad=0.75):
        self.items = list(items)
        self._cells = {}
        self._huge = []
        for k, it in enumerate(self.items):
            # A sphere around the box, from its extent and scale alone (no turning needed).
            ext, x, z = it.get("ext"), it["pos"][0], it["pos"][2]
            if ext:
                s = abs(it.get("scale", 1.0))
                reach = s * (math.sqrt(sum(((a + b) / 2) ** 2 for a, b in zip(ext[:3], ext[3:])))
                             + math.sqrt(sum(((b - a) / 2) ** 2 for a, b in zip(ext[:3], ext[3:]))))
            else:
                reach = pad
            if reach > self.HUGE:
                self._huge.append((k, x, z, reach))
                continue
            x0, x1, z0, z1 = x - reach, x + reach, z - reach, z + reach
            for i in range(math.floor(x0 / self.SIZE), math.floor(x1 / self.SIZE) + 1):
                for j in range(math.floor(z0 / self.SIZE), math.floor(z1 / self.SIZE) + 1):
                    self._cells.setdefault((i, j), []).append(k)

    def reaching(self, region, margin=0.0):
        """Everything whose box (or padded position) may reach into `region`, a box."""
        x0, x1 = box_span(region, (1.0, 0.0, 0.0))
        z0, z1 = box_span(region, (0.0, 0.0, 1.0))
        out = [self.items[k] for k, x, z, reach in self._huge
               if x - reach <= x1 + margin and x + reach >= x0 - margin and z - reach <= z1 + margin and z + reach >= z0 - margin]
        seen = {k for k, *_ in self._huge}
        for i in range(math.floor((x0 - margin) / self.SIZE), math.floor((x1 + margin) / self.SIZE) + 1):
            for j in range(math.floor((z0 - margin) / self.SIZE), math.floor((z1 + margin) / self.SIZE) + 1):
                for k in self._cells.get((i, j), ()):
                    if k not in seen:
                        seen.add(k)
                        out.append(self.items[k])
        return out


def candidates(objects, x, z, radius):
    return objects.around(x, z, radius) if isinstance(objects, Indexed) else objects


class Level:
    """The cached data of one level: its navigation grid, the objects the game places in it (its
    sub-levels included), the tiles of its walls and floors, and its trigger volumes."""

    def __init__(self, name: str, cache: str = CACHE):
        folder = os.path.join(cache, "levels", name)
        self.name = name
        self.grid = NavGrid(os.path.join(folder, "aigrid.data"))
        with open(os.path.join(folder, "objects.json"), encoding="utf-8") as fh:
            self.objects = json.load(fh)
        tiles = os.path.join(folder, "tiles.json")
        if os.path.exists(tiles):
            with open(tiles, encoding="utf-8") as fh:
                self.tiles = Indexed(json.load(fh))
        else:
            self.tiles = Indexed()
        self.tile_boxes = BoxIndex(self.tiles)
        self.solid = Indexed(o for o in self.objects
                             if o["kind"] in ("Characters", "Items", "Scenery") and not RE_HELPER.search(o["name"]))
        self.solid_boxes = BoxIndex(self.solid)
        self.points = Indexed(o for o in self.objects if o["kind"] == "Triggers" and o["tpl"] == POINT_TRIGGER_TEMPLATE)
        self.volumes = [o for o in self.objects if o["kind"] == "Triggers" and "shape" in o]
        self.decals = Indexed(o for o in self.objects if o["kind"] == "Decals")

    @staticmethod
    def available(name: str, cache: str = CACHE) -> bool:
        folder = os.path.join(cache, "levels", name)
        return os.path.exists(os.path.join(folder, "aigrid.data")) and os.path.exists(os.path.join(folder, "objects.json"))

    def floor(self, x, z, near, tolerance=2.0):
        return self.grid.floor(x, z, near, tolerance)

    def near(self, objects, x, y, z, radius, height=2.0):
        return [o for o in candidates(objects, x, z, radius)
                if abs(o["pos"][1] - y) <= height and math.hypot(o["pos"][0] - x, o["pos"][2] - z) <= radius]

    def inside(self, objects, shrine, yaw, box, margin, height=(-1.0, ROCK_HEIGHT)):
        """Objects within `margin` of a rectangle given in the shrine's frame, between the given heights."""
        q = quat_yaw(-yaw)
        reach = max(abs(v) for v in box) + margin
        found = []
        for o in candidates(objects, shrine[0], shrine[2], reach):
            dy = o["pos"][1] - shrine[1]
            if not height[0] <= dy <= height[1]:
                continue
            x, _, z = rotate(q, (o["pos"][0] - shrine[0], 0.0, o["pos"][2] - shrine[2]))
            if box[0] - margin <= x <= box[1] + margin and box[2] - margin <= z <= box[3] + margin:
                found.append(o)
        return found

    def zones(self, point):
        """The trigger volumes that contain a point."""
        return [o for o in self.volumes if inside_volume(o, point)]


def inside_volume(obj, point) -> bool:
    """Whether a point is inside a trigger's volume. Boxes are centred on the trigger and their
    "Extents" are the full size; prisms ("Points" and "Height") rise from the trigger's height."""
    shape = obj.get("shape")
    if not shape:
        return False
    x, y, z, w = obj["rot"]
    scale = obj.get("scale", 1.0) or 1.0
    lx, ly, lz = rotate((-x, -y, -z, w), tuple((p - c) / scale for p, c in zip(point, obj["pos"])))
    if "box" in shape:
        ex, ey, ez = shape["box"]
        return abs(lx) <= ex / 2 and abs(ly) <= ey / 2 and abs(lz) <= ez / 2
    if "sphere" in shape:
        return math.sqrt(lx * lx + ly * ly + lz * lz) <= shape["sphere"]
    if "poly" in shape:
        if not 0.0 <= ly <= shape.get("h", 0.0):
            return False
        return point_in_polygon(lx, lz, shape["poly"])
    return False


def point_in_polygon(x, z, poly) -> bool:
    inside = False
    n = len(poly)
    for i in range(n):
        x1, z1 = poly[i]
        x2, z2 = poly[(i + 1) % n]
        if (z1 > z) != (z2 > z) and x < x1 + (z - z1) * (x2 - x1) / (z2 - z1):
            inside = not inside
    return inside


def describe(o) -> str:
    """An object's name, with the sub-level it comes from and whether the story loads it later."""
    out = o.get("name") or o.get("c") or o.get("key", "?")
    if o.get("via"):
        out += " (%s)" % o["via"].split("/")[-1]
    if o.get("later"):
        out += ", once the story loads it"
    return out


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


class Failed(Exception):
    """Raised in quick mode at the first error: the searches only need to know whether a place passes."""


class Errors(list):
    def __init__(self, quick=False):
        super().__init__()
        self.quick = quick

    def append(self, item):
        super().append(item)
        if self.quick:
            raise Failed(item)


def check_placement(level: Level, wp, quick=False) -> tuple[list[str], list[str]]:
    """(errors, warnings) for one waypoint, measured against the game's data. An error that the waypoint's
    "accept" list names (a piece of its text) was looked at and accepted: it is reported as a warning.
    In quick mode it stops at the first error (and an accepted one counts as an error)."""
    try:
        if wp.get("style", "boulder") == "wall":
            errors, warnings = check_wall(level, wp, Errors(quick))
        else:
            errors, warnings = check_boulder(level, wp, Errors(quick))
    except Failed as e:
        return [str(e)], []
    accepted = [e for e in errors if any(a in e for a in wp.get("accept", []))]
    for e in accepted:
        errors.remove(e)
        warnings.append(e.replace(": ", ": accepted after review: ", 1))
    return errors, warnings


def obstacles(level: Level, region, floor):
    """The game's characters, items and props that reach into `region` (a box), each as (object, kind):
    "solid" for something in the way, "flat" for something lying on the floor (a carpet, floor tiles),
    "large" for a big piece (a cliff, a building's shell) whose box fits it loosely. An object whose
    extent is not known counts when its position is within 0.75 m of the region."""
    centre, _axes, half = region
    found = []
    for o in level.solid_boxes.reaching(region, 0.75):
        b = box(o)
        if b is None:
            if point_in_box(region, o["pos"], 0.75) and o["pos"][1] >= floor - 0.3:
                if in_the_way(o, floor):
                    found.append((o, "solid"))
                elif RE_FLAT.search(o["name"]):
                    found.append((o, "flat"))
            continue
        if not boxes_overlap(region, b):
            continue
        _low, high = box_span(b, (0.0, 1.0, 0.0))
        if high < floor + 0.12:
            if RE_FLAT.search(o["name"]):
                found.append((o, "flat"))
            continue
        if RE_FLAT.search(o["name"]):
            found.append((o, "flat"))
        elif sum(1 for h in b[2] if h > 2.0) >= 2:
            found.append((o, "large"))
        else:
            found.append((o, "solid"))
    return found


def tile_hits(level: Level, region, base):
    """Tiles of walls, floors and roofs whose box reaches into `region`: ("wall", tile, height) for a wall,
    ("over", tile, height) for a floor, ceiling or roof more than 1 m above `base` (the height is where
    the tile's box starts, above `base`). Tiles whose extent is not known are left out."""
    centre, _axes, half = region
    found = []
    for t in level.tile_boxes.reaching(region):
        b = box(t)
        if b is None or not boxes_overlap(region, b):
            continue
        low, high = box_span(b, (0.0, 1.0, 0.0))
        if high < base + 0.12:
            continue
        if t.get("walk") or RE_TILE_OVER.search(t.get("c", "")):
            if low > base + 1.0:
                found.append(("over", t, low - base))
            continue
        if not t.get("thru"):
            found.append(("wall", t, low - base))
    return found


def check_arrival(level: Level, wp, errors, warnings):
    """The arrival point: on free floor, with room around it for the whole party, and nothing of the
    game's standing there. Returns the floor's height there, or None."""
    trigger = wp["trigger"]["position"]
    tag = wp["id"]
    floor = level.floor(trigger[0], trigger[2], trigger[1], 1.0)
    if floor is None:
        errors.append("%s: no free floor under the arrival point" % tag)
        return None
    if abs(trigger[1] - floor) > 0.15:
        errors.append("%s: the arrival point is %+.2f m from the floor (%.2f)" % (tag, trigger[1] - floor, floor))
    tight = sum(1 for dz in (-2, -1, 0, 1, 2) for dx in (-2, -1, 0, 1, 2)
                if level.floor(trigger[0] + dx * CELL, trigger[2] + dz * CELL, floor, 0.4) is None)
    if tight > ARRIVAL_BLOCKED:
        errors.append("%s: %d of the 25 floor cells within 1 m of the arrival point are blocked" % (tag, tight))
    elif tight:
        warnings.append("%s: %d of the 25 floor cells within 1 m of the arrival point are blocked" % (tag, tight))
    region = frame_box((trigger[0], floor, trigger[2]), 0.0, (-0.6, 0.12, -0.6), (0.6, 2.0, 0.6))
    for o, kind in obstacles(level, region, floor):
        if kind == "solid":
            errors.append("%s: %s stands at the arrival point" % (tag, describe(o)))
        elif kind == "large":
            warnings.append("%s: the arrival point is inside the box of %s, a large piece that its box fits "
                            "loosely" % (tag, describe(o)))
    for o in level.near(level.points, trigger[0], trigger[1], trigger[2], 1.0):
        warnings.append("%s: the arrival point is %.1f m from %s, a point scripts send characters to" % (
            tag, math.dist(o["pos"], trigger), describe(o)))
    return floor


def check_way(level: Level, wp, floor, short, errors, warnings):
    """The waypoint faces its arrival point, with walkable floor from it to `short` metres before the shrine."""
    shrine, trigger = wp["shrine"]["position"], wp["trigger"]["position"]
    fx, fz = front(shrine_yaw(wp))
    dx, dz = trigger[0] - shrine[0], trigger[2] - shrine[2]
    dist = math.hypot(dx, dz)
    if dist and (fx * dx + fz * dz) / dist < 0.5:
        warnings.append("%s: the rune does not face the arrival point" % wp["id"])
    steps = max(2, int(dist / 0.25))
    for k in range(1, steps):
        t = k / steps
        if t * dist < short:
            continue
        if level.floor(shrine[0] + dx * t, shrine[2] + dz * t, floor, 0.5) is None:
            errors.append("%s: something blocks the way between the arrival point and the %s" % (
                wp["id"], "wall" if wp.get("style") == "wall" else "boulder"))
            break


def check_boulder(level: Level, wp, errors=None) -> tuple[list[str], list[str]]:
    errors, warnings = errors if errors is not None else [], []
    shrine = wp["shrine"]["position"]
    trigger = wp["trigger"]["position"]
    yaw = shrine_yaw(wp)
    tag = wp["id"]
    base = shrine[1] - SHRINE_ABOVE_FLOOR   # the floor the arrangement was made for

    floor = check_arrival(level, wp, errors, warnings)
    if floor is None:
        return errors, warnings

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

    check_way(level, wp, floor, 0.0, errors, warnings)

    # Nothing of the game's in the way: characters, items and props in the boulder, those of the level's
    # sub-levels included (furniture, pillars, beams ...), measured on the boxes they fill.
    body = frame_box(shrine, yaw, (ROCK_BODY[0], -ROCK_DEPTH, ROCK_BODY[2]), (ROCK_BODY[1], ROCK_HEIGHT, ROCK_BODY[3]))
    for o, kind in obstacles(level, body, base):
        if kind == "solid":
            errors.append("%s: the boulder would touch %s" % (tag, describe(o)))
        elif kind == "flat":
            warnings.append("%s: the boulder would stand on %s" % (tag, describe(o)))
        else:
            warnings.append("%s: the boulder reaches into the box of %s, a large piece that its box fits "
                            "loosely" % (tag, describe(o)))
    for o in level.inside(level.points, shrine, yaw, ROCK_BODY, 0.5):
        warnings.append("%s: the boulder stands on a point scripts send characters to (%s)" % (tag, describe(o)))
    for kind, t, dy in tile_hits(level, body, base):
        if kind == "wall":
            errors.append("%s: the boulder would cut into the wall %s" % (tag, describe(t)))
        else:
            errors.append("%s: %s is built %.1f m above the waypoint, through the boulder" % (tag, describe(t), dy))
    return errors, warnings


# Room for the party: at most this many of the 25 floor cells within 1 m of the arrival point may be
# blocked (the game spreads the party around it).
ARRIVAL_BLOCKED = 5
# In front of a rune on a wall: anything this close to the face would have the rune drawn on it; further
# out, up to VIEW_DEPTH, anything that reaches higher than VIEW_HEIGHT above the floor hides the rune.
PROJECTION_DEPTH = 0.25
VIEW_DEPTH = 0.8
VIEW_HEIGHT = 0.9

# What a rune must not be drawn across: a way through the wall, or something hung in it.
RE_OPENING = re.compile(r"Door|Gate|Hatch|Portcullis|Window|Shutter|Arch(?!ive)|Opening|Entrance|Ladder|Stairs", re.I)


def wall_axes(yaw):
    """For a shrine on a wall: (across, along the wall; behind, into the wall)."""
    q = quat_yaw(yaw)
    return rotate(q, (1.0, 0.0, 0.0)), rotate(q, (0.0, 0.0, 1.0))


def rune_box(shrine, yaw):
    """The box the rune is projected in, as the game would draw it (centre, axes, half sizes)."""
    position, rotation = place(shrine, yaw, WALL_DECAL_OFFSET, WALL_DECAL_ROTATION)
    axes = tuple(rotate(rotation, e) for e in ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0)))
    return position, axes, tuple(v / 2 * WALL_DECAL_SCALE for v in WALL_DECAL_DIMENSIONS)


def check_wall(level: Level, wp, errors=None) -> tuple[list[str], list[str]]:
    """(errors, warnings) for a waypoint whose rune is drawn on a wall."""
    errors, warnings = errors if errors is not None else [], []
    shrine = wp["shrine"]["position"]
    yaw = shrine_yaw(wp)
    tag = wp["id"]
    base = shrine[1] - SHRINE_ABOVE_FLOOR
    across, behind = wall_axes(yaw)
    plane = shrine   # the shrine stands on the wall's face

    floor = check_arrival(level, wp, errors, warnings)
    if floor is None:
        return errors, warnings

    # The shrine stands on the floor at the foot of the wall.
    near = level.floor(shrine[0] - behind[0] * 0.5, shrine[2] - behind[2] * 0.5, base, 0.3)
    if near is None or abs(near - base) > 0.1:
        errors.append("%s: the shrine is not at the floor in front of the wall (%s)" % (
            tag, "no floor there" if near is None else "%.2f, shrine floor %.2f" % (near, base)))

    # The wall's face runs along the shrine's plane everywhere the rune is drawn: there is wall just
    # behind the plane and still WALL_THICKNESS behind it, and open air just in front of it.
    area = frame_box(shrine, yaw, (WALL_RUNE[0] - 0.5, -0.5, -1.0), (WALL_RUNE[1] + 0.5, WALL_RUNE[3] + 0.5, 1.0))
    nearby = level.tile_boxes.reaching(area)
    walls = [box(t) for t in nearby if not t.get("walk") and not t.get("thru") and t.get("ext")]
    openings = [t for t in nearby if RE_OPENING.search(t.get("c", ""))]

    def solid_at(p):
        return any(point_in_box(b, p) for b in walls)

    missing = thin = buried = total = 0
    for u in (-1.3, -0.87, -0.43, 0.0, 0.43, 0.87, 1.3):
        for v in (0.2, 0.64, 1.08, 1.52, 1.96, 2.4, 2.84):
            p = add(add(plane, mul(across, u)), (0.0, base + v - plane[1], 0.0))
            total += 1
            if not solid_at(add(p, mul(behind, WALL_FACE_TOLERANCE))):
                missing += 1
            elif not solid_at(add(p, mul(behind, WALL_THICKNESS - 0.02))):
                thin += 1
            elif solid_at(add(p, mul(behind, -WALL_FACE_TOLERANCE))):
                buried += 1
    if missing:
        errors.append("%s: there is no wall behind %d of the rune's %d points (an opening, or the face is further "
                      "back)" % (tag, missing, total))
    if thin:
        errors.append("%s: the wall is thinner than %.1f m behind %d of the rune's %d points (the rune could show on "
                      "its far side)" % (tag, WALL_THICKNESS, thin, total))
    if buried:
        errors.append("%s: the wall stands in front of %d of the rune's %d points (the face is further out)" % (
            tag, buried, total))
    rune = rune_box(shrine, yaw)
    for t in openings:
        b = box(t)
        if (b and boxes_overlap(rune, b, 0.3)) or (not b and point_in_box(rune, t["pos"], 1.0)):
            errors.append("%s: the rune would be drawn across %s" % (tag, describe(t)))
    # Doors and windows are items set into the wall: none may be along the rune.
    span = frame_box(shrine, yaw, (WALL_RUNE[0] - 0.1, 0.0, -1.0), (WALL_RUNE[1] + 0.1, WALL_RUNE[3], 1.0))
    for o in level.solid_boxes.reaching(span, 0.5):
        if o.get("kind") != "Characters" and RE_OPENING.search(o["name"]):
            b = box(o)
            if (b and boxes_overlap(span, b)) or (not b and point_in_box(span, o["pos"], 0.5)):
                errors.append("%s: the rune would be next to %s, a way through the wall" % (tag, describe(o)))

    # Nothing stands in front of the rune. Close to the wall the rune would be drawn on it; further out,
    # something tall would hide it, while a stool or a low table only hides its foot.
    lo = (WALL_RUNE[0] - 0.1, WALL_RUNE[2] - SHRINE_ABOVE_FLOOR, -VIEW_DEPTH)
    hi = (WALL_RUNE[1] + 0.1, WALL_RUNE[3] - SHRINE_ABOVE_FLOOR, -0.02)
    ahead = frame_box(shrine, yaw, lo, hi)
    projection = frame_box(shrine, yaw, (lo[0], lo[1], -PROJECTION_DEPTH), hi)
    out = mul(behind, -1.0)
    for o, kind in obstacles(level, ahead, base):
        if o.get("kind") == "Characters":
            continue   # they walk about; the arrival point is kept clear of them
        b = box(o)
        close = b is None or boxes_overlap(projection, b)
        tall = b is None or box_span(b, (0.0, 1.0, 0.0))[1] > base + VIEW_HEIGHT
        if kind == "solid" and (close or tall):
            name = "stands in front of" if not RE_OPENING.search(o["name"]) else "is a way through the wall at"
            errors.append("%s: %s %s the rune" % (tag, describe(o), name))
        elif kind == "solid":
            warnings.append("%s: %s stands in front of the rune, below its middle" % (tag, describe(o)))
        elif kind == "large":
            warnings.append("%s: the rune is inside the box of %s, a large piece that its box fits loosely" % (
                tag, describe(o)))
    for kind, t, _dy in tile_hits(level, ahead, base):
        # The wall's own tiles reach the face, give or take their relief; a tile that juts out further
        # (a corner, a pillar, a balustrade) stands in front of the rune.
        if box_span(box(t), out)[1] - dot(plane, out) > 0.1:
            errors.append("%s: %s stands in front of the rune" % (tag, describe(t)))
    for o in level.inside(level.points, shrine, yaw, (lo[0], hi[0], -1.0, 0.0), 0.0):
        warnings.append("%s: a point scripts send characters to is in front of the rune (%s)" % (tag, describe(o)))
    for o in candidates(getattr(level, "decals", ()), plane[0], plane[2], 4.0):
        if point_in_box(rune, o["pos"], 0.5):
            warnings.append("%s: the rune would cover the game's decal %s" % (tag, describe(o)))

    # The floor stays below the rune's box, or the rune would smear across it.
    bottom, _top = box_span(rune, (0.0, 1.0, 0.0))
    for u in (-1.3, -0.43, 0.43, 1.3):
        x, z = plane[0] + across[0] * u - behind[0] * 0.1, plane[2] + across[2] * u - behind[2] * 0.1
        for h, _flags in level.grid.surfaces(x, z):
            if bottom - 0.01 < h < bottom + 0.5:
                errors.append("%s: the floor rises into the rune's box (%.2f m above the shrine's floor)" % (tag, h - base))
                break
        else:
            continue
        break

    check_way(level, wp, floor, 0.6, errors, warnings)
    return errors, warnings


def story_zones(level: Level, story: dict, point):
    """The story's travel zones whose volume contains the point: [(trigger, [zone entries])]. A danger
    zone stops everyone inside it from travelling out while it is active; a blocked waypoint zone
    stops waypoints working at all."""
    zones = (story or {}).get("zones", {})
    return [(o, zones[o["key"]]) for o in level.volumes if o["key"] in zones and inside_volume(o, point)]


def load_story(cache: str = CACHE) -> dict:
    path = os.path.join(cache, "story.json")
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def cache_version(cache: str = CACHE):
    path = os.path.join(cache, "manifest.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        return json.load(fh).get("version", 1)
