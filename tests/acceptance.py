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

import hashlib
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import tomllib

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDED = ["bin", "canonical", "derived", "adapters", "state", "CLAUDE.md", "AGENTS.md"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def patch(path, old, new):
    """Rewrite a file for a negative control, asserting the edit actually landed.

    A control whose anchor has drifted replaces nothing, leaves the mechanism
    intact, and PASSES — reporting that a disabled check still fails when it was
    never disabled. See tests/cap.py, where that happened twice in one session.
    """
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"negative control anchor not found: {old[:70]!r}")
    path.write_text(text.replace(old, new))


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
        # Restore the pre-projection state. Once the live repo has been projected its
        # vendor files already carry our region, and copying them would make "from a
        # clean tree" quietly false: nothing would be created, and the before-snapshot
        # would already contain what the test is about to add.
        for name in ("CLAUDE.md", "AGENTS.md"):
            p = self.repo / name
            data = p.read_bytes()
            span = region_span(data)
            if span:
                p.write_bytes(data[:span[0]] + data[span[1]:])
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


def region_span(data: bytes, marker=b"MACHINE-STATE POLICY"):
    """(start, stop) of our region including its trailing newline, or None."""
    begin, end = b"<!-- BEGIN " + marker + b" -->", b"<!-- END " + marker + b" -->"
    i = data.find(begin)
    if i == -1:
        return None
    j = data.find(end, i) + len(end)
    if data[j:j + 1] == b"\n":
        j += 1
    return i, j


def region_of(data: bytes, marker=b"MACHINE-STATE POLICY"):
    span = region_span(data, marker)
    return None if span is None else data[span[0]:span[1]].rstrip(b"\n")


def declared_target_count():
    """How many targets the manifests declare — never a hardcoded number.

    Asserting a literal count means the test breaks the day a manifest grows,
    reporting a failure where the real answer is "and one more".
    """
    n = 0
    for f in sorted((REPO / "adapters").glob("*.toml")):
        n += len(tomllib.loads(f.read_text()).get("target", []))
    return n


def shared_fragment_bytes():
    parts = [(REPO / p).read_bytes().rstrip(b"\n")
             for p in ("canonical/policy/00-generated.md", "canonical/policy/10-substrate.md")]
    return b"\n\n".join(parts)


def main():
    print("machine-state acceptance test\n")
    with Sandbox() as box:
        before = {f: box.read(f) for f in ("CLAUDE.md", "AGENTS.md")}

        # 1. PROJECT ---------------------------------------------------------
        want = declared_target_count()
        rc, out = box.ms("project")
        skill = box.home / ".claude" / "skills" / "machine-state"
        claude_region = region_of(box.read("CLAUDE.md"))
        agents_region = region_of(box.read("AGENTS.md"))
        shared = shared_fragment_bytes()
        check("1a project realises every target", rc == 0 and out.count("created") == want,
              f"{out.count('created')}/{want} created" if rc or out.count("created") != want else "")
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
              rc == 0 and "created" not in out and out.count("unchanged") == want
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

    # --- only canonical and derived may be a source (8cy.4) ----------------

    with Sandbox() as b:
        man = b.repo / "adapters" / "src.toml"
        base = ('[[target]]\nkind    = "render"\npath    = "~/.probe"\n'
                'sources = ["%s"]\n')

        # Assert on the REFUSAL, not on the exit code: a freshly declared target
        # is unprojected, so diff exits non-zero for a reason that has nothing to
        # do with the source rule. Conflating the two has misled this suite before.
        man.write_text(base % "derived/hypr/bindings.lua")
        _, out_ok = b.ms("diff")

        man.write_text(base % "CLAUDE.md")            # vendor-owned
        rc_vendor, out_vendor = b.ms("diff")

        man.write_text(base % "../../../etc/passwd")  # outside the repository
        rc_out, out_out = b.ms("diff")

        man.unlink()
        check("12 only canonical and derived may be an adapter source",
              "outside" not in out_ok and rc_vendor != 0 and rc_out != 0
              and "outside" in out_vendor and "outside" in out_out,
              "a vendor path and an escaping path are both refused")

    # --- a projection record belongs to one repo and one home (8cy / 7.5) ---

    with Sandbox() as box:
        # A record inherited from elsewhere names absolute paths outside this
        # tree. Orphan reconciliation acts on records no manifest claims, so
        # acting on a foreign record reaches out of the sandbox — which is
        # exactly how tests/machine.py unprojected the live workstation once.
        decoy = box.dir / "decoy.md"
        decoy.write_bytes(b"a real file belonging to another checkout\n")
        (box.repo / "state").mkdir(exist_ok=True)
        (box.repo / "state" / "projection.json").write_text(json.dumps({
            "schema": 1,
            "for": {"repo": "/elsewhere/machine-state", "home": "/elsewhere"},
            "targets": {str(decoy): {
                "kind": "render", "adapter": "gone",
                "sha": hashlib.sha256(decoy.read_bytes()).hexdigest(),
                "sources": ["canonical/policy/10-substrate.md"]}}}))
        rc, out = box.ms("project")
        check("13 a projection record from another repo or home is not acted on",
              decoy.exists() and "ignoring" in out,
              "its records name paths outside this tree, so they are left alone")

    # --- a check must not read as one thing and run as another (codex wiring) --

    with Sandbox() as box:
        rec = box.repo / "canonical" / "tooling" / "probe.md"
        rec.write_text("# Probe\n\n## Verification\n\n```toml\n"
                       'group   = "Probe"\n'
                       'version = "true"\n'
                       'check   = "grep -q needle /etc/hostname && grep -q needle /etc/os-release"\n'
                       'ok      = "ok"\nfail = "no"\nmissing = "gone"\n```\n')
        rc, out = box.ms("status")
        refused = rc != 0 and "do not run in a shell" in out and "sh -c" in out

        # the same intent, written so it actually runs that way, is accepted
        rec.write_text(rec.read_text().replace(
            'check   = "grep -q needle /etc/hostname && grep -q needle /etc/os-release"',
            'check   = "sh -c \'grep -q needle /etc/hostname && grep -q needle /etc/os-release\'"'))
        rc2, out2 = box.ms("status")
        rec.unlink()
        check("14 a check using shell operators is refused, not silently mis-run",
              refused and "do not run in a shell" not in out2,
              "checks run without a shell, so `a && b` would pass b to a as arguments")

    # --- ms changes: query the package db, do not watch it (machine-state-2zm) --

    def seed(box):
        """Record the machine, then rewrite the mark to describe an earlier one."""
        (box.repo / "state" / "machine.json").unlink(missing_ok=True)
        box.ms("changes")
        m = box.repo / "state" / "machine.json"
        d = json.loads(m.read_text())
        pk = d["packages"]
        victim = sorted(pk)[0]
        d["packages"] = {k: v for k, v in pk.items() if k != victim}
        second = sorted(pk)[1]
        d["packages"][second] = {**pk[second], "version": "0.0.0-old"}
        d["packages"]["ghost-pkg"] = {"version": "1.0", "at": 0}
        # A loose entry the sandbox PATH cannot resolve, pointing at a real file.
        # Re-checking it at its RECORDED path is the behaviour under test: without
        # that, a narrower PATH silently drops tools from the inventory.
        d.setdefault("loose", {})["probe-tool"] = {
            "path": str(box.repo / "bin" / "ms"), "sha": "0" * 64}
        m.write_text(json.dumps(d, indent=2, sort_keys=True))
        return victim, second

    with Sandbox() as box:
        victim, second = seed(box)
        rc, out = box.ms("changes")
        check("15 changes are found by querying recorded state, not by watching",
              rc == 1 and f"added     {victim}" in out and f"upgraded  {second}" in out
              and "removed   ghost-pkg" in out and "replaced" in out,
              "add, upgrade, remove and an unpackaged replacement, all retroactive")

        rc2, out2 = box.ms("changes", "--record")
        rc3, out3 = box.ms("changes")
        check("16 --record accepts the machine as seen, and then it is quiet",
              rc2 == 0 and rc3 == 0 and "nothing changed" in out3,
              "the mark composes: exit 1 pending, exit 0 clean")

    # --- a tooling record declares the machine should have the tool (an1) ----

    GHOST = ("# Ghost\n\n## Verification\n\n```toml\n"
             'group   = "Applications"\n'
             'version = "definitely-not-a-real-command-xyz --version"\n'
             'check   = "definitely-not-a-real-command-xyz"\n'
             'ok      = "ok"\nfail = "no"\nmissing = "not installed"\n```\n')

    with Sandbox() as box:
        rec = box.repo / "canonical" / "tooling" / "ghost.md"
        rec.write_text(GHOST)
        rc, out = box.ms("status")
        rec.unlink()
        check("17 a recorded tool that is absent fails the run",
              rc == 1 and "ghost" in out and "recorded here but not installed" in out,
              "a record is the declaration that the machine should have it")

    # negative controls ------------------------------------------------------
    print("\n  negative controls (the mechanism is broken on purpose):")
    with Sandbox() as box:
        ms = box.repo / "bin" / "ms"
        patch(ms,
              'return (OK, "region matches") if have == region(t) else (DRIFT, "region differs")',
              'return OK, "region matches"')
        box.ms("project")
        p = box.repo / "CLAUDE.md"
        p.write_bytes(box.read("CLAUDE.md").replace(b"<!-- END MACHINE-STATE POLICY -->",
                                                    b"tampered\n<!-- END MACHINE-STATE POLICY -->"))
        rc, _ = box.ms("diff")
        check("3n assertion 3 fails when drift detection is disabled", rc == 0,
              "drift went unreported, as expected of a broken detector")

    with Sandbox() as box:
        ms = box.repo / "bin" / "ms"
        patch(ms, "    return status != FOREIGN", "    return True")
        foreign = box.repo / "HANDWRITTEN.md"
        foreign.write_bytes(b"a human wrote this and it was never projected\n")
        (box.repo / "adapters" / "zz-scratch.toml").write_text(
            '[[target]]\nkind = "render"\npath = "./HANDWRITTEN.md"\n'
            'sources = ["canonical/policy/10-substrate.md"]\n')
        box.ms("project")
        check("5n assertion 5 fails when the refusal is disabled",
              foreign.read_bytes() != b"a human wrote this and it was never projected\n",
              "the file was clobbered, as expected of a broken guard")

    with Sandbox() as b:
        # Remove the enforcement, leaving the rule as prose again — which is the
        # state that let a generated file become a canonical source unnoticed.
        ms = b.repo / "bin" / "ms"
        patch(ms, "            for rel in t[\"sources\"]:\n"
                  "                check_source(t, rel)\n", "")
        man = b.repo / "adapters" / "src.toml"
        man.write_text('[[target]]\nkind    = "render"\npath    = "~/.probe"\n'
                       'sources = ["CLAUDE.md"]\n')
        _, out = b.ms("diff")
        man.unlink()
        check("12n source enforcement removed -> assertion 12 fails",
              "outside" not in out,
              "a vendor path is accepted as a source again, silently")

    with Sandbox() as box:
        # Remove the identity check, and the foreign record is obeyed again.
        ms = box.repo / "bin" / "ms"
        patch(ms, "    if was is not None and was != ident:", "    if False:")
        decoy = box.dir / "decoy.md"
        decoy.write_bytes(b"a real file belonging to another checkout\n")
        (box.repo / "state").mkdir(exist_ok=True)
        (box.repo / "state" / "projection.json").write_text(json.dumps({
            "schema": 1,
            "for": {"repo": "/elsewhere/machine-state", "home": "/elsewhere"},
            "targets": {str(decoy): {
                "kind": "render", "adapter": "gone",
                "sha": hashlib.sha256(decoy.read_bytes()).hexdigest(),
                "sources": ["canonical/policy/10-substrate.md"]}}}))
        box.ms("project")
        check("13n identity check removed -> assertion 13 fails",
              not decoy.exists(),
              "a file in another checkout is deleted by this one")

    with Sandbox() as box:
        # Remove the guard: the record then reads as a conjunction and runs as
        # grep searching extra files, which is how a wiring check reported a
        # guarded harness whose hook was never trusted.
        ms = box.repo / "bin" / "ms"
        patch(ms, "    bad = [tok for tok in argv if tok in SHELL_OPS]", "    bad = []")
        rec = box.repo / "canonical" / "tooling" / "probe.md"
        rec.write_text("# Probe\n\n## Verification\n\n```toml\n"
                       'group   = "Probe"\n'
                       'version = "true"\n'
                       'check   = "grep -q root /etc/passwd && grep -q nomatchxyz /etc/hostname"\n'
                       'ok      = "ok"\nfail = "no"\nmissing = "gone"\n```\n')
        rc, out = box.ms("status")
        rec.unlink()
        check("14n operator guard removed -> assertion 14 fails",
              "do not run in a shell" not in out and "ok" in out,
              "the false half never runs; the check passes on the first file alone")

    with Sandbox() as box:
        # Disable the comparison itself. The command still runs, still reads the
        # machine, still prints — and reports nothing, which is the shape of a
        # detector that has quietly stopped detecting.
        ms = box.repo / "bin" / "ms"
        patch(ms, "    added   = [n for n in pkgs if n not in old_p]",
                  "    added   = []")
        seed(box)
        rc, out = box.ms("changes")
        check("15n the added-package comparison disabled -> assertion 15 fails",
              "added     " not in out,
              "a package that appeared since the mark goes unreported")

    with Sandbox() as box:
        # Stop counting absent tools. The line still prints "not installed", so the
        # surface looks identical — which is precisely the state before an1: a
        # record described something installed instead of asserting it should be.
        ms = box.repo / "bin" / "ms"
        patch(ms, "                        absent.append(tool[\"name\"])", "                        pass")
        rec = box.repo / "canonical" / "tooling" / "ghost.md"
        rec.write_text(GHOST)
        rc, out = box.ms("status")
        rec.unlink()
        check("17n absence no longer counted -> assertion 17 fails",
              "recorded here but not installed" not in out and "not installed" in out,
              "the tool is still shown missing and the run passes anyway")

    failed = [n for n, ok, _ in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
