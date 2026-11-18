"""
check_story.py - compile the story of the mod and of its uninstaller together with the game's
story, with LSLib's StoryCompiler, and report every problem they add.

When a save is loaded, the game compiles the story scripts of every active mod together with
its own. So every goal this repository ships is compiled here first, against the story of your
own installation: the functions a goal calls and the databases it reads must exist there, with
the same parameters and types, and nothing may be left that reads a database no one writes.

Needs Baldur's Gate 3 and LSLib's ExportTool (Divine.exe, StoryCompiler.exe and
StoryDecompiler.exe, which sit together). Nothing is downloaded and nothing of the game's is
committed: what it prepares stays in tools/.cache/story/.

Preparing (the first run, and the first after a game patch):
  1. the goals of the game's story modules (Shared, SharedDev, Gustav, GustavDev, GustavX) and
     their meta.lsx, from the game's packages, later packages over earlier ones;
  2. a story header. The game ships none, so it is written from the function table of the
     game's own compiled story (Mods/GustavX/Story/story.div.osi, through StoryDecompiler's
     debug log): every call, query and event the engine offers, with its parameters and types;
  3. the enum constants in the game's goals (DEATHTYPE.Chasm) as the numbers they are in the
     compiled story: LSLib's parser cannot read them.

Checking (every run): the game's story is compiled on its own, then with the mod, with the
uninstaller in its place, and with both. LSLib is stricter than the game in a few places (about
a hundred messages about the game's own goals), so what counts is what this repository's goals
add: a message about one of their files, or one that the game's story alone does not give.

Usage:
  python tools/check_story.py              # prepare if needed, then check
  python tools/check_story.py --rebuild    # prepare again from the game files
  python tools/check_story.py --game PATH --divine PATH\\TO\\Divine.exe

Exit status: 0 no problems, 1 problems, 2 it could not run (no game, no ExportTool).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from waypoints import CACHE, MOD, ROOT, UNINSTALLER  # noqa: E402

STORY = os.path.join(CACHE, "story")
TREE = os.path.join(STORY, "tree")
MANIFEST = os.path.join(STORY, "manifest.json")
LAYOUT = 1                     # raise when what is prepared changes
MODULES = ("Shared", "SharedDev", "Gustav", "GustavDev", "GustavX")   # the campaign's story, in load order
COMPILED = "GustavX"           # the top module: its compiled story holds the whole game's
PACKAGES = ("Shared", "Gustav", "GustavX")
OURS = (MOD, UNINSTALLER)
CONFIGURATIONS = (             # what players load: the mod; the uninstaller in its place; both by mistake
    ("the mod", (MOD,)),
    ("the uninstaller in place of the mod", (UNINSTALLER,)),
    ("the mod and the uninstaller together", (MOD, UNINSTALLER)),
)

KIND = {"Call": "call", "Query": "query", "Event": "event", "SysCall": "syscall", "SysQuery": "sysquery"}
RX_TYPE = re.compile(r"^(\d+): (\w+)(?: \(Alias: (\d+)\))?$")
RX_ENUM_TYPE = re.compile(r"^Type (\d+)$")
RX_ENUM_VALUE = re.compile(r"^(\w+): (-?\d+)$")
RX_FUNCTION = re.compile(r"^(Call|Query|Event|SysCall|SysQuery) (\w+)\((.*?)\)(?: @ \S+)? CondRefs .*"
                         r"Meta \((\d+), (\d+), (\d+), (\d+)\)$")
RX_MESSAGE = re.compile(r"(?:(Mods[\\/][^:\r\n]+?\.txt):(\d+):\d+: )?\[([EWX]\d+)\] ([^\r\n]*)")


# ------------------------------------------------------------------ the game's story, read

def read_debug_log(lines):
    """Types, enums and engine functions from the head of a StoryDecompiler debug log.

    Returns (aliases, enums, functions): aliases {type id: (name, alias of)}, enums {type name:
    {VALUE: number}}, functions [(kind, name, [(direction, type)], meta)]. It stops at the
    nodes, which come after (the rest of the log is large)."""
    aliases, enum_ids, functions = {}, {}, []
    section, current = None, None
    for line in lines:
        line = line.rstrip("\r\n")
        if line.startswith(" --- "):
            section = line.strip(" -")
            if section == "NODES":
                break
            continue
        if section == "ENUMS":
            m = RX_ENUM_TYPE.match(line)
            if m:
                current = int(m.group(1))
                enum_ids[current] = {}
                continue
            m = RX_ENUM_VALUE.match(line)
            if m and current is not None and m.group(1) != "__OSIRIS_ENUM_FALLBACK":
                enum_ids[current][m.group(1).upper()] = int(m.group(2))
        elif section == "TYPES":
            m = RX_TYPE.match(line)
            if m:
                aliases[int(m.group(1))] = (m.group(2), int(m.group(3)) if m.group(3) else None)
        elif section == "FUNCTIONS":
            m = RX_FUNCTION.match(line)
            if m:
                kind, name, params = m.group(1), m.group(2), m.group(3)
                parsed = []
                for p in (p.strip() for p in params.split(",")):
                    if p:
                        parsed.append(("out", p[4:]) if p.startswith("out ") else ("in", p))
                functions.append((kind, name, parsed, tuple(int(m.group(i)) for i in range(4, 8))))
    enums = {aliases[t][0]: values for t, values in enum_ids.items() if t in aliases}
    return aliases, enums, functions


def story_header(aliases, functions):
    """A story_header.div in the layout LSLib reads (LSLib/LS/Story/HeaderParser)."""
    def intrinsic(t):
        seen = set()
        while t in aliases and aliases[t][1] is not None and t not in seen:   # LSLib wants every alias
            seen.add(t)                                                       # to name an intrinsic type
            t = aliases[t][1]
        return t
    lines = ["// Written by tools/check_story.py from the game's compiled story. Not the game's own file."]
    for tid in sorted(aliases):
        name, alias = aliases[tid]
        if alias is not None:
            lines.append("alias_type {%s,%d,%d}" % (name, tid, intrinsic(alias)))
    for kind, name, params, meta in sorted(functions, key=lambda f: (f[0], f[1])):
        if kind in ("Query", "SysQuery"):
            args = ["[%s](%s)_P%d" % (d, t, i) for i, (d, t) in enumerate(params, 1)]
        else:
            args = ["(%s)_P%d" % (t, i) for i, (_d, t) in enumerate(params, 1)]
        lines.append("%s %s(%s) (%d,%d,%d,%d)" % (KIND[kind], name, ",".join(args), *meta))
    return "\n".join(lines) + "\n"


def rewrite_enums(text, enums):
    """Enum constants (DEATHTYPE.Chasm) as numbers; returns (text, how many it could not resolve)."""
    if not enums:
        return text, 0
    rx = re.compile(r"\b(%s)\.(\w+)\b" % "|".join(re.escape(n) for n in sorted(enums, key=len, reverse=True)))
    unknown = 0

    def number(m):
        nonlocal unknown
        value = enums[m.group(1)].get(m.group(2).upper())
        if value is None:
            unknown += 1
            return m.group(0)
        return str(value)
    return rx.sub(number, text), unknown


# ---------------------------------------------------------------------- the compiler's output

def messages(output):
    """Every message of a StoryCompiler run: (code, text, file or None, line or None).

    The compiler reports parse errors from several threads at once, so their lines can come
    interleaved; the text after each [code] stays whole, and a location is kept where it stands
    right before a message."""
    out = []
    for m in RX_MESSAGE.finditer(output):
        path = m.group(1).replace("\\", "/") if m.group(1) else None
        out.append((m.group(3), m.group(4).strip(), path, int(m.group(2)) if m.group(2) else None))
    return out


def is_ours(message):
    """A message about one of this repository's goals."""
    code, text, path, _line = message
    if path and any(path.startswith("Mods/%s/" % m) for m in OURS):
        return True
    return any(re.search(r"\b%s\b" % re.escape(m), text) for m in OURS)


def added(baseline, run):
    """The messages of a run that the game's story alone does not give, and those about our goals."""
    known = {(c, t) for c, t, _p, _l in baseline}
    seen, out = set(), []
    for msg in run:
        key = msg[:2]
        if (key not in known or is_ours(msg)) and msg not in seen:
            seen.add(msg)
            out.append(msg)
    return out


def describe(message):
    code, text, path, line = message
    where = "%s:%d: " % (path, line) if path else ""
    return "%s[%s] %s" % (where, code, text)


# ------------------------------------------------------------------------- preparing

def tools_for(divine):
    folder = os.path.dirname(divine)
    compiler = os.path.join(folder, "StoryCompiler.exe")
    decompiler = os.path.join(folder, "StoryDecompiler.exe")
    return compiler, decompiler


def packages(game):
    import glob
    data = os.path.join(game, "Data")
    found = [os.path.join(data, p + ".pak") for p in PACKAGES]
    hotfixes = sorted(glob.glob(os.path.join(data, "Patch*_*ot*ix*.pak")),
                      key=lambda p: [int(t) if t.isdigit() else t.lower() for t in re.split(r"(\d+)", os.path.basename(p))])
    return [p for p in dict.fromkeys(found + hotfixes) if os.path.exists(p)]


def fingerprint(paks, divine):
    return {"layout": LAYOUT, "exporttool": os.path.dirname(divine),
            "packages": {os.path.basename(p): [os.path.getsize(p), int(os.path.getmtime(p))] for p in paks}}


def run(cmd, what):
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if res.returncode != 0:
        print(res.stdout[-2000:], res.stderr[-2000:])
        raise SystemExit("%s failed (exit %d)" % (what, res.returncode))
    return res.stdout


def prepare(game, divine, paks):
    compiler, decompiler = tools_for(divine)
    work = os.path.join(STORY, "work")
    for d in (work, TREE):
        shutil.rmtree(d, ignore_errors=True)
    os.makedirs(work)
    print("Preparing the game's story in %s (once per game patch)..." % os.path.relpath(STORY, ROOT))
    names = "|".join(MODULES)
    expr = (r"^Mods/(%s)/(meta\.lsx|Story/story\.div\.osi|Story/story_orphanqueries_ignore_local\.txt"
            r"|Story/RawFiles/TypeCoercionWhitelist\.txt|Story/RawFiles/Goals/[^/]+\.txt)$" % names)
    for pak in paks:   # later packages override earlier ones, as in the game
        print("  extracting from", os.path.basename(pak))
        run([divine, "-g", "bg3", "-l", "warn", "-a", "extract-package", "-s", pak, "-d", work, "-x", expr,
             "--use-regex"], "Divine")
    osi = os.path.join(work, "Mods", COMPILED, "Story", "story.div.osi")
    if not os.path.exists(osi):
        raise SystemExit("No compiled story found in the game's packages (Mods/%s/Story/story.div.osi)" % COMPILED)
    print("  decompiling the game's compiled story for its functions and enums")
    decompiled = os.path.join(work, "decompiled")
    os.makedirs(decompiled)   # StoryDecompiler writes its log there before it makes the folder
    log = os.path.join(decompiled, "debug.log")
    run([decompiler, "--input", osi, "--output", decompiled, "--debug-log", log], "StoryDecompiler")
    with open(log, encoding="utf-8", errors="replace") as fh:
        aliases, enums, functions = read_debug_log(fh)
    if len(functions) < 500:
        raise SystemExit("Only %d engine functions found in the decompiled story: has the log's layout changed?"
                         % len(functions))
    unknown = goals = 0
    for module in MODULES:
        src = os.path.join(work, "Mods", module)
        dst = os.path.join(TREE, "Mods", module)
        if not os.path.exists(os.path.join(src, "meta.lsx")):
            raise SystemExit("Mods/%s/meta.lsx not found in the game's packages" % module)
        os.makedirs(os.path.join(dst, "Story", "RawFiles", "Goals"))
        shutil.copy2(os.path.join(src, "meta.lsx"), os.path.join(dst, "meta.lsx"))
        for extra in (os.path.join("Story", "story_orphanqueries_ignore_local.txt"),
                      os.path.join("Story", "RawFiles", "TypeCoercionWhitelist.txt")):
            if os.path.exists(os.path.join(src, extra)):
                shutil.copy2(os.path.join(src, extra), os.path.join(dst, extra))
        goal_dir = os.path.join(src, "Story", "RawFiles", "Goals")
        for name in sorted(os.listdir(goal_dir)) if os.path.isdir(goal_dir) else []:
            with open(os.path.join(goal_dir, name), encoding="utf-8", errors="replace", newline="") as fh:
                text, n = rewrite_enums(fh.read(), enums)
            unknown += n
            goals += 1
            with open(os.path.join(dst, "Story", "RawFiles", "Goals", name), "w", encoding="utf-8", newline="") as fh:
                fh.write(text)
    with open(os.path.join(TREE, "Mods", "Shared", "Story", "RawFiles", "story_header.div"), "w",
              encoding="utf-8", newline="\n") as fh:   # no byte order mark: LSLib's header parser rejects one
        fh.write(story_header(aliases, functions))
    with open(MANIFEST, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(dict(fingerprint(paks, divine), functions=len(functions), goals=goals), fh, indent=1)
        fh.write("\n")
    shutil.rmtree(work, ignore_errors=True)
    print("  %d goals, %d engine functions, %d enum types%s" % (
        goals, len(functions), len(enums), ", %d enum constants left as they were" % unknown if unknown else ""))


# --------------------------------------------------------------------------- checking

def place_ours():
    """This repository's goals as they are now, next to the game's."""
    for mod in OURS:
        dst = os.path.join(TREE, "Mods", mod)
        shutil.rmtree(dst, ignore_errors=True)
        src = os.path.join(ROOT, "Mods", mod)
        os.makedirs(os.path.join(dst, "Story", "RawFiles", "Goals"))
        shutil.copy2(os.path.join(src, "meta.lsx"), os.path.join(dst, "meta.lsx"))
        goals = os.path.join(src, "Story", "RawFiles", "Goals")
        for name in os.listdir(goals):
            shutil.copy2(os.path.join(goals, name), os.path.join(dst, "Story", "RawFiles", "Goals", name))


def compile_story(compiler, extra):
    cmd = [compiler, "--game", "bg3", "--no-packages", "--game-data-path", TREE, "--check-only"]
    for mod in MODULES + tuple(extra):
        cmd += ["--mod", mod]
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = res.stdout + res.stderr
    if "Unhandled exception" in output:
        print(output[-2000:])
        raise SystemExit("StoryCompiler stopped with an exception")
    return messages(output)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--game", default=None, help="BG3 install folder (contains Data\\)")
    ap.add_argument("--divine", default=None, help="path to LSLib's Divine.exe (StoryCompiler.exe sits next to it)")
    ap.add_argument("--rebuild", action="store_true", help="prepare the game's story again")
    args = ap.parse_args()

    from extract_game_data import divine_candidates, first_existing, game_candidates
    divine = args.divine or first_existing(divine_candidates())
    game = args.game or first_existing(game_candidates(), lambda p: os.path.isdir(os.path.join(p, "Data")))
    if not divine or not os.path.exists(divine):
        print("Divine.exe (LSLib ExportTool) not found: pass --divine. The story was not checked.")
        return 2
    compiler, decompiler = tools_for(divine)
    if not (os.path.exists(compiler) and os.path.exists(decompiler)):
        print("StoryCompiler.exe and StoryDecompiler.exe are not next to %s: use a full ExportTool. "
              "The story was not checked." % divine)
        return 2
    if not game or not os.path.isdir(os.path.join(game, "Data")):
        print("BG3 install not found: pass --game. The story was not checked.")
        return 2
    paks = packages(game)
    current = None
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as fh:
            current = json.load(fh)
    want = fingerprint(paks, divine)
    if args.rebuild or not current or any(current.get(k) != v for k, v in want.items()) \
            or not os.path.isdir(TREE):
        prepare(game, divine, paks)

    place_ours()
    print("Compiling the game's story with LSLib (%s)..." % ", ".join(MODULES))
    baseline = compile_story(compiler, ())
    if any(c == "X00" and re.search(r"\b(_Waypoints|_Gustav_Waypoints)\b", t) for c, t, _p, _l in baseline):
        print("The game's waypoint goals did not parse: the check would mean little (see check_story.py).")
        return 2
    print("  the game's story alone: %d messages from LSLib (the baseline)" % len(baseline))
    failed = False
    for what, mods in CONFIGURATIONS:
        new = added(baseline, compile_story(compiler, mods))
        if new:
            failed = True
            print("PROBLEM  %s: %d new message%s" % (what, len(new), "" if len(new) == 1 else "s"))
            for msg in new:
                print("         " + describe(msg))
        else:
            print("OK       %s" % what)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
