"""
Tests for reading the game's level and story files (tools/gamefiles.py) and for the checks that
use what they give (trigger volumes, wall tiles). Small hand-written samples in the layout LSLib
writes stand in for the game files, so CI needs none:

    python -m unittest discover -s tests -v
"""
from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

import gamefiles  # noqa: E402
from waypoints import (ROCK_BODY, SHRINE_ABOVE_FLOOR, WALL_ARRIVAL, WALL_DECAL_OFFSET, BoxIndex, Indexed, Level, box,  # noqa: E402
                       box_span, boxes_overlap, check_placement, frame_box, inside_volume, obstacles, point_in_box,
                       point_in_polygon, quat_yaw, rune_box, tile_hits)


def close(a, b, places=4):
    return all(abs(x - y) < 10 ** -places for x, y in zip(a, b))


def lsx(objects: str) -> str:
    """A level file around the given <node id="GameObjects"> nodes."""
    return ('<?xml version="1.0" encoding="utf-8"?>\n<save>\n'
            '<version major="4" minor="0" revision="9" build="0" lslib_meta="v1,bswap_guids,lsf_adjacency" />\n'
            '<region id="Templates"><node id="Templates"><children>\n' + objects +
            '</children></node></region>\n</save>\n')


def transform(position, rotation="0 0 0 1", scale="1"):
    return ('<node id="Transform"><attribute id="Position" type="fvec3" value="%s" />'
            '<attribute id="RotationQuat" type="fvec4" value="%s" />'
            '<attribute id="Scale" type="float" value="%s" /></node>' % (position, rotation, scale))


BOX_TRIGGER = ('<node id="GameObjects"><attribute id="Extents" type="fvec3" value="10 4 6" />'
               '<attribute id="MapKey" type="FixedString" value="11111111-1111-1111-1111-111111111111" />'
               '<attribute id="Name" type="LSString" value="S_TEST_DangerZoneTrigger" />'
               '<attribute id="TemplateName" type="FixedString" value="987b8a4d-2208-4bae-a92d-706db0e593e8" />'
               '<attribute id="Type" type="FixedString" value="trigger" />'
               '<children><node id="FadeChildren" />' + transform("100 20 50", "0 0.70710677 0 0.70710677") +
               '</children></node>\n')
PRISM_TRIGGER = ('<node id="GameObjects"><attribute id="Height" type="float" value="5" />'
                 '<attribute id="MapKey" type="FixedString" value="22222222-2222-2222-2222-222222222222" />'
                 '<attribute id="Name" type="LSString" value="S_TEST_Region" />'
                 '<attribute id="TemplateName" type="FixedString" value="3787cd7f-f111-4935-a250-c0fd5b72fc44" />'
                 '<children>'
                 '<node id="Points"><attribute id="Object" type="fvec2" value="-2 -2" /></node>'
                 '<node id="Points"><attribute id="Object" type="fvec2" value="2 -2" /></node>'
                 '<node id="Points"><attribute id="Object" type="fvec2" value="2 2" /></node>'
                 '<node id="Points"><attribute id="Object" type="fvec2" value="-2 2" /></node>'
                 + transform("0 10 0") + '</children></node>\n')
SPHERE_TRIGGER = ('<node id="GameObjects"><attribute id="MapKey" type="FixedString" value="33333333-3333-3333-3333-333333333333" />'
                  '<attribute id="Name" type="LSString" value="S_TEST_Sphere" /><attribute id="Radius" type="float" value="2.5" />'
                  '<attribute id="TemplateName" type="FixedString" value="5e41a73b-05ce-4011-b188-d313c15760ee" />'
                  '<children>' + transform("0 0 0") + '</children></node>\n')
DECAL = ('<node id="GameObjects"><attribute id="Dimensions" type="fvec3" value="3 0.6 3" />'
         '<attribute id="MapKey" type="FixedString" value="44444444-4444-4444-4444-444444444444" />'
         '<attribute id="Name" type="LSString" value="S_TEST_DCL" />'
         '<attribute id="TemplateName" type="FixedString" value="4aa6eeee-3d1b-45fc-8397-ad149db8c581" />'
         '<children>' + transform("1 2 3", scale="0.9") + '</children></node>\n')
LEVEL_TEMPLATE = ('<node id="GameObjects"><attribute id="LevelTemplateType" type="uint8" value="1" />'
                  '<attribute id="MapKey" type="FixedString" value="ba88dcc4-7bf5-450c-b8c5-52468677bef4" />'
                  '<attribute id="Name" type="LSString" value="LT_BGO_UC_GuildHall_A" />'
                  '<attribute id="StartingLoaded" type="bool" value="True" />'
                  '<attribute id="SubLevelName" type="FixedString" value="BGO_UC_GuildHall_A" />'
                  '<attribute id="Type" type="FixedString" value="LevelTemplate" /></node>\n'
                  '<node id="GameObjects"><attribute id="MapKey" type="FixedString" value="927e9e0c-9f37-4c0f-ac02-0e04d42fe5dc" />'
                  '<attribute id="Name" type="LSString" value="LT_BlockerDruidGrove_A" />'
                  '<attribute id="StartingLoaded" type="bool" value="False" />'
                  '<attribute id="SubLevelName" type="FixedString" value="WLD_BlockerDruidGrove_A" />'
                  '<attribute id="Type" type="FixedString" value="LevelTemplate" /></node>\n'
                  '<node id="GameObjects"><attribute id="MapKey" type="FixedString" value="99179bdb-43f3-4fa4-a40e-46c2101d3426" />'
                  '<attribute id="Name" type="LSString" value="NAT_Rock_Boulder_B_Grey" />'
                  '<attribute id="Type" type="FixedString" value="scenery" /></node>\n')
TILES = ('<node id="GameObjects"><attribute id="MapKey" type="FixedString" value="add77154-d88d-4a01-96ec-b4471a90d390" />'
         '<attribute id="Name" type="LSString" value="WALL_City_Wooden_House_A_0n5D_4H_B_015" />'
         '<attribute id="Type" type="FixedString" value="TileConstruction" />'
         '<children><node id="tiles"><children>'
         '<node id="tile"><attribute id="Rotate" type="mat3x3" value=" 0.00  0.00  1.00 &#xD;&#xA; 0.00  1.00  0.00 &#xD;&#xA;-1.00  0.00  0.00 &#xD;&#xA;" />'
         '<attribute id="Scale" type="float" value="1" /><attribute id="ScaleZ" type="float" value="0.884" /><attribute id="Stretchable" type="bool" value="True" />'
         '<attribute id="Translate" type="fvec3" value="-19.9 30.58 -120.49" />'
         '<attribute id="WalkOn" type="bool" value="False" /><attribute id="WalkThrough" type="bool" value="False" />'
         '<attribute id="tile" type="guid" value="0db69b54-7cfb-436b-bdd0-934cfc40c41d" /></node>'
         '<node id="tile"><attribute id="QRotate" type="fvec4" value="0 0.9238795 0 -0.3826834" />'
         '<attribute id="Scale" type="float" value="1" /><attribute id="Translate" type="fvec3" value="-17.9 30.58 -120.49" />'
         '<attribute id="WalkOn" type="bool" value="True" /><attribute id="WalkThrough" type="bool" value="False" /></node>'
         '</children></node>' + transform("-17.85 30.58 -120.95") + '</children></node>\n')


class LevelFiles(unittest.TestCase):
    def read(self, text, kind):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "_merged.lsx")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(lsx(text))
            if kind == "templates":
                return gamefiles.level_templates(path)
            if kind == "tiles":
                return [gamefiles.read_tiles(n) for n in gamefiles.game_objects(path)]
            return [gamefiles.read_object(n, kind, "Levels") for n in gamefiles.game_objects(path)]

    def test_trigger_volumes(self):
        box, prism, sphere = self.read(BOX_TRIGGER + PRISM_TRIGGER + SPHERE_TRIGGER, "Triggers")
        self.assertEqual(box["shape"], {"box": [10.0, 4.0, 6.0]})
        self.assertEqual(box["name"], "S_TEST_DangerZoneTrigger")
        self.assertEqual(prism["shape"], {"poly": [[-2.0, -2.0], [2.0, -2.0], [2.0, 2.0], [-2.0, 2.0]], "h": 5.0})
        self.assertEqual(sphere["shape"], {"sphere": 2.5})

    def test_decal_size_and_scale(self):
        (decal,) = self.read(DECAL, "Decals")
        self.assertEqual(decal["dims"], [3.0, 0.6, 3.0])
        self.assertAlmostEqual(decal["scale"], 0.9)
        self.assertEqual(decal["pos"], [1.0, 2.0, 3.0])

    def test_level_templates_name_their_sub_level(self):
        templates = self.read(LEVEL_TEMPLATE, "templates")
        self.assertEqual(templates["ba88dcc4-7bf5-450c-b8c5-52468677bef4"],
                         {"name": "LT_BGO_UC_GuildHall_A", "sub": "BGO_UC_GuildHall_A", "loaded": True})
        self.assertFalse(templates["927e9e0c-9f37-4c0f-ac02-0e04d42fe5dc"]["loaded"])
        self.assertEqual(len(templates), 2)   # the boulder is not a level template

    def test_tiles(self):
        ((wall, floor),) = self.read(TILES, "tiles")
        self.assertEqual(wall.pos, [-19.9, 30.58, -120.49])
        self.assertTrue(close(wall.rot, quat_yaw(90)), wall.rot)   # the matrix is written row by row
        self.assertAlmostEqual(wall.scale_z, 0.884)
        self.assertFalse(wall.walk_on or wall.walk_through or wall.no_decal)
        self.assertTrue(wall.stretch)
        self.assertEqual(wall.guid, "0db69b54-7cfb-436b-bdd0-934cfc40c41d")
        self.assertTrue(floor.walk_on)
        self.assertTrue(close(floor.rot, quat_yaw(-135)), floor.rot)   # QRotate quaternion (canonicalised)
        rec = gamefiles.tile_record("WALL_City_Wooden_House_A_0n5D_4H_B_015", wall,
                                    ext=[-1, 0, -0.25, 1, 4, 0.25], visual="WALL_Test_S_Piece_A")
        self.assertNotIn("walk", rec)
        self.assertEqual(rec["stretch"], 1)
        self.assertEqual(rec["sz"], 0.884)
        self.assertEqual(rec["ext"], [-1, 0, -0.25, 1, 4, 0.25])
        self.assertEqual(rec["v"], "WALL_Test_S_Piece_A")
        self.assertEqual(gamefiles.tile_record("FLOOR", floor)["walk"], 1)

    def test_visual_bounds_and_tile_sets(self):
        bank = ('<?xml version="1.0" encoding="utf-8"?>\n<save><version major="4" minor="0" revision="9" build="0" />'
                '<region id="TileSetBank"><node id="TileSetBank"><children><node id="Resource">'
                '<attribute id="ID" type="FixedString" value="set" /><children><node id="TileSet"><children>'
                '<node id="Tile"><attribute id="TileGUID" type="guid" value="0db69b54-7cfb-436b-bdd0-934cfc40c41d" />'
                '<attribute id="VisualGUID" type="FixedString" value="v1" /></node>'
                '</children></node></children></node></children></node></region>'
                '<region id="VisualBank"><node id="VisualBank"><children><node id="Resource">'
                '<attribute id="BoundsMax" type="fvec3" value="1 4 0.25" />'
                '<attribute id="BoundsMin" type="fvec3" value="-1 0 -0.25" />'
                '<attribute id="ID" type="FixedString" value="v1" />'
                '<attribute id="Name" type="FixedString" value="WALL_Test_S_Piece_A" /></node>'
                '</children></node></region></save>\n')
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "_merged.lsx")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(bank)
            bounds, tiles, names = gamefiles.bank(path)
        self.assertEqual(bounds, {"v1": [-1.0, 0.0, -0.25, 1.0, 4.0, 0.25]})
        self.assertEqual(tiles, {"0db69b54-7cfb-436b-bdd0-934cfc40c41d": "v1"})
        self.assertEqual(names, {"v1": "WALL_Test_S_Piece_A"})

    def test_visuals_are_inherited(self):
        roots = {"child": {"visual": "", "parent": "parent"}, "parent": {"visual": "v1", "parent": ""},
                 "loop": {"visual": "", "parent": "loop"}}
        self.assertEqual(gamefiles.visual_of("child", roots), "v1")
        self.assertEqual(gamefiles.visual_of("loop", roots), "")
        self.assertEqual(gamefiles.visual_of("unknown", roots), "")


class Placement(unittest.TestCase):
    def test_matrix_to_quat(self):
        for yaw in (0, 30, 90, 180, -90, -150):
            r = math.radians(yaw)
            m = ((math.cos(r), 0, math.sin(r)), (0, 1, 0), (-math.sin(r), 0, math.cos(r)))
            q = gamefiles.matrix_to_quat(m)
            self.assertTrue(close(q, quat_yaw(yaw)) or close(q, tuple(-v for v in quat_yaw(yaw))), (yaw, q))

    def test_sub_level_objects_follow_their_template(self):
        # A template placed at (10, 0, 5), turned 90 degrees: its local +x points to world -z.
        placement = ((10.0, 0.0, 5.0), quat_yaw(90), 1.0)
        pos, rot, scale = gamefiles.place(placement, (1.0, 2.0, 0.0), quat_yaw(45), 1.0)
        self.assertTrue(close(pos, (10.0, 2.0, 4.0)), pos)
        self.assertTrue(close(rot, quat_yaw(135)), rot)
        self.assertEqual(scale, 1.0)
        # Scale applies to the offset and to the object.
        pos, _, scale = gamefiles.place(((0, 0, 0), quat_yaw(0), 2.0), (1.0, 0.0, 0.0), scale=1.5)
        self.assertTrue(close(pos, (2.0, 0.0, 0.0)))
        self.assertEqual(scale, 3.0)

    def test_placed_record(self):
        rec = {"name": "FUR_GEN_Cabinet_A_000", "key": "k", "tpl": "t", "kind": "Items", "scope": "Levels",
               "pos": [-17.88, 30.6, -118.16], "rot": [0, 0, 0, 1]}
        out = gamefiles.placed(rec, ((-23.0, 0.0, 879.0), (0, 0, 0, 1), 1.0), "LT_BGO_UC_GuildHall_A_000",
                               "BGO_UC_GuildHall_A", False)
        self.assertEqual(out["pos"], [-40.88, 30.6, 760.84])
        self.assertEqual(out["via"], "LT_BGO_UC_GuildHall_A_000")
        self.assertNotIn("later", out)
        self.assertEqual(rec["pos"], [-17.88, 30.6, -118.16])   # the sub-level's own record is left alone
        self.assertTrue(gamefiles.placed(rec, ((0, 0, 0), (0, 0, 0, 1), 1.0), "LT", "S", True)["later"])


class Story(unittest.TestCase):
    GOAL = "\n".join([
        "Version 1",
        "INITSECTION",
        "/* DB_DangerZone((TRIGGER)S_X_00000000-0000-0000-0000-000000000000, \"Commented\"); */",
        "KBSECTION",
        "PROC",
        "PROC_State_Changed(S_DEN_RangerDen_SUB_50062397-bf9c-4765-9cbc-e40b5148f211, \"DEN\", \"DEN_State_Lockdown\")",
        "THEN",
        "PROC_LockWaypointForAll(\"WAYP_DEN_Camp\");",
        "//PROC_UnlockWaypointForAll(\"WAYP_DEN_Camp\");",
        "DB_DangerZone((TRIGGER)S_MOO_DangerZoneTrigger_31e89040-1673-46df-b12c-227f1714475a, \"MOO_Assault_DangerZone\");",
        "NOT DB_BlockedWaypointZone(S_LOW_SubmersibleInteriorArea_79fedabd-52a5-4d81-9169-ec7d5d43e8c4);",
        "PROC_LockAllGroupWaypoints(\"Act1\");",
        "",
        "PROC",
        "PROC_LockWaypointForAll(\"WAYP_DEN_Camp\")",
        "THEN",
        "PROC_LockWaypointForAll(\"NEW_WAYP_DEN_Hollow\");",
        "IF",
        "DB_DangerZone(_Trigger, _ID)",
        "THEN",
        "PROC_LockAllUnlockedWaypoints();",
    ])

    def test_story(self):
        s = gamefiles.story([("Gustav", "Act1_DEN_Lockdown", self.GOAL)])
        grove = s["waypoints"]["WAYP_DEN_Camp"]
        self.assertEqual([(c["call"], c["listener"], c["line"]) for c in grove],
                         [("PROC_LockWaypointForAll", False, 8), ("PROC_LockWaypointForAll", True, 15)])
        self.assertEqual(s["groups"]["Act1"][0]["call"], "PROC_LockAllGroupWaypoints")
        self.assertEqual(len(s["all"]), 1)
        danger = s["zones"]["31e89040-1673-46df-b12c-227f1714475a"]
        self.assertEqual(danger, [{"type": "danger", "id": "MOO_Assault_DangerZone", "goal": "Act1_DEN_Lockdown",
                                   "module": "Gustav", "line": 10, "removed": False}])
        blocked = s["zones"]["79fedabd-52a5-4d81-9169-ec7d5d43e8c4"]
        self.assertTrue(blocked[0]["removed"])
        self.assertNotIn("00000000-0000-0000-0000-000000000000", s["zones"])   # commented out


class Volumes(unittest.TestCase):
    def test_box_is_centred_and_turned(self):
        # 10 m along its own x, 6 m along its own z, turned 90 degrees: 6 m along world x, 10 m along world z.
        box = {"pos": [100, 20, 50], "rot": list(quat_yaw(90)), "shape": {"box": [10, 4, 6]}}
        self.assertTrue(inside_volume(box, (100, 20, 50)))
        self.assertTrue(inside_volume(box, (102.9, 21.9, 54.9)))
        self.assertFalse(inside_volume(box, (104, 20, 50)))   # 4 m along world x: outside the 6 m side
        self.assertFalse(inside_volume(box, (100, 22.5, 50)))

    def test_prism_rises_from_the_trigger(self):
        prism = {"pos": [0, 10, 0], "rot": [0, 0, 0, 1], "shape": {"poly": [[-2, -2], [2, -2], [2, 2], [-2, 2]], "h": 5}}
        self.assertTrue(inside_volume(prism, (1, 10.5, 1)))
        self.assertTrue(inside_volume(prism, (1, 14.9, -1.9)))
        self.assertFalse(inside_volume(prism, (1, 9.5, 1)))
        self.assertFalse(inside_volume(prism, (2.1, 12, 0)))

    def test_sphere(self):
        sphere = {"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "shape": {"sphere": 2.5}}
        self.assertTrue(inside_volume(sphere, (1.5, 1.5, 1.0)))
        self.assertFalse(inside_volume(sphere, (2.0, 2.0, 0.0)))

    def test_point_in_polygon(self):
        l_shape = [[0, 0], [4, 0], [4, 1], [1, 1], [1, 4], [0, 4]]
        self.assertTrue(point_in_polygon(0.5, 3, l_shape))
        self.assertFalse(point_in_polygon(2, 2, l_shape))


WALL_EXT = [-1.0, 0.0, -0.25, 1.0, 4.0, 0.25]   # a wall tile 2 m long, 4 m high and 0.5 m thick


class FakeGrid:
    """Flat free floor at height `height` everywhere, except where `holes` (x/z boxes) cut it."""

    def __init__(self, holes=(), height=0.0, blocked=None):
        self.holes = holes
        self.height = height
        self.blocked = blocked

    def surfaces(self, x, z):
        if self.blocked and self.blocked(x, z):
            return [(self.height, 0x2)]
        if any(x0 <= x <= x1 and z0 <= z <= z1 for x0, x1, z0, z1 in self.holes):
            return [(self.height, 0x2)]
        return [(self.height, 0)]

    def floor(self, x, z, near, tolerance=2.0):
        free = [h for h, flags in self.surfaces(x, z) if not flags & 0x7 and abs(h - near) <= tolerance]
        return free[0] if free else None


class FakeLevel:
    def __init__(self, tiles=(), solid=(), holes=(), height=0.0, blocked=None):
        self.grid = FakeGrid(holes, height=height, blocked=blocked)
        self.tiles = Indexed(tiles)
        self.tile_boxes = BoxIndex(self.tiles)
        self.solid = Indexed(solid)
        self.solid_boxes = BoxIndex(self.solid)
        self.points = Indexed()
        self.objects = list(solid)
        self.volumes = []
        self.decals = Indexed()

    floor = Level.floor
    near = Level.near
    inside = Level.inside


class Boxes(unittest.TestCase):
    def test_index_finds_neighbours(self):
        items = Indexed([{"pos": [0, 0, 0]}, {"pos": [7.9, 0, 0]}, {"pos": [40, 0, 40]}])
        self.assertEqual(len(items.around(1, 1, 2)), 2)
        self.assertEqual(len(items.around(40, 40, 1)), 1)

    def test_box_follows_the_object(self):
        # A 2 by 4 by 0.5 m wall tile turned 90 degrees: its length now runs along world z.
        c, axes, half = box({"pos": [10.0, 0.0, 5.0], "rot": list(quat_yaw(90)), "ext": WALL_EXT})
        self.assertTrue(close(c, (10.0, 2.0, 5.0)))
        self.assertTrue(close(half, (1.0, 2.0, 0.25)))
        self.assertTrue(close(axes[0], (0.0, 0.0, -1.0)))
        # Uniform Scale applies to all three axes; ScaleZ ("sz") stretches length along local x.
        _, _, half = box({"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "ext": WALL_EXT, "scale": 1.5, "sz": 0.8})
        self.assertTrue(close(half, (1.2, 3.0, 0.375)))
        _, _, half = box({"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "ext": WALL_EXT, "sz": 1.5})
        self.assertTrue(close(half, (1.5, 2.0, 0.25)))
        _, _, half = box({"pos": [0, 0, 0], "rot": [0, 0, 0, 1], "ext": WALL_EXT, "scale": 0.5})
        self.assertTrue(close(half, (0.5, 1.0, 0.125)))
        self.assertIsNone(box({"pos": [0, 0, 0], "rot": [0, 0, 0, 1]}))

    def test_overlap_of_turned_boxes(self):
        a = frame_box((0.0, 0.0, 0.0), 0.0, (-1, -1, -1), (1, 1, 1))
        near = frame_box((1.6, 0.0, 0.0), 45.0, (-0.5, -0.5, -0.5), (0.5, 0.5, 0.5))   # corner reaches x = 0.89
        self.assertTrue(boxes_overlap(a, near))
        far = frame_box((2.0, 0.0, 0.0), 45.0, (-0.5, -0.5, -0.5), (0.5, 0.5, 0.5))    # corner reaches x = 1.29
        self.assertFalse(boxes_overlap(a, far))
        self.assertTrue(boxes_overlap(a, far, margin=0.3))
        self.assertTrue(point_in_box(a, (0.9, -0.9, 0.9)))
        self.assertFalse(point_in_box(a, (1.1, 0.0, 0.0)))

    def test_obstacles(self):
        region = frame_box((0.0, 0.0, 0.0), 0.0, (-1, 0, -1), (1, 3, 1))
        cabinet = {"name": "FUR_GEN_Cabinet_A_000", "pos": [0.5, 0, 0.5], "rot": [0, 0, 0, 1], "ext": [-0.5, 0, -0.3, 0.5, 2, 0.3]}
        carpet = {"name": "DEC_GEN_Carpet_Rich_A_001", "pos": [0, 0, 0], "rot": [0, 0, 0, 1], "ext": [-1, 0, -1, 1, 0.02, 1]}
        slab = {"name": "NAT_Rock_Granite_Platform_C_024", "pos": [0, -1, 0], "rot": [0, 0, 0, 1], "ext": [-2, -1, -2, 2, 0.9, 2]}
        cliff = {"name": "NAT_Cliff_Granite_B_001", "pos": [3, 0, 0], "rot": [0, 0, 0, 1], "ext": [-3, 0, -3, 3, 6, 3]}
        beside = {"name": "FUR_GEN_Chair_A_001", "pos": [1.8, 0, 0], "rot": [0, 0, 0, 1], "ext": [-0.3, 0, -0.3, 0.3, 1, 0.3]}
        unknown = {"name": "BOOK_GEN_Books_Stack_B_004", "pos": [0.2, 0.5, 0.2], "rot": [0, 0, 0, 1]}
        found = dict((o["name"], kind) for o, kind in obstacles(FakeLevel(solid=[cabinet, carpet, slab, cliff, beside, unknown]), region, 0.0))
        self.assertEqual(found, {"FUR_GEN_Cabinet_A_000": "solid", "DEC_GEN_Carpet_Rich_A_001": "flat",
                                 "NAT_Cliff_Granite_B_001": "large", "BOOK_GEN_Books_Stack_B_004": "solid"})

    def test_walls_and_ceilings_through_the_boulder(self):
        shrine, yaw = (0.0, 0.0, 0.0), 0.0
        # Yaw 0: the shrine's front looks along -z, so the boulder lies on +z, from 0 to 2.35 m.
        body = frame_box(shrine, yaw, (ROCK_BODY[0], -0.71, ROCK_BODY[2]), (ROCK_BODY[1], 3.2, ROCK_BODY[3]))
        wall = {"c": "WALL_City_Wooden_House_A_0n5D_4H_B_001", "pos": [0.0, 0.0, 1.5], "rot": [0, 0, 0, 1], "ext": WALL_EXT}
        far = {"c": "WALL_City_Wooden_House_A_0n5D_4H_B_002", "pos": [0.0, 0.0, 6.0], "rot": [0, 0, 0, 1], "ext": WALL_EXT}
        below = {"c": "WALL_City_Wooden_House_A_0n5D_4H_B_003", "pos": [0.0, -4.0, 1.0], "rot": [0, 0, 0, 1], "ext": WALL_EXT}
        ceiling = {"c": "WALL_Dungeon_Ceiling_A_001", "pos": [0.5, 2.6, 1.0], "rot": [0, 0, 0, 1], "ext": [-1, 0, -1, 1, 0.3, 1]}
        upstairs = {"c": "FLOOR_Wood_A_001", "pos": [0.0, 4.0, 1.0], "rot": [0, 0, 0, 1], "walk": 1, "ext": [-1, 0, -1, 1, 0.2, 1]}
        hits = tile_hits(FakeLevel(tiles=[wall, far, below, ceiling, upstairs]), body, 0.0)
        self.assertEqual([(k, t["c"]) for k, t, _ in hits], [("wall", wall["c"]), ("over", ceiling["c"])])


class Walls(unittest.TestCase):
    """A rune on a wall: a wall along x at z = 0 (its face looks along -z), floor at height 0."""

    def wall(self, x_from=-4, x_to=4):
        # 2 m tiles whose face is at z = 0: their centres are 0.25 m behind it.
        return [{"c": "WALL_Test_0n5D_4H_A_%03d" % i, "pos": [float(x), 0.0, 0.25], "rot": [0, 0, 0, 1], "ext": WALL_EXT}
                for i, x in enumerate(range(x_from + 1, x_to, 2))]

    def waypoint(self, x=0.0):
        return {"id": "TEST", "style": "wall",
                "shrine": {"position": [x, SHRINE_ABOVE_FLOOR, 0.0], "yaw": 0.0},
                "trigger": {"position": [x, 0.0, -WALL_ARRIVAL]}}

    def holes(self):
        return [(-50.0, 50.0, -0.25, 50.0)]   # the wall and what is behind it are not floor

    def test_rune_on_a_long_wall(self):
        errors, warnings = check_placement(FakeLevel(tiles=self.wall(), holes=self.holes()), self.waypoint())
        self.assertEqual(errors, [])

    def test_wall_must_carry_the_whole_rune(self):
        errors, _ = check_placement(FakeLevel(tiles=self.wall(-4, 0), holes=self.holes()), self.waypoint())
        self.assertTrue(any("no wall behind" in e for e in errors), errors)

    def test_face_must_be_where_the_rune_is(self):
        wp = self.waypoint()
        wp["shrine"]["position"][2] -= 0.4   # the rune 0.4 m out from the face
        wp["trigger"]["position"][2] -= 0.4
        errors, _ = check_placement(FakeLevel(tiles=self.wall(), holes=self.holes()), wp)
        self.assertTrue(any("no wall behind" in e for e in errors), errors)

    def test_wall_must_be_thick_enough(self):
        # A 20 cm wall: the rune's box would reach through it and show on its far side.
        thin = [dict(t, ext=[-1.0, 0.0, -0.1, 1.0, 4.0, 0.1], pos=[t["pos"][0], 0.0, 0.1]) for t in self.wall()]
        errors, _ = check_placement(FakeLevel(tiles=thin, holes=self.holes()), self.waypoint())
        self.assertTrue(any("thinner than" in e for e in errors), errors)

    def test_nothing_may_stand_in_front(self):
        barrel = {"name": "CONT_Barrel_A_001", "pos": [0.8, 0.0, -0.4], "rot": [0, 0, 0, 1], "ext": [-0.4, 0, -0.4, 0.4, 1.2, 0.4]}
        errors, _ = check_placement(FakeLevel(tiles=self.wall(), solid=[barrel], holes=self.holes()), self.waypoint())
        self.assertTrue(any("CONT_Barrel_A_001 stands in front of the rune" in e for e in errors), errors)

    def test_no_rune_across_a_door(self):
        door = {"c": "WALL_Test_Door_A_000", "pos": [1.0, 0.0, 0.25], "rot": [0, 0, 0, 1], "ext": WALL_EXT}
        errors, _ = check_placement(FakeLevel(tiles=self.wall() + [door], holes=self.holes()), self.waypoint())
        self.assertTrue(any("drawn across WALL_Test_Door_A_000" in e for e in errors), errors)

    def test_no_rune_on_door_piece_broken_or_nodecal_tile(self):
        door_piece = [dict(t, v="WALL_City_Castlewall_Inside_1D_4H_4W_D_Piece_B") for t in self.wall()]
        errors, _ = check_placement(FakeLevel(tiles=door_piece, holes=self.holes()), self.waypoint())
        self.assertTrue(any("drawn across" in e for e in errors), errors)
        broken = [dict(t, v="WALL_Dungeon_Abbey_A_2n5D_10H_4W_E_Piece_Broken_D") for t in self.wall()]
        errors, _ = check_placement(FakeLevel(tiles=broken, holes=self.holes()), self.waypoint())
        self.assertTrue(any("no wall behind" in e for e in errors), errors)
        nodecal = [dict(t, nodecal=1) for t in self.wall()]
        errors, _ = check_placement(FakeLevel(tiles=nodecal, holes=self.holes()), self.waypoint())
        self.assertTrue(any("does not receive decals" in e for e in errors), errors)

    def test_walkable_floor_behind_wall_is_rejected(self):
        # An archway or loose wall box leaves walkable floor right behind the shrine's plane.
        errors, _ = check_placement(FakeLevel(tiles=self.wall(), holes=()), self.waypoint())
        self.assertTrue(any("walkable floor runs behind" in e for e in errors), errors)

    def test_games_own_wall_runes_pass_on_their_real_tiles(self):
        # Tiles copied from the game's CTY_Main_A (Lower City Central Wall, 45-degree wall using QRotate)
        # and SCL_Main_A (Moonrise Towers, using Rotate and ScaleZ = 0.884). Both must pass at the game's
        # own yaw, within a few centimetres of the game's own shrine.
        central_wall_tiles = [
            {"c": "WALL_City_Lower_House_A_1D_4H_A_645", "pos": [-54.476, 29.185, -56.402],
             "rot": [0.0, -0.9234, 0.0, 0.38384], "sz": 1.0, "stretch": 1,
             "ext": [0.0, 0.0, -0.32, 2.0, 4.002, 0.001], "v": "WALL_City_Lower_House_A_0n5D_4H_2W_S_Piece_Outside_A"},
            {"c": "WALL_City_Lower_House_A_1D_4H_A_645", "pos": [-51.654, 29.185, -59.238],
             "rot": [0.0, -0.9234, 0.0, 0.38384], "sz": 1.0, "stretch": 1,
             "ext": [0.0, 0.0, -0.32, 2.0, 4.002, 0.001], "v": "WALL_City_Lower_House_A_0n5D_4H_2W_S_Piece_Outside_A"},
            {"c": "WALL_City_Lower_House_A_1D_4H_A_645", "pos": [-53.065, 29.185, -57.82],
             "rot": [0.0, -0.9234, 0.0, 0.38384], "sz": 1.0, "stretch": 1,
             "ext": [0.0, 0.0, -0.32, 2.0, 4.002, 0.001], "v": "WALL_City_Lower_House_A_0n5D_4H_2W_S_Piece_Outside_A"},
            {"c": "WALL_City_Lower_House_A_1D_4H_A_645", "pos": [-55.888, 29.185, -54.984],
             "rot": [0.0, 0.38384, 0.0, 0.9234], "sz": 1.0, "stretch": 1,
             "ext": [0.0, 0.0, -0.32, 6.001, 4.002, 0.001], "v": "WALL_City_Lower_House_A_0n5D_4H_6W_S_Piece_Outside_A"},
        ]
        # Game shrine at (-53.573, 29.335, -56.934), yaw 225 (-135): the tile face stands 5.8 cm out along (+0.707, +0.707).
        cw_face = (-53.573 + 0.058 * math.sqrt(0.5), 29.335, -56.934 + 0.058 * math.sqrt(0.5))
        cw_wp = {"id": "WAYP_LOW_CentralWall", "style": "wall",
                 "shrine": {"position": list(cw_face), "yaw": -135.0},
                 "trigger": {"position": [cw_face[0] + 2.0 * math.sqrt(0.5), 29.335 - SHRINE_ABOVE_FLOOR,
                                          cw_face[2] + 2.0 * math.sqrt(0.5)]}}
        cw_level = FakeLevel(tiles=central_wall_tiles, height=29.335 - SHRINE_ABOVE_FLOOR,
                             blocked=lambda x, z: (x - cw_face[0]) + (z - cw_face[2]) < 0.0)
        self.assertEqual(check_placement(cw_level, cw_wp)[0], [])

        moonrise_tiles = [
            {"c": "WALL_Harbor_House_Base_A_1D_4H_A_050", "pos": [-160.37, 22.02, -100.296],
             "rot": [0.0, 0.0, 0.0, 1.0], "ext": [-1.004, -0.013, -0.588, 0.585, 4.003, 1.001],
             "v": "WALL_Harbor_House_Base_B_1D_4H_1W_L_Piece_A"},
            {"c": "WALL_Harbor_House_Base_A_1D_4H_A_050", "pos": [-160.37, 22.02, -94.761],
             "rot": [0.0, -0.70711, 0.0, 0.70711], "ext": [-1.004, -0.013, -0.588, 0.585, 4.003, 1.001],
             "v": "WALL_Harbor_House_Base_B_1D_4H_1W_L_Piece_A"},
            {"c": "WALL_Harbor_House_Base_A_1D_4H_A_050", "pos": [-160.37, 22.02, -95.761],
             "rot": [0.0, 0.70711, 0.0, 0.70711], "sz": 0.884, "stretch": 1,
             "ext": [-0.005, -0.002, -0.588, 4.008, 4.018, 0.584], "v": "WALL_Harbor_House_Base_B_1D_4H_4W_S_Piece_A"},
        ]
        # Game shrine at (-159.756, 22.354, -97.297), yaw -90: exact shrine position is 3 cm from the wall face.
        moo_wp = {"id": "WAYP_MOO_TowerExterior", "style": "wall",
                  "shrine": {"position": [-159.756, 22.354, -97.297], "yaw": -90.0},
                  "trigger": {"position": [-157.756, 22.354 - SHRINE_ABOVE_FLOOR, -97.297]}}
        moo_level = FakeLevel(tiles=moonrise_tiles, height=22.354 - SHRINE_ABOVE_FLOOR,
                              blocked=lambda x, z: x < -159.78)
        self.assertEqual(check_placement(moo_level, moo_wp)[0], [])

    def test_rune_box_lies_on_the_face(self):
        rune = rune_box(self.waypoint()["shrine"]["position"], 0.0)
        c, axes, half = rune
        self.assertTrue(close(c, (0.0, SHRINE_ABOVE_FLOOR + WALL_DECAL_OFFSET[1], -0.06), 3), c)
        self.assertAlmostEqual(abs(axes[1][2]), 1.0, places=4)    # the rune is projected across the wall
        self.assertAlmostEqual(box_span(rune, (0, 0, 1))[1] - box_span(rune, (0, 0, 1))[0], 0.27, places=4)
        self.assertGreater(box_span(rune, (0, 1, 0))[0], 0.15)    # and its box clears the floor by 15 cm
        self.assertLess(box_span(rune, (0, 0, 1))[1], 0.25)       # and reaches at most 0.21 m into the wall


if __name__ == "__main__":
    unittest.main()
