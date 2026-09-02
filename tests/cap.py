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

import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDED = ["bin", "canonical", "adapters", "state"]
ART = "canonical/desktop/hypr/bindings.lua"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


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
        (vend / "binds.lua").write_text('-- fake\n')
        b.cap("render")
        rc_before, _ = b.cap("check")
        (vend / "binds.lua").write_text(
            '-- fake\nhl.bind(mainMod .. " + M", hl.dsp.exec_cmd("something-else"))\n')
        rc_after, out = b.cap("check")
        check("11 a vendor claim after render is detected, not prevented",
              rc_before == 0 and rc_after != 0 and "CONFLICT" in out
              and "ok       artifact" in out,
              "artifact is not stale — the world changed, not the file")

    # --- negative controls -------------------------------------------------
    print("\n  negative controls (the mechanism is broken on purpose):")

    with Box() as b:
        cap = b.repo / "bin" / "cap"
        # Disable the COMPARISON, not the existence branch: replacing
        # `if RENDERED.exists()` falls through to the elif that reports a
        # missing artifact, so a problem is still raised and the control would
        # test nothing. The first attempt did exactly that.
        cap.write_text(cap.read_text().replace(
            "        if on_disk != expected:", "        if False:"))
        b.cap("render")
        (b.repo / ART).write_text("-- hand edited, nothing else\n")
        rc, _ = b.cap("check")
        check("5n stale detection disabled -> assertion 5 fails", rc == 0,
              "staleness went unreported, as expected of a disabled check")

    with Box() as b:
        # the failure that made a broken surface look like an empty one
        cap = b.repo / "bin" / "cap"
        cap.write_text(cap.read_text().replace(
            "            free, holder = check_chord(chord)",
            "            free, holder = check_chord(chord); STALE_REFERENCE_LIKE_THE_OLD_BUG"))
        rc, out = b.cap("preview")
        stdout_only = subprocess.run([str(cap), "preview"], capture_output=True, text=True,
                                     cwd=b.repo, env={"HOME": str(b.dir), "PATH": "/usr/bin:/bin"})
        check("Xn a broken surface never resembles an empty one",
              rc != 0 and stdout_only.stdout.strip() == "" and "could not be built" in out,
              "no header, no partial rows, clear error, non-zero exit")

    with Box() as b:
        # Disable normalisation itself, so chords are compared as declared.
        cap = b.repo / "bin" / "cap"
        cap.write_text(cap.read_text().replace(
            '    mods = sorted(dict.fromkeys(k for k in ks if k in MOD_ORDER),\n'
            '                  key=lambda k: MOD_ORDER[k])',
            '    mods = [k for k in ks if k in MOD_ORDER]'))
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

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
