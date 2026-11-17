## What changed

<!-- One topic per pull request. Link the issue it fixes, if any (e.g. "Fixes #12"). -->

## Type

- [ ] A waypoint (new, moved or removed)
- [ ] Tooling or documentation

## How was it verified?

<!--
A waypoint: paste the output of `py tools/build_waypoints.py --check` run with the game cache,
and describe the in-game test (or attach a screenshot of the waypoint).
-->

## Checklist

- [ ] `py tools/build_waypoints.py --check` passes with the game cache (`py tools/extract_game_data.py` first), and the generated files are committed
- [ ] `py -m unittest discover -s tests` passes
- [ ] Tested in game, or explained above why not
- [ ] No released waypoint id was renamed and no GUID was reused (unlocked waypoints are stored in saves by id)
- [ ] Waypoint names are plain ASCII
- [ ] `CHANGELOG.md` updated under *Unreleased*
