#!/usr/bin/env python3
"""Lifecycle test for bin/cap — the output boundary.

The loader boundary is proven: invalid input is rejected. This asserts the other
half, which is that failed derivation leaves the last coherent truth intact.

    add     -> appears
    remove  -> disappears, and nothing else does
    rename  -> refused; no stale identity reaches the artifact
    invalid -> the previous good artifact survives byte-for-byte
    stale   -> cap check fails
    same in -> same bytes out

Hermetic: every case runs against a throwaway copy of the repository, so it never
touches the working tree or the live desktop.

Two assertions carry negative controls. An assertion that cannot fail is not an
assertion, and one of these — that a broken surface never looks like an empty one
— exists because that exact failure happened here.
"""

import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDED = ["bin", "canonical", "derived", "adapters", "state"]
ART = "derived/hypr/bindings.lua"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def patch(path, old, new):
    """Rewrite a file for a negative control, asserting the edit actually landed.

    A control whose anchor has drifted replaces nothing, leaves the mechanism
    intact, and PASSES — reporting that a disabled check still fails when it was
    never disabled. That happened twice here in one session, both times because
    a composite condition gained another term. So the anchor is verified rather
    than trusted, and controls anchor on the smallest thing they mean to break.
    """
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"negative control anchor not found: {old[:70]!r}")
    path.write_text(text.replace(old, new))


class Box:
    def __enter__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="cap-lifecycle-"))
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        for item in NEEDED:
            src, dst = REPO / item, self.repo / item
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=True)
            elif src.exists():
                shutil.copy2(src, dst)
        return self

    def __exit__(self, *_):
        shutil.rmtree(self.dir, ignore_errors=True)

    def cap(self, *args):
        r = subprocess.run([str(self.repo / "bin" / "cap"), *args],
                           capture_output=True, text=True, cwd=self.repo,
                           env={"HOME": str(self.dir), "PATH": "/usr/bin:/bin"})
        return r.returncode, r.stdout + r.stderr

    def artifact(self):
        p = self.repo / ART
        return p.read_text() if p.exists() else None

    def bindings(self):
        p = self.repo / "canonical/bindings/keys.toml"
        return tomllib.loads(p.read_text()).get("key_binding", [])

    def write_bindings(self, entries):
        out = []
        for b in entries:
            out.append("[[key_binding]]")
            # any arity, not just two — a chord may carry several modifiers
            out.append("keys   = [" + ", ".join(f'"{k}"' for k in b["keys"]) + "]")
            out.append('action = "%s"' % b["action"])
            if b.get("args"):
                out.append('args   = { role = "%s" }' % b["args"]["role"])
            out.append('label  = "%s"' % b.get("label", ""))
            out.append("")
        (self.repo / "canonical/bindings/keys.toml").write_text("\n".join(out))


def main():
    print("cap lifecycle test\n")

    with Box() as b:
        b.cap("render")
        start = b.artifact()
        chords = [" + ".join(k["keys"]) for k in b.bindings()]
        check("1  add: every declared chord appears in the artifact",
              start is not None and all(c in start for c in chords), f"{len(chords)} chords")

        # remove one, keep the rest
        keep = [k for k in b.bindings() if k["keys"] != ["SUPER", "G"]]
        dropped = " + ".join(["SUPER", "G"])
        b.write_bindings(keep)
        b.cap("render")
        after = b.artifact()
        check("2  remove: it disappears, and nothing else does",
              dropped not in after and all(" + ".join(k["keys"]) in after for k in keep))

        # rename the action out from under the bindings
        p = b.repo / "canonical/bindings/keys.toml"
        p.write_text(p.read_text().replace("desktop.application.ensure",
                                           "desktop.application.summon"))
        before = b.artifact()
        rc, out = b.cap("render")
        check("3  rename: render refuses and writes no stale identity",
              rc != 0 and "summon" not in b.artifact(), f"exit={rc}")
        check("4  invalid: the previous good artifact survives byte-for-byte",
              b.artifact() == before)
        p.write_text(p.read_text().replace("desktop.application.summon",
                                           "desktop.application.ensure"))

        # hand-edit the artifact
        b.cap("render")
        (b.repo / ART).write_text(b.artifact() + "\n-- hand edited\n")
        rc, out = b.cap("check")
        check("5  stale: check fails and names the artifact",
              rc != 0 and "STALE" in out, f"exit={rc}")

        b.cap("render")
        one = b.artifact()
        b.cap("render")
        check("6  same input yields the same bytes", one == b.artifact())

    # --- conflict pressure (bru.7.3) ---------------------------------------
    with Box() as b:
        p = b.repo / "canonical/bindings/keys.toml"
        p.write_text(p.read_text() + '''
[[key_binding]]
keys   = ["SUPER", "SHIFT", "X"]
action = "desktop.window.list"
label  = "One order"

[[key_binding]]
keys   = ["SHIFT", "SUPER", "X"]
action = "desktop.window.list"
label  = "The other order"
''')
        rc, out = b.cap("check")
        check("7  equivalent modifier orders collide",
              rc != 0 and "CONFLICT" in out,
              "SUPER+SHIFT+X and SHIFT+SUPER+X are one chord")
        check("8  both claimants are named with their provenance",
              out.count("keys.toml") >= 2 and "declared as" in out)

        # removing one claimant restores validity, and touches nothing else
        keep = [k for k in b.bindings() if k["keys"] != ["SHIFT", "SUPER", "X"]]
        b.write_bindings(keep)
        b.cap("render")   # else check fails on staleness, not on a conflict
        rc, out = b.cap("check")
        check("9  removing one claimant restores validity",
              rc == 0 and "CONFLICT" not in out and out.count("ok   ") >= len(keep),
              f"{len(keep)} bindings, none conflicting")

    with Box() as b:
        # coordinated rename: action and every reference together
        for f in ("canonical/actions/desktop.toml", "canonical/bindings/keys.toml"):
            q = b.repo / f
            q.write_text(q.read_text().replace("desktop.application.ensure", "desktop.app.open"))
        rc, _ = b.cap("render")
        art = b.artifact()
        first = art
        b.cap("render")
        check("10 coordinated rename succeeds and drops the old identity",
              rc == 0 and "application.ensure" not in art and "desktop.app.open" in art
              and art == b.artifact(), f"exit={rc}, deterministic")

    with Box() as b:
        # THE RACE: vendor claims the chord after render, before project.
        # cap render re-reads vendor state so it cannot render into a KNOWN
        # conflict, but nothing stops the vendor changing afterwards.
        vend = b.dir / ".config/hypr/config"
        vend.mkdir(parents=True, exist_ok=True)
        (vend / "binds.lua").write_text('local mainMod = "SUPER"\n')
        b.cap("render")
        rc_before, _ = b.cap("check")
        (vend / "binds.lua").write_text(
            'local mainMod = "SUPER"\n'
            'hl.bind(mainMod .. " + M", hl.dsp.exec_cmd("something-else"))\n')
        rc_after, out = b.cap("check")
        check("11 a vendor claim after render is detected, not prevented",
              rc_before == 0 and rc_after != 0 and "CONFLICT" in out
              and "ok       artifact" in out,
              "artifact is not stale — the world changed, not the file")

    # --- observed bindings: evidence, not description (bru.7.4) -------------

    VENDOR = '''local mainMod = "SUPER"
local noctCall = "noctalia msg "
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(launchPrefix .. FILE_MANAGER))
hl.bind("ALT + Tab", hl.dsp.window.cycle_next())
hl.bind(mainMod .. " + CONTROL + SHIFT + Right", hl.dsp.window.move({ workspace = "m+1" }))
hl.bind(mainMod .. " + Z", hl.dsp.exec_cmd(noctCall .. "settings-toggle"))
for i, key in ipairs(keys) do
  hl.bind(mainMod .. " + ALT + " .. key, hl.dsp.focus({ workspace = i }))
end
'''

    def with_vendor(b, text=VENDOR):
        v = b.dir / ".config/hypr/config"
        v.mkdir(parents=True, exist_ok=True)
        (v / "binds.lua").write_text(text)
        return v / "binds.lua"

    with Box() as b:
        with_vendor(b)
        rc, out = b.cap("preview")
        # 5 hl.bind lines: 4 readable, 1 computed. None may go missing silently.
        listed = sum(1 for l in out.splitlines() if l.strip().startswith(":"))
        check("12 every vendor binding is accounted for, readable or not",
              rc == 0 and out.count(":") >= 5 and "UNREADABLE — 1 binding" in out
              and all(c in out for c in ("SUPER + E", "ALT + Tab",
                                         "SUPER + CONTROL + SHIFT + Right", "SUPER + Z")),
              "4 read + 1 declared unreadable = 5 hl.bind lines")

        check("13 an observed row carries source, line and the expression as written",
              "~/.config/hypr/config/binds.lua" in out and ":3" in out
              and "hl.dsp.exec_cmd(launchPrefix .. FILE_MANAGER)" in out
              and "OBSERVED" in out and "OWNED" in out,
              "no invented label; owned and observed are separate tables")

        check("14 no observed row claims a semantic it cannot support",
              "Semantics are not declared anywhere" in out
              and not any(w in out for w in ("Open file manager", "File manager", "Open terminal")),
              "the expression stands in for a label that does not exist")

    with Box() as b:
        with_vendor(b)
        # a chord whose modifiers match a binding whose KEY is computed
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text() + '''
[[key_binding]]
keys   = ["SUPER", "ALT", "Q"]
action = "desktop.window.list"
label  = "In the computed family"
''')
        b.cap("render")
        rc, out = b.cap("check")
        check("15 a chord in a computed-key family is UNKNOWN, not free",
              rc != 0 and "UNKNOWN" in out and "cannot be shown free" in out
              and "SUPER + M" in out and out.count("UNKNOWN") == 1,
              "unprovable is reported as unprovable, not as conflict or as ok")

    with Box() as b:
        # attribution follows the evidence and degrades when the bytes diverge
        v = with_vendor(b)
        rc, out = b.cap("preview")
        divergent = "owner local" in out
        real = pathlib.Path.home() / ".config/hypr/config/binds.lua"
        skel = pathlib.Path("/etc/skel/.config/hypr/config/binds.lua")
        attributed = True
        if real.is_file() and skel.is_file() and real.read_bytes() == skel.read_bytes():
            r = subprocess.run([str(REPO / "bin" / "cap"), "preview"],
                               capture_output=True, text=True, cwd=REPO)
            attributed = "owner cachyos" in r.stdout
        check("16 ownership is attributed from evidence and degrades with it",
              divergent and attributed,
              "packaged bytes name their package; edited bytes claim no owner")

    # --- review findings 8cy.1 and 8cy.3 ------------------------------------

    ALT_BINDING = '''
[[key_binding]]
keys   = ["SUPER", "ALT", "Q"]
action = "desktop.window.list"
label  = "In the computed family"
'''

    with Box() as b:
        with_vendor(b)
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text() + ALT_BINDING)
        before = b.artifact()
        rc, out = b.cap("render")
        check("17 render refuses a chord check would call UNKNOWN",
              rc != 0 and "cannot be shown free" in out and b.artifact() == before,
              "the gate and the report ask one question")

    with Box() as b:
        # an unaccepted modifier spelling, the one that sat in MOD_ORDER as valid
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text().replace('keys   = ["SUPER", "G"]',
                                             'keys   = ["CTRL", "G"]'))
        before = b.artifact()
        rc, out = b.cap("render")
        check("18 an unaccepted modifier spelling is refused, naming the accepted one",
              rc != 0 and "CTRL" in out and "\'CONTROL\'" in out
              and b.artifact() == before,
              "one spelling per modifier, so two declarations cannot name one chord")

        p_.write_text(p_.read_text().replace('keys   = ["CTRL", "G"]',
                                             'keys   = ["HYPER", "G"]'))
        rc, out = b.cap("render")
        check("19 a token that is not a modifier at all is refused",
              rc != 0 and "is not a modifier" in out, "rejected, not treated as a key")

    # --- refusal states name the right fact (from a keypress, 8cy.9) --------

    with Box() as b:
        # Start from an empty journal. The sandbox copies state/ from the repo,
        # so the live journal comes with it — and its older refusals predate the
        # state field, which would make this assertion read them as failures.
        (b.repo / "state" / "actions.jsonl").unlink(missing_ok=True)

        # unimplemented: a declared action no provider implements
        rc, out = b.cap("act", "desktop.workspace.arrange")
        unimpl = rc != 0 and "declared but not implemented" in out and "unavailable" not in out

        # unavailable: implemented, but its runtime dependency is absent. The
        # sandbox PATH has no hyprctl, so requires_hyprland fails honestly.
        rc2, out2 = b.cap("act", "desktop.window.list", "role=mail")
        unavail = rc2 != 0 and "is unavailable" in out2 and "not implemented" not in out2

        rc3, out3 = b.cap("act", "desktop.no.such.action")
        unknown = rc3 != 0 and "no such action" in out3

        check("20 each refusal names its own state, not a shared one",
              unimpl and unavail and unknown,
              "not implemented / unavailable / no such action stay distinct")

        j = b.repo / "state" / "actions.jsonl"
        states = [json.loads(l).get("state") for l in j.read_text().splitlines()
                  if json.loads(l).get("outcome") == "refused"]
        check("21 the journal records which refusal it was",
              set(states) == {"unimplemented", "unavailable", "unknown"},
              "a corpus of bare 'refused' cannot tell absent code from an absent desktop")

        # the surfaces must agree about the same action
        rcp, prev = b.cap("preview")
        check("22 preview and refusal agree about one action",
              "missing" in prev and unimpl,
              "preview says missing, the refusal says not implemented — one fact")

    # --- declarations and invocations validated alike (8cy.6) ---------------

    with Box() as b:
        rolep = b.repo / "canonical/roles/roles.toml"
        good = rolep.read_text()
        cases = [
            ("a role missing a required key",
             good.replace('command      = "proton-mail"\n', ""), "missing 'command'"),
            ("an extra key silently dropped",
             good.replace('label        = "Mail"',
                          'label        = "Mail"\nicon         = "mail"'), "unknown key"),
            ("a role whose command has no executable",
             good.replace('command      = "proton-mail"', 'command      = "   "'),
             "non-empty string"),
            ("window_class of the wrong type",
             good.replace('window_class = ["Proton Mail", "proton-mail"]',
                          'window_class = "Proton Mail"'), "non-empty list"),
        ]
        ok = True
        for what, text, expect in cases:
            rolep.write_text(text)
            rc, out = b.cap("check")
            if not (rc != 0 and expect in out and "roles.toml" in out):
                ok = False
                print(f"      {what}: expected {expect!r}, got rc={rc} {out.strip()[:90]}")
        rolep.write_text(good)
        check("23 a malformed role is diagnosed, naming the file and the problem", ok,
              f"{len(cases)} shapes, each rejected on load")

    with Box() as b:
        bindp = b.repo / "canonical/bindings/keys.toml"
        good = bindp.read_text()
        cases = [
            ("binding with no action", good.replace(
                'action = "desktop.workspace.arrange"\n', ""), "missing 'action'"),
            ("binding with an unknown key", good.replace(
                'label  = "Open mail"', 'lable  = "Open mail"'), "unknown key"),
            ("keys of the wrong type", good.replace(
                'keys   = ["SUPER", "M"]', 'keys   = "SUPER + M"'), "must be a list"),
            ("args of the wrong type", good.replace(
                'args   = { role = "mail" }', 'args   = "mail"'), "must be a table"),
        ]
        ok = True
        for what, text, expect in cases:
            bindp.write_text(text)
            rc, out = b.cap("check")
            if not (rc != 0 and expect in out and "keys.toml" in out):
                ok = False
                print(f"      {what}: expected {expect!r}, got rc={rc} {out.strip()[:90]}")
        bindp.write_text(good)
        check("24 a malformed key binding is diagnosed the same way", ok,
              f"{len(cases)} shapes, each rejected on load")

    with Box() as b:
        bare = b.cap("act", "desktop.application.ensure", "mail")
        mis  = b.cap("act", "desktop.application.ensure", "rle=mail")
        dup  = b.cap("act", "desktop.application.ensure", "role=mail", "role=browser")
        none = b.cap("act", "desktop.workspace.arrange", "role=mail")
        check("25 a bare token is an error, not a discarded word",
              bare[0] != 0 and "not name=value" in bare[1] and "Traceback" not in bare[1],
              "it used to be dropped, then crash the provider with a TypeError")
        check("26 argument names are checked against the declaration",
              mis[0] != 0 and "unknown argument(s) rle" in mis[1]
              and dup[0] != 0 and "more than once" in dup[1]
              and none[0] != 0 and "declares no arguments" in none[1],
              "misspelled, repeated, and undeclared are each named")

        j = b.repo / "state" / "actions.jsonl"
        before = j.read_text() if j.exists() else ""
        b.cap("act", "desktop.application.ensure", "mail")
        check("27 a usage error is not journalled as a refusal",
              (j.read_text() if j.exists() else "") == before,
              "nothing was attempted, so the corpus records nothing")

    with Box() as b:
        # a binding referencing a role that no longer exists
        rolep = b.repo / "canonical/roles/roles.toml"
        rolep.write_text(rolep.read_text().replace("[role.mail]", "[role.post]"))
        rc, out = b.cap("check")
        rc2, out2 = b.cap("render")
        check("28 a dangling role reference fails where a dangling action does",
              rc != 0 and "no such role" in out and rc2 != 0
              and "missing role" in out2,
              "check reports it and render refuses, rather than the key dying on press")

    # --- the accounting invariant, on the input (8cy.7) ---------------------

    TWO_ON_A_LINE = ('local mainMod = "SUPER"\n'
                     'hl.bind(mainMod .. " + E", a()) hl.bind(mainMod .. " + F", b())\n')
    ODD_SHAPE     = ('local mainMod = "SUPER"\n'
                     'hl.bind(mainMod .. " + E", a())\n'
                     'hl.bind (mainMod .. " + F", b())\n')   # space before the paren
    COMMENTED     = ('local mainMod = "SUPER"\n'
                     '-- hl.bind(mainMod .. " + E", a())\n'
                     'hl.bind(mainMod .. " + F", b())\n')

    with Box() as b:
        with_vendor(b, TWO_ON_A_LINE)
        rc, out = b.cap("check")
        check("29 several call sites on one line are all found",
              "2 read, 0 computed, 0 unrecognised of 2" in out,
              "scanning per line and taking the first would undercount silently")

    with Box() as b:
        with_vendor(b, ODD_SHAPE)
        rc, out = b.cap("check")
        before = b.artifact()
        rc2, out2 = b.cap("render")
        check("30 a shape the parser cannot read is counted, not dropped",
              "1 unrecognised" in out and rc != 0,
              "the file mentions hl.bind twice and yields one call site")
        check("31 an unrecognised shape refuses to render",
              rc2 != 0 and "not recognised as call sites" in out2
              and b.artifact() == before,
              "a chord may be hidden in it, so it cannot be shown free")

    with Box() as b:
        with_vendor(b, COMMENTED)
        rc, out = b.cap("check")
        check("32 a commented-out bind is neither a binding nor unrecognised",
              "1 read, 0 computed, 0 unrecognised of 1" in out,
              "counting it either way would be wrong")

    # --- negative controls -------------------------------------------------
    print("\n  negative controls (the mechanism is broken on purpose):")

    with Box() as b:
        cap = b.repo / "bin" / "cap"
        # Disable the COMPARISON, not the existence branch: replacing
        # `if RENDERED.exists()` falls through to the elif that reports a
        # missing artifact, so a problem is still raised and the control would
        # test nothing. The first attempt did exactly that.
        patch(cap,
            "        if on_disk != expected:", "        if False:")
        b.cap("render")
        (b.repo / ART).write_text("-- hand edited, nothing else\n")
        rc, _ = b.cap("check")
        check("5n stale detection disabled -> assertion 5 fails", rc == 0,
              "staleness went unreported, as expected of a disabled check")

    with Box() as b:
        # the failure that made a broken surface look like an empty one
        cap = b.repo / "bin" / "cap"
        patch(cap,
            "            free, holder = check_chord(chord, mine)",
            "            free, holder = check_chord(chord, mine); STALE_REFERENCE_LIKE_THE_OLD_BUG")
        rc, out = b.cap("preview")
        stdout_only = subprocess.run([str(cap), "preview"], capture_output=True, text=True,
                                     cwd=b.repo, env={"HOME": str(b.dir), "PATH": "/usr/bin:/bin"})
        check("Xn a broken surface never resembles an empty one",
              rc != 0 and stdout_only.stdout.strip() == "" and "could not be built" in out,
              "no header, no partial rows, clear error, non-zero exit")

    with Box() as b:
        # Disable normalisation itself, so chords are compared as declared.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            '    mods = sorted(dict.fromkeys(k for k in ks if k in MOD_ORDER),\n'
            '                  key=lambda k: MOD_ORDER[k])',
            '    mods = [k for k in ks if k in MOD_ORDER]')
        p = b.repo / "canonical/bindings/keys.toml"
        p.write_text(p.read_text() + '''
[[key_binding]]
keys   = ["SUPER", "SHIFT", "X"]
action = "desktop.window.list"
label  = "One order"

[[key_binding]]
keys   = ["SHIFT", "SUPER", "X"]
action = "desktop.window.list"
label  = "The other order"
''')
        b.cap("render")   # isolate the control from the staleness check
        rc, out = b.cap("check")
        check("7n normalisation disabled -> assertion 7 fails",
              rc == 0 and "CONFLICT" not in out,
              "equivalent orders no longer collide, as expected")

    with Box() as b:
        # Restore the OLD narrow parser: only mainMod-prefixed single-modifier
        # chords. It read 30 of the real file's 75 bindings and reported the
        # other 45 as free. Nothing failed; the safeguard was just wrong.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            '        chord = _resolve(first, consts)',
            '        chord = _resolve(first, consts)\n'
            '        if chord and chord.count("+") > 1: chord = None\n'
            '        if chord is None: continue')
        with_vendor(b)
        rc, out = b.cap("preview")
        check("12n narrow parsing -> assertion 12 fails",
              rc == 0 and "SUPER + CONTROL + SHIFT + Right" not in out
              and "UNREADABLE" not in out,
              "multi-modifier and computed bindings vanish without a trace")

    with Box() as b:
        # Disable the family match, so a computed key is treated as no evidence.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            "        if pm == mods:", "        if False:")
        with_vendor(b)
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text() + '''
[[key_binding]]
keys   = ["SUPER", "ALT", "Q"]
action = "desktop.window.list"
label  = "In the computed family"
''')
        b.cap("render")
        rc, out = b.cap("check")
        check("15n family matching disabled -> assertion 15 fails",
              rc == 0 and "UNKNOWN" not in out,
              "the unprovable chord is reported free again")

    with Box() as b:
        # Collapse the refusal states back into one message, as they were when a
        # keypress on SUPER + G reported an unimplemented action as unavailable.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            '    title, template = REFUSAL[state]',
            '    title, template = REFUSAL["unavailable"]')
        rc, out = b.cap("act", "desktop.workspace.arrange")
        check("20n one shared wording -> assertion 20 fails",
              rc != 0 and "is unavailable" in out and "not implemented" not in out,
              "an unimplemented action reported as unavailable again")

    with Box() as b:
        # Disable render's UNKNOWN gate, leaving check's report intact. This is
        # the state the reviewer found: render writes, check objects afterwards.
        cap = b.repo / "bin" / "cap"
        patch(cap,
              "    unknown = [(chord_of(b), r[0]) for b in mine\n"
              "               if check_chord(chord_of(b), mine)[0]\n"
              "               and (r := unreadable_risk(norm_of(b), unreadable))]",
              "    unknown = []")
        with_vendor(b)
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text() + ALT_BINDING)
        rc, out = b.cap("render")
        rc2, _ = b.cap("check")
        check("17n render's UNKNOWN gate disabled -> assertion 17 fails",
              rc == 0 and rc2 != 0,
              "render writes and advises project; only the later check objects")

    with Box() as b:
        # Accept the alias instead of rejecting it, as MOD_ORDER used to.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            'MOD_ORDER = {"SUPER": 0, "CONTROL": 1, "ALT": 2, "SHIFT": 3, "MOD5": 4}',
            'MOD_ORDER = {"SUPER": 0, "CONTROL": 1, "CTRL": 1, "ALT": 2, "SHIFT": 3, "MOD5": 4}')
        p_ = b.repo / "canonical/bindings/keys.toml"
        p_.write_text(p_.read_text().replace('keys   = ["SUPER", "G"]',
                                             'keys   = ["CTRL", "G"]'))
        rc, out = b.cap("render")
        check("18n the alias accepted again -> assertion 18 fails",
              rc == 0 and "CTRL + G" in b.artifact(),
              "a spelling this compositor's table does not contain reaches the artifact")

    with Box() as b:
        # Drop the bare-token rejection, restoring the silent discard.
        cap = b.repo / "bin" / "cap"
        patch(cap, '        if "=" not in tok:', '        if False:')
        patch(cap, '        k, v = tok.split("=", 1)',
              '        if "=" not in tok: continue\n        k, v = tok.split("=", 1)')
        rc, out = b.cap("act", "desktop.application.ensure", "mail")
        check("25n bare-token rejection removed -> assertion 25 fails",
              "not name=value" not in out,
              "the word is dropped again and the failure moves elsewhere")

    with Box() as b:
        # Disable the invariant itself: report nothing unrecognised, whatever the
        # file says. This is the state the reviewer flagged — the accounting held
        # only in a fixture, so a shape nobody anticipated would just vanish.
        cap = b.repo / "bin" / "cap"
        patch(cap,
            "    return resolved, unresolved, max(0, _mentions(text) - len(sites))",
            "    return resolved, unresolved, 0")
        with_vendor(b, ODD_SHAPE)
        rc, out = b.cap("check")
        rc2, _ = b.cap("render")
        check("30n the invariant disabled -> assertions 30 and 31 fail",
              "unrecognised" in out and "0 unrecognised" in out and rc2 == 0,
              "the hidden binding is gone from the accounting and render proceeds")

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
