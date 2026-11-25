# Contributing

Thanks for helping. The most useful contributions are:

1. **Placement reports**: a waypoint that floats, sinks into the floor, clips into something, stands in the way, or an arrival point that puts the party somewhere awkward. Use the *Placement problem* issue form and attach a screenshot.
2. **Waypoint ideas**: a place you keep walking back to that is far from any waypoint. Use the *Waypoint idea* form, or open a pull request.
3. **Code and documentation**: bug fixes and tooling.

Please read the [Code of Conduct](CODE_OF_CONDUCT.md) first.

## The one rule: verify, don't guess

Every position comes from the game's own data, never from memory or a screenshot estimate: the tools read the navigation grid and the placed objects of each level from your installation, and `tools/build_waypoints.py` checks every waypoint against them. Say in your pull request how you checked a new spot, and whether you saw it in game.

## Setting up

| You want to | You need |
|---|---|
| Change the tools or the documentation and run the tests | Python 3.10+ (any OS, nothing to install) |
| Add or move a waypoint | Windows, Baldur's Gate 3, [LSLib ExportTool](https://github.com/Norbyte/lslib/releases) (`Divine.exe`) |
| Change a story script, or look into a save | the above; the full ExportTool (`StoryCompiler.exe` and `StoryDecompiler.exe` sit next to `Divine.exe`) |
| Build and test the `.pak` files in game | the above |

On Windows the commands below use the `py` launcher; use `python` elsewhere.

## Adding or moving a waypoint

```powershell
# 1. Read the levels from your install (once per game patch, and for every level you work in):
#    their sub-levels, walls, trigger volumes and how far everything reaches, and the story.
#    Takes a few minutes.
#    Writes tools/.cache/ (git-ignored; never commit it).
py tools/extract_game_data.py --levels WLD_Main_A,SCL_Main_A,BGO_Main_A,CTY_Main_A

# 2. Find the place: who stands there, what the floor looks like.
py tools/survey.py find SCL_Main_A "Vendor"
py tools/survey.py map SCL_Main_A -154 21.4 -171

# 3. Let the survey suggest places that pass every check: runes on walls (in and against
#    buildings), or boulders (in the open). --all also lists what stops the rest.
py tools/survey.py walls CTY_Main_A -27 30.6 765
py tools/survey.py spots SCL_Main_A -154 21.4 -171
py tools/survey.py check SCL_Main_A -156.5 -170.75 -154.75 -170.75 --y 21.4
py tools/survey.py map SCL_Main_A -155 21.4 -171 --try -156.5 -170.75 -154.75 -170.75

# 4. Add the entry to waypoints.json (walls and spots print one with fresh GUIDs).

# 5. Check it and regenerate the mod files (commit them with your change). A new waypoint, or one
#    that changes group or nextTo, also needs the story it follows recorded (story_baseline.json).
py tools/build_waypoints.py
py tools/build_waypoints.py --accept-story

# 6. Review everything around it: what each check found, the story's regions it stands in,
#    and the objects nearby with the sub-level each comes from.
py tools/survey.py report NEW_WAYP_MOO_MainFloor

# 7. Compile the story with the game's, run the tests, and try it in game.
py tools/check_story.py
py -m unittest discover -s tests
.\pack.ps1 -Install
```

### waypoints.json

| Field | Meaning |
|---|---|
| `id` | `NEW_WAYP_<AREA>_<Name>`, with the game's area code (`DEN` Emerald Grove, `UND` Underdark, `GOB` goblin camp, `MOO` Moonrise Towers, `WYR` Rivington and Wyrm's Rock, `LOW` Lower City). Saves store unlocked waypoints by id, and the uninstaller takes them out by id, so **a released id never changes**. |
| `name` | What the map shows. Plain ASCII, at most 40 characters, and not a name the game already uses. Use the game's own name for the place where it has one. |
| `where` | A sentence for people: where it is, who is near. It is copied into the story script as a comment. |
| `level`, `group` | The level the waypoint is in, and the act group that goes with it (`WLD_Main_A` Act1, `SCL_Main_A` Act2, `BGO_Main_A` Act3, `CTY_Main_A` Act3b). The story locks a whole group when it leaves that act. |
| `nextTo` | The id of the game's own waypoint that players walk from today (the README's table names it). The patch-day check watches what the story does with it. |
| `handle` | The localisation handle of the name. New ones come from `survey.py spots`. |
| `style` | `wall` for the rune on a wall the game already has (in and against buildings), or `boulder` (the default) for the Blighted Village boulder and rune (in the open). |
| `shrine.position` | Where the (invisible) shrine stands: for a rune on a wall, on the wall's face; for a boulder, where the boulder's front meets the floor. Its height is the floor's plus 2.6 cm. `survey.py` works these out. |
| `shrine.yaw` | The way the rune faces. Needed for a rune on a wall (the way the wall faces); a boulder turns its rune towards the arrival point unless this says otherwise. |
| `trigger.position` | The arrival point, on the floor. |
| `trigger.yaw` | Optional. The arrival point's turn, in degrees. Without it, its +z points at the shrine, as the game turns most of its own. |
| `trigger.camera` | Optional. The camera's direction on arrival (`Angle`), whole degrees from 0 to 359, or -1 to leave the camera as it is. Without it, the camera keeps the relation most of the game's own waypoints keep (see `docs/ARCHITECTURE.md`, *Arrival*); set it after a look in game to frame what players come for. |
| `decal.style` | `dark` (Acts 1 and 2, cellars and caves) or `light` (Baldur's Gate streets), as the game does. |
| `rock.style` | A boulder's colour: `grey`, `grey_wet`, `grey_moss`, `brown` or `brown_moss`. One mesh, different materials, so any of them fits. A rune on a wall has no `rock`. |
| `shrine.guid`, `trigger.guid`, `decal.guid`, `rock.guid` | New random GUIDs. Never reuse or change a released one. |
| `placement` | Optional, 1 if missing. **Raise it by one whenever a released waypoint moves**: the story then moves the shrine and the arrival point in saves made before, once, when the level is loaded. |
| `retired` | GUIDs a released waypoint no longer uses (the boulder of a waypoint that moved onto a wall). Kept so that they are never used again. |
| `accept` | Check results (a piece of their text, such as an object's name) that were looked at and judged harmless, best in game. They are reported as warnings instead of errors. |
| `underdark` | `true` for a waypoint in the Underdark, so that Sovereign Glut follows the party there. |
| `lockWith` | The id of one of the game's waypoints. Whenever the story locks that one, this one is locked too (the Hollow uses `WAYP_DEN_Camp`, for the Grove's lockdown). |

How the pieces fit together, and what the checks look for, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Choosing a good spot

- Somewhere players go back to, and far from the nearest waypoint.
- Built like the game's own: in a town, a fortress or a building, the rune on a wall; a boulder only in the open or in a cave, where the game uses rocks too.
- Out of the way: a boulder is 3 m wide and reaches 2.3 m behind the shrine, so keep it out of doorways and paths (draw it with `map --try`; the checks cannot see walkways) and off spots where the story sends characters (the checks warn about those).
- Where travelling in cannot skip the story. A waypoint behind a door or barrier that the story keeps shut lets players walk around it, so use `lockWith`, or choose another spot.
- Not in a place where fast travel is blocked for the whole visit (a danger zone such as the House of Hope): players could travel in, but not out again.

## After a game patch

```powershell
py tools/extract_game_data.py                 # read the levels and the story of the new patch
py tools/build_waypoints.py                   # check every waypoint; "patch day:" warnings list what the story
                                              # now does differently with what the waypoints follow
py tools/check_story.py                       # compile the story with the new patch's
py tools/build_waypoints.py --accept-story    # once each change was looked at: record the story for this patch
```

Look at each "patch day" change in the goal it names. A new lock of the game's waypoint next to one of ours, or of its act, is the usual one: if ours should follow it, give it `lockWith`. Commit `story_baseline.json` with the rest; its `patch` says which patch the waypoints were last checked on.

## Code guidelines

- **Python 3.10+, standard library only.** The tools must run in CI without the game files: everything that needs the cache skips with a note when it is missing.
- **Generated files are never edited by hand.** Everything under `Mods/NotEnoughWaypoints/` except `meta.lsx`, the uninstaller's story, and `Localization/` come from `waypoints.json`. CI fails if they are out of date.
- **Every story script is compiled with the game's** (`py tools/check_story.py`) before it ships. Whatever the mod's story writes into one of the game's databases, the uninstaller's story must take out again: a test fails until it does.
- **The game's layout is the reference.** The level files follow the game's own (same attributes, same header); if you change the generator, compare its output with the game's files.
- The navigation grid format is not documented; [`tools/navgrid.py`](tools/navgrid.py) explains what is known. If a game patch changes it, the reader stops with an error instead of guessing.
- [`tools/gamefiles.py`](tools/gamefiles.py) reads the level and story files; it needs no game files, so its tests run in CI on small samples written in the same layout. What it assumes about the files (a box trigger's size, how a prism rises, the order a tile's rotation is written in) was checked against where the game's own characters stand; [docs/ROADMAP.md](docs/ROADMAP.md) lists those facts under *Notes for contributors*.

## Testing in game

- `.\pack.ps1 -Install` copies the pak to your BG3 `Mods` folder; enable it in your mod manager once.
- Check a fresh save and a save that is far into the story: the waypoints must appear in both.
- Look at the waypoint from a few sides: the rune whole on its wall or boulder, nothing of it on the floor, on furniture or on the far side of the wall. Travel to it with a full party.
- A waypoint that moved: load a save made before the move, in or near its level, and check that clicking the new rune opens the travel window and that the party arrives in front of it.
- The uninstaller, on a copy of a save where a waypoint of the mod is unlocked: `.\pack.ps1 -InstallUninstaller`, turn the mod off and the uninstaller on, load, and check that the waypoint left the travel list; save, and `py tools/inspect_save.py --latest` must find nothing of the mod. Turn the uninstaller off, load that save and save again: still nothing. Turn the mod back on: its waypoints return.

## Pull requests

- One topic per pull request.
- Fill in the template: what changed, how you verified it, and whether you tested it in game.
- `py tools/build_waypoints.py --check` (with the game cache for a waypoint change) and the tests must pass, and `py tools/check_story.py` for a change to a story script. CI runs the offline check and the tests.
- Add a line to `CHANGELOG.md` under *Unreleased*.
- Never rename a released waypoint id and never reuse a GUID.

## Releasing (maintainers)

1. Bump `Version64` in both `meta.lsx` files, the mod's and the uninstaller's (two places in each): they are released together, as one version. `build_waypoints.py --check --version X.Y.Z` checks it.
2. Move the *Unreleased* changelog entries under the new version.
3. `.\pack.ps1` (it compiles the story with the game's first) and smoke-test both paks in game: a new game and an existing save with the mod, then the uninstaller on a copy of that save (see *Testing in game*).
4. Tag `vX.Y.Z` and publish a GitHub release with both `dist/NotEnoughWaypoints-X.Y.Z.0.zip` and `dist/NotEnoughWaypointsUninstaller-X.Y.Z.0.zip` attached. Attach the zips you tested; do not rebuild them in between. `python tools/release_notes.py X.Y.Z` prints the changelog section for the release text.
5. Publishing the release runs [`nexus-release.yml`](.github/workflows/nexus-release.yml). It checks that the tag, `meta.lsx` and the attached zips agree, then sends the mod's zip to Nexus Mods as a new version of the main file, with the version's changelog section, and the uninstaller's as a new version of its optional file. It needs the repository secret `NEXUSMODS_API_KEY`, and `NEXUS_MOD_ID`, `NEXUS_FILE_ID` and `NEXUS_UNINSTALLER_FILE_ID` in the workflow: Nexus can only add versions to a file that exists, so the first version of each file is uploaded by hand (the uninstaller as an *Optional file*), and its IDs are copied in afterwards. Until then that file is only checked. Pre-releases are skipped.
6. The mod page text lives in [`.github/nexus/`](.github/nexus/README.md) (`description.bbcode`, `summary.txt`). The same run updates the page when that text changed since the previous release, after saving the old description as a run artifact (details in that README). Edit the page there, not on the website, or the next update overwrites the website edit. Images are still managed on Nexus by hand.
7. From the Actions tab the workflow can also be run by hand: *dry run* (the default: checks everything, sends nothing), *upload*, or *page only* (for example to correct the page without a new release; the ref can be `main`).

`Version64` encodes `major << 55 | minor << 47 | revision << 31 | build`; for example 1.0.0.0 is `36028797018963968`, 1.1.0.0 is `36169534507319296` and 1.2.0.0 is `36310271995674624`.
