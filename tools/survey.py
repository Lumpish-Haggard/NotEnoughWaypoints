"""
survey.py - look at a level the way the waypoint checks see it, and find room for a waypoint.

    python tools/survey.py find <level> <regex>               # placed objects by name (NPCs, doors, shrines)
    python tools/survey.py map <level> <x> <y> <z> [--size 30] [--scale 0.5] [--try <shrine x> <z> <arrival x> <z>]
    python tools/survey.py spots <level> <x> <y> <z> [--radius 12] [--count 8]
    python tools/survey.py check <level> <shrine x> <z> <arrival x> <z> [--y 30]   # one placement, heights from the floor

Needs the cache from extract_game_data.py (with that level in it).

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
from waypoints import (DATA_FILE, GROUP_OF_LEVEL, ROCK_FOOTPRINT, SHRINE_ABOVE_FLOOR, SHRINE_TEMPLATE, Level,  # noqa: E402
                       area, check_placement, facing_yaw, load, rock_base, shrine_yaw)


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

    # The waypoints of waypoints.json in this level, and a proposed one (--try): boulder R, shrine W, arrival A.
    shown = [wp for wp in load(DATA_FILE)["waypoints"] if wp["level"] == args.level]
    if args.try_:
        sx, sz, tx, tz = args.try_
        shown.append({"shrine": {"position": [sx, h0, sz]}, "trigger": {"position": [tx, h0, tz]}})
    for wp in shown:
        yaw = shrine_yaw(wp)
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
                errors, warnings = check_placement(lv, wp)
                if errors:
                    continue
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


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("find")
    p.add_argument("level")
    p.add_argument("regex")
    p.add_argument("--count", type=int, default=60)
    for name in ("map", "spots"):
        p = sub.add_parser(name)
        p.add_argument("level")
        p.add_argument("x", type=float)
        p.add_argument("y", type=float)
        p.add_argument("z", type=float)
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
    args = ap.parse_args()
    sys.exit({"find": cmd_find, "map": cmd_map, "spots": cmd_spots, "check": cmd_check}[args.cmd](args) or 0)


if __name__ == "__main__":
    main()
