"""
survey.py - look at a level the way the waypoint checks see it, and find room for a waypoint.

    python tools/survey.py find <level> <regex>               # placed objects by name (NPCs, doors, shrines)
    python tools/survey.py map <level> <x> <y> <z> [--size 30] [--scale 0.5] [--try <shrine x> <z> <arrival x> <z>]
    python tools/survey.py spots <level> <x> <y> <z> [--radius 12] [--count 8]           # boulders
    python tools/survey.py walls <level> <x> <y> <z> [--radius 12] [--count 8]           # runes on walls
    python tools/survey.py check <level> <shrine x> <z> <arrival x> <z> [--y 30]   # one placement, heights from the floor
    python tools/survey.py report <waypoint id> [--radius 6]                       # everything around a waypoint

Needs the cache from extract_game_data.py (with that level in it).

`report` lists what a waypoint of waypoints.json has around it: the results of every check,
the trigger volumes it stands in (the story's danger zones and blocked waypoint zones among
them), the game's characters, items, props and script points nearby with the sub-level each
comes from, the walls nearby, and what the story does with the game's waypoint it is locked with.

`map` draws the floor at the height of the given point, seen from above (+z up, +x right):
  .  free floor within 0.6 m of that height      ,  floor covered by something (walls, furniture)
  +  free floor 0.6 to 2 m higher or lower        #  nothing to stand on near that height
  C  character   i  item   s  prop   D  door   W  waypoint shrine   @  the point
  R  this mod's boulders (waypoints.json, and --try)   A  their arrival points
Objects are drawn when they are within 1.5 m of that height; characters, doors and
shrines are listed under the map.

`spots` tries arrival points on free floor around the point and, for each, a waypoint
(shrine, boulder and rune) 1.75 m away in 16 directions. Every result passes the same
checks as build_waypoints.py. It prefers a boulder with a wall or cliff behind it, room
around the arrival point, and a spot close to the point given. Each result is printed
as a waypoints.json entry with fresh GUIDs, ready to paste.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from navgrid import CELL, cell_centre  # noqa: E402
from waypoints import (DATA_FILE, GROUP_OF_LEVEL, RE_OPENING, RE_TILE_OVER, ROCK_FOOTPRINT,  # noqa: E402
                       SHRINE_ABOVE_FLOOR, SHRINE_TEMPLATE, WALL_ARRIVAL, Level, add, area, box,
                       box_span, check_placement, describe, facing_yaw, load, load_story, mul, rock_base, shrine_yaw,
                       story_zones, tile_is_broken, tile_is_opening, wall_axes)


def need(level: str) -> Level:
    if not Level.available(level):
        sys.exit(f"{level} is not in the cache. Run: python tools/extract_game_data.py --levels {level}")
    return Level(level)


def cmd_find(args):
    lv = need(args.level)
    rx = re.compile(args.regex, re.I)
    hits = [o for o in lv.objects if rx.search(o["name"])]
    for o in hits[:args.count]:
        print("%-11s %-50s %9.2f %8.2f %9.2f" % (o["kind"], o["name"][:50], *o["pos"]))
    print(f"{len(hits)} matches")


def cmd_map(args):
    lv = need(args.level)
    x0, y0, z0 = args.x, args.y, args.z
    surfaces = [h for h, flags in lv.grid.surfaces(x0, z0) if not flags & 0x1]
    h0 = min(surfaces, key=lambda h: abs(h - y0)) if surfaces else y0
    size, scale = args.size, args.scale

    def char(x, z):
        best = None
        for h, flags in lv.grid.surfaces(x, z):
            d = abs(h - h0)
            if d <= 2.0 and (best is None or d < best[0]):
                best = (d, flags)
        if not best:
            return "#"
        free = not best[1] & 0x7
        if best[0] <= 0.6:
            return "." if free else ","
        return "+" if free else "#"

    rows = [[char(x0 + (c - size) * scale, z0 + (size - r) * scale) for c in range(2 * size + 1)] for r in range(2 * size + 1)]
    listed = []
    for o in lv.objects:
        if o["kind"] not in ("Characters", "Items", "Scenery") or abs(o["pos"][1] - h0) > 1.5:
            continue
        c = round((o["pos"][0] - x0) / scale) + size
        r = size - round((o["pos"][2] - z0) / scale)
        if not (0 <= c <= 2 * size and 0 <= r <= 2 * size):
            continue
        if o["kind"] == "Characters":
            ch = "C"
        elif o["tpl"] == SHRINE_TEMPLATE:
            ch = "W"
        elif re.search(r"door|gate", o["name"], re.I):
            ch = "D"
        else:
            ch = "s" if o["kind"] == "Scenery" else "i"
        if rows[r][c] not in "CDW":
            rows[r][c] = ch
        if ch in "CDW":
            listed.append((r, c, ch, o))
    rows[size][size] = "@"

    def mark(x, z, ch):
        c = round((x - x0) / scale) + size
        r = size - round((z - z0) / scale)
        if 0 <= c <= 2 * size and 0 <= r <= 2 * size:
            rows[r][c] = ch

    # The waypoints of waypoints.json in this level, and a proposed one (--try): boulder R, or the rune
    # along its wall |, shrine W, arrival A. Walls of the level's tiles near that height: =
    for t in lv.tiles.around(x0, z0, size * scale * 1.5):
        if t.get("walk") or t.get("thru") or not t.get("ext") or abs(t["pos"][1] - h0) > 1.5:
            continue
        c, axes, half = box(t)
        for k in range(-4, 5):
            for i in range(3):
                if abs(axes[i][1]) < 0.5 and half[i] > 0.4:
                    p = add(c, mul(axes[i], half[i] * k / 4))
                    col = round((p[0] - x0) / scale) + size
                    row = size - round((p[2] - z0) / scale)
                    if 0 <= col <= 2 * size and 0 <= row <= 2 * size and rows[row][col] in ".,+#":
                        rows[row][col] = "="
    shown = [wp for wp in load(DATA_FILE)["waypoints"] if wp["level"] == args.level]
    if args.try_:
        sx, sz, tx, tz = args.try_
        shown.append({"shrine": {"position": [sx, h0, sz]}, "trigger": {"position": [tx, h0, tz]}})
    for wp in shown:
        yaw = shrine_yaw(wp)
        if wp.get("style") == "wall":
            across, _behind = wall_axes(yaw)
            s = wp["shrine"]["position"]
            for k in range(-6, 7):
                mark(s[0] + across[0] * k / 4, s[2] + across[2] * k / 4, "|")
        else:
            for x, z in area(wp["shrine"]["position"], yaw, ROCK_FOOTPRINT, min(scale, 0.25)):
                mark(x, z, "R")
        mark(wp["shrine"]["position"][0], wp["shrine"]["position"][2], "W")
        mark(wp["trigger"]["position"][0], wp["trigger"]["position"][2], "A")
    print("%s around (%.2f, %.2f, %.2f), floor height %.2f, %.2f m per character" % (args.level, x0, y0, z0, h0, scale))
    for row in rows:
        print("  " + "".join(row))
    for r, c, ch, o in sorted(listed, key=lambda t: (t[0], t[1])):
        print("  %s  %-48s %9.2f %8.2f %9.2f" % (ch, o["name"][:48], *o["pos"]))


ARRIVAL_DISTANCE = 1.75   # the Blighted Village waypoint's arrival point is 1.56 m in front of its shrine


def shrine_height(lv: Level, sx, sz, yaw, floor):
    """Height for the shrine so that the boulder meets the floor in front, or None if there is no floor there."""
    base = rock_base(lv, (sx, floor, sz), yaw, floor)
    return None if base is None else round(base + SHRINE_ABOVE_FLOOR, 3)


def back_to_wall(lv: Level, shrine, yaw, floor) -> int:
    """How many points just behind the boulder have no floor at its height (a wall, a cliff or a drop)."""
    hits = 0
    for x, z in area(shrine, yaw, (-1.0, 1.0, 2.75, 3.75), 0.5):
        if lv.floor(x, z, floor, 0.6) is None:
            hits += 1
    return hits


def candidate(lv: Level, sx, sz, tx, tz, floor):
    yaw = facing_yaw((sx, 0, sz), (tx, 0, tz))
    height = shrine_height(lv, sx, sz, yaw, floor)
    if height is None:
        return None, yaw
    return {"id": "candidate", "shrine": {"position": [round(sx, 3), height, round(sz, 3)]},
            "trigger": {"position": [round(tx, 3), round(floor, 3), round(tz, 3)]}}, yaw


def cmd_spots(args):
    lv = need(args.level)
    x0, y0, z0 = args.x, args.y, args.z
    n = int(args.radius / CELL)
    found = []
    for iz in range(-n, n + 1):
        for ix in range(-n, n + 1):
            tx, tz = cell_centre(x0 + ix * CELL), cell_centre(z0 + iz * CELL)
            dist = math.hypot(tx - x0, tz - z0)
            if dist > args.radius:
                continue
            floor = lv.floor(tx, tz, y0, 2.0)
            if floor is None:
                continue
            room = sum(1 for dz in range(-5, 6) for dx in range(-5, 6)
                       if lv.floor(tx + dx * CELL, tz + dz * CELL, floor, 0.4) is not None)
            if room < 60:
                continue
            best = None
            for k in range(16):
                a = 2 * math.pi * k / 16
                wp, yaw = candidate(lv, tx + ARRIVAL_DISTANCE * math.cos(a), tz + ARRIVAL_DISTANCE * math.sin(a), tx, tz, floor)
                if wp is None:
                    continue
                errors, warnings = check_placement(lv, wp, quick=True)
                if errors:
                    continue
                errors, warnings = check_placement(lv, wp)
                score = 3 * back_to_wall(lv, wp["shrine"]["position"], yaw, floor) + room / 10 - dist - 5 * len(warnings)
                if best is None or score > best[0]:
                    best = (score, wp, warnings)
            if best:
                found.append((best[0], dist, best[1], best[2]))
    found.sort(key=lambda f: -f[0])
    picked = []
    for f in found:
        t = f[2]["trigger"]["position"]
        if all(math.hypot(t[0] - p[2]["trigger"]["position"][0], t[2] - p[2]["trigger"]["position"][2]) >= 1.5 for p in picked):
            picked.append(f)
        if len(picked) >= args.count:
            break
    print("%d places pass every check within %.0f m of (%.2f, %.2f, %.2f) in %s; best %d:" % (
        len(found), args.radius, x0, y0, z0, args.level, len(picked)))
    for score, dist, wp, warnings in picked:
        print()
        print("  score %.1f, %.1f m from the point%s" % (score, dist, ("; " + "; ".join(warnings)) if warnings else ""))
        entry = {
            "shrine": {"guid": str(uuid.uuid4()), "position": wp["shrine"]["position"]},
            "trigger": {"guid": str(uuid.uuid4()), "position": wp["trigger"]["position"]},
            "decal": {"guid": str(uuid.uuid4()), "style": "dark"},
            "rock": {"guid": str(uuid.uuid4()), "style": "grey"},
        }
        print("  " + json.dumps(entry))
    if picked:
        h = uuid.uuid4().hex
        print()
        print("  a fresh name handle: h%sg%sg%sg%sg%s; group for %s: %s" % (
            h[:8], h[8:12], h[12:16], h[16:20], h[20:], args.level, GROUP_OF_LEVEL.get(args.level, "?")))


def wall_faces(lv: Level, x0, y0, z0, radius):
    """The faces of the level's walls near a point and near its height, as (point on the face, the way the
    face looks (horizontal), the way along the wall, half its length, its bottom, its top, the tile)."""
    faces = []
    for t in lv.tiles.around(x0, z0, radius + 4.0):
        name = t.get("c", "")
        if (t.get("walk") or t.get("thru") or t.get("nodecal") or not t.get("ext")
                or RE_TILE_OVER.search(name) or RE_TILE_OVER.search(t.get("v", ""))
                or tile_is_opening(t) or tile_is_broken(t)):
            continue
        b = box(t)
        centre, axes, half = b
        up = max(range(3), key=lambda i: abs(axes[i][1]))
        if abs(axes[up][1]) < 0.95:
            continue   # a sloping piece
        flat = [i for i in range(3) if i != up]
        depth, length = min(flat, key=lambda i: half[i]), max(flat, key=lambda i: half[i])
        if half[length] < 0.5:
            continue   # a post, not a wall
        low, high = box_span(b, (0.0, 1.0, 0.0))
        if not low - 1.0 <= y0 <= high or math.hypot(centre[0] - x0, centre[2] - z0) > radius:
            continue
        for sign in (1.0, -1.0):
            n = mul(axes[depth], sign)
            n = (n[0] / math.hypot(n[0], n[2]), 0.0, n[2] / math.hypot(n[0], n[2]))
            along = axes[length]
            faces.append((add(centre, mul(n, half[depth])), n, (along[0], 0.0, along[2]), half[length], low, high, t))
    return faces


ARRIVALS = [(WALL_ARRIVAL, 0.0), (2.5, 0.0), (1.6, 0.0), (2.0, 0.5), (2.0, -0.5), (3.0, 0.0), (2.5, 0.75), (2.5, -0.75)]


def wall_candidate(lv: Level, point, n, y0, arrival=(WALL_ARRIVAL, 0.0)):
    """A waypoint with its rune on the wall at `point` (on the face), looking out along `n`, its arrival
    point `arrival` = (metres out, metres along the wall) away; None when there is no floor there."""
    floor = lv.floor(point[0] + n[0] * 0.6, point[2] + n[2] * 0.6, y0, 1.5)
    if floor is None:
        return None
    shrine = (point[0], floor + SHRINE_ABOVE_FLOOR, point[2])   # on the face
    out, side = arrival
    arrival = (shrine[0] + n[0] * out - n[2] * side, shrine[2] + n[2] * out + n[0] * side)
    arrival_floor = lv.floor(arrival[0], arrival[1], floor, 0.4)
    if arrival_floor is None:
        return None
    yaw = facing_yaw(shrine, (shrine[0] + n[0], 0.0, shrine[2] + n[2]))
    return {"id": "candidate", "style": "wall",
            "shrine": {"position": [round(v, 3) for v in shrine], "yaw": yaw},
            "trigger": {"position": [round(arrival[0], 3), round(arrival_floor, 3), round(arrival[1], 3)]}}


def best_wall_candidate(lv: Level, point, n, y0, explain=False):
    """The candidate on the wall at `point` with the first arrival point that passes, or the one with the
    fewest errors: (waypoint, errors, warnings), or None when there is no floor in front."""
    best = None
    for arrival in ARRIVALS:
        wp = wall_candidate(lv, point, n, y0, arrival)
        if wp is None:
            continue
        errors, warnings = check_placement(lv, wp, quick=not explain)
        if not errors and not explain:
            errors, warnings = check_placement(lv, wp)
        if best is None or len(errors) < len(best[1]):
            best = (wp, errors, warnings)
        if not errors or not any("arrival point" in e for e in errors):
            break   # nothing to gain from moving the arrival point
    return best


def cmd_walls(args):
    lv = need(args.level)
    x0, y0, z0 = args.x, args.y, args.z
    found, near_misses = [], []
    for point, n, along, half, low, high, tile in wall_faces(lv, x0, y0, z0, args.radius):
        k = -half + 0.5
        while k <= half - 0.5 + 1e-6:
            p = add(point, mul(along, k))
            k += 0.5
            hit = best_wall_candidate(lv, p, n, y0, explain=args.all)
            if hit is None:
                continue
            wp, errors, warnings = hit
            if low > wp["shrine"]["position"][1] + 0.2:
                continue
            if errors:
                if args.all:
                    s = wp["shrine"]["position"]
                    near_misses.append((len(errors), round(s[0], 2), round(s[2], 2), wp["shrine"]["yaw"],
                                        "; ".join(e.split(": ", 1)[1] for e in errors)))
                continue
            t = wp["trigger"]["position"]
            dist = math.hypot(t[0] - x0, t[2] - z0)
            room = sum(1 for dz in range(-5, 6) for dx in range(-5, 6)
                       if lv.floor(t[0] + dx * CELL, t[2] + dz * CELL, t[1], 0.4) is not None)
            score = room / 10 - dist - 3 * len(warnings)
            found.append((score, dist, wp, warnings, tile))
    if args.all:
        print("Places that do not pass, with what stops them:")
        for count, x, z, yaw, why in sorted(set(near_misses)):
            print("  %2d  %8.2f %8.2f  yaw %6.1f  %s" % (count, x, z, yaw, why[:400]))
        print()
    found.sort(key=lambda f: -f[0])
    picked = []
    for f in found:
        s = f[2]["shrine"]["position"]
        if all(math.hypot(s[0] - p[2]["shrine"]["position"][0], s[2] - p[2]["shrine"]["position"][2]) >= 1.5 for p in picked):
            picked.append(f)
        if len(picked) >= args.count:
            break
    print("%d places on walls pass every check within %.0f m of (%.2f, %.2f, %.2f) in %s; best %d:" % (
        len(found), args.radius, x0, y0, z0, args.level, len(picked)))
    for score, dist, wp, warnings, tile in picked:
        print()
        print("  score %.1f, %.1f m from the point, on %s%s" % (score, dist, describe(tile),
                                                             ("; " + "; ".join(w.split(": ", 1)[1] for w in warnings)) if warnings else ""))
        entry = {
            "style": "wall",
            "shrine": {"guid": str(uuid.uuid4()), "position": wp["shrine"]["position"], "yaw": wp["shrine"]["yaw"]},
            "trigger": {"guid": str(uuid.uuid4()), "position": wp["trigger"]["position"]},
            "decal": {"guid": str(uuid.uuid4()), "style": "dark"},
        }
        print("  " + json.dumps(entry))


def cmd_check(args):
    lv = need(args.level)
    floor = lv.floor(args.tx, args.tz, args.y, 3.0)
    if floor is None:
        sys.exit("No free floor at the arrival point near height %.2f" % args.y)
    wp, yaw = candidate(lv, args.sx, args.sz, args.tx, args.tz, floor)
    if wp is None:
        print("ERROR  the boulder has no flat free floor to rest on there")
        return 1
    errors, warnings = check_placement(lv, wp)
    for e in errors:
        print("ERROR  " + e)
    for w in warnings:
        print("WARN   " + w)
    print("shrine yaw %.2f, boulder backed by a wall: %d of 15" % (yaw, back_to_wall(lv, wp["shrine"]["position"], yaw, floor)))
    print(json.dumps({"shrine": {"position": wp["shrine"]["position"]}, "trigger": {"position": wp["trigger"]["position"]}}))
    return 1 if errors else 0


def cmd_report(args):
    waypoints = {wp["id"]: wp for wp in load(DATA_FILE)["waypoints"]}
    if args.id not in waypoints:
        sys.exit("No waypoint %s in waypoints.json (known: %s)" % (args.id, ", ".join(waypoints)))
    wp = waypoints[args.id]
    lv = need(wp["level"])
    story = load_story()
    shrine, trigger = wp["shrine"]["position"], wp["trigger"]["position"]
    yaw = shrine_yaw(wp)
    print("%s, %s (%s, %s)" % (wp["id"], wp["name"], wp["level"], wp["group"]))
    print("  %s" % wp.get("where", ""))
    print("  shrine %s, yaw %.1f; arrival point %s" % (shrine, yaw, trigger))

    errors, warnings = check_placement(lv, wp)
    print("\nChecks")
    for e in errors:
        print("  ERROR  " + e.split(": ", 1)[1])
    for w in warnings:
        print("  WARN   " + w.split(": ", 1)[1])
    if not errors and not warnings:
        print("  all pass")

    print("\nTrigger volumes the arrival point stands in")
    zones = {o["key"]: entries for o, entries in story_zones(lv, story, trigger)}
    for o in sorted(lv.zones(trigger), key=lambda o: o["name"]):
        shape = "box" if "box" in o["shape"] else "prism" if "poly" in o["shape"] else "sphere"
        note = ("  <- " + zone_note(zones[o["key"]])) if o["key"] in zones else ""
        print("  %-55s %-6s%s" % (describe(o)[:55], shape, note))

    radius = args.radius
    print("\nWithin %.0f m of the shrine (distance, height above it, where it comes from)" % radius)
    near = [o for o in lv.objects if o["kind"] in ("Characters", "Items", "Scenery", "Triggers", "Decals")
            and math.hypot(o["pos"][0] - shrine[0], o["pos"][2] - shrine[2]) <= radius
            and abs(o["pos"][1] - shrine[1]) <= 6]
    for kind in ("Characters", "Items", "Scenery", "Decals", "Triggers"):
        rows = sorted((o for o in near if o["kind"] == kind), key=lambda o: math.dist(o["pos"], shrine))
        if not rows:
            continue
        print("  %s (%d)" % (kind, len(rows)))
        for o in rows[:args.count]:
            print("    %5.1f m %+5.1f  %-58s %s" % (math.dist(o["pos"], shrine), o["pos"][1] - shrine[1], o["name"][:58],
                                                 (o.get("via", "").split("/")[-1] or "main level") + (", later" if o.get("later") else "")))
        if len(rows) > args.count:
            print("    ... %d more" % (len(rows) - args.count))

    walls = [t for t in lv.tiles.around(shrine[0], shrine[2], radius)
             if math.hypot(t["pos"][0] - shrine[0], t["pos"][2] - shrine[2]) <= radius and abs(t["pos"][1] - shrine[1]) <= 6]
    print("\nTiles within %.0f m: %d (walls %d, floors %d; %d of them with a known extent)" % (
        radius, len(walls), sum(1 for t in walls if not t.get("walk") and not t.get("thru")),
        sum(1 for t in walls if t.get("walk")), sum(1 for t in walls if t.get("ext"))))

    if story:
        print("\nWhat the story does with waypoints here")
        for label, calls in (("group " + wp["group"], story.get("groups", {}).get(wp["group"], [])),
                             ("all waypoints", story.get("all", [])),
                             (wp.get("lockWith") or "", story.get("waypoints", {}).get(wp.get("lockWith") or "", []))):
            if not label:
                continue
            for c in calls:
                print("  %-22s %-30s %s:%d%s" % (label, c["call"], c["goal"], c["line"],
                                                  "  (a rule that runs when it is called)" if c["listener"] else ""))
    return 1 if errors else 0


def zone_note(entries) -> str:
    out = []
    for e in entries:
        what = {"danger": "danger zone " + e["id"], "blocked": "blocked waypoint zone", "safe": "safe bubble"}[e["type"]]
        out.append("%s %s (%s)" % ("removed:" if e["removed"] else "story:", what, e["goal"]))
    return "; ".join(out)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find")
    p.add_argument("level")
    p.add_argument("regex")
    p.add_argument("--count", type=int, default=60)
    for name in ("map", "spots", "walls"):
        p = sub.add_parser(name)
        p.add_argument("level")
        p.add_argument("x", type=float)
        p.add_argument("y", type=float)
        p.add_argument("z", type=float)
        if name == "walls":
            p.add_argument("--all", action="store_true", help="also list the places that fail, with what stops them")
        if name == "map":
            p.add_argument("--size", type=int, default=30, help="characters from the centre to the edge")
            p.add_argument("--scale", type=float, default=0.5, help="metres per character")
            p.add_argument("--try", dest="try_", type=float, nargs=4, metavar=("SX", "SZ", "AX", "AZ"),
                           help="also draw a proposed waypoint: shrine x z, arrival x z")
        else:
            p.add_argument("--radius", type=float, default=12.0)
            p.add_argument("--count", type=int, default=8)
    p = sub.add_parser("check")
    p.add_argument("level")
    for name in ("sx", "sz", "tx", "tz"):
        p.add_argument(name, type=float)
    p.add_argument("--y", type=float, required=True, help="about the floor height at the arrival point")
    p = sub.add_parser("report")
    p.add_argument("id", help="a waypoint id of waypoints.json, for example NEW_WAYP_LOW_Guildhall")
    p.add_argument("--radius", type=float, default=6.0)
    p.add_argument("--count", type=int, default=15, help="at most this many objects of each kind")
    args = ap.parse_args()
    sys.exit({"find": cmd_find, "map": cmd_map, "spots": cmd_spots, "walls": cmd_walls, "check": cmd_check,
              "report": cmd_report}[args.cmd](args) or 0)


if __name__ == "__main__":
    main()
