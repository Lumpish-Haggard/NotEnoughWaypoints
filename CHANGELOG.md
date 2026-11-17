# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

Nothing yet.

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

[Unreleased]: ../../compare/v1.1.0...HEAD
[1.1.0]: ../../compare/v1.0.0...v1.1.0
[1.0.0]: ../../releases/tag/v1.0.0
