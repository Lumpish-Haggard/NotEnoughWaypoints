<div align="center">

# Not Enough Waypoints

**Six new waypoints for Baldur's Gate 3, in the places you keep walking back to.**

![BG3 Patch 8](https://img.shields.io/badge/BG3-Patch%208-7a1f1f)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

[Download](../../releases/latest) ·
[Report a bug or a misplaced waypoint](../../issues/new/choose) ·
[What is planned](docs/ROADMAP.md) ·
[Contributing](CONTRIBUTING.md) ·
[Changelog](CHANGELOG.md)

</div>

> [!NOTE]
> **Version 1.2.1 fixes the four smeared runes from 1.1 and 1.2.** Underdark - Arcane Tower, Shattered Sanctum, Moonrise Towers - Main Floor and Guildhall now sit on boulders at clean new spots, and all six waypoints have been seen and checked in game on Patch 8 Hotfix 10. Existing saves update automatically when each level is loaded. **Not Enough Waypoints Uninstaller** (added in 1.2) takes the waypoints out of a save so that the mod can be removed in the middle of a playthrough: see [Removing the mod](#removing-the-mod). What comes next is in [what is planned](docs/ROADMAP.md).

---

Baldur's Gate 3 puts most of its waypoints at the edge of a place: outside the Emerald Grove, outside the goblin camp's temple, outside Moonrise Towers. The traders, quest givers and doors you keep coming back to are often a long walk further in. **This mod adds six waypoints where that walk is longest.**

Each one copies the game's own Blighted Village waypoint (the invisible shrine, the boulder in a colour that suits the place, and the rune projected onto its face), and works like the game's own: walk near one to unlock it, then travel to it from the map or any other waypoint.

## The waypoints

| Waypoint | Act | Where | Saves you |
|---|---|---|---|
| The Hollow | 1 | Emerald Grove: on the floor of the Hollow, against the ledge below Okta's and Auntie Ethel's stalls, across from Dammon's forge | the walk in from the game's *Emerald Grove Environs* waypoint, outside the gate |
| Underdark - Arcane Tower | 1 | Underdark: on the landing outside the tower's front door, backed against the cliff edge to the east | the walk from the nearest Underdark waypoint and up past the tower's turrets |
| Shattered Sanctum | 1 | Inside the temple: backed into the northwest corner of the central hall, south of Dror Ragzlin's doors | the walk from the game's *Goblin Camp* waypoint, outside, through the temple's entrance hall |
| Moonrise Towers - Main Floor | 2 | On the main floor, on the west edge of the central entrance hall beside the bazaar | the walk from the game's *Moonrise Towers* waypoint, outside, through the front doors |
| Open Hand Temple | 3 | Rivington: in the street in front of the temple, where the refugees beg | the walk up from the *Rivington* waypoint |
| Guildhall | 3 | Lower City: in the Guildhall's lower main hall, backed into the alcove on the south side | the walk through the sewers |

## Features

- **Built like the game's own**: each waypoint is a copy of the Blighted Village boulder and rune, in a colour that suits the place. Unlocked the same way: come near one, or use it.
- **They follow the story.** Like the game's own waypoints, each is locked with the rest of its act when the story moves on. The Hollow is also locked when the druids seal the Emerald Grove, at the same moment as the game's Grove waypoint, so it never gets you past the barrier.
- **Sovereign Glut comes along**: the Arcane Tower counts as an Underdark waypoint, so he follows the party there like he does between the game's Underdark waypoints.
- **New game or existing save**: the story picks the waypoints up when you load, and moves a waypoint that an update moved in a save made before it.
- **Safe to remove**: the uninstaller takes the waypoints out of a save before you remove the mod, the way the story locks a waypoint when its act ends.
- **No other mods needed.** The mod adds its own objects, one small story script and the waypoint names; it replaces none of the game's files.
- **Multiplayer**: waypoints unlock for the whole party, as usual.

## Requirements

| | |
|---|---|
| Baldur's Gate 3 | Patch 8. The waypoints are placed and checked against the Patch 8 Hotfix 10 game files. |

## Installation

1. Download `NotEnoughWaypoints-<version>.zip` from the [latest release](../../releases/latest).
2. Install it with your mod manager:
   - **BG3 Mod Manager**: import the zip, move *Not Enough Waypoints* to the active list, then save and export the load order.
   - **Vortex**: install the zip, enable it, deploy.
   - **Manual**: put `NotEnoughWaypoints.pak` in `%LOCALAPPDATA%\Larian Studios\Baldur's Gate 3\Mods\` and enable it in your mod manager.
3. Load a save and walk to one of the places above.

To take it out of a playthrough again, use the uninstaller: see [Removing the mod](#removing-the-mod).

## Using the waypoints

| To | Do this |
|---|---|
| Unlock one | Walk near the rune, or use it. |
| Travel | Use any waypoint, or the map's travel button, and pick it from the list. |
| Find one that disappeared | The story locks every waypoint of an act when it leaves that act, and the Hollow when the Emerald Grove is sealed. Locked waypoints leave the list, the game's own included. |

## Removing the mod

A save that has used the mod keeps its waypoints: in the story, and in the travel list of your party once you have unlocked one. Remove only the mod and they stay behind without their names and runes: a waypoint you unlocked stays in the travel list and leads nowhere, until the story locks its act. **Not Enough Waypoints Uninstaller** takes them out first.

1. Download `NotEnoughWaypointsUninstaller-<version>.zip`: on Nexus Mods it is under *Optional files*, on GitHub in the [latest release](../../releases/latest). Install it like the mod.
2. In your mod manager, turn **Not Enough Waypoints off** and **the uninstaller on** (BG3 Mod Manager: export the load order).
3. Load your save. The game says that Not Enough Waypoints is missing: carry on. Its waypoints are gone from the travel list.
4. **Save.**
5. Turn the uninstaller off. The next time you load that save, the game says once that the uninstaller is missing: carry on, and save again.

From the save in step 4 on, the mod's waypoints are out of that playthrough; only their ids stay in the game's own list of waypoints for the map, which the game has no way to drop. Saves made before it still have the waypoints; to remove the mod from one of those, repeat the steps with it.

| The uninstaller | |
|---|---|
| Locks every waypoint of the mod | the way the story locks a waypoint when its act ends: it leaves the travel list of every party that unlocked it |
| Takes them out of the story | the game's list of waypoints, the record of who unlocked each, and Sovereign Glut's list of Underdark waypoints |
| Leaves the rest to the game | the shrines, arrival points, runes and boulders come from the mod's files, and go with them |
| Does nothing while the mod is loaded | it only takes the waypoints out once the mod is gone, so loading both by mistake breaks nothing |

Changed your mind? Turn the mod back on (and the uninstaller off) and load your save: the mod adds its waypoints again, as in a save that never had them. Walk near one to unlock it.

## How the waypoints were placed

- **With the game's own data.** The game keeps a navigation grid for every level: where characters can stand, and how high the floor is. The tools in this repository read it from your installation, together with every object the game places and how far it reaches, and place every rune, boulder and arrival point with it. Nothing is a guessed coordinate.
- **Copied from the game's own waypoints.** In the game, the waypoint you use is an invisible object; what you see is the rune projected onto something next to it: in towns and buildings a wall that is already there, in the open a rock set up by hand. On a wall, these runes have the turn, height and size of the game's own wall runes (the tests compare them with the Lower City Central Wall and Moonrise Towers waypoints), and stand on the wall's face as measured from its tiles. In the open, they copy the Blighted Village waypoint exactly (the invisible object, the boulder at the same size and angle, the rune 1.5 m up its face), and the tests check that the copy gives back the game's own boulder and rune.
- **Checked on every change.** [`tools/build_waypoints.py`](tools/build_waypoints.py) checks each waypoint against the game files, including the sub-levels the game builds its places from (the Guildhall, Rivington, the goblin camp and the Emerald Grove are each one), and against the box each object fills. For a rune on a wall: a wall at least 0.3 m thick behind the whole rune, nothing standing in front of it, no door or window along it, and the floor clear of it. For a boulder: free floor under all of it (it may sit into a rise behind it, as the game's rocks do, but never over a drop), nothing of the game's inside it, and no wall, floor or ceiling through it. For both: room for the party at the arrival point and nothing standing there, a clear way to the waypoint, the story's travel zones it stands in, and no clash with the game's own waypoint names or IDs.
- **What it cannot see**: the exact shape of each object (it knows the box each fills, which is loose around a rock or a tree), and how the spot looks. Only the game shows that, so please [report](../../issues/new/choose) anything that looks wrong.

## Compatibility

- **Mods that add their own waypoints** work alongside it.
- **Mods that change how waypoints work** (the game's `_Waypoints` story script) are fine as long as they keep the game's waypoint table, `DB_WaypointInfo`.
- **Mods that rebuild these areas or move their characters**: a waypoint may end up in the way. Please tell us which mod.
- **Multiplayer**: unlocks are shared by the party, as in the unmodded game.

## Troubleshooting

<details>
<summary>The new waypoints are not on the map</summary>

Like the game's own, each one only appears after you discover it: walk near its rune. If you are standing next to it and nothing happens, check that the mod is active and that the load order was exported (BG3 Mod Manager: *Export Order to Game*).
</details>

<details>
<summary>A waypoint disappeared from the list</summary>

The story locked it, together with the game's own waypoints of that act (or, for the Hollow, when the Emerald Grove was sealed). That is intended: it is how the game keeps you from travelling back into an act that is over.
</details>

<details>
<summary>I removed the mod and a waypoint is still in the travel list</summary>

It was removed without the uninstaller. Load that save once with the uninstaller (see [Removing the mod](#removing-the-mod), from step 1), save, and remove the uninstaller. It also cleans up a save that the mod was removed from long ago.
</details>

<details>
<summary>The uninstaller did nothing</summary>

It only works while Not Enough Waypoints itself is off: with both loaded, it leaves everything as it is. Turn the mod off, check that the uninstaller is on in the exported load order, and load the save again.
</details>

<details>
<summary>A waypoint floats, sinks into the floor, blocks a path, or its rune is not on its wall</summary>

Please use the [placement form](../../issues/new/choose) and attach a screenshot.
</details>

## Building from source

On Windows, with BG3 and [LSLib](https://github.com/Norbyte/lslib/releases) (ExportTool) installed:

```powershell
py tools/extract_game_data.py       # read the levels the waypoints are in from your BG3 install (local cache, not committed)
py tools/build_waypoints.py         # check waypoints.json against the game and regenerate the mod files
py tools/check_story.py             # compile the story of the mod and the uninstaller with the game's own
py -m unittest discover -s tests    # run the tests (no game files needed)
.\pack.ps1                          # dist/: the pak and the zip of the mod and of the uninstaller
py tools/inspect_save.py --latest   # what your newest save holds of the mod (reads a copy of it)
```

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Project layout

```
waypoints.json                    the waypoints: name, act, and where the shrine and the arrival point stand
Mods/NotEnoughWaypoints/          the mod (what goes into the .pak)
  meta.lsx
  Globals/<level>/Items/          invisible shrines      )
  Globals/<level>/Triggers/       the arrival points     )
  Levels/<level>/Scenery/         the boulders           )  generated from waypoints.json
  Levels/<level>/Decals/          the runes              )
  Story/RawFiles/Goals/           the story script       )
  Localization/                   waypoint id -> name    )
Mods/NotEnoughWaypointsUninstaller/   the uninstaller (its own .pak)
  meta.lsx
  Story/RawFiles/Goals/           takes the waypoints out of a save (generated from waypoints.json)
Localization/English/             the English names (generated)
tools/            game-data extraction, navigation-grid reader, placement checks, survey, generator,
                  story check, save inspector, release helpers
tests/            tests for the tools
docs/             how a waypoint works, and what is planned
pack.ps1          build and verify the two .pak files and their release zips
```

## Contributing

A misplaced waypoint is the most useful report, with a screenshot. Ideas for new waypoints are welcome too, and so are pull requests. Start with [CONTRIBUTING.md](CONTRIBUTING.md). By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Credits

- **Norbyte**: [LSLib](https://github.com/Norbyte/lslib), which reads and writes the game's files, builds the paks, and compiles and reads the story.
- **Larian Studios**: Baldur's Gate 3.

This project is not affiliated with or endorsed by Larian Studios.

## License

[MIT](LICENSE). Baldur's Gate 3 names, places and identifiers belong to Larian Studios. This repository contains no game data and no game art: the shrines, boulders, runes and arrival points are the game's own templates, referenced by ID. The reference data is read locally: `tools/extract_game_data.py` reads it from your own installation into a local cache that is never committed.
