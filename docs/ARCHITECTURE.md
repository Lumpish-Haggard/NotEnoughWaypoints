# How it works

## A waypoint in Baldur's Gate 3

The game builds every waypoint from the same pieces, and this mod uses the same ones:

| Piece | What it is | Where it lives |
|---|---|---|
| Shrine | An item made from the game's waypoint template (`Helper_Waypoint_A`, `2dab7df1-...`). Its behaviour script unlocks the waypoint when a player comes within 18 m and can see it. | `Globals/<level>/Items/` (global: the story refers to it from anywhere) |
| Arrival point | A teleport trigger (`TeleportTrigger`, `f7bd7465-...`) on the floor in front of the shrine. Travelling puts the party there. | `Globals/<level>/Triggers/` |
| Rune | A decal (`DCL_Waypoint_Dark_A` or `DCL_Waypoint_Light_A`) projected onto the shrine's face. | `Levels/<level>/Decals/` |
| Story fact | `DB_WaypointInfo(group, id, shrine, arrival point)` | a story goal |
| Name | A translated-string key named after the waypoint id, pointing at the name's localisation handle | `Mods/<mod>/Localization/*.lsf` and `Localization/<Language>/*.loca` |

The game's story script `_Waypoints` (in the Shared module) does everything else. When a `DB_WaypointInfo` fact is added it registers the waypoint for the map; it unlocks a waypoint when the shrine reports a player nearby or a player uses it; it opens the travel window; it teleports the party; and it locks waypoints, one by one or a whole group at once. The game locks a whole group when the story leaves an act (`Act1` and `Act1b` when Act 2 starts, `Act2` when Act 3 starts), so the group must match the level.

## What the mod adds

- One shrine, arrival point and rune per waypoint, generated from `waypoints.json` (see below).
- One story goal, `NotEnoughWaypoints.txt`:
  - its INIT section adds a `DB_WaypointInfo` fact per waypoint, and the Arcane Tower to the game's list of Underdark waypoints (`DB_UND_BroodingSpovereign_UnderdarkWaypoints`), so that Sovereign Glut follows the party there;
  - a rule registers the waypoints once more when gameplay first starts (see *Existing saves*);
  - a rule locks the Hollow whenever the game locks its own Emerald Grove waypoint (`PROC_LockWaypointForAll("WAYP_DEN_Camp")`, when the druids seal the Grove), so it never leads past the barrier.
- The names, in `Localization/English/NotEnoughWaypoints.loca`. The file name matters: a mod file called `english.loca` would replace the game's own and remove every English text in the game, so `pack.ps1` refuses to build a pak with anything but `NotEnoughWaypoints.loca` in it.

The mod replaces none of the game's files and needs no Script Extender.

## Existing saves

The goal has no parent goal (no `ParentTargetEdge`). A goal like that starts as soon as the story does, including when a save that was made without the mod is loaded, so its INIT section adds the waypoints to that save.

Starting first has one catch: the goal may start before the game's `_Waypoints` goal is running, and that goal registers a waypoint for the map only at the moment its `DB_WaypointInfo` fact is added. So the mod's own rule registers its waypoints once more on the first `LevelGameplayStarted`, and remembers that it did (`DB_NEW_WAYP_Registered`). Whichever order the goals start in, every waypoint is registered.

## Placement

A waypoint is only as good as where it stands. The checks in `tools/waypoints.py` are measured on the game's own 38 waypoints, and run against two kinds of game data that `tools/extract_game_data.py` reads from your installation:

- **The navigation grid** (`Levels/<level>/Ai/aigrid.data`), read by `tools/navgrid.py`. It covers each level in 0.5 m cells and stores, per cell, the height of every walkable surface and whether something stands on it. Tiles overlap where a place has several floors (the storeys of a tower, a bridge over a road).
- **The placed objects** of the level: characters, items, props and triggers, with their positions.

For every waypoint `tools/build_waypoints.py` checks:

| Check | Why |
|---|---|
| Free floor under the arrival point, within 15 cm of its height | the party lands on the floor, not in it or above it |
| The 25 cells within 1 m of the arrival point are all free | room for the whole party |
| Free floor under the whole shrine (2.4 m by 0.25 m), varying by at most 30 cm, and the shrine base at most 20 cm under the lowest point | it stands on the floor: not floating, not on a step edge, not over a drop |
| No other floor up to 3.3 m above the shrine or the arrival point | no balcony or upper storey cutting through it |
| Walkable floor all the way between the arrival point and the shrine | no wall in between |
| No character, item or prop of the game's within 2.2 m of the shrine or 1.5 m of the arrival point | nothing clips into it, and it blocks no one |
| A warning for a story point (where scripts send characters) under the shrine | it would stand in their way |
| No clash with the game's waypoint ids, names or object GUIDs | the map list stays readable; nothing is overwritten |

The shrine faces its arrival point, and the rune is placed the way the game places it: 1.5 m up the shrine, turned -90 degrees about the shrine's width so that it lies on its face. The tests compare this with the game's own shrines.

What the checks cannot see: decoration that is not in the navigation grid or the object lists, light, and how the spot looks. That is what testing in game is for.

## Building

`pack.ps1` stages `Mods/NotEnoughWaypoints/` and `Localization/`, converts the generated `.lsx` files to the binary `.lsf` the game loads and the names from `.xml` to `.loca`, packs everything with LSLib's `Divine.exe`, and then lists the pak: every expected file must be there, nothing else may be, and no unconverted source may slip in. It writes `info.json` for the mod managers and the release zip.
