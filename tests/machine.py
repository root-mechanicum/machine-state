#!/usr/bin/env python3
"""Test for bin/machine — the coordinator built after bru.7.5 measured the need.

The eval found that the two-step workflow does not fail silently; it fails
REASSURINGLY. Whichever step is outstanding, the other tool reports success. So
the first two assertions are about the exact states where a single tool lies,
and the rest are about recovery — because a coordinator that only detects sooner
adds a step without adding safety.

Hermetic: every case runs against a throwaway copy of the repository with HOME
redirected, so it never touches the working tree or the live desktop.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
# state/ is NOT copied. Its projection record holds absolute paths into the real
# $HOME and the real repository, and orphan reconciliation acts on records no
# manifest claims. Copying it made this sandbox able to reach outside itself —
# which it did, unprojecting the live workstation. bin/ms now refuses a foreign
# record as well; both guards are wanted, since either alone was enough to fail.
NEEDED = ["bin", "canonical", "derived", "adapters"]
ART = "derived/hypr/bindings.lua"

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def patch(path, old, new):
    """Assert the edit landed. See tests/cap.py for why this is not optional."""
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"anchor not found: {old[:70]!r}")
    path.write_text(text.replace(old, new))


class Box:
    def __enter__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="machine-"))
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        for item in NEEDED:
            src = REPO / item
            if src.is_dir():
                shutil.copytree(src, self.repo / item, symlinks=True)
        (self.repo / "state").mkdir()
        # a vendor file, so cap has something real to fingerprint
        v = self.dir / ".config" / "hypr" / "config"
        v.mkdir(parents=True)
        (v / "binds.lua").write_text('local mainMod = "SUPER"\n')
        self.vendor = v / "binds.lua"
        # only the hypr adapter; the others target files this sandbox has no copy of
        for f in (self.repo / "adapters").glob("*.toml"):
            if f.stem != "hypr":
                f.unlink()
        return self

    def __exit__(self, *_):
        shutil.rmtree(self.dir, ignore_errors=True)

    def run(self, tool, *args):
        r = subprocess.run([str(self.repo / "bin" / tool), *args],
                           capture_output=True, text=True, cwd=self.repo,
                           env={"HOME": str(self.dir), "PATH": "/usr/bin:/bin"})
        return r.returncode, r.stdout + r.stderr

    def artifact(self):
        p = self.repo / ART
        return p.read_text() if p.exists() else None

    def add_binding(self, chord="SUPER + N"):
        keys = ", ".join(f'"{k}"' for k in chord.split(" + "))
        p = self.repo / "canonical/bindings/keys.toml"
        p.write_text(p.read_text() + f'\n[[key_binding]]\nkeys   = [{keys}]\n'
                     'action = "desktop.window.list"\nlabel  = "Added"\n')


def stub_cap(b, body):
    """Replace bin/cap with a shim that delegates except where the test needs it."""
    real = b.repo / "bin" / "cap.real"
    shutil.copy2(b.repo / "bin" / "cap", real)
    shim = b.repo / "bin" / "cap"
    shim.write_text("#!/usr/bin/env python3\n"
                    "import os, pathlib, subprocess, sys\n"
                    f"REAL = {str(real)!r}\n"
                    + body +
                    "sys.exit(subprocess.run([REAL, *sys.argv[1:]]).returncode)\n")
    shim.chmod(0o755)


def main():
    print("machine coordinator test\n")

    with Box() as b:
        b.run("machine", "apply")
        rc, out = b.run("machine", "status")
        check("1  a current machine reports current",
              rc == 0 and "matches the declarations" in out)

        # STATE A: declaration edited, nothing rendered. ms diff alone says fine.
        b.add_binding()
        ms_rc, _ = b.run("ms", "diff")
        rc, out = b.run("machine", "status")
        check("2  status catches a pending render that ms diff calls clean",
              ms_rc == 0 and rc != 0 and "cap render is pending" in out,
              "ms diff exits 0 here — the reassuring failure")

        # STATE B: rendered, not projected. cap check alone says fine.
        b.run("cap", "render")
        cap_rc, _ = b.run("cap", "check")
        rc, out = b.run("machine", "status")
        check("3  status catches a pending project that cap check calls clean",
              cap_rc == 0 and rc != 0 and "ms project is pending" in out,
              "cap check exits 0 here — the same failure from the other side")

        rc, out = b.run("machine", "apply")
        rc2, _ = b.run("machine", "status")
        check("4  apply runs the whole sequence and leaves both clean",
              rc == 0 and rc2 == 0 and "post-check" in out
              and "vendor unchanged" in out and "SUPER + N" in b.artifact())

    # --- the race: the vendor file changes inside the render window ----------

    with Box() as b:
        b.run("machine", "apply")
        good_art = b.artifact()
        good_live = (b.dir / ".config/hypr/config/machine-state.lua").read_text()
        b.add_binding("SUPER + O")
        stub_cap(b, "if sys.argv[1] == 'render':\n"
                    "    p = pathlib.Path(os.environ['HOME'])/'.config/hypr/config/binds.lua'\n"
                    "    r = subprocess.run([REAL, *sys.argv[1:]])\n"
                    "    p.write_text(p.read_text() + 'hl.bind(mainMod .. \" + O\", x())\\n')\n"
                    "    sys.exit(r.returncode)\n")
        rc, out = b.run("machine", "apply")
        live = (b.dir / ".config/hypr/config/machine-state.lua").read_text()
        check("5  a vendor change during render is caught before projection",
              rc != 0 and "vendor unchanged" in out and "no longer exists" in out
              and live == good_live,
              "cap checked a version of the file that no longer exists")
        check("6  and the artifact is left as it was, not half-updated",
              b.artifact() == good_art,
              "nothing was projected, so nothing needs undoing on the machine")

    # --- rollback: the post-check fails after projection ---------------------

    with Box() as b:
        b.run("machine", "apply")
        good_art = b.artifact()
        good_live = (b.dir / ".config/hypr/config/machine-state.lua").read_text()
        b.add_binding("SUPER + R")
        stub_cap(b, "if sys.argv[1] == 'check':\n"
                    "    print('CONFLICT  something changed underneath us')\n"
                    "    sys.exit(1)\n")
        rc, out = b.run("machine", "apply")
        live = (b.dir / ".config/hypr/config/machine-state.lua").read_text()
        check("7  a failed post-check rolls back to the last good projection",
              rc == 1 and "ROLLING BACK" in out and b.artifact() == good_art
              and live == good_live,
              "the machine is back where it was, and the output says so")
        check("8  the rollback is loud, not silent",
              "reverted with it" in out and "post-check failed" in out,
              "a silent revert would look like the change simply not working")

    # --- negative controls ---------------------------------------------------
    print("\n  negative controls (the mechanism is broken on purpose):")

    with Box() as b:
        m = b.repo / "bin" / "machine"
        patch(m, "    if cap_rc or ms_rc:", "    if ms_rc:")
        b.run("machine", "apply")
        b.add_binding("SUPER + U")
        rc, out = b.run("machine", "status")
        check("2n status ignoring cap -> assertion 2 fails",
              rc == 0 and "matches the declarations" in out,
              "the pending render is invisible again, exactly as ms diff alone saw it")

    with Box() as b:
        m = b.repo / "bin" / "machine"
        patch(m, "    if after_vendor != before_vendor:", "    if False:")
        b.run("machine", "apply")
        b.add_binding("SUPER + Y")
        stub_cap(b, "if sys.argv[1] == 'render':\n"
                    "    p = pathlib.Path(os.environ['HOME'])/'.config/hypr/config/binds.lua'\n"
                    "    r = subprocess.run([REAL, *sys.argv[1:]])\n"
                    "    p.write_text(p.read_text() + 'hl.bind(mainMod .. \" + Y\", x())\\n')\n"
                    "    sys.exit(r.returncode)\n")
        rc, out = b.run("machine", "apply")
        check("5n fingerprint comparison disabled -> assertion 5 fails",
              "no longer exists" not in out,
              "the race goes unreported and projection proceeds")

    with Box() as b:
        m = b.repo / "bin" / "machine"
        patch(m, "        return rollback(kept, \"the post-check failed after projection\")",
              "        return 1")
        b.run("machine", "apply")
        good_art = b.artifact()
        b.add_binding("SUPER + I")
        stub_cap(b, "if sys.argv[1] == 'check':\n    sys.exit(1)\n")
        rc, out = b.run("machine", "apply")
        check("7n rollback removed -> assertion 7 fails",
              "ROLLING BACK" not in out and b.artifact() != good_art,
              "the failed projection stays on the machine")

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
