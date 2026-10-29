#!/usr/bin/env python3
"""Event path test for bin/cap — machine-state-bru.4.5.

    unbound      -> recorded, nothing runs
    ungranted    -> every response refused and recorded; no side effect
    granted      -> one event, two responses, one of them an agent, one event id
    boundary     -> a user-writable grants directory is not trusted
    relabel      -> a grant follows the implementation, not the action's name
    class        -> commit never runs from an event, granted or not
    isolation    -> a response that crashes does not stop the next one
    loopback     -> the model endpoint cannot be moved off the machine
    quiet        -> a notification repeats only for a new kind of error
    inbox        -> notes are listed, shown, and marked read
    envelope     -> malformed events are usage errors, not events

Hermetic: a throwaway copy of the repository, stub journalctl and notify-send,
and a fake model server on loopback. Nothing reaches the live desktop, the real
journal, the real model or /etc.

Each mechanism carries a negative control: the copy is patched to disable it and
the matching assertion must then fail. An assertion that cannot fail is not one.
"""

import http.server
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
import threading

REPO = pathlib.Path(__file__).resolve().parent.parent
NEEDED = ["bin", "canonical", "derived", "adapters", "state"]

results = []


def check(name, ok, detail=""):
    results.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))
    return ok


def patch(path, old, new):
    """Rewrite a file for a control, asserting the edit actually landed."""
    text = path.read_text()
    if old not in text:
        raise AssertionError(f"patch anchor not found: {old[:70]!r}")
    path.write_text(text.replace(old, new))


JOURNAL_FIXTURE = [
    {"SYSLOG_IDENTIFIER": "kernel", "MESSAGE": "spd5118 17-0053: PM: failed to resume async: error -6"},
    {"SYSLOG_IDENTIFIER": "kernel", "MESSAGE": "spd5118 17-0051: PM: failed to resume async: error -6"},
    {"SYSLOG_IDENTIFIER": "nm-dispatcher", "MESSAGE": "failed to activate"},
]

GRANT_BOTH = """
[[grant]]
event = "time.daily"
action = "journal.errors.notify"
implementation = "journal.errors.notify"
class = "report"

[[grant]]
event = "time.daily"
action = "journal.digest"
implementation = "journal.digest"
class = "report"
"""


class Model(http.server.BaseHTTPRequestHandler):
    fail = False

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send(200, {"data": [{"id": "fake-model"}]})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if Model.fail:
            return self._send(500, {"error": "boom"})
        self._send(200, {"choices": [{"message": {"content": "FAKE DIGEST BODY"}}]})

    def log_message(self, *_):
        pass


class Box:
    """A repository copy, stub tools, and a place for grants that is not /etc."""

    def __init__(self, grants=None, trust_grants=True):
        self.grants, self.trust = grants, trust_grants

    def __enter__(self):
        self.dir = pathlib.Path(tempfile.mkdtemp(prefix="cap-events-"))
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        for item in NEEDED:
            src, dst = REPO / item, self.repo / item
            if src.is_dir():
                shutil.copytree(src, dst, symlinks=True)
        (self.repo / "state" / "actions.jsonl").unlink(missing_ok=True)
        self.cap_path = self.repo / "bin" / "cap"
        # Grants can't be root-owned in a test, so the copy reads them from here.
        # The boundary check is bypassed only where the case says so.
        gdir = self.dir / "etc-machine-state"
        gdir.mkdir()
        patch(self.cap_path, 'GRANTS = pathlib.Path("/etc/machine-state/grants.toml")',
              f'GRANTS = pathlib.Path("{gdir}/grants.toml")')
        if self.grants is not None:
            (gdir / "grants.toml").write_text(self.grants)
        if self.trust:
            patch(self.cap_path,
                  '    """(intact, reason). The same two-level check bin/ms reports on."""\n',
                  '    """(intact, reason). The same two-level check bin/ms reports on."""\n'
                  '    return GRANTS.exists(), None if GRANTS.exists() else "no grants file"\n')
        stubs = self.dir / "stubs"
        stubs.mkdir()
        self.journal(JOURNAL_FIXTURE)
        (stubs / "journalctl").write_text(f'#!/bin/sh\ncat "{self.dir}/journal.jsonl"\n')
        (stubs / "notify-send").write_text(
            f'#!/bin/sh\nprintf "%s\\n" "$*" >> "{self.dir}/notify.log"\n')
        for f in stubs.iterdir():
            f.chmod(0o755)
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Model)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = {"HOME": str(self.dir), "PATH": f"{stubs}:/usr/bin:/bin",
                    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
                    "CAP_MODEL_URL": f"http://127.0.0.1:{self.server.server_port}/v1"}
        return self

    def __exit__(self, *_):
        self.server.shutdown()
        Model.fail = False
        shutil.rmtree(self.dir, ignore_errors=True)

    def cap(self, *args, **env):
        r = subprocess.run([str(self.cap_path), *args], capture_output=True, text=True,
                           cwd=self.repo, env={**self.env, **env}, timeout=60)
        return r.returncode, r.stdout + r.stderr

    def journal(self, entries):
        (self.dir / "journal.jsonl").write_text("\n".join(json.dumps(e) for e in entries) + "\n")

    def records(self):
        p = self.repo / "state" / "actions.jsonl"
        return [json.loads(l) for l in p.read_text().splitlines()] if p.exists() else []

    def notified(self):
        p = self.dir / "notify.log"
        return p.read_text() if p.exists() else ""

    def notes(self):
        d = self.dir / ".local" / "state" / "agents" / "inbox"
        return sorted(d.glob("*.md")) if d.is_dir() else []

    def bindings(self, text):
        (self.repo / "canonical" / "bindings" / "events.toml").write_text(text)


# ---------------------------------------------------------------- cases
# Each returns (ok, detail) so a control can rerun it against a patched copy.

def case_unbound(b):
    rc, out = b.cap("emit", "time.nothing", "--source", "timer")
    recs = b.records()
    ok = (rc == 0 and len(recs) == 1 and recs[0].get("outcome") == "unbound"
          and not b.notified() and not b.notes())
    return ok, f"rc={rc}, {len(recs)} record(s)"


def case_ungranted(b):
    rc, out = b.cap("emit", "time.daily", "--source", "timer")
    acts = [r for r in b.records() if r.get("action")]
    ok = (rc == 1 and len(acts) == 2 and all(r["state"] == "ungranted" for r in acts)
          and not b.notified() and not b.notes())
    return ok, f"rc={rc}, states={[r.get('state') for r in acts]}"


def case_granted(b):
    rc, out = b.cap("emit", "time.daily", "--source", "timer")
    recs = b.records()
    ev = [r for r in recs if r.get("kind") == "event"]
    acts = [r for r in recs if r.get("action")]
    notes = b.notes()
    body = notes[0].read_text() if notes else ""
    ok = (rc == 0 and len(ev) == 1 and len(acts) == 2
          and all(r["outcome"] == "ok" and r["event"] == ev[0]["id"] for r in acts)
          and "2 new kind(s)" in b.notified() and "cap inbox" in b.notified()
          and "FAKE DIGEST BODY" in body and f"event: {ev[0]['id']}" in body)
    return ok, f"rc={rc}, outcomes={[r.get('outcome') for r in acts]}, notes={len(notes)}"


def case_relabel(b):
    # An agent edits canonical/ so the granted name now runs another provider.
    p = b.repo / "canonical" / "actions" / "journal.toml"
    patch(p, 'implementation = "journal.digest"', 'implementation = "journal.errors.notify"')
    b.cap("emit", "time.daily", "--source", "timer")
    d = [r for r in b.records() if r.get("action") == "journal.digest"]
    ok = len(d) == 1 and d[0].get("state") == "ungranted"
    return ok, f"journal.digest -> {d[0].get('state') if d else None}"


COMMIT_BINDING = '''
[action."test.commit"]
implementation = "journal.errors.notify"
label       = "A commit-class action wearing a harmless implementation"
category    = "Test"
consequence = "commit"
'''


def case_commit(b):
    (b.repo / "canonical" / "actions" / "test.toml").write_text(COMMIT_BINDING)
    b.bindings('[[event_binding]]\nevent = "time.daily"\naction = "test.commit"\n')
    (b.dir / "etc-machine-state" / "grants.toml").write_text(
        '[[grant]]\nevent = "time.daily"\naction = "test.commit"\n'
        'implementation = "journal.errors.notify"\nclass = "commit"\n')
    b.cap("emit", "time.daily", "--source", "timer")
    rc, out = b.cap("check")
    r = [x for x in b.records() if x.get("action") == "test.commit"]
    ok = (len(r) == 1 and r[0].get("state") == "ungranted" and not b.notified()
          and rc == 1 and "NEVER" in out)
    return ok, f"state={r[0].get('state') if r else None}, check rc={rc}"


def case_isolation(b):
    # The agent response first, and failing; the plain one after it must still run.
    b.bindings('[[event_binding]]\nevent = "time.daily"\naction = "journal.digest"\n\n'
               '[[event_binding]]\nevent = "time.daily"\naction = "journal.errors.notify"\n')
    Model.fail = True
    rc, out = b.cap("emit", "time.daily", "--source", "timer")
    acts = {r["action"]: r for r in b.records() if r.get("action")}
    d, n = acts.get("journal.digest", {}), acts.get("journal.errors.notify", {})
    ok = (rc == 1 and d.get("state") == "failed" and n.get("outcome") == "ok"
          and "new kind(s)" in b.notified() and "Traceback" not in out)
    return ok, f"digest={d.get('state')}, notify={n.get('outcome')}"


def case_quiet(b):
    # Same kinds again -> silent; a new kind -> one more notification.
    b.cap("emit", "time.daily", "--source", "timer")
    rc, _ = b.cap("emit", "time.daily", "--source", "timer")
    quiet = len(b.notified().splitlines())
    b.journal(JOURNAL_FIXTURE + [{"SYSLOG_IDENTIFIER": "bluetoothd", "MESSAGE": "new trouble"}])
    b.cap("emit", "time.daily", "--source", "timer")
    lines = b.notified().splitlines()
    n = [r for r in b.records() if r.get("action") == "journal.errors.notify"]
    ok = (rc == 0 and quiet == 1 and len(lines) == 2 and "1 new kind(s)" in lines[1]
          and "bluetoothd" in lines[1] and [r["outcome"] for r in n] == ["ok", "skipped", "ok"])
    return ok, f"notifications after repeat={quiet}, after new kind={len(lines)}"


def case_inbox(b):
    b.cap("emit", "time.daily", "--source", "timer")
    _, listed = b.cap("inbox")
    rc, shown = b.cap("inbox", "show")
    _, after = b.cap("inbox")
    _, read = b.cap("inbox", "read")
    ok = (rc == 0 and "Journal digest" in listed and "FAKE DIGEST BODY" in shown
          and "inbox empty" in after and "Journal digest" in read)
    return ok, "listed, shown, moved to read/"


def case_loopback(b):
    rc, out = b.cap("act", "journal.digest", CAP_MODEL_URL="http://example.invalid:9/v1")
    ok = rc == 2 and "not loopback" in out
    return ok, f"rc={rc}"


def main():
    print("event path:")
    with Box() as b:
        check("1 an unbound event is recorded and runs nothing", *case_unbound(b))
    with Box() as b:
        check("2 without grants every response is refused, with no side effect",
              *case_ungranted(b))
    with Box(grants=GRANT_BOTH) as b:
        check("3 one event, two responses (plain + agent), one event id", *case_granted(b))
    with Box(grants=GRANT_BOTH, trust_grants=False) as b:
        rc, out = b.cap("emit", "time.daily", "--source", "timer")
        acts = [r for r in b.records() if r.get("action")]
        check("4 grants in a user-writable directory are not trusted",
              acts and all(r["state"] == "ungranted" and "writable" in r["reason"]
                           for r in acts) and not b.notified(),
              acts[0]["reason"] if acts else "")
    with Box(grants=GRANT_BOTH) as b:
        check("5 a grant follows the implementation, not the action's name", *case_relabel(b))
    with Box() as b:
        check("6 commit never runs from an event, even granted", *case_commit(b))
    with Box(grants=GRANT_BOTH) as b:
        check("7 a crashing response does not stop the next", *case_isolation(b))
    with Box() as b:
        check("8 the model endpoint cannot leave the machine", *case_loopback(b))
    with Box(grants=GRANT_BOTH) as b:
        check("11 a repeat stays quiet; a new kind of error notifies", *case_quiet(b))
    with Box(grants=GRANT_BOTH) as b:
        check("12 the inbox lists, shows, and marks read", *case_inbox(b))
    with Box() as b:
        bad = [b.cap("emit", "Daily", "--source", "timer")[0],
               b.cap("emit", "time.daily")[0],
               b.cap("emit", "time.daily", "--source", "cron")[0],
               b.cap("emit", "time.daily", "--source", "timer", "loose")[0]]
        check("9 malformed events are usage errors and leave no record",
              bad == [2, 2, 2, 2] and not b.records(), f"exit codes {bad}")
    with Box() as b:
        b.bindings('[[event_binding]]\nevent = "time.daily"\naction = "no.such"\n')
        rc, out = b.cap("check")
        check("10 a binding to a missing action fails cap check",
              rc == 1 and "DANGLING" in out, f"rc={rc}")

    print("\n  negative controls (the mechanism is broken on purpose):")

    with Box() as b:
        patch(b.cap_path, 'if b["event"] == name]', 'if True]')
        ok, d = case_unbound(b)
        check("1n binding match disabled -> assertion 1 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '    cls = a.get("consequence")\n    if cls not in EVENT_CLASSES:',
              '    return True, None\n    cls = a.get("consequence")\n    if cls not in EVENT_CLASSES:')
        ok, d = case_ungranted(b)
        check("2n grant check disabled -> assertion 2 fails", not ok, d)
    with Box(grants=GRANT_BOTH) as b:
        patch(b.cap_path, '\n                and g["implementation"] == a.get("implementation")', '')
        ok, d = case_relabel(b)
        check("5n implementation match removed -> assertion 5 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, 'EVENT_CLASSES = {"observe", "report"}',
              'EVENT_CLASSES = {"observe", "report", "commit"}')
        ok, d = case_commit(b)
        check("6n commit admitted -> assertion 6 fails", not ok, d)
    with Box(grants=GRANT_BOTH) as b:
        patch(b.cap_path, "        except Exception as exc:          # one response",
              "        except ZeroDivisionError as exc:  # one response")
        ok, d = case_isolation(b)
        check("7n isolation narrowed -> assertion 7 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, 'if host not in ("127.0.0.1", "localhost", "::1"):',
              'if host not in ("127.0.0.1", "localhost", "::1", "example.invalid"):')
        ok, d = case_loopback(b)
        check("8n loopback check widened -> assertion 8 fails", not ok, d)

    with Box(grants=GRANT_BOTH) as b:
        patch(b.cap_path, '    new = [g for g in groups if g["key"] not in _notified_keys()]\n    if not new:',
              '    new = groups\n    if not new:')
        ok, d = case_quiet(b)
        check("11n novelty check removed -> assertion 11 fails", not ok, d)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
