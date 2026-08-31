#!/usr/bin/env python3
"""Acceptance test for the machine-state substrate.

One invariant, five assertions plus teardown:

    canonical is truth, and projections are derived.

Hermetic by construction. Every assertion runs against a throwaway copy of the
repository with HOME redirected into the sandbox, so the test never touches the
real ~/.claude, never modifies the working tree, and is safe to run at any time.

Two of the assertions carry negative controls: the test deliberately breaks the
mechanism and confirms the assertion then fails. An assertion that cannot fail
is not an assertion.

Exit 0 = the substrate works.
"""

import pathlib
import shutil
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDED = ["bin", "canonical", "adapters", "state", "CLAUDE.md", "AGENTS.md"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


class Sandbox:
    def __enter__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="ms-acceptance-"))
        self.repo = self.dir / "repo"
        self.home = self.dir / "home"
        self.repo.mkdir()
        self.home.mkdir()
        for item in NEEDED:
            src = REPO / item
            dst = self.repo / item
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=True)
            else:
                shutil.copy2(src, dst)
        (self.repo / "state" / "projection.json").write_text('{\n  "schema": 1,\n  "targets": {}\n}\n')
        return self

    def __exit__(self, *_):
        shutil.rmtree(self.dir, ignore_errors=True)

    def ms(self, *args):
        r = subprocess.run([str(self.repo / "bin" / "ms"), *args],
                           capture_output=True, text=True,
                           env={"HOME": str(self.home), "PATH": "/usr/bin:/bin"})
        return r.returncode, r.stdout + r.stderr

    def read(self, rel):
        return (self.repo / rel).read_bytes()


def region_of(data: bytes, marker=b"MACHINE-STATE POLICY"):
    begin, end = b"<!-- BEGIN " + marker + b" -->", b"<!-- END " + marker + b" -->"
    i = data.find(begin)
    if i == -1:
        return None
    j = data.find(end, i) + len(end)
    return data[i:j]


def shared_fragment_bytes():
    parts = [(REPO / p).read_bytes().rstrip(b"\n")
             for p in ("canonical/policy/00-generated.md", "canonical/policy/10-substrate.md")]
    return b"\n\n".join(parts)


def main():
    print("machine-state acceptance test\n")
    with Sandbox() as box:
        before = {f: box.read(f) for f in ("CLAUDE.md", "AGENTS.md")}

        # 1. PROJECT ---------------------------------------------------------
        rc, out = box.ms("project")
        skill = box.home / ".claude" / "skills" / "machine-state"
        claude_region = region_of(box.read("CLAUDE.md"))
        agents_region = region_of(box.read("AGENTS.md"))
        shared = shared_fragment_bytes()
        check("1a project realises every target", rc == 0 and out.count("created") == 3,
              out.strip().splitlines()[-1] if rc else "")
        check("1b the HOME crossing is a symlink into canonical",
              skill.is_symlink() and skill.resolve() == (box.repo / "canonical/skills/machine-state").resolve())
        check("1c both harnesses receive the shared fragments byte-for-byte",
              claude_region is not None and agents_region is not None
              and shared in claude_region and shared in agents_region)
        check("1d each vendor file is untouched outside our region",
              all(before[f] == box.read(f).replace(region_of(box.read(f)) + b"\n", b"")
                  for f in ("CLAUDE.md", "AGENTS.md")))

        # 2. IDEMPOTENT ------------------------------------------------------
        snap = {f: box.read(f) for f in ("CLAUDE.md", "AGENTS.md")}
        state1 = box.read("state/projection.json")
        rc, out = box.ms("project")
        check("2  a second project changes nothing",
              rc == 0 and "created" not in out and out.count("unchanged") == 3
              and all(snap[f] == box.read(f) for f in snap)
              and state1 == box.read("state/projection.json"))

        # 3. DRIFT -----------------------------------------------------------
        p = box.repo / "CLAUDE.md"
        p.write_bytes(box.read("CLAUDE.md").replace(
            b"<!-- END MACHINE-STATE POLICY -->", b"a human edited this\n<!-- END MACHINE-STATE POLICY -->"))
        rc, out = box.ms("diff")
        check("3  drift is detected and names the file", rc != 0 and "CLAUDE.md" in out)

        # 4. RESTORE ---------------------------------------------------------
        box.ms("project")
        check("4  canonical wins: the edit is gone, byte-for-byte",
              box.read("CLAUDE.md") == snap["CLAUDE.md"])

        # 5. FOREIGN ---------------------------------------------------------
        foreign = box.repo / "HANDWRITTEN.md"
        foreign.write_bytes(b"a human wrote this and it was never projected\n")
        (box.repo / "adapters" / "zz-scratch.toml").write_text(
            '[[target]]\nkind = "render"\npath = "./HANDWRITTEN.md"\n'
            'sources = ["canonical/policy/10-substrate.md"]\n')
        rc, out = box.ms("project")
        check("5  a file we never created is refused, not clobbered",
              rc != 0 and "REFUSED" in out
              and foreign.read_bytes() == b"a human wrote this and it was never projected\n")
        (box.repo / "adapters" / "zz-scratch.toml").unlink()
        box.ms("project")

        # 6. TEARDOWN --------------------------------------------------------
        rc, out = box.ms("unproject")
        check("6  unproject restores the vendor files exactly and leaves nothing",
              rc == 0
              and all(before[f] == box.read(f) for f in before)
              and not skill.exists() and not skill.is_symlink()
              and not (box.repo / "POLICY.md").exists())

    # negative controls ------------------------------------------------------
    print("\n  negative controls (the mechanism is broken on purpose):")
    with Sandbox() as box:
        ms = box.repo / "bin" / "ms"
        ms.write_text(ms.read_text().replace(
            'return (OK, "region matches") if have == region(t) else (DRIFT, "region differs")',
            'return OK, "region matches"'))
        box.ms("project")
        p = box.repo / "CLAUDE.md"
        p.write_bytes(box.read("CLAUDE.md").replace(b"<!-- END MACHINE-STATE POLICY -->",
                                                    b"tampered\n<!-- END MACHINE-STATE POLICY -->"))
        rc, _ = box.ms("diff")
        check("3n assertion 3 fails when drift detection is disabled", rc == 0,
              "drift went unreported, as expected of a broken detector")

    with Sandbox() as box:
        ms = box.repo / "bin" / "ms"
        ms.write_text(ms.read_text().replace("    return status != FOREIGN", "    return True"))
        foreign = box.repo / "HANDWRITTEN.md"
        foreign.write_bytes(b"a human wrote this and it was never projected\n")
        (box.repo / "adapters" / "zz-scratch.toml").write_text(
            '[[target]]\nkind = "render"\npath = "./HANDWRITTEN.md"\n'
            'sources = ["canonical/policy/10-substrate.md"]\n')
        box.ms("project")
        check("5n assertion 5 fails when the refusal is disabled",
              foreign.read_bytes() != b"a human wrote this and it was never projected\n",
              "the file was clobbered, as expected of a broken guard")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
