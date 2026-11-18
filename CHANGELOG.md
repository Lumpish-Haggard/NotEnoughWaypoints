# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

Nothing yet.

## [1.2.1] - 2026-11-18

Fixes the four waypoints whose runes appeared smeared in 1.1 and 1.2 (Underdark - Arcane Tower, Shattered Sanctum, Moonrise Towers - Main Floor and Guildhall). All six waypoints have been seen and checked in game on Patch 8 Hotfix 10. Existing saves update automatically when each level is loaded.

### Fixed
- **Four smeared wall runes moved onto boulders at clean new places.** Repairing the tile reader showed that none of those four public areas has an unobstructed, decal-receiving tile wall (the Arcane Tower wall has `RecieveDecal="False"`, and the other three rooms are built of large props or lined with wainscots, furniture and archways). All four now use the Blighted Village boulder arrangement at newly verified places clear of doors, walkways and furniture (with prop-built wall runes left for 1.3):
  - **Underdark - Arcane Tower**: on the landing outside the tower's front door, backed against the cliff edge to the east.
  - **Shattered Sanctum**: backed into the northwest corner of the central hall, south of Dror Ragzlin's doors.
  - **Moonrise Towers - Main Floor**: on the west edge of the central entrance hall beside the bazaar.
  - **Guildhall**: in the lower main hall, backed into the alcove on the south side.
- **Tile reader and wall checks** (`tools/gamefiles.py`, `tools/extract_game_data.py`, `tools/waypoints.py`, `tools/survey.py`): reads `QRotate` (quaternion rotations used by about a third of the game's tiles), `ScaleZ` (length stretch along local x), `RecieveDecal` and tileset visual names (cache version 4). Rejects doorway (`_D_Piece`), window (`_W_Piece`) and broken tile pieces, non-decal walls, loose wall boxes with walkable floor behind them and corrupted roof bounds, with an offline regression test against the game's own Lower City Central Wall and Moonrise Towers wall tiles.

## [1.2.0] - 2026-11-18

The mod is now safe to remove, moved up from 1.4 on the [roadmap](docs/ROADMAP.md). The uninstaller was designed from a save made with the mod and compiled against the game's own story, but has not been tried in game yet: if it leaves anything behind, please report it.

### Added
- **Not Enough Waypoints Uninstaller**, a small second file that takes the waypoints out of a save so that the mod can be removed in the middle of a playthrough: load the save once with it in place of the mod, save, then remove it too. It locks every waypoint of the mod the way the story locks a waypoint when its act ends, which takes it out of the travel list of every party that unlocked it, and then takes the waypoints out of the story: the game's list of waypoints, the record of who unlocked each, Sovereign Glut's list of Underdark waypoints and the story's travel records. It does nothing while the mod itself is loaded, so loading both by mistake breaks nothing. It also cleans up a save that the mod was removed from without it.
- `tools/inspect_save.py`: what a save holds of the mod, read from a copy of it: the mods it was made with, the story's goals and facts, the travel list of each party, the waypoints registered for the map, and the shrines and arrival points among its objects. The uninstaller was designed from what it found in a save made with the mod.
- `tools/check_story.py`: compiles the story of the mod and of the uninstaller together with the game's own, with LSLib's StoryCompiler, and reports every problem they add: as the mod alone, as the uninstaller in its place, and as both loaded together. The game ships no story header, so the check writes one from the game's compiled story. `pack.ps1` runs it before packing.

### Changed
- `pack.ps1` builds and checks two packages, the mod and the uninstaller, each with its own zip.
- The release workflow checks the uninstaller's zip too, and publishes it on Nexus Mods as an optional file once that file exists.

## [1.1.0] - 2026-11-18

Five of the six waypoints move to where they were meant to be. The new places pass every check of the tools, which now read the whole level, but have not been seen in game yet: if one looks wrong, please report it with a screenshot. What comes next is in the [roadmap](docs/ROADMAP.md).

### Changed
- **Five of the six waypoints move** to where they were meant to be, and four of them are now **the rune on a wall**, as the game does in and against buildings, with nothing added:
  - **Guildhall**: from Nine-Fingers Keene's private office, where its boulder took in a cabinet, to the wall beside the bar in the main hall, where her visitors wait.
  - **Open Hand Temple**: from inside the temple's main hall, where its boulder took in a pile of books, to the street in front of the temple, where the refugees beg. It keeps a boulder, now a mossy one like the rocks around it, as the game's own Rivington waypoint stands on a rock.
  - **Moonrise Towers - Main Floor**: from in front of Lann Tarv's stall, where its boulder cut into the stall's frame and into rubble that the assault brings, to a wall of the main floor, east of the bazaar.
  - **Underdark - Arcane Tower**: from the end of the ledge, where its boulder took in a stone bench, to the tower's own wall, a few steps from its front door.
  - **Shattered Sanctum**: from against the pillar east of the spider pits, where its boulder was pushed into the abbey wall behind it, to that wall.
  - **The Hollow** stays where it is.
- **Saves made with 1.0 are moved too.** The first time a moved waypoint's level is loaded, the story puts its shrine (what you click) and its arrival point where this version has them, the way the game's own hotfixes move objects in existing saves.

### Added
- **The tools see the whole level.** `extract_game_data.py` now also reads the sub-levels the game builds its places from (the Guildhall, Rivington, the goblin camp, the Emerald Grove and about 120 more in the Act 1 level alone), the tiles of walls, floors and ceilings, the volume of every trigger, the size of every decal, and what the story does with waypoints and travel: every lock and unlock, the danger zones and the blocked waypoint zones. It checks its own arithmetic by counting how many of each sub-level's characters and items stand on the floor.
- **How far everything reaches.** The bounds of every visual in the game's resource banks give each item, prop and tile the box it fills, and the checks compare boxes instead of positions.
- **Runes on walls** (`"style": "wall"`): the rune turned and raised like the game's own wall runes, on a wall's face measured from its tiles, with checks of their own: a wall at least 0.3 m thick behind the whole rune, nothing standing in front of it, no door or window along it, and the floor clear of it.
- **New checks** for both kinds: the game's furniture, items and props from the sub-levels, walls and ceilings through a boulder, script points next to the arrival point, and the story's travel zones a waypoint stands in.
- `survey.py walls` (runes on walls near a point), `survey.py report <id>` (everything around a waypoint, for review), and walls on `survey.py map`.
- In `waypoints.json`: `placement` (raised when a released waypoint moves), `retired` (GUIDs never to be used again) and `accept` (check results looked at and judged harmless).
- The roadmap: what comes after 1.0, and what the review of 1.0 found.

## [1.0.0] - 2026-11-17

First public release.

### Added
- **Six waypoints**, each built like the game's own waypoint at the Blighted Village: a boulder with the game's waypoint rune on it.
  - **The Hollow** (Act 1): on the floor of the Hollow in the Emerald Grove, against the ledge below Okta's and Auntie Ethel's stalls, across from Dammon's forge.
  - **Underdark - Arcane Tower** (Act 1): outside the tower's front door, at the end of the ledge beside the landing.
  - **Shattered Sanctum** (Act 1): inside the goblin camp's temple, against a pillar east of the spider pits.
  - **Moonrise Towers - Main Floor** (Act 2): inside the front doors, in front of Lann Tarv's stall.
  - **Open Hand Temple** (Act 3): in the street outside the temple in Rivington, next to the Circus of the Last Days.
  - **Guildhall** (Act 3): in Nine-Fingers Keene's hall.
- They work like the game's own waypoints: walk near one to unlock it, and the story locks it with the rest of its act when it leaves that act.
- The Hollow is locked when the druids seal the Emerald Grove, together with the game's Grove waypoint.
- Sovereign Glut follows the party to the Arcane Tower, which counts as an Underdark waypoint.
- Works in a new game or an existing save. No other mods needed.
- Developer tools: game-data extraction from your own install, a reader for the game's navigation grid, a survey tool that finds and checks places for new waypoints, a generator that writes every mod file from `waypoints.json` and checks each waypoint against the game, tests, and a packager that verifies the pak and builds the release zip.
- GitHub project files: contributing guide, code of conduct, security policy, issue forms, pull request template, CI, and a workflow that publishes releases on Nexus Mods.

[Unreleased]: ../../compare/v1.2.1...HEAD
[1.2.1]: ../../compare/v1.2.0...v1.2.1
[1.2.0]: ../../compare/v1.1.0...v1.2.0
[1.1.0]: ../../compare/v1.0.0...v1.1.0
[1.0.0]: ../../releases/tag/v1.0.0
