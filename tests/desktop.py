#!/usr/bin/env python3
"""Desktop action test for bin/cap — machine-state-w7o.

    float     -> a named window floats; asking again changes nothing
    move      -> a named window moves; the move is read back
    focused   -> no window named means the focused one, resolved to an address
    unknown   -> an address that is not a window is refused, nothing dispatched
    lua       -> a value that would break out of the Lua expression is refused
    readback  -> a dispatcher that answers ok and does nothing is unverified
    insert    -> unavailable without wtype; with it, text is passed after --

Hermetic: the event suite's repository copy, plus a hyprctl stand-in that keeps
window state in a file and answers `ok` to everything, like the real one does.
Each check of a guard carries a negative control: the copy is patched to remove
it and the assertion must then fail.
"""

import json
import sys

from events import Box, check, patch, results

# Answers like Hyprland: `ok` to any dispatch, acting only on what it parses.
# While ignore exists it parses nothing, which is a dispatcher that does nothing.
HYPRCTL = r'''#!/usr/bin/python3
import json, pathlib, re, sys
d = pathlib.Path(__file__).resolve().parent.parent
state = json.loads((d / "windows.json").read_text())
args = [a for a in sys.argv[1:] if a != "-j"]
if args[0] == "version":
    print("stub")
elif args[0] == "clients":
    print(json.dumps(state))
elif args[0] == "activewindow":
    print(json.dumps(next(w for w in state if w["focused"])))
elif args[0] == "dispatch":
    with open(d / "dispatch.log", "a") as fh:
        fh.write(args[1] + "\n")
    m = re.search(r'window = "address:(0x[0-9a-f]+)"', args[1])
    if m and not (d / "ignore").exists():
        for w in state:
            if w["address"] == m.group(1):
                if "window.float" in args[1]:
                    w["floating"] = not w["floating"]
                ws = re.search(r'workspace = "([^"]+)"', args[1])
                if "window.move" in args[1] and ws:
                    w["workspace"]["name"] = ws.group(1)
        (d / "windows.json").write_text(json.dumps(state))
    print("ok")
'''

WINDOWS = [
    {"address": "0xa1", "class": "kitty", "title": "shell", "floating": False,
     "focused": True, "workspace": {"name": "1"}},
    {"address": "0xb2", "class": "firefox", "title": "page", "floating": False,
     "focused": False, "workspace": {"name": "2"}},
]


def setup(b):
    stubs = b.dir / "stubs"
    (stubs / "hyprctl").write_text(HYPRCTL)
    (stubs / "hyprctl").chmod(0o755)
    (b.dir / "windows.json").write_text(json.dumps(WINDOWS))


def win(b, addr):
    return next(w for w in json.loads((b.dir / "windows.json").read_text())
                if w["address"] == addr)


def dispatched(b):
    p = b.dir / "dispatch.log"
    return p.read_text().splitlines() if p.exists() else []


def case_float(b):
    setup(b)
    rc1, _ = b.cap("act", "desktop.window.float", "floating=yes", "window=0xb2")
    rc2, out2 = b.cap("act", "desktop.window.float", "floating=yes", "window=0xb2")
    ok = (rc1 == 0 and win(b, "0xb2")["floating"] and rc2 == 0 and "skipped" in out2
          and len(dispatched(b)) == 1 and not win(b, "0xa1")["floating"])
    return ok, f"rc={rc1},{rc2} dispatches={len(dispatched(b))}"


def case_move(b):
    setup(b)
    rc, out = b.cap("act", "desktop.window.move", "workspace=5", "window=0xb2")
    ok = rc == 0 and win(b, "0xb2")["workspace"]["name"] == "5" and "ok:" in out
    return ok, f"rc={rc}"


def case_focused(b):
    setup(b)
    rc, _ = b.cap("act", "desktop.window.float", "floating=yes")
    d = dispatched(b)
    # The dispatch names the focused window's address; never left to default.
    ok = rc == 0 and win(b, "0xa1")["floating"] and len(d) == 1 and "address:0xa1" in d[0]
    return ok, f"rc={rc} dispatch={d}"


def case_unknown(b):
    setup(b)
    rc, out = b.cap("act", "desktop.window.float", "floating=yes", "window=0xdead")
    return rc == 1 and "no window" in out and not dispatched(b), f"rc={rc}"


def case_lua(b):
    setup(b)
    rc, _ = b.cap("act", "desktop.window.move",
                  'workspace=1" }) os.execute("touch pwned") --', "window=0xb2")
    return rc == 1 and not dispatched(b), f"rc={rc} dispatches={dispatched(b)}"


def case_readback(b):
    setup(b)
    (b.dir / "ignore").touch()
    rc, out = b.cap("act", "desktop.window.move", "workspace=5", "window=0xb2")
    recs = b.records()
    outcome = recs[-1].get("outcome") if recs else None
    return rc == 1 and outcome == "unverified", f"rc={rc} outcome={outcome}"


def case_insert(b):
    setup(b)
    rc1, out1 = b.cap("act", "desktop.text.insert", "text=hi")
    stub = b.dir / "stubs" / "wtype"
    stub.write_text(f'#!/bin/sh\nfor a in "$@"; do printf "%s\\n" "$a"; done >> "{b.dir}/wtype.log"\n')
    stub.chmod(0o755)
    rc2, _ = b.cap("act", "desktop.text.insert", "text=-x rm")
    log = (b.dir / "wtype.log").read_text().splitlines() if (b.dir / "wtype.log").exists() else []
    ok = rc1 == 1 and "wtype is not installed" in out1 and rc2 == 0 and log == ["--", "-x rm"]
    return ok, f"rc={rc1},{rc2} wtype={log}"


def main():
    print("desktop actions:")
    with Box() as b:
        check("1 float a named window; again is skipped", *case_float(b))
    with Box() as b:
        check("2 move a named window, read back", *case_move(b))
    with Box() as b:
        check("3 no window named: the focused one, by address", *case_focused(b))
    with Box() as b:
        check("4 an unknown address is refused before dispatch", *case_unknown(b))
    with Box() as b:
        check("5 a Lua-breaking value is refused before dispatch", *case_lua(b))
    with Box() as b:
        check("6 ok without effect is unverified, not ok", *case_readback(b))
    with Box() as b:
        check("7 insert: unavailable without wtype; text passed after --", *case_insert(b))

    print("negative controls:")
    with Box() as b:
        patch(b.cap_path, '    for c in clients():\n        if c["address"] == window:\n'
                          '            return c\n    raise ValueError(f"no window {window}")',
              '    for c in clients():\n        if c["address"] == window:\n'
              '            return c\n    return {"address": window, "floating": False, '
              '"workspace": {"name": "?"}}')
        ok, d = case_unknown(b)
        check("4n existence check removed -> assertion 4 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, 'WORKSPACE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")',
              'WORKSPACE = re.compile(r".*")')
        ok, d = case_lua(b)
        check("5n workspace pattern removed -> assertion 5 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '    if _window(plan["window"])["workspace"]["name"] != workspace:',
              '    if False:')
        ok, d = case_readback(b)
        check("6n read-back removed -> assertion 6 fails", not ok, d)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
