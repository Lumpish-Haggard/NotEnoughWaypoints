<div align="center">

# Not Enough Waypoints

**Six new waypoint shrines for Baldur's Gate 3, in the places you keep walking back to.**

![BG3 Patch 8](https://img.shields.io/badge/BG3-Patch%208-7a1f1f)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

[Download](../../releases/latest) ·
[Report a bug or a misplaced shrine](../../issues/new/choose) ·
[Contributing](CONTRIBUTING.md) ·
[Changelog](CHANGELOG.md)

</div>

> [!NOTE]
> **First release.** Every shrine was placed with the game's own navigation data and checked against everything the game puts nearby. If one still floats, clips into something or stands in the way, please [report it](../../issues/new/choose) with a screenshot.

---

Baldur's Gate 3 puts most of its waypoints at the edge of a place: outside the Emerald Grove, outside the goblin camp's temple, outside Moonrise Towers. The traders, quest givers and doors you keep coming back to are often a long walk further in. **This mod adds six waypoint shrines where that walk is longest.**

They are the game's own waypoint shrines, with the game's rune on them, and they work like the game's own: walk near one to unlock it, then travel to it from the map or any other waypoint.

## The waypoints

| Waypoint | Act | Where | Saves you |
|---|---|---|---|
| The Hollow | 1 | Emerald Grove: on the floor of the Hollow, below Okta's and Auntie Ethel's stalls, across from Dammon's forge | the walk in from the game's *Emerald Grove Environs* waypoint, outside the gate |
| Underdark - Arcane Tower | 1 | Outside the Arcane Tower's front door, at the top of the stairs | the walk from the nearest Underdark waypoint and up past the tower's turrets |
| Shattered Sanctum | 1 | Inside the temple, east of the spider pits, between Dror Ragzlin's throne room, Minthara and True Soul Gut | the walk from the game's *Goblin Camp* waypoint, outside, through the temple's entrance hall |
| Moonrise Towers - Main Floor | 2 | Inside the front doors, next to Lann Tarv's stall | the walk from the game's *Moonrise Towers* waypoint, outside, through the front doors |
| Open Hand Temple | 3 | Rivington: in the street outside the Open Hand Temple, a few steps from the Circus of the Last Days | the walk up from the *Rivington* waypoint |
| Guildhall | 3 | Lower City: in Nine-Fingers Keene's hall | the walk through the sewers |

## Features

- **The game's own shrines**: the same model and rune as every other waypoint, unlocked the same way (come near one, or use it).
- **They follow the story.** Like the game's own waypoints, each is locked with the rest of its act when the story moves on. The Hollow's shrine is also locked when the druids seal the Emerald Grove, at the same moment as the game's Grove waypoint, so it never gets you past the barrier.
- **Sovereign Glut comes along**: the Arcane Tower counts as an Underdark waypoint, so he follows the party there like he does between the game's Underdark waypoints.
- **New game or existing save**: the story picks the waypoints up when you load.
- **No other mods needed.** The mod adds its own objects, one small story script and the waypoint names; it replaces none of the game's files.
- **Multiplayer**: waypoints unlock for the whole party, as usual.

## Requirements

| | |
|---|---|
| Baldur's Gate 3 | Patch 8. The shrines are placed and checked against the Patch 8 Hotfix 10 game files. |

## Installation

1. Download `NotEnoughWaypoints-<version>.zip` from the [latest release](../../releases/latest).
2. Install it with your mod manager:
   - **BG3 Mod Manager**: import the zip, move *Not Enough Waypoints* to the active list, then save and export the load order.
   - **Vortex**: install the zip, enable it, deploy.
   - **Manual**: put `NotEnoughWaypoints.pak` in `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\` and enable it in your mod manager.
3. Load a save and walk to one of the places above.

Removing it in the middle of a playthrough is not recommended: once a save has the waypoints, they are part of its story. The save still loads without the mod (the game warns that a mod is missing), but waypoints you unlocked may stay on the map without working.

## Using the waypoints

| To | Do this |
|---|---|
| Unlock one | Walk near the shrine, or use it. |
| Travel | Use any waypoint, or the map's travel button, and pick it from the list. |
| Find one that disappeared | The story locks every waypoint of an act when it leaves that act, and the Hollow when the Emerald Grove is sealed. Locked waypoints leave the list, the game's own included. |

## How the shrines were placed

- **With the game's own data.** The game keeps a navigation grid for every level: where characters can stand, and how high the floor is. The tools in this repository read it from your installation and place every shrine and arrival point on it. Nothing is a guessed coordinate.
- **Like the game's own shrines.** All 38 of the game's waypoints were measured: the shrine stands upright with its rune facing the arrival point, about 2 m away on free floor, and the rune sits 1.5 m up its face. These six follow the same rules.
- **Checked on every change.** [`tools/build_waypoints.py`](tools/build_waypoints.py) checks each waypoint against the game files: flat free floor under the whole shrine, room for the party around the arrival point, nothing of the game's (characters, items, props) within reach, no floor overhead, a clear way between the arrival point and the shrine, and no clash with the game's own waypoint names or IDs.
- **What it cannot see**: decoration that is not part of the navigation grid, and how the spot looks. Only the game shows that, so please [report](../../issues/new/choose) anything that looks wrong.

## Compatibility

- **Mods that add their own waypoints** work alongside it.
- **Mods that change how waypoints work** (the game's `_Waypoints` story script) are fine as long as they keep the game's waypoint table, `DB_WaypointInfo`.
- **Mods that rebuild these areas or move their characters**: a shrine may end up in the way. Please tell us which mod.
- **Multiplayer**: unlocks are shared by the party, as in the unmodded game.

## Troubleshooting

<details>
<summary>The new waypoints are not on the map</summary>

Like the game's own, each one only appears after you discover it: walk near the shrine. If you are standing next to it and nothing happens, check that the mod is active and that the load order was exported (BG3 Mod Manager: *Export Order to Game*).
</details>

<details>
<summary>A waypoint disappeared from the list</summary>

The story locked it, together with the game's own waypoints of that act (or, for the Hollow, when the Emerald Grove was sealed). That is intended: it is how the game keeps you from travelling back into an act that is over.
</details>

<details>
<summary>A shrine floats, sinks into the floor or blocks a path</summary>

Please use the [placement form](../../issues/new/choose) and attach a screenshot.
</details>

## Building from source

On Windows, with BG3 and [LSLib](https://github.com/Norbyte/lslib/releases) (ExportTool) installed:

```powershell
py tools/extract_game_data.py       # read the levels the waypoints are in from your BG3 install (local cache, not committed)
py tools/build_waypoints.py         # check waypoints.json against the game and regenerate the mod files
py -m unittest discover -s tests    # run the tests (no game files needed)
.\pack.ps1                          # dist/NotEnoughWaypoints.pak and dist/NotEnoughWaypoints-<version>.zip
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project layout

```
waypoints.json                    the waypoints: name, act, and where the shrine and the arrival point stand
Mods/NotEnoughWaypoints/          the mod (what goes into the .pak)
  meta.lsx
  Globals/<level>/Items/          the shrines            )
  Globals/<level>/Triggers/       the arrival points     )
  Levels/<level>/Decals/          the runes              )  generated from waypoints.json
  Story/RawFiles/Goals/           the story script       )
  Localization/                   waypoint id -> name    )
Localization/English/             the English names (generated)
tools/            game-data extraction, navigation-grid reader, placement checks, survey, generator, release helpers
tests/            tests for the tools
docs/             how a waypoint works
pack.ps1          build and verify the .pak and the release zip
```

## Contributing

A misplaced shrine is the most useful report, with a screenshot. Ideas for new waypoints are welcome too, and so are pull requests. Start with [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Credits

- **Norbyte**: [LSLib](https://github.com/Norbyte/lslib), which reads and writes the game's files and builds the pak.
- **Larian Studios**: Baldur's Gate 3.

This project is not affiliated with or endorsed by Larian Studios.

## License

[MIT](LICENSE). Baldur's Gate 3 names, places and identifiers belong to Larian Studios. This repository contains no game data and no game art: the shrines, runes and arrival points are the game's own templates, referenced by ID. The reference data is read locally: `tools/extract_game_data.py` reads it from your own installation into a local cache that is never committed.
