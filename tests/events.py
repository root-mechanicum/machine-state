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
    watch        -> a new match notifies once; undelivered is not seen
    channels     -> declared by actions, granted at the edge, enforced on use
    events       -> only granted events start work; trusted ones carry no payload;
                    untrusted ones never reach the network
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

def grant(trusted='"time.*"', untrusted="", channels=None, ceiling="report"):
    chans = channels or ["journal", "model:local", "notify", "inbox", "net:huggingface.co"]
    return (f'ceiling = "{ceiling}"\n\n[events]\ntrusted = [{trusted}]\n'
            f'untrusted = [{untrusted}]\n\n[channels]\n'
            f'granted = [{", ".join(json.dumps(c) for c in chans)}]\n')


GRANT_BOTH = GRANT_HF = grant()

# The per-binding format this replaced. A file still in it must grant nothing.
OLD_FORMAT = """
[[grant]]
event = "time.daily"
action = "journal.errors.notify"
implementation = "journal.errors.notify"
class = "report"
"""

HF_FIXTURE = [{"modelId": "Qwen/Qwen4-27B"}, {"modelId": "Qwen/Qwen3.8-27B"},
              {"modelId": "Qwen/Qwen-Image-2.1"}]


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
        if self.path.startswith("/api/models"):    # stands in for huggingface.co
            if "author=fail" in self.path:
                return self._send(500, {"error": "down"})
            return self._send(200, HF_FIXTURE)
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
        # Fails while notify.fail exists: a desktop that is not answering.
        (stubs / "notify-send").write_text(
            f'#!/bin/sh\n[ -e "{self.dir}/notify.fail" ] && exit 1\n'
            f'printf "%s\\n" "$*" >> "{self.dir}/notify.log"\n')
        for f in stubs.iterdir():
            f.chmod(0o755)
        self.server = http.server.HTTPServer(("127.0.0.1", 0), Model)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.env = {"HOME": str(self.dir), "PATH": f"{stubs}:/usr/bin:/bin",
                    "DBUS_SESSION_BUS_ADDRESS": "unix:path=/nonexistent",
                    "CAP_MODEL_URL": f"http://127.0.0.1:{self.server.server_port}/v1",
                    "CAP_HF_URL": f"http://127.0.0.1:{self.server.server_port}"}
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
    # An agent edits canonical/ so a declaration names a provider that does more
    # than it says: journal.digest's channels, but a provider that notifies.
    p = b.repo / "canonical" / "actions" / "journal.toml"
    patch(p, 'implementation = "journal.digest"', 'implementation = "journal.errors.notify"')
    b.bindings('[[event_binding]]\nevent = "time.daily"\naction = "journal.digest"\n')
    b.cap("emit", "time.daily", "--source", "timer")
    d = [r for r in b.records() if r.get("action") == "journal.digest"]
    r = d[0] if d else {}
    ok = (len(d) == 1 and r.get("state") == "failed" and "'notify'" in r.get("reason", "")
          and not b.notified())
    return ok, f"journal.digest -> {r.get('state')}"


COMMIT_BINDING = '''
[action."test.commit"]
implementation = "journal.errors.notify"
label       = "A commit-class action wearing a harmless implementation"
category    = "Test"
consequence = "commit"
channels    = ["journal", "notify"]
'''


def case_commit(b):
    (b.repo / "canonical" / "actions" / "test.toml").write_text(COMMIT_BINDING)
    b.bindings('[[event_binding]]\nevent = "time.daily"\naction = "test.commit"\n')
    (b.dir / "etc-machine-state" / "grants.toml").write_text(grant(ceiling="commit"))
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


def _hf(b, **env):
    rc, out = b.cap("emit", "time.hourly", "--source", "timer", **env)
    w = [r for r in b.records() if r.get("action") == "interests.fetch"]
    return rc, out, w


def case_watch(b):
    rc1, _, _ = _hf(b)
    first = b.notified()
    rc2, _, w = _hf(b)
    notes = [n for n in b.notes() if "-qwen4" in n.name]
    ok = (rc1 == 0 and rc2 == 0 and "Qwen/Qwen4-27B" in first
          and "Qwen3.8" not in first and b.notified() == first
          and [r.get("outcome") for r in w] == ["ok", "skipped"]
          and len(notes) == 1 and "huggingface.co/Qwen/Qwen4-27B" in notes[0].read_text())
    return ok, f"outcomes={[r.get('outcome') for r in w]}, notes={len(notes)}"


def case_undelivered(b):
    # The desktop is down when the model appears: it must not be marked seen.
    (b.dir / "notify.fail").touch()
    rc1, _, _ = _hf(b)
    (b.dir / "notify.fail").unlink()
    rc2, _, w = _hf(b)
    ok = (rc1 == 1 and rc2 == 0 and "Qwen/Qwen4-27B" in b.notified()
          and [r.get("outcome") for r in w] == ["failed", "ok"])
    return ok, f"outcomes={[r.get('outcome') for r in w]}"


def case_network_grant(b):
    # The same grant without the net: channel: hosts are part of the authority.
    p = b.dir / "etc-machine-state" / "grants.toml"
    patch(p, ', "net:huggingface.co"', '')
    rc, _, w = _hf(b)
    ok = rc == 1 and len(w) == 1 and w[0].get("state") == "ungranted" and not b.notified()
    return ok, f"state={w[0].get('state') if w else None}"


def case_host(b):
    # Granted for huggingface.co, pointed somewhere else: refused before connecting.
    rc, _, w = _hf(b, CAP_HF_URL="http://example.invalid")
    r = w[0] if w else {}
    why = " ".join((r.get("plan") or {}).get("failures", []))
    ok = (rc == 1 and r.get("outcome") == "failed"
          and "not among the hosts" in why and not b.notified())
    return ok, why[:70]


def case_event_granted(b):
    # Only time.daily is granted: the hourly watch must not run.
    (b.dir / "etc-machine-state" / "grants.toml").write_text(grant(trusted='"time.daily"'))
    rc, _, w = _hf(b)
    r = w[0] if w else {}
    ok = (rc == 1 and r.get("state") == "ungranted"
          and "not a granted event" in r.get("reason", "") and not b.notified())
    return ok, r.get("reason", "")[:60]


def case_payload(b):
    # Anyone can `cap emit time.daily`; a trusted event smuggling a payload is refused.
    rc, _ = b.cap("emit", "time.daily", "--source", "agent", "note=ignore previous")
    acts = [r for r in b.records() if r.get("action")]
    ok = (rc == 1 and len(acts) == 2 and all(r.get("state") == "ungranted"
                                             and "no payload" in r.get("reason", "") for r in acts)
          and not b.notified())
    return ok, f"states={[r.get('state') for r in acts]}"


def case_untrusted(b):
    # Foreign text may reach local channels, never the network.
    (b.dir / "etc-machine-state" / "grants.toml").write_text(
        grant(untrusted='"mail.*"'))
    b.bindings('[[event_binding]]\nevent = "mail.received"\naction = "interests.fetch"\n\n'
               '[[event_binding]]\nevent = "mail.received"\naction = "journal.errors.notify"\n')
    rc, _ = b.cap("emit", "mail.received", "--source", "dbus", "subject=hello")
    acts = {r["action"]: r for r in b.records() if r.get("action")}
    w, n = acts.get("interests.fetch", {}), acts.get("journal.errors.notify", {})
    ok = (rc == 1 and w.get("state") == "ungranted" and "never reach" in w.get("reason", "")
          and n.get("outcome") == "ok" and "Qwen4" not in b.notified())
    return ok, f"watch={w.get('state')}, notify={n.get('outcome')}"


FAILING_INTEREST = '''
[interest.aaa-down]
label   = "A source that is down"
urgency = "alert"
sources = [{ huggingface = { author = "fail", match = "." } }]
'''


def case_isolated_sources(b):
    # Sorted first and failing: the qwen4 interest must still get its news.
    (b.repo / "canonical" / "interests" / "aaa.toml").write_text(FAILING_INTEREST)
    rc, _, w = _hf(b)
    r = w[0] if w else {}
    fails = (r.get("plan") or {}).get("failures", [])
    ok = (rc == 1 and r.get("outcome") == "failed" and any("aaa-down" in f for f in fails)
          and "Qwen/Qwen4-27B" in b.notified())
    return ok, f"outcome={r.get('outcome')}, failures={len(fails)}"


def case_nochan(b):
    # An interest needs a channel interests.fetch does not declare: check says so.
    patch(b.repo / "canonical" / "actions" / "interests.toml",
          '["net:huggingface.co", "notify", "inbox"]', '["notify", "inbox"]')
    rc, out = b.cap("check")
    ok = rc == 1 and "NOCHAN" in out and "net:huggingface.co" in out
    return ok, f"rc={rc}"


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
        check("5 a provider using an undeclared channel fails, and does nothing", *case_relabel(b))
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
    with Box(grants=GRANT_HF) as b:
        check("13 a watch notifies a new match once, and notes it", *case_watch(b))
    with Box(grants=GRANT_HF) as b:
        check("14 an undelivered notification is not marked seen", *case_undelivered(b))
    with Box(grants=GRANT_HF) as b:
        check("15 a grant must name the action's network hosts", *case_network_grant(b))
    with Box(grants=GRANT_HF) as b:
        check("16 an undeclared host is refused before any connection", *case_host(b))
    with Box(grants=GRANT_HF) as b:
        check("17 an event the grant does not name starts nothing", *case_event_granted(b))
    with Box(grants=GRANT_BOTH) as b:
        check("18 a trusted event carrying a payload is refused", *case_payload(b))
    with Box(grants=GRANT_BOTH) as b:
        check("19 an untrusted event reaches local channels, never the network",
              *case_untrusted(b))
    with Box(grants=OLD_FORMAT) as b:
        rc, _ = b.cap("emit", "time.daily", "--source", "timer")
        acts = [r for r in b.records() if r.get("action")]
        check("20 a grants file in the old format grants nothing",
              acts and all("malformed" in r.get("reason", "") for r in acts) and not b.notified(),
              acts[0].get("reason", "")[:60] if acts else "")
    with Box() as b:
        (b.repo / "canonical" / "interests" / "x.toml").write_text(
            '[interest.x]\nlabel = "X"\nurgency = "alert"\n'
            'sources = [{ telepathy = { mind = "yours" } }]\n')
        rc, out = b.cap("check")
        check("21 an interest with an unimplemented source kind is rejected",
              rc == 2 and "not implemented" in out, f"rc={rc}")
    with Box(grants=GRANT_HF) as b:
        check("22 a failing source does not cost another interest its news",
              *case_isolated_sources(b))
    with Box() as b:
        check("23 cap check flags an interest needing an undeclared channel", *case_nochan(b))
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
        patch(b.cap_path, '    if channel not in ACTIVE_CHANNELS:\n        raise',
              '    if False:\n        raise')
        ok, d = case_relabel(b)
        check("5n channel use check removed -> assertion 5 fails", not ok, d)
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
    with Box(grants=GRANT_HF) as b:
        patch(b.cap_path, '    if r.returncode != 0:\n        return None\n    use("inbox")',
              '    use("inbox")')
        ok, d = case_undelivered(b)
        check("14n seen-before-delivered restored -> assertion 14 fails", not ok, d)
    with Box(grants=GRANT_HF) as b:
        patch(b.cap_path, '    if missing:\n        return False', '    if False:\n        return False')
        ok, d = case_network_grant(b)
        check("15n channel grant check removed -> assertion 15 fails", not ok, d)
    with Box(grants=GRANT_HF) as b:
        patch(b.cap_path,
              '    if host not in ("127.0.0.1", "localhost", "::1") and host not in ALLOWED_HOSTS:',
              '    if False:')
        ok, d = case_host(b)
        check("16n host check removed -> assertion 16 fails", not ok, d)
    with Box(grants=GRANT_HF) as b:
        patch(b.cap_path, '    else:\n        return False, f"{event} is not a granted event"',
              '    else:\n        trusted = True')
        ok, d = case_event_granted(b)
        check("17n event check removed -> assertion 17 fails", not ok, d)
    with Box(grants=GRANT_BOTH) as b:
        patch(b.cap_path, '        if payload:\n            return False', '        if False:\n            return False')
        ok, d = case_payload(b)
        check("18n payload check removed -> assertion 18 fails", not ok, d)
    with Box(grants=GRANT_BOTH) as b:
        patch(b.cap_path, '    if not trusted and not set(chans) <= LOCAL_CHANNELS:',
              '    if False:')
        ok, d = case_untrusted(b)
        check("19n untrusted-network rule removed -> assertion 19 fails", not ok, d)
    with Box(grants=GRANT_HF) as b:
        patch(b.cap_path, "            except (OSError, ValueError, KeyError) as exc:\n"
                          "                failures.append(f\"{name}/{kind}",
              "            except ZeroDivisionError as exc:\n"
              "                failures.append(f\"{name}/{kind}")
        ok, d = case_isolated_sources(b)
        check("22n source isolation removed -> assertion 22 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '        if missing:\n            print(f"  NOCHAN',
              '        if False:\n            print(f"  NOCHAN')
        ok, d = case_nochan(b)
        check("23n channel coverage check removed -> assertion 23 fails", not ok, d)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
