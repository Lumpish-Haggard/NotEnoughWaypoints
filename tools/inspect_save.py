"""
inspect_save.py - what a Baldur's Gate 3 save holds of Not Enough Waypoints.

Reads a copy of the save (the save itself is never changed) with LSLib's Divine.exe and
StoryDecompiler.exe and reports, for the waypoints of every version (ids NEW_WAYP_..., and the
GUIDs in waypoints.json):

  the mods     whether the save was made with the mod or with its uninstaller (meta.lsf)
  the story    the goals of the mod and of the uninstaller, and every fact of the story's
               databases that names a waypoint, its shrine or its arrival point (StorySave.bin)
  the game     the waypoints registered for the map (RegisteredWaypoints), those in the travel
               list of a party (found in the party data, NewAge), and the shrines and arrival
               points among the save's objects (Globals.lsf)

This is how the uninstaller was designed (what a save keeps of a waypoint), and how to check
what it did: inspect a save made after loading with the uninstaller, then one made after
removing it.

Usage:
  python tools/inspect_save.py --latest               # the newest save of the Public profile
  python tools/inspect_save.py "PATH\\TO\\Save folder"  # or the .lsv inside it
  python tools/inspect_save.py --latest --keep        # keep the converted files (prints where)

Exit status: 0 nothing of the mod in the save (but for its ids in the list of waypoints registered
for the map: the game has no call to take one off it), 1 something of it is there, 2 it could not run.
"""
from __future__ import annotations

import argparse
import base64
import glob
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waypoints import DATA_FILE, MOD, UNINSTALLER, load, parts_of  # noqa: E402

SAVES = os.path.join(os.environ.get("LOCALAPPDATA", ""), "Larian Studios", "Baldur's Gate 3", "PlayerProfiles",
                     "Public", "Savegames", "Story")
RX_ID = re.compile(r"\bNEW_WAYP_[A-Za-z0-9]+_[A-Za-z0-9_]+\b")
RX_DB_HEAD = re.compile(r"^#\d+ (\w+)\((\d+)\)")
RX_GOAL = re.compile(r"^#\d+ (\w+): SGC \d+, Flags (\d+)$")
GOAL_STATE = {0: "running", 2: "waiting to start", 7: "completed"}   # as the decompiler writes the goal flags


# ------------------------------------------------------------------------ what to look for

def our_marks(waypoints):
    """The ids and object GUIDs of the mod's waypoints: {GUID or id: what it is}."""
    marks = {}
    for wp in waypoints:
        marks[wp["id"]] = wp["id"]
        for part in parts_of(wp):
            if part in ("shrine", "trigger"):
                marks[wp[part]["guid"]] = "%s %s" % (wp["id"], "shrine" if part == "shrine" else "arrival point")
    return marks


def names_ours(text, marks):
    """Whether a piece of story text names one of the mod's waypoints or objects."""
    return bool(RX_ID.search(text)) or any(g in text for g in marks if "-" in g)


# ------------------------------------------------------------------------------- reading

def read_story_log(lines, marks):
    """From a StoryDecompiler debug log: the goals of the mod and the uninstaller with their state,
    and the facts that name the mod's waypoints, by database. The log is large: read as a stream."""
    goals, facts = {}, {}
    section, db = None, None
    for line in lines:
        line = line.rstrip("\r\n")
        if line.startswith(" --- "):
            section = line.strip(" -")
            db = None
            continue
        if section == "DATABASES":
            m = RX_DB_HEAD.match(line)
            if m:
                db = m.group(1)
                continue
            s = line.strip()
            if db and s.startswith("(") and names_ours(s, marks):
                facts.setdefault(db, []).append(s)
        elif section == "GOALS":
            m = RX_GOAL.match(line)
            if m and m.group(1) in (MOD, UNINSTALLER):
                goals[m.group(1)] = GOAL_STATE.get(int(m.group(2)), "flags %s" % m.group(2))
    return goals, facts


def read_globals(text, marks):
    """From Globals.lsx: registered waypoints of the mod, its objects, and the ids in the party data."""
    registered = []
    region = re.search(r'<region id="RegisteredWaypoints">(.*?)</region>', text, re.S)
    if region:
        registered = [i for i in re.findall(r'id="WaypointName" type="FixedString" value="([^"]+)"', region.group(1))
                      if RX_ID.match(i)]
    objects = sorted({marks[g] for g in re.findall(r'id="(?:TemplateID|CurrentTemplate)" type="(?:guid|FixedString)" '
                                                   r'value="([0-9a-f-]{36})"', text) if g in marks})
    party = []
    blob = re.search(r'<attribute id="NewAge" type="ScratchBuffer" value="([^"]*)"', text)
    if blob:
        party = ids_in_blob(base64.b64decode(blob.group(1)), [k for k in marks if "-" not in k])
    return registered, objects, party


def ids_in_blob(data, ids):
    """Waypoint ids in the party data. Its strings are stored one after another with nothing in
    between, so the known ids are matched exactly; any other NEW_WAYP_ string is shown as found."""
    found = set()
    for m in re.finditer(rb"NEW_WAYP_", data):
        rest = data[m.start():m.start() + 64]
        known = [i for i in ids if rest.startswith(i.encode("ascii"))]
        if known:
            found.add(max(known, key=len))
        else:
            found.add(re.match(rb"[A-Za-z0-9_]*", rest).group(0).decode("ascii") + " (not in waypoints.json)")
    return sorted(found)


def read_mods(text):
    """The mods a save was made with (meta.lsx): [(name, folder, version)]."""
    mods = []
    for node in re.findall(r'<node id="ModuleShortDesc">(.*?)</node>', text, re.S):
        attrs = dict(re.findall(r'id="(\w+)" type="\w+" value="([^"]*)"', node))
        v64 = int(attrs.get("Version64", "0") or 0)
        version = "%d.%d.%d.%d" % (v64 >> 55, (v64 >> 47) & 0xFF, (v64 >> 31) & 0xFFFF, v64 & 0x7FFFFFFF)
        mods.append((attrs.get("Name", "?"), attrs.get("Folder", "?"), version))
    return mods


def verdict(goals, facts, registered, objects, party):
    """(exit status, sentence) for a save."""
    if goals.get(MOD) or facts or objects or party:
        return 1, "Not Enough Waypoints is in this save."
    if goals.get(UNINSTALLER):
        tail = " (the uninstaller is still loaded: remove it, then load and save once more)"
    else:
        tail = ""
    if registered:
        return 0, ("Nothing of Not Enough Waypoints is left in this save but its waypoints' ids in the game's list of "
                   "waypoints registered for the map (the game has no call to take one off it)%s." % tail)
    return 0, "Nothing of Not Enough Waypoints is left in this save%s." % tail


# ------------------------------------------------------------------------------- running

def find_save(path):
    if os.path.isdir(path):
        found = glob.glob(os.path.join(path, "*.lsv"))
        if not found:
            raise SystemExit("No .lsv file in %s" % path)
        return found[0]
    if not os.path.exists(path):
        raise SystemExit("Not found: %s" % path)
    return path


def latest_save():
    found = glob.glob(os.path.join(SAVES, "*", "*.lsv"))
    if not found:
        raise SystemExit("No saves found in %s" % SAVES)
    return max(found, key=os.path.getmtime)


def run(cmd, what):
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(res.stdout[-1500:], res.stderr[-1500:])
        raise SystemExit("%s failed (exit %d)" % (what, res.returncode))


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("save", nargs="?", help="a save folder, or the .lsv in it")
    ap.add_argument("--latest", action="store_true", help="the newest save in %s" % SAVES)
    ap.add_argument("--divine", default=None, help="path to LSLib's Divine.exe (StoryDecompiler.exe sits next to it)")
    ap.add_argument("--keep", action="store_true", help="keep the converted files")
    args = ap.parse_args()
    if not args.save and not args.latest:
        ap.error("name a save, or use --latest")

    from extract_game_data import divine_candidates, first_existing
    divine = args.divine or first_existing(divine_candidates())
    if not divine:
        print("Divine.exe (LSLib ExportTool) not found: pass --divine.")
        return 2
    decompiler = os.path.join(os.path.dirname(divine), "StoryDecompiler.exe")
    if not os.path.exists(decompiler):
        print("StoryDecompiler.exe is not next to %s: use a full ExportTool." % divine)
        return 2
    lsv = latest_save() if args.latest else find_save(args.save)
    marks = our_marks(load(DATA_FILE)["waypoints"])

    work = tempfile.mkdtemp(prefix="new_wayp_save_")
    try:
        copy = os.path.join(work, "save.lsv")
        shutil.copy2(lsv, copy)   # Divine only ever reads the copy
        files = os.path.join(work, "files")
        run([divine, "-g", "bg3", "-l", "warn", "-a", "extract-package", "-s", copy, "-d", files], "Divine")
        for name in ("Globals", "meta"):
            run([divine, "-g", "bg3", "-l", "warn", "-a", "convert-resource", "-s", os.path.join(files, name + ".lsf"),
                 "-d", os.path.join(files, name + ".lsx")], "Divine")
        story = os.path.join(work, "story")
        os.makedirs(story)
        osi = os.path.join(work, "StorySave.osi")   # the decompiler goes by the extension
        shutil.copy2(os.path.join(files, "StorySave.bin"), osi)
        log = os.path.join(story, "debug.log")
        run([decompiler, "--input", osi, "--output", story, "--debug-log", log], "StoryDecompiler")

        with open(os.path.join(files, "meta.lsx"), encoding="utf-8", errors="replace") as fh:
            mods = read_mods(fh.read())
        with open(os.path.join(files, "Globals.lsx"), encoding="utf-8", errors="replace") as fh:
            registered, objects, party = read_globals(fh.read(), marks)
        with open(log, encoding="utf-8", errors="replace") as fh:
            goals, facts = read_story_log(fh, marks)
    finally:
        if args.keep:
            print("Converted files kept in", work)
        else:
            shutil.rmtree(work, ignore_errors=True)

    print("Save: %s" % os.path.basename(os.path.dirname(lsv)))
    ours = [m for m in mods if m[1] in (MOD, UNINSTALLER)]
    print("  made with: %s" % (", ".join("%s %s" % (n, v) for n, _f, v in ours) or "neither the mod nor its uninstaller"))
    print("The story")
    for goal in (MOD, UNINSTALLER):
        print("  goal %-40s %s" % (goal, goals.get(goal, "not there")))
    if not facts:
        print("  no fact names a waypoint of the mod")
    for db, rows in sorted(facts.items()):
        print("  %-45s %d fact%s" % (db, len(rows), "" if len(rows) == 1 else "s"))
        for row in rows:
            print("      " + row)
    print("The game")
    print("  %-45s %s" % ("in the travel list of a party", ", ".join(party) or "none"))
    print("  %-45s %s" % ("registered for the map", ", ".join(registered) or "none"))
    for kind in ("shrine", "arrival point"):
        of = [o[:-len(kind) - 1] for o in objects if o.endswith(" " + kind)]
        print("  %-45s %s" % (kind + "s among the objects", ", ".join(of) or "none"))
    status, sentence = verdict(goals, facts, registered, objects, party)
    print(sentence)
    return status


if __name__ == "__main__":
    sys.exit(main())
