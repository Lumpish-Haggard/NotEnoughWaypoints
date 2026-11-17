"""
Tests for the tools. They need no game files, so CI runs them:

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import copy
import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import build_waypoints  # noqa: E402
from navgrid import cell_centre, lz4_block  # noqa: E402
from waypoints import (DATA_FILE, ROCK_SCALE, ROCK_TEMPLATES, decal_transform, facing_yaw, front, load,  # noqa: E402
                       problems, quat_yaw, rock_transform, rotate, shrine_yaw)


def close(a, b, places=4):
    return all(abs(x - y) < 10 ** -places for x, y in zip(a, b))


def same_rotation(a, b, places=4):
    return close(a, b, places) or close(a, tuple(-v for v in b), places)


# The game's own Blighted Village waypoint (WLD_Main_A), which every waypoint of this mod copies.
FOR_SHRINE = ((33.663925, 31.565928, 392.15353), (0, 0.9998932, 0, -0.014615281))
FOR_ROCK = ((33.475048, 32.575485, 391.56042), (0.702719, -0.6543975, 0.20599847, 0.18845336))
FOR_DECAL = ((33.649197, 33.076702, 391.98032), (0.019167274, 0.70684683, 0.7068471, -0.019167226))


class Geometry(unittest.TestCase):
    def test_yaw_quaternion_is_what_the_game_stores(self):
        # S_UND_Fort_WaypointShrine is turned 90 degrees: (0, 0.70711, 0, 0.70711) in the game files.
        self.assertTrue(close(quat_yaw(90), (0, math.sqrt(0.5), 0, math.sqrt(0.5))))

    def test_blighted_village_is_reproduced(self):
        # From the game's shrine alone, the arrangement must give back the game's boulder and rune.
        position, rotation = FOR_SHRINE
        yaw = math.degrees(2 * math.atan2(rotation[1], rotation[3]))
        rock_pos, rock_rot = rock_transform(position, yaw)
        decal_pos, decal_rot = decal_transform(position, yaw)
        self.assertTrue(close(rock_pos, FOR_ROCK[0], 2), rock_pos)
        self.assertTrue(same_rotation(rock_rot, FOR_ROCK[1], 3), rock_rot)
        self.assertTrue(close(decal_pos, FOR_DECAL[0], 2), decal_pos)
        self.assertTrue(same_rotation(decal_rot, FOR_DECAL[1], 3), decal_rot)

    def test_arrangement_turns_with_the_shrine(self):
        # Turning the shrine turns the boulder around it: the boulder stays behind the shrine.
        for yaw in (0, 45, 90, 180, -135):
            rock_pos, _ = rock_transform((0, 0, 0), yaw)
            fx, fz = front(yaw)
            self.assertLess(fx * rock_pos[0] + fz * rock_pos[2], -0.5)  # behind = against the front direction

    def test_rune_face_looks_at_the_arrival_point(self):
        for trigger in ((2, 0, 0), (-2, 0, 0), (0, 0, 2), (0, 0, -2), (1.5, 0, 1.5)):
            yaw = facing_yaw((0, 0, 0), trigger)
            fx, fz = front(yaw)
            d = math.hypot(trigger[0], trigger[2])
            self.assertAlmostEqual(fx * trigger[0] / d + fz * trigger[2] / d, 1.0, places=3)
            # local -z is the rune face
            lx, _, lz = rotate(quat_yaw(yaw), (0, 0, -1))
            self.assertTrue(close((lx, lz), (fx, fz), 3))

    def test_cell_centre(self):
        self.assertEqual(cell_centre(0.1), 0.25)
        self.assertEqual(cell_centre(-0.1), -0.25)

    def test_lz4_block(self):
        # "abcabcabcabc": three literals, then a 9 byte match at offset 3
        self.assertEqual(lz4_block(bytes([0x35]) + b"abc" + bytes([3, 0])), b"abcabcabcabc")


class Data(unittest.TestCase):
    def setUp(self):
        self.data = load(DATA_FILE)

    def test_waypoints_json_is_valid(self):
        self.assertEqual(problems(self.data), [])

    def test_duplicates_and_groups_are_caught(self):
        bad = copy.deepcopy(self.data)
        bad["waypoints"].append(copy.deepcopy(bad["waypoints"][0]))
        bad["waypoints"][1]["group"] = "Act3"
        found = "\n".join(problems(bad))
        self.assertIn("id used twice", found)
        self.assertIn("guid used twice", found)
        self.assertIn("handle used twice", found)
        self.assertIn("belong to group", found)

    def test_names_must_be_plain_ascii(self):
        bad = copy.deepcopy(self.data)
        bad["waypoints"][0]["name"] = "The Hollow " + chr(0x2014) + " Grove"  # an em dash
        self.assertTrue(any("plain ASCII" in p for p in problems(bad)))

    def test_arrival_distance(self):
        bad = copy.deepcopy(self.data)
        bad["waypoints"][0]["trigger"]["position"] = list(bad["waypoints"][0]["shrine"]["position"])
        self.assertTrue(any("arrival point is 0.0 m" in p for p in problems(bad)))


class Generated(unittest.TestCase):
    def setUp(self):
        self.waypoints = load(DATA_FILE)["waypoints"]

    def test_generated_files_are_committed_and_current(self):
        for path, text in build_waypoints.all_files(self.waypoints).items():
            with open(path, encoding="utf-8", newline="") as fh:
                self.assertEqual(fh.read().replace("\r\n", "\n"), text, path)

    def test_goal_declares_every_waypoint(self):
        goal = build_waypoints.goal(self.waypoints)
        for wp in self.waypoints:
            self.assertIn('DB_WaypointInfo("%s","%s",(ITEM)S_%s_Shrine_%s,(TRIGGER)S_%s_Trigger_%s);' % (
                wp["group"], wp["id"], wp["id"], wp["shrine"]["guid"], wp["id"], wp["trigger"]["guid"]), goal)
        self.assertNotIn("ParentTargetEdge", goal)  # top-level: starts with the story, also in existing saves
        self.assertEqual(goal.count("DB_UND_BroodingSpovereign_UnderdarkWaypoints"),
                         sum(1 for wp in self.waypoints if wp.get("underdark")))
        for wp in self.waypoints:
            if wp.get("lockWith"):
                self.assertIn('PROC_LockWaypointForAll("%s")\nTHEN\nPROC_LockWaypointForAll("%s");' % (wp["lockWith"], wp["id"]), goal)

    def test_shrines_face_their_arrival_points(self):
        for wp in self.waypoints:
            yaw = shrine_yaw(wp)
            fx, fz = front(yaw)
            s, t = wp["shrine"]["position"], wp["trigger"]["position"]
            d = math.hypot(t[0] - s[0], t[2] - s[2])
            self.assertGreater((fx * (t[0] - s[0]) + fz * (t[2] - s[2])) / d, 0.99, wp["id"])

    def test_every_waypoint_has_its_boulder_and_rune(self):
        files = build_waypoints.all_files(self.waypoints)
        for wp in self.waypoints:
            rock = [t for p, t in files.items() if wp["rock"]["guid"] in p and os.sep + "Scenery" + os.sep in p]
            decal = [t for p, t in files.items() if wp["decal"]["guid"] in p and os.sep + "Decals" + os.sep in p]
            self.assertEqual(len(rock), 1, wp["id"])
            self.assertIn('value="%s"' % ROCK_TEMPLATES[wp["rock"]["style"]], rock[0])
            self.assertIn('id="Scale" type="float" value="%s"' % ROCK_SCALE, rock[0])
            self.assertIn('id="Type" type="FixedString" value="scenery"', rock[0])
            self.assertIn('id="Dimensions" type="fvec3" value="3 0.6 3"', decal[0])

    def test_names_file(self):
        xml = build_waypoints.english(self.waypoints)
        for wp in self.waypoints:
            self.assertIn('contentuid="%s" version="1">%s<' % (wp["handle"], wp["name"]), xml)

    def test_version_decoding(self):
        self.assertEqual(build_waypoints.version_of(36028797018963968), "1.0.0.0")
        self.assertEqual(build_waypoints.version_of(36169534507319296), "1.1.0.0")


if __name__ == "__main__":
    unittest.main()
