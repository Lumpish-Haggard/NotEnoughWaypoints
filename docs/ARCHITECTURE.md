# How it works

## A waypoint in Baldur's Gate 3

The game builds every waypoint from the same pieces, and this mod uses the same ones:

| Piece | What it is | Where it lives |
|---|---|---|
| Shrine | An **invisible** item made from the game's waypoint template (`Helper_Waypoint_A`, `2dab7df1-...`): what players use. Its behaviour script unlocks the waypoint when a player comes within 18 m and can see it. | `Globals/<level>/Items/` (global: the story refers to it from anywhere) |
| What carries the rune | What players see. The game has no waypoint model: in towns, fortresses and dungeons the rune is drawn on a wall that is already there; in the open and in caves on a rock or cliff piece, usually placed by hand for that waypoint. | the level itself, or `Levels/<level>/Scenery/` |
| Rune | A decal (`DCL_Waypoint_Dark_A` or `DCL_Waypoint_Light_A`) projected onto the wall or the rock. | `Levels/<level>/Decals/` |
| Arrival point | A teleport trigger (`TeleportTrigger`, `f7bd7465-...`) on the floor in front of the shrine. Travelling puts the party there. Its turn and its `Angle` (the camera's direction on arrival, -1 to leave the camera alone) are set as the game sets those of its own waypoints: see *Arrival*. | `Globals/<level>/Triggers/` |
| Story fact | `DB_WaypointInfo(group, id, shrine, arrival point)` | a story goal |
| Name | A translated-string key named after the waypoint id, pointing at the name's localisation handle | `Mods/<mod>/Localization/*.lsf` and `Localization/<Language>/*.loca` |

The game's story script `_Waypoints` (in the Shared module) does everything else. When a `DB_WaypointInfo` fact is added it registers the waypoint for the map; it unlocks a waypoint when the shrine reports a player nearby or a player uses it; it opens the travel window; it teleports the party; and it locks waypoints, one by one or a whole group at once. The game locks a whole group when the story leaves an act (`Act1` and `Act1b` when Act 2 starts, `Act2` when Act 3 starts), so the group must match the level.

## What the mod adds

- One shrine, rune and arrival point per waypoint, and a boulder for those in the open, generated from `waypoints.json`. A waypoint is one of two arrangements (`style`):
  - **`wall`**, for buildings and walls: the rune on a wall the game already has, and nothing added. The game's fifteen runes in these levels that have no rock of their own are all turned the same way relative to their shrine, to within a few degrees, and sit about 1.5 m above it; `tools/waypoints.py` keeps that turn and height, measured on the Lower City Central Wall waypoint, and the 0.9 scale of the Moonrise Towers one, which keeps the rune's box 15 cm clear of the floor. The shrine stands on the wall's face, measured from the bounds of the wall's tiles, and the rune's centre 6 cm in front of it, where the Moonrise Towers rune is in front of its wall. The box the rune is projected in is 0.27 m deep: it takes in the face whether the game projects a decal from the middle of its box or inward from its front, and reaches at most 0.21 m into the wall, which must be at least 0.3 m thick so that the rune never shows on its far side. Tests compare the arrangement with both of the game's waypoints.
  - **`boulder`**, for the open: a copy of the Blighted Village waypoint (`S_FOR_WaypointShrine` in `WLD_Main_A`). Its shrine is upright, its rock is a boulder (`NAT_Rock_Boulder_B` at 1.2 scale) standing on flat ground, and its rune lies on the boulder's face, so the same arrangement fits on any flat floor. The boulder comes in several colours that share one mesh (grey, wet grey, brown, mossy), so any colour fits. The decal keeps the depth the game gives it there (`Dimensions` 3 0.6 3), so that it marks the boulder and not the floor in front of it. A test feeds the game's own shrine into the arrangement and checks that it gives back the game's own boulder and rune.

  The generator turns each arrangement to face its arrival point (a rune on a wall faces the way the wall does, `shrine.yaw`). The rune on its own, with nothing behind it, has nothing to land on and smears across the floor: that is what the first test build showed.
- One story goal, `NotEnoughWaypoints.txt`:
  - its INIT section adds a `DB_WaypointInfo` fact per waypoint, and the Arcane Tower to the game's list of Underdark waypoints (`DB_UND_BroodingSpovereign_UnderdarkWaypoints`), so that Sovereign Glut follows the party there;
  - a rule registers the waypoints once more when gameplay first starts (see *Existing saves*);
  - a rule locks the Hollow whenever the game locks its own Emerald Grove waypoint (`PROC_LockWaypointForAll("WAYP_DEN_Camp")`, when the druids seal the Grove), so it never leads past the barrier;
  - a rule per moved waypoint puts it where the current version has it, in saves made before (see *Existing saves*).
- The names, in `Localization/English/NotEnoughWaypoints.loca`. The file name matters: a mod file called `english.loca` would replace the game's own and remove every English text in the game, so `pack.ps1` refuses to build a pak with anything but `NotEnoughWaypoints.loca` in it.

The mod replaces none of the game's files and needs no other mods.

## Existing saves

The goal has no parent goal (no `ParentTargetEdge`). A goal like that starts as soon as the story does, including when a save that was made without the mod is loaded, so its INIT section adds the waypoints to that save.

Starting first has one catch: the goal may start before the game's `_Waypoints` goal is running, and that goal registers a waypoint for the map only at the moment its `DB_WaypointInfo` fact is added. So the mod's own rule registers its waypoints once more on the first `LevelGameplayStarted`, and remembers that it did (`DB_NEW_WAYP_Registered`). Whichever order the goals start in, every waypoint is registered.

**Moving a waypoint.** A save keeps where its items and triggers stand. Moving a released waypoint in `waypoints.json` would therefore move it in new games only: in a save that has been in its level, the shrine (what players click) and the arrival point would stay at the old place while the rune moved. So a moved waypoint carries a `placement` number, raised by one each time it moves, and the goal gets a rule for it: when its level is loaded (`LevelLoaded`) and the save has not had this placement yet (`DB_NEW_WAYP_Placed(id, placement)`), it puts the shrine there with `ToTransform` and the arrival point with `TeleportToPosition`, and remembers that it did. That is how the game's own hotfixes move objects in existing saves (`BG3_SavegamePatches`, and the boat in `Act3b_END_EmperorPreludeCave`, which is put back on `LevelLoaded`). In a new game the rule moves them to where they already are. Boulders and runes are part of the level, not of the save, so they move with the mod's files; a boulder that is no longer used is deleted, and its GUID is kept under `retired` so that it is never used again.

## Placement

A waypoint is only as good as where it stands. The checks in `tools/waypoints.py` run against the game data that `tools/extract_game_data.py` reads from your installation (with `tools/gamefiles.py`) into `tools/.cache/`:

- **The navigation grid** (`Levels/<level>/Ai/aigrid.data`), read by `tools/navgrid.py`. It covers each level in 0.5 m cells and stores, per cell, the height of every walkable surface and whether something stands on it. Tiles overlap where a place has several floors (the storeys of a tower, a bridge over a road).
- **The placed objects** (`objects.json`): characters, items, props, decals and triggers, with their position, rotation and scale; for triggers also their volume (a box, a prism or a sphere), for decals their size.
- **The sub-levels.** The main file of a level holds only part of it. Most places are sub-levels of their own (the Guildhall, Rivington's streets and buildings, the goblin camp, the Emerald Grove), placed into the level by a *level template*: an object whose root template names the sub-level (`SubLevelName`). The extractor follows every level template, nested ones too, reads the sub-level and moves its objects into world coordinates. Sub-levels the story loads later (`StartingLoaded` false, for example the barrier that seals the Grove) are marked `later`. As a check on the arithmetic, the extractor reports how many of each sub-level's characters and items stand on the main level's navigation grid: about half (the rest sit on tables and shelves) for the gameplay sub-levels, turned ones included, and none for the cutscene sets placed off the map.
- **The tiles** (`tiles.json`) of every tile construction: the walls, floors, ceilings and trims built from tiles, each with its position, rotation and whether it can be walked on or through.
- **How far things reach** (`ext`). Every item, prop and tile is drawn with a visual, and the game's resource banks give each visual's bounds (`BoundsMin`, `BoundsMax`; tiles find their visual through their tile set). With its position, rotation and scale that makes the box the object fills in the world: tight for a wall tile or a cabinet, loose around a rock, a tree or a building's shell. About 99% of items and props have one, and every tile.
- **The story** (`story.json`): every place a story goal locks or unlocks a waypoint or a group, and the triggers it makes a danger zone (nobody inside can travel out while it is active), a blocked waypoint zone (no waypoint works there) or a safe bubble.

For every waypoint `tools/build_waypoints.py` checks:

| Check | Why |
|---|---|
| Free floor under the arrival point, within 15 cm of its height | the party lands on the floor, not in it or above it |
| At most 5 of the 25 cells within 1 m of the arrival point blocked (a warning for 1 to 5) | room for the whole party |
| No character, item or prop of the game's, sub-levels included, whose box reaches the arrival point | the party does not land in it |
| Walkable floor all the way between the arrival point and the waypoint | no wall in between |
| **Boulder:** the shrine at the floor where the boulder's front meets it | the boulder sits into the floor as deep as at the Blighted Village (0.7 m) |
| **Boulder:** free floor under its whole footprint (3 m by 2 m, measured on its mesh), never more than 25 cm lower than its front and at most 1 m higher | it may sit into a rise behind it, as the game's rocks do on slopes, but never floats over a drop |
| **Boulder:** where the boulder or the party stands on a floor, no second floor up to 3.5 m above it | no balcony or upper storey cutting through it |
| **Boulder:** no box of a character, item or prop inside it, and no wall, floor or ceiling tile through it | nothing clips into it |
| **Wall:** the wall's face within 5 cm of the shrine's plane, and wall at least 0.3 m thick, behind all 49 points of the rune | the rune lands on the wall everywhere, and never shows on its far side |
| **Wall:** nothing within 25 cm in front of the rune, and nothing higher than 0.9 m within 0.8 m (lower things are a warning) | the rune would be drawn on it, or hidden |
| **Wall:** no door, gate, window or arch along the rune, and no tile jutting out in front of it | the rune is never drawn across a way through the wall |
| **Wall:** the floor below the rune's box | the rune would smear across it |
| Warnings for something flat under a boulder, a large loose box, a story point (where scripts send characters) under the waypoint or within 1 m of the arrival point, a decal under a rune | each needs a look, not a change |
| A warning for a danger zone or a blocked waypoint zone of the story that the waypoint stands in | each needs a decision: Moonrise Towers is a danger zone during the assault |
| No clash with the game's waypoint ids, names or object GUIDs | the map list stays readable; nothing is overwritten |

An error that a waypoint's `accept` list names was looked at and judged harmless (in game, where it matters); it is reported as a warning, so that it stays visible. The checks know the box each object fills, which is loose around rocks, trees and big pieces of a building: a box that reaches the waypoint only gives a warning when two of its sides are longer than 4 m. They cannot see walkways (a waypoint can pass every check and still half-block a path), light, or how the spot looks. `tools/survey.py report <id>` lists everything around a waypoint for review, `tools/survey.py walls ...` and `spots ...` search a place for runes on walls and for boulders, and `tools/survey.py map ...` draws the floor plan with its walls. Testing in game covers the rest.

## Arrival

The game's 37 waypoints in these levels set up their arrival points by hand (read from `Globals/<level>/Triggers`):

- **The turn.** The game turns 27 of them; 17 of those point their +z at their waypoint's shrine to within 30 degrees (14 to within 15), and the other 10 are not turned at all. Ours are turned to face their shrine (`arrival_yaw`), unless `trigger.yaw` says otherwise. A test gives back the turn of five of the game's arrival points from their shrine and arrival point.
- **The camera.** 22 set `Angle`, the direction of the camera on arrival in degrees (the template's default, -1, leaves the camera as it is). Each is picked by hand, but most keep one relation to the waypoint: `Angle` minus the compass direction from the shrine to the arrival point is 225 degrees at the median, and within 30 degrees of it at 14 of the 22. Ours keep that relation, rounded to 5 degrees as Larian's are (`arrival_camera`), unless `trigger.camera` picks a view.

What each does on screen is not written down anywhere; the game's own scripts set a character's facing separately after a teleport where they need it (`LookFromTrigger`). The game's scripts also never turn a trigger, so in a save made before, an arrival point keeps the turn it had; `Angle` belongs to the arrival point's template, the mod's own object.

## Removing the mod

What a save keeps of the mod was read from a save made with it (`tools/inspect_save.py`):

| Where | What | Without the mod's files |
|---|---|---|
| The story | the mod's goal and its records (`DB_NEW_WAYP_*`); its waypoints in the game's `DB_WaypointInfo`; who unlocked each (`DB_WaypointUnlocked`); the Arcane Tower in Sovereign Glut's list; after travel from another level, the story's record of which waypoint an arrival point belongs to | the goal and its own records go; the facts in the game's databases stay |
| Each party | its travel list: the id, arrival point and level of each waypoint it unlocked | stays: listed without a name, leading nowhere, until the story locks its act |
| The game | the waypoints registered for the map | stay; the game has no call to unregister one |
| The objects | the shrines and arrival points (global objects, made from the mod's own) | their templates are gone with the mod's files |
| The levels | the runes and boulders | not in the save: they go with the mod's files |

**The uninstaller** (`Mods/NotEnoughWaypointsUninstaller/`) is a second mod: its `meta.lsx` and one story goal, generated from `waypoints.json` like the mod's own. It is loaded in place of the mod for one save:

- Its INIT section lists every waypoint id, and names the mod's own list (`NOT DB_NEW_WAYP_Waypoint("")`) so that the list the save already holds stays readable once the mod's goal is gone; a waypoint of a later version is taken out too.
- On `SavegameLoaded` (where the game applies its own savegame patches) and on every `LevelGameplayStarted`, for each id, in one rule: `PROC_LockWaypointForAll`, the game's own lock, which calls the engine's `LockWaypoint` for every player who unlocked it and so takes it out of every party's travel list; then any unlock records left; then the waypoint's `DB_WaypointInfo` fact. Separately, the id in Sovereign Glut's list and in the story's travel records. Doing it twice does nothing.
- It never names an object: the shrine and the arrival point are found through the story, so nothing depends on the mod's objects still being there.
- It does nothing while the mod's goal is running (`NOT SysIsActive("NotEnoughWaypoints")`): with both loaded, the mod would keep its objects but lose its waypoints for good, since its INIT section runs only once in a save.

Put back later, the mod's goal is new to that save again: its INIT section adds the waypoints, and the rules above register them and put them where this version has them.

## Checking the story

The game compiles the story of every mod together with its own when a save is loaded. `tools/check_story.py` does the same with LSLib's StoryCompiler before a release: the mod alone, the uninstaller in its place, and both together, each against the game's story from your installation. The game ships no story header, so the check writes one from the function table of the game's compiled story (StoryDecompiler's debug log), and turns the enum constants in the game's goals (`DEATHTYPE.Chasm`), which LSLib cannot read, into the numbers they are. LSLib reports about a hundred messages about the game's own goals that the game's compiler accepts; the check compiles the game's story alone first and reports only what the repository's goals add. It found the planted mistakes it was tried with: a misspelt database, a procedure called with the wrong number of arguments, a parameter of the wrong type.

## Patch day

A game patch can change what the story does with the game's waypoints that ours follow: lock an act's waypoints at another moment, stop locking the Grove, change the waypoint rules themselves. After a patch, `tools/extract_game_data.py` reads the story again, and `tools/build_waypoints.py` compares what it does with what the waypoints follow against `story_baseline.json`, the record of the patch they were last checked on:

| What | Why ours follow it |
|---|---|
| The locks and unlocks of their act groups (`PROC_LockAllGroupWaypoints`) | the story locks a whole act's waypoints when it leaves the act, ours included |
| The locks and unlocks of the game's waypoint each starts from (`nextTo`), and of every `lockWith` | ours are locked and unlocked with the game's waypoint next to them |
| The lock of every waypoint (`PROC_LockAllUnlockedWaypoints`, at the epilogue) | it takes ours too |
| The travel zones over each shrine and arrival point | a danger zone or a blocked waypoint zone changes what a waypoint does there |
| A fingerprint of the game's waypoint rules (`_Waypoints`), comments and spacing left out | ours rely on them for everything: registering, unlocking, travel, locking |
| The waypoints Sovereign Glut follows the party between | the Arcane Tower is added to that list |

Call sites are compared without their line numbers, which move with any edit to a goal. Each change is a warning that names the goal. Once each has been looked at, and a waypoint that should follow a new lock has been given `lockWith`, `build_waypoints.py --accept-story` records the story for the new patch. When nothing changed, the check says so, and `--accept-story` notes the new patch in the record. A test checks that the record covers every waypoint, so adding one means recording the story again.

## Building

`pack.ps1` builds two packages. For the mod it stages `Mods/NotEnoughWaypoints/` and `Localization/`, converts the generated `.lsx` files to the binary `.lsf` the game loads and the names from `.xml` to `.loca`, and packs everything with LSLib's `Divine.exe`; for the uninstaller, `Mods/NotEnoughWaypointsUninstaller/`. It then lists each pak: every expected file must be there, nothing else may be, and no unconverted source may slip in. It writes `info.json` for the mod managers into each release zip. Before that it runs `build_waypoints.py --check` and, where the game and ExportTool are installed, `check_story.py`.
