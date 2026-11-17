# Roadmap

Where Not Enough Waypoints is going after 1.0. The aim is simple to say and hard to do: **every waypoint should look, stand and behave as if Larian had put it there.** Built the way the game builds its own waypoints in that kind of place, clear of everything the game puts nearby, right on every story path, readable in every language, and safe to update and to remove.

New waypoints will come as well, but only once the six that exist meet that bar, and with the tools that got them there.

This is a plan, not a promise. Order and scope will change with what players report. If something here matters to you, or you think the order is wrong, [open an issue](../../../issues/new/choose).

## Principles

1. **Game data first.** Every position, rule and name comes from the game's own files, read from your installation. Nothing is a guessed coordinate.
2. **Built the way Larian builds them.** Each waypoint copies one of the game's own, chosen for the kind of place, and a test checks that the copy gives back the original.
3. **The story decides.** A waypoint never takes the party somewhere the story has closed, and it is locked and unlocked with the game's own waypoint next to it.
4. **Existing saves come first.** An update must work in a save made with an earlier version. If a waypoint moves, it moves in your save too.
5. **Nothing replaced, nothing else needed.** The mod adds objects, story rules and names. It replaces none of the game's files and needs no other mods.
6. **Seen in game.** A waypoint is released only after it has been looked at in the game, on the current patch.

## What the review of 1.0 found

The 1.0 checks read the main file of each level: its characters, items, props and triggers. The game builds most places from **sub-levels** that it places into that file: the Guildhall, Rivington's streets and buildings, the goblin camp and the Emerald Grove are each one. The tools now read those as well (about 100,000 more objects in the Act 1 level alone), together with the tiles of walls and floors, the volume of every trigger, what the story does with waypoints and travel, and, from the bounds of every visual in the game, how far each object reaches. Every waypoint was checked again against all of it:

| Waypoint | What the review found | What 1.1 does |
|---|---|---|
| Guildhall | It stands in Nine-Fingers Keene's private office, not in her hall: a cabinet is inside the boulder, and a bookcase, a bed and the secret bookcase door are within reach. | The rune on the wall beside the bar in the main hall, where her visitors wait |
| Open Hand Temple | It stands inside the temple's main hall, not in the street: a pile of books is inside the boulder, a chair against its side and a bookcase behind it. | A boulder in the street in front of the temple, where the refugees beg |
| Moonrise Towers - Main Floor | The boulder cuts 0.34 m into the wooden frame of Lann Tarv's stall behind it, and into rubble the assault brings. A point the bazaar's crowd walks to is 0.7 m from the arrival point. | The rune on a wall of the main floor, east of the bazaar |
| Underdark - Arcane Tower | A stone bench reaches 0.2 m into the side of the boulder. | The rune on the tower's own wall, a few steps from its front door |
| Shattered Sanctum | The back of the boulder is pushed 0.7 m into the abbey wall behind it (seen once the checks knew how far each object reaches). | The rune on that wall |
| The Hollow | Clear. | Stays |

Three more things came out of it:

- **The game does not put a boulder in a building.** Of its 37 waypoints in these four levels, 20 have the rune on a rock or a cliff, outdoors or in caves. The other 17 are in towns, fortresses and dungeons, and none of them has a rock: the rune is on a wall (Moonrise Towers, the Gauntlet of Shar, Grymforge, the Selûnite Outpost and Cazador's Dungeon among them) or on some other part of the place itself. In 1.0, all six of ours used the boulder from the Blighted Village, four of them indoors.
- **A moved waypoint stays where it was in an existing save.** The game keeps the position of items and triggers in the save; Larian's own hotfixes move them with story patches. Without one, a save made with 1.0 would keep the invisible part of a moved waypoint (what you click, and where the party lands) at its old place.
- **The names are in English only.** In the game's other languages there is no text for them. Four of the six are places the game already names in every language: The Hollow, Shattered Sanctum, Open Hand Temple and Guildhall.

And what it confirmed:

- **The Hollow's lock is complete.** The game locks its Emerald Grove waypoint once, when the druids seal the Grove, and the Hollow follows that lock. The only unlock is at the gate on the first visit, long before.
- **Moonrise Towers needs no lock.** It is a danger zone during the assault (nobody inside can travel out), and the assault is fought on the main floor itself. It starts from the story, not from walking in, so arriving on the main floor is the same as walking in through the doors.
- **No waypoint stands where the game blocks waypoints.**

## Versions

| Version | Theme | What it brings |
|---|---|---|
| **1.1** (released) | Where it belongs | Tools that see the whole level and how far everything reaches; five waypoints moved, four of them onto a wall as the game does; moves that reach existing saves; every waypoint seen in game (still to come) |
| **1.2** | Finishing touches | Runes on walls built of props (inside Moonrise's front doors), arriving facing into the place, the patch-day check |
| **1.3** | Every language | The names in all of the game's languages, in the game's own words |
| **1.4** | Safe to remove | A way to take the waypoints out of a save before removing the mod |
| **Later** | More waypoints | New places, placed and reviewed the same way |

## 1.1: where it belongs

- **Tools that see the whole level.** [`tools/extract_game_data.py`](../tools/extract_game_data.py) reads the sub-levels the game places into each level (and marks those the story loads later, such as the Grove's barrier), the tiles of walls and floors, the volume of every trigger, the size of every decal, and what the story does with waypoints and travel: each lock and unlock, the danger zones and the blocked waypoint zones. The checks use all of it, and `survey.py report <id>` lists everything around a waypoint for review.
- **How far everything reaches.** The game's resource banks give the bounds of every visual, and so the box every item, prop and tile fills. The checks compare boxes instead of positions.
- **The rune on a wall** (moved up from 1.2, so that each waypoint moves only once). In buildings and towns the game draws the rune on a wall that is already there and adds nothing. A second arrangement does the same: the turn and height of the game's own wall runes (tests compare it with the Lower City Central Wall and Moonrise Towers waypoints), on a wall's face measured from its tiles, in a box shallow enough never to reach through a wall 0.3 m thick or onto the floor. `survey.py walls` finds walls that carry it.
- **Placement fixes.** Five waypoints move, as in the table above; four of them onto a wall. The Open Hand Temple keeps a boulder: the temple's front is a single large prop rather than a wall of tiles, and in Rivington the game puts its own rune on a rock.
- **Moves that reach your save.** When a waypoint moves, a story rule moves its invisible shrine and its arrival point in saves made before, the way the game's own hotfix patches move items: once per save, when its level is loaded.
- **Seen in game** (still to come). Each new place, from several sides: the rune whole on its wall, nothing of it on the floor, on furniture or on the far side of the wall; unlocking it; arriving with a full party; and, in a save made with 1.0, that clicking the new rune works. A note in `waypoints.json` of the patch each was last seen on.

Where this stands: released as 1.1.0, with everything above but the check in game. That is an exception to the sixth principle: the new places pass every check of the tools, but nobody has looked at them in the game yet. If one of them looks wrong, a 1.1 update moves it, in existing saves too.

## 1.2: finishing touches

- **Walls built of props.** Moonrise Towers and the Open Hand Temple are built mostly of large props rather than wall tiles, so the checks can carry a rune only onto the few tile walls they have: Moonrise's rune is east of the bazaar, not inside the front doors where the game would put it. Reading the meshes of those props would show their faces, and let the rune go where it belongs.
- **Arriving facing into the place.** Several of the game's arrival points are turned; ours all face the same way. If that decides which way the party faces on arrival, ours will face the traders and doors they are there for.
- **The Hollow's rock.** In the wild the game often puts the rune on a rock that is already there. Whether the Hollow keeps the Blighted Village boulder or moves its rune onto the ledge behind it is decided once the wall runes have been seen in game.
- **Patch-day check.** After a game patch, the tools compare what the story now does with the game's waypoints that ours follow, and say so when a lock or unlock was added or removed.

## 1.3: every language

- **First, look.** Check in game what a player with the game in another language sees in the list today.
- **The game's own names.** Four of the names are places the game already names in every language. Using the game's own text for them gives every player the name the game uses for that place, in their language.
- **The other two**, Underdark - Arcane Tower and Moonrise Towers - Main Floor, are put together in each language from the game's own words: the "Underdark - " the game puts before its own Underdark waypoints, and its names for the Arcane Tower and Moonrise Towers. "Main Floor" needs a translator, or another name.
- **Until then**, the English names ship for every language, so that no list shows an empty line.

## 1.4: safe to remove

- Removing the mod from a save that has used it leaves its waypoints on the map without working. A small separate file, loaded in place of the mod for one save, would lock the waypoints and take them out of the story; after that save the mod can be removed cleanly.
- Needs testing in game first: whether a locked waypoint whose objects are gone leaves anything behind.

## Later: more waypoints

Ideas are welcome now, through the [waypoint idea form](../../../issues/new/choose). They will be placed with the same tools and go through the same review, after 1.1.

## How to help

- **Report what looks wrong.** A boulder in the way, a rune that is not whole on its wall or its rock, a party arriving somewhere awkward: use the placement form and attach a screenshot.
- **Look at a waypoint in game.** None of the five places 1.1 moved to has been seen in game yet. A screenshot of a rune on its wall, from the front and at an angle, settles the most: whether it is whole, and whether any of it shows on the floor, on furniture or on the far side of the wall.
- **Translate the two names** the game has no words for, once 1.3 starts.

## Notes for contributors

Verified against the Patch 8 Hotfix 10 game files, for anyone picking up the items above:

- The game's waypoint rules are the story goal `_Waypoints` (Shared): `DB_WaypointInfo(group, id, shrine, trigger)`; `PROC_LockWaypoint` and `PROC_UnlockWaypoint` (a player and their party), `PROC_LockWaypointForAll`, `PROC_UnlockWaypointForAll`, `PROC_LockAllGroupWaypoints`, `PROC_UnlockAllGroupWaypoints`, and `PROC_LockAllUnlockedWaypoints` (the epilogue). `QRY_GLO_BlockTeleportToWaypoint(player, trigger)` lets a goal stop travel to one waypoint; Sovereign Glut uses it.
- Travel out of a place is blocked in a danger zone (`DB_DangerZone(trigger, id)`, goal `GLO_DangerZone`), and waypoints do not work at all in a blocked waypoint zone (`DB_BlockedWaypointZone(trigger)`). Arrests, prisons and night at camp block travel too.
- Where the game locks waypoints: `Act1` and `Act1b` when Act 2 starts (`Act2_General`), `Act2` when Act 3 starts (`Act3_WYR_General`) and when the Emperor is revealed (`Act2b_INT_EmperorRevealed`), the Emerald Grove when it is sealed (`Act1_DEN_Lockdown`), the Crèche (`Act1b_CRE_Creche_Misc`), Wyrm's Rock, which is locked and unlocked again in Act 3 (`Act3_GEN_Misc`), and every waypoint at the epilogue. The Moonrise Towers waypoint is unlocked when the party first enters the towers (`Act2_MOO_Misc`).
- A level template names its sub-level in the root templates (`SubLevelName`, and `StartingLoaded` for those the story loads later); the sub-level's objects are relative to the template's position and rotation. A tile construction lists its tiles with `Translate` in level coordinates and `Rotate` written row by row.
- A box trigger's `Extents` is the full size of a box centred on the trigger; a prism (`Points` and `Height`) rises from the trigger's height. Both were checked against where the game's own characters stand.
- Larian moves items and triggers in existing saves with `TeleportToPosition` and `ToTransform` in the `BG3_*SavegamePatches` goals, applied when the level they are in is loaded.
- Runes on walls: Moonrise Towers uses the decal template's own size (3 by 1 by 3 m) at 0.9 scale, 1.31 m above its shrine; Baldur's Gate and the Lower City Central Wall use a box 3 m wide, 3 m high and 8 to 10 cm deep on the wall's face. The Blighted Village rune on its boulder is 60 cm deep. Where the tools can measure a wall's face behind one of the game's runes (six of them), it lies 6 to 52 cm behind the rune's centre.
- How far things reach: visual resources (`VisualBank` in the banks under `Public/*/Content/`) have `BoundsMin` and `BoundsMax`; templates name their visual (`VisualTemplate`, inherited through `ParentTemplateId`); tiles find theirs through their tile set (`TileSetBank`: `TileGUID` to `VisualGUID`). A stretchable tile is stretched along its length only.
