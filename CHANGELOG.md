# Changelog

All notable changes to this project are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

Nothing yet.

## [1.0.0] - 2026-11-17

First public release.

### Added
- **Six waypoint shrines**, each with the game's own shrine and rune:
  - **The Hollow** (Act 1): on the floor of the Hollow in the Emerald Grove, below Okta's and Auntie Ethel's stalls, across from Dammon's forge.
  - **Underdark - Arcane Tower** (Act 1): outside the tower's front door.
  - **Shattered Sanctum** (Act 1): inside the goblin camp's temple, east of the spider pits.
  - **Moonrise Towers - Main Floor** (Act 2): inside the front doors, next to Lann Tarv's stall.
  - **Open Hand Temple** (Act 3): in the street outside the temple in Rivington, next to the Circus of the Last Days.
  - **Guildhall** (Act 3): in Nine-Fingers Keene's hall.
- They work like the game's own waypoints: walk near one to unlock it, and the story locks it with the rest of its act when it leaves that act.
- The Hollow is locked when the druids seal the Emerald Grove, together with the game's Grove waypoint.
- Sovereign Glut follows the party to the Arcane Tower, which counts as an Underdark waypoint.
- Works in a new game or an existing save. No Script Extender needed.
- Developer tools: game-data extraction from your own install, a reader for the game's navigation grid, a survey tool that finds and checks places for new waypoints, a generator that writes every mod file from `waypoints.json` and checks each waypoint against the game, tests, and a packager that verifies the pak and builds the release zip.
- GitHub project files: contributing guide, code of conduct, security policy, issue forms, pull request template, CI, and a workflow that publishes releases on Nexus Mods.

[Unreleased]: ../../compare/v1.0.0...HEAD
[1.0.0]: ../../releases/tag/v1.0.0
