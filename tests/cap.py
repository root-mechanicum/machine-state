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
            out.append('keys   = ["%s", "%s"]' % tuple(b["keys"]))
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

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
