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
| **1.2** (released) | Safe to remove | The uninstaller, which takes the waypoints out of a save before the mod is removed (moved up from 1.4); a check that compiles the story with the game's; a tool that shows what a save holds of the mod. 1.2.1: the four runes on walls, which were smeared in game, onto boulders |
| **1.3** (released) | Finishing touches | Arriving facing into the place, the patch-day check |
| **1.4** | Every language | The names in all of the game's languages, in the game's own words |
| **Later** | Runes on walls again | The four waypoints indoors back on walls, once the tools know which surfaces take a rune and the real shape of props |
| **Later** | More waypoints | New places, placed and reviewed the same way |

## 1.1: where it belongs

- **Tools that see the whole level.** [`tools/extract_game_data.py`](../tools/extract_game_data.py) reads the sub-levels the game places into each level (and marks those the story loads later, such as the Grove's barrier), the tiles of walls and floors, the volume of every trigger, the size of every decal, and what the story does with waypoints and travel: each lock and unlock, the danger zones and the blocked waypoint zones. The checks use all of it, and `survey.py report <id>` lists everything around a waypoint for review.
- **How far everything reaches.** The game's resource banks give the bounds of every visual, and so the box every item, prop and tile fills. The checks compare boxes instead of positions.
- **The rune on a wall** (moved up from 1.2, so that each waypoint moves only once). In buildings and towns the game draws the rune on a wall that is already there and adds nothing. A second arrangement does the same: the turn and height of the game's own wall runes (tests compare it with the Lower City Central Wall and Moonrise Towers waypoints), on a wall's face measured from its tiles, in a box shallow enough never to reach through a wall 0.3 m thick or onto the floor. `survey.py walls` finds walls that carry it.
- **Placement fixes.** Five waypoints move, as in the table above; four of them onto a wall. The Open Hand Temple keeps a boulder: the temple's front is a single large prop rather than a wall of tiles, and in Rivington the game puts its own rune on a rock.
- **Moves that reach your save.** When a waypoint moves, a story rule moves its invisible shrine and its arrival point in saves made before, the way the game's own hotfix patches move items: once per save, when its level is loaded.
- **Seen in game** (still to come). Each new place, from several sides: the rune whole on its wall, nothing of it on the floor, on furniture or on the far side of the wall; unlocking it; arriving with a full party; and, in a save made with 1.0, that clicking the new rune works. A note in `waypoints.json` of the patch each was last seen on.

Where this stands: released as 1.1.0, with everything above but the check in game. That is an exception to the sixth principle: the new places pass every check of the tools, but nobody has looked at them in the game yet. If one of them looks wrong, a 1.1 update moves it, in existing saves too.

One part has been seen at work since, in the files of a save rather than on screen: a playthrough that took up the mod at 1.0 and was loaded with 1.1 in Act 1 has the shrines of the Arcane Tower and the Shattered Sanctum at their new places, and the story's record that it moved them (`DB_NEW_WAYP_Placed`). How the runes look there is still to be seen.

## 1.2: safe to remove

Moved up from 1.4: a mod that cannot be taken out of a save again asks a lot of a player trying it out.

- **What a save keeps.** Read from a save made with the mod (`tools/inspect_save.py`). In the story: the six waypoints in the game's list of waypoints (`DB_WaypointInfo`), who unlocked each (`DB_WaypointUnlocked`), the Arcane Tower in Sovereign Glut's list of Underdark waypoints, and the mod's own goal and records. Outside it: the travel list of each party (the waypoints it unlocked), the game's list of waypoints registered for the map, and the invisible shrines and arrival points, whose templates are the mod's own objects. The runes and boulders belong to the levels, not to the save.
- **What removing the mod alone leaves.** The story keeps its facts, and a party keeps an unlocked waypoint in its travel list: listed without its name, and leading nowhere, since the story's travel rule needs the arrival point. It goes when the story locks its act.
- **The uninstaller.** A second mod with a story script and nothing else, loaded in place of the mod for one save. When the save is loaded (`SavegameLoaded`, where the game applies its own savegame patches) it locks every waypoint of the mod through the game's own procedure (`PROC_LockWaypointForAll`, as when an act ends), which takes it out of every party's travel list, and then takes the waypoints out of the story: `DB_WaypointInfo`, any unlock records left, Sovereign Glut's list, and the story's record of which waypoint an arrival point belongs to. It finds the waypoints by id, from its own list and from the list the mod keeps in the save, never by object, so it works with the mod's objects gone. It does nothing while the mod's own story is running: the mod would lose its waypoints for good, since its story adds them only when it first starts in a save.
- **Checked against the game's story.** `tools/check_story.py` compiles it, and the mod's own story, with the game's: on its own, in place of the mod, and loaded together with it.
- **What stays.** The game has no call to take a waypoint off its list of waypoints registered for the map, so the mod's ids stay on that list, with nothing behind them.
- **Seen in game** (still to come). A save from Act 1 with the Hollow unlocked, loaded with the uninstaller in place of the mod: the Hollow leaves the travel list, and the next save holds nothing of the mod (`inspect_save.py`). Then without the uninstaller: the save loads and plays on. Then the mod put back: its waypoints return, to be unlocked again.

Where this stands: released as 1.2.0, with everything above but the check in game, an exception to the sixth principle as in 1.1. If the uninstaller leaves anything behind, `inspect_save.py` on a save made after it shows what, and a 1.2 update takes that out too.

**1.2.1.** The first look in game, after 1.2.0, found the four runes on walls drawn smeared over wall and floor. The tools had misread the walls: about a third of the game's wall tiles give their turn as a quaternion (`QRotate`), which they did not read, and some walls do not take a decal at all (`RecieveDecal`, false on the Arcane Tower's walls). With both read, none of the four places had a clean tile wall, so 1.2.1 put the four on boulders, at new places checked in game. The boulders work and look whole, but a boulder indoors is not how the game does it: see *Runes on walls again*.

## 1.3: finishing touches

- **Arriving facing into the place.** The game sets up its arrival points by hand: most of those it turns face their waypoint's shrine, and 22 of 37 set the camera's direction on arrival (`Angle`), most in one relation to the waypoint. Ours were all unturned, with the camera left alone. They now follow the game: turned to face their shrine, the camera in the game's usual relation (see `docs/ARCHITECTURE.md`, *Arrival*), and `trigger.camera` to frame a place by hand. Still to come: a look in game at what each setting does, arriving at the Hollow and at the game's own Grove waypoint, before and after; then a camera picked for each place that needs one.
- **Patch-day check.** After a game patch, `build_waypoints.py` compares what the story does with what the waypoints follow against `story_baseline.json`, the record of the patch they were last checked on: the locks of their act groups, the locks and unlocks of the game's waypoint each starts from (`nextTo`, new in `waypoints.json`), the lock of everything at the epilogue, the travel zones over them, a fingerprint of the game's waypoint rules and Sovereign Glut's list. Each change is reported with the goal it is in; `--accept-story` records the story once they were looked at (see `docs/ARCHITECTURE.md`, *Patch day*).

Where this stands: released as 1.3.0 without the look in game, an exception to the sixth principle as in 1.1 and 1.2. The patch-day check needs none; the arrival points do. If arriving at one of ours looks odd, a 1.3 update gives it a camera of its own (`trigger.camera`).

## 1.4: every language

- **First, look.** Check in game what a player with the game in another language sees in the list today.
- **The game's own names.** Four of the names are places the game already names in every language. Using the game's own text for them gives every player the name the game uses for that place, in their language.
- **The other two**, Underdark - Arcane Tower and Moonrise Towers - Main Floor, are put together in each language from the game's own words: the "Underdark - " the game puts before its own Underdark waypoints, and its names for the Arcane Tower and Moonrise Towers. "Main Floor" needs a translator, or another name.
- **Until then**, the English names ship for every language, so that no list shows an empty line.

## Later: runes on walls again

The Arcane Tower, the Shattered Sanctum, Moonrise Towers and the Guildhall stand on boulders since 1.2.1 ("a giant rock at the top of the stairs", as a player put it). They go back on walls once the groundwork below is solid and checked against the game's own runes.

**How the game does it.** Of its 37 runes in these four levels, about half are on rocks and cliffs, most of them a rock placed for that waypoint (`S_..._WaypointShrine_geo`). The rest are on walls that are already there: fortress, temple and city walls built of tiles, and props too, such as a carved pillar at the Morphic Pool, a rubble wall in Baldur's Gate and a trim at Moonrise Towers. Where a building needs one, the game places a piece of it: a small ruined abbey wall carries the Goblin Camp's rune, and a castle-wall pillar the Basilisk Gate's (`S_PlateForWaypointSoItCanBeClicked`). One rune lies on the floor, like a teleport circle: Verge of the Shadows, where the shrine lies flat too.

**The groundwork,** found in a first look (the scripts are kept out of the repository until they become tools):

- **Which surfaces take a rune.** Props say it as tiles do: `RecieveDecal` in their root templates, passed down from parent templates. 1,256 templates refuse decals, 766 of them props. Every surface under one of the game's runes takes them.
- **The real shape of props.** Their boxes are too loose to put a rune on. The models cannot be read (LSLib needs `granny2.dll`, which the game does not ship), but their collision shapes can: each template names a physics resource (`PhysicsTemplate`), whose file in `Models.pak` LSLib's `PhysicsTool` turns into boxes and convex meshes. Every one of the game's runes that sits on a prop lies on a collision face square to it, within half a metre of its centre, over nearly all its area. Two cautions: some props' collision does not follow what is seen (a carpet's is tall), so a face counts only inside the prop's visible box; and the shrine has collision of its own.
- **The shrine is the click.** The invisible shrine's collision is a panel 3 m wide and 3 m tall standing on its foot: what players click. A smaller rune, or one raised above a wainscot, needs its shrine scaled or raised to match.
- **Arrangements beyond the rune on a wall:** a smaller rune (0.55 to 0.9) for narrower faces; a rune raised above a wainscot; the floor rune of Verge of the Shadows; the Underdark's cliff slab (`NAT_Cliff_Granite_B_Wet`, the carrier at the Myconid Colony and the Sussur Tree).

**The four places,** as they look with that groundwork:

| Waypoint | What is there | Where the rune can go |
|---|---|---|
| Shattered Sanctum | A ruined abbey wall (a prop), 2 m from 1.1's place, takes a rune of 0.7 whole | On that wall |
| Moonrise Towers - Main Floor | Abbey walls that take decals, with a stone wainscot 1.25 m high | Raised above the wainscot |
| Guildhall | No prop wall; tile walls lined with wainscots, arches and furniture | Raised above a wainscot if a clear stretch exists; otherwise on the floor |
| Underdark - Arcane Tower | The tower's walls refuse decals; the cave wall around the landing is terrain, not an object | A cliff slab set into the cave wall, as at the game's Underdark waypoints, or on the floor |

Also here: **the Hollow's rock.** In the wild the game often puts the rune on a rock that is already there; whether the Hollow keeps its boulder or moves its rune onto the ledge behind it is decided with the rest. Nothing of this is released before a test build has been looked at in game.

## Later: more waypoints

Ideas are welcome now, through the [waypoint idea form](../../../issues/new/choose). They will be placed with the same tools and go through the same review, after 1.1.

## How to help

- **Report what looks wrong.** A boulder in the way, a rune that is not whole on its wall or its rock, a party arriving somewhere awkward: use the placement form and attach a screenshot.
- **Suggest a wall.** For the four waypoints indoors, a screenshot of a bare stretch of wall (or pillar, or cave wall) near the boulder helps choose where the rune goes back to.
- **Translate the two names** the game has no words for, once 1.4 starts.
- **Try the uninstaller** on a copy of a save: say what the travel list and the map show afterwards.

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
- A save (`.lsv`, a package Divine extracts) holds `Globals.lsf`, `LevelCache/<level>.lsf`, `meta.lsf` and `StorySave.bin`. `StorySave.bin` is the story with all its facts, which StoryDecompiler reads once it is named `.osi`; its debug log lists every database with its facts, and every goal with its state (flags 0 running, 2 waiting to start, 7 completed). `Globals.lsf` has the waypoints registered for the map (region `RegisteredWaypoints`: id and object), the global items and triggers with the template each was made from, and most other state in a binary block (`NewAge`), where each party's travel list is a `game.party.v0.WaypointsComponent`: the id, the arrival point and the level of each waypoint the party unlocked.
- The engine's waypoint calls are `RegisterWaypoint(id, item)`, `UnlockWaypoint(id, trigger, character)` and `LockWaypoint(id, character)`; there is none to unregister a waypoint. The game hides a registered shrine with `SetOnStage` (Gale's chapel waypoint) rather than unregistering it. Unlocks are kept per party.
- The game applies its savegame patches on `SavegameLoaded()`. A goal without a parent starts with the story, also when a mod brings it into an existing save, and runs its INIT section then. The game's savegame patches keep a database that no goal uses any more by naming it in an INIT section (`NOT DB_...`), "so the transfer can happen to the new DBs"; the uninstaller keeps the mod's list of its waypoints the same way. `SysIsActive(goal)` tells whether a goal is running; the game negates system queries too (`NOT SysStatus(...)`, `NOT SysCount(...)`).
- The game ships no story header (`story_header.div`), but its compiled story (`Mods/GustavX/Story/story.div.osi`) lists every engine function with its parameters and types. LSLib's StoryCompiler needs every alias type to name an intrinsic type (`ITEMROOT` aliases `ROOT` in the game), and cannot read the enum constants of the game's goals (`DEATHTYPE.Chasm`), which the compiled story holds as numbers. With both taken care of it parses all but two of the game's 944 goals, and reports about a hundred differences of its own on them.
- Sovereign Glut's list of Underdark waypoints is spelt `DB_UND_BroodingSpovereign_UnderdarkWaypoints` in the game; the story check catches the "corrected" spelling.
