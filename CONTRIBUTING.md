# Contributing

Thanks for helping. The most useful contributions are:

1. **Placement reports**: a shrine that floats, sinks into the floor, clips into something, stands in the way, or an arrival point that puts the party somewhere awkward. Use the *Placement problem* issue form and attach a screenshot.
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
| Build and test the `.pak` in game | the above |

On Windows the commands below use the `py` launcher; use `python` elsewhere.

## Adding or moving a waypoint

```powershell
# 1. Read the levels from your install (once per game patch, and for every level you work in).
#    Writes tools/.cache/ (git-ignored; never commit it).
py tools/extract_game_data.py --levels WLD_Main_A,SCL_Main_A,BGO_Main_A,CTY_Main_A

# 2. Find the place: who stands there, what the floor looks like.
py tools/survey.py find SCL_Main_A "Vendor"
py tools/survey.py map SCL_Main_A -154 21.4 -171

# 3. Let the survey suggest spots that pass every check, then try your own.
py tools/survey.py spots SCL_Main_A -154 21.4 -171
py tools/survey.py check SCL_Main_A -157.75 -170.75 -155.75 -170.75 --y 21.4

# 4. Add the entry to waypoints.json (spots prints one with fresh GUIDs and a name handle).

# 5. Check it and regenerate the mod files (commit them with your change).
py tools/build_waypoints.py

# 6. Run the tests and try it in game.
py -m unittest discover -s tests
.\pack.ps1 -Install
```

### waypoints.json

| Field | Meaning |
|---|---|
| `id` | `NEW_WAYP_<AREA>_<Name>`, with the game's area code (`DEN` Emerald Grove, `UND` Underdark, `GOB` goblin camp, `MOO` Moonrise Towers, `WYR` Rivington and Wyrm's Rock, `LOW` Lower City). Saves store unlocked waypoints by id, so **a released id never changes**. |
| `name` | What the map shows. Plain ASCII, at most 40 characters, and not a name the game already uses. Use the game's own name for the place where it has one. |
| `where` | A sentence for people: where it is, who is near. It is copied into the story script as a comment. |
| `level`, `group` | The level the waypoint is in, and the act group that goes with it (`WLD_Main_A` Act1, `SCL_Main_A` Act2, `BGO_Main_A` Act3, `CTY_Main_A` Act3b). The story locks a whole group when it leaves that act. |
| `handle` | The localisation handle of the name. New ones come from `survey.py spots`. |
| `shrine.position` | Where the shrine stands: x, the floor height under it minus 5 cm, z. |
| `shrine.yaw` | Optional. The shrine turns its rune face towards the arrival point unless this says otherwise. |
| `trigger.position` | The arrival point, on the floor. |
| `decal.style` | `dark` (Acts 1 and 2, cellars and caves) or `light` (Baldur's Gate streets), as the game does. |
| `shrine.guid`, `trigger.guid`, `decal.guid` | New random GUIDs. Never reuse or change a released one. |
| `underdark` | `true` for a waypoint in the Underdark, so that Sovereign Glut follows the party there. |
| `lockWith` | The id of one of the game's waypoints. Whenever the story locks that one, this one is locked too (the Hollow uses `WAYP_DEN_Camp`, for the Grove's lockdown). |

How the pieces fit together, and what the checks look for, is in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

### Choosing a good spot

- Somewhere players go back to, and far from the nearest waypoint.
- Out of the way: not in a doorway, not across a path, not on a spot where the story sends characters (the checks warn about those).
- Where travelling in cannot skip the story. A waypoint behind a door or barrier that the story keeps shut lets players walk around it, so use `lockWith`, or choose another spot.
- Not in a place where fast travel is blocked for the whole visit (a danger zone such as the House of Hope): players could travel in, but not out again.

## Code guidelines

- **Python 3.10+, standard library only.** The tools must run in CI without the game files: everything that needs the cache skips with a note when it is missing.
- **Generated files are never edited by hand.** Everything under `Mods/NotEnoughWaypoints/` except `meta.lsx`, and `Localization/`, comes from `waypoints.json`. CI fails if they are out of date.
- **The game's layout is the reference.** The level files follow the game's own (same attributes, same header); if you change the generator, compare its output with the game's files.
- The navigation grid format is not documented; [`tools/navgrid.py`](tools/navgrid.py) explains what is known. If a game patch changes it, the reader stops with an error instead of guessing.

## Testing in game

- `.\pack.ps1 -Install` copies the pak to your BG3 `Mods` folder; enable it in your mod manager once.
- Check a fresh save and a save that is far into the story: the waypoints must appear in both.
- Look at the shrine from a few sides and travel to it with a full party.

## Pull requests

- One topic per pull request.
- Fill in the template: what changed, how you verified it, and whether you tested it in game.
- `py tools/build_waypoints.py --check` (with the game cache for a waypoint change) and the tests must pass. CI runs the offline check and the tests.
- Add a line to `CHANGELOG.md` under *Unreleased*.
- Never rename a released waypoint id and never reuse a GUID.

## Releasing (maintainers)

1. Bump `Version64` in `meta.lsx` (both places). `build_waypoints.py --check --version X.Y.Z` checks it.
2. Move the *Unreleased* changelog entries under the new version.
3. `.\pack.ps1` and smoke-test the pak in game: a new game and an existing save.
4. Tag `vX.Y.Z` and publish a GitHub release with `dist/NotEnoughWaypoints-X.Y.Z.0.zip` attached. Attach the zip you tested; do not rebuild it in between. `python tools/release_notes.py X.Y.Z` prints the changelog section for the release text.
5. Publishing the release runs [`nexus-release.yml`](.github/workflows/nexus-release.yml). It checks that the tag, `meta.lsx` and the attached zip agree, then sends that zip to Nexus Mods as a new version of the main file, with the version's changelog section. It needs the repository secret `NEXUSMODS_API_KEY`, and `NEXUS_MOD_ID` and `NEXUS_FILE_ID` in the workflow: Nexus can only add versions to a file that exists, so the first version is uploaded by hand, and its IDs are copied in afterwards. Until then every run only checks. Pre-releases are skipped.
6. The mod page text lives in [`.github/nexus/`](.github/nexus/README.md) (`description.bbcode`, `summary.txt`). The same run updates the page when that text changed since the previous release, after saving the old description as a run artifact (details in that README). Edit the page there, not on the website, or the next update overwrites the website edit. Images are still managed on Nexus by hand.
7. From the Actions tab the workflow can also be run by hand: *dry run* (the default: checks everything, sends nothing), *upload*, or *page only* (for example to correct the page without a new release; the ref can be `main`).

`Version64` encodes `major << 55 | minor << 47 | revision << 31 | build`; for example 1.0.0.0 is `36028797018963968` and 1.1.0.0 is `36169534507319296`.
