# Security policy

## What the mod does on your machine

The mod is data for the game, loaded by the game itself:

- six waypoint shrines, their arrival points and their runes, placed in the game's levels;
- one story script, run by the game's own story engine, that declares the waypoints;
- the waypoint names.

It contains no Script Extender code, writes no files of its own, makes no internet connections and runs no external programs.

The developer tools in `tools/` run LSLib's `Divine.exe` on your machine to read your local game files into `tools/.cache/`. They never upload anything. `pack.ps1` runs `Divine.exe` to build the pak.

## Supported versions

Only the latest release receives fixes.

## Reporting a vulnerability

Please report security problems privately with GitHub's **Report a vulnerability** button on the repository's *Security* tab, not in a public issue. Include the steps to reproduce it and your mod version.
