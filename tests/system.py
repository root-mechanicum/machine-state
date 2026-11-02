#!/usr/bin/env python3
"""Read-only system actions for bin/cap — machine-state-s4a.

    hardware  -> cores are counted per core, not per thread; VRAM is read, not guessed
    bare      -> without nvidia-smi or lspci, the rest is still answered
    status    -> load, memory, temperature, fans and GPU from their sources
    battery   -> charge, power source and health; a machine without one is refused
    disks     -> one line per filesystem, however many subvolumes it mounts
    observe   -> all four are observe, and running them touches no desktop tool

Hermetic: the event suite's repository copy, a fake /proc and /sys under
CAP_SYSROOT, and stand-ins for nvidia-smi, lspci and df. Each check of a rule
carries a negative control: the copy is patched to break it and the assertion
must then fail.
"""

import json
import sys

from events import Box, check, patch, results

CPUINFO = "".join(
    f"processor\t: {i}\nmodel name\t: Fixture CPU 9000\nphysical id\t: 0\ncore id\t\t: {i // 2}\n\n"
    for i in range(4))

FILES = {
    "proc/cpuinfo": CPUINFO,
    "proc/meminfo": "MemTotal:       16777216 kB\nMemAvailable:    4194304 kB\n",
    "proc/uptime": "93784.5 1000.0\n",
    "proc/loadavg": "0.50 0.40 0.30 1/100 42\n",
    "proc/sys/kernel/osrelease": "6.0.0-fixture\n",
    "etc/os-release": 'NAME="Fixture"\nPRETTY_NAME="Fixture OS"\n',
    "sys/class/dmi/id/sys_vendor": "ACME\n",
    "sys/class/dmi/id/product_name": "Laptop 1\n",
    "sys/class/hwmon/hwmon0/name": "coretemp\n",
    "sys/class/hwmon/hwmon0/temp1_input": "51000\n",
    "sys/class/hwmon/hwmon1/name": "asus\n",
    "sys/class/hwmon/hwmon1/fan1_input": "1800\n",
    "sys/class/hwmon/hwmon1/fan1_label": "cpu_fan\n",
    "sys/firmware/acpi/platform_profile": "balanced\n",
    "sys/class/power_supply/ADP0/type": "Mains\n",
    "sys/class/power_supply/ADP0/online": "0\n",
    "sys/class/power_supply/BAT0/capacity": "64\n",
    "sys/class/power_supply/BAT0/status": "Discharging\n",
    "sys/class/power_supply/BAT0/charge_control_end_threshold": "80\n",
    "sys/class/power_supply/BAT0/power_now": "12500000\n",
    "sys/class/power_supply/BAT0/energy_full": "81000000\n",
    "sys/class/power_supply/BAT0/energy_full_design": "90000000\n",
}

DF = """Filesystem Type 1B-blocks Used Avail Mounted on
/dev/nvme0n1p2 btrfs 1000000000000 250000000000 750000000000 /
/dev/nvme0n1p2 btrfs 1000000000000 250000000000 750000000000 /home
/dev/nvme0n1p2 btrfs 1000000000000 250000000000 750000000000 /var/log
/dev/nvme0n1p1 vfat 4000000000 2000000000 2000000000 /boot
tmpfs tmpfs 8000000000 1000 7999999000 /tmp
"""

STUBS = {
    "nvidia-smi": "#!/bin/sh\necho 'Fixture GPU 24, 21750, 24463, 3, 40, 9.50'\n",
    "lspci": "#!/bin/sh\necho '02:00.0 VGA compatible controller: Fixture Corp GPU 24 (rev a1)'\n"
             "echo '00:14.0 USB controller: Fixture USB'\n",
    "df": f"#!/bin/sh\ncat <<'EOF'\n{DF}EOF\n",
}


def setup(b, battery=True, gpu=True):
    root = b.dir / "root"
    for rel, text in FILES.items():
        if not battery and "BAT0" in rel:
            continue
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    stubs = b.dir / "stubs"
    for name, text in STUBS.items():
        if not gpu and name in ("nvidia-smi", "lspci"):
            text = "#!/bin/sh\nexit 127\n"     # the real ones are on PATH too
        (stubs / name).write_text(text)
        (stubs / name).chmod(0o755)
    b.env["CAP_SYSROOT"] = str(root)


def case_hardware(b):
    setup(b)
    rc, out = b.cap("act", "system.hardware")
    ok = (rc == 0 and "4 cores" not in out and "2 cores, 4 threads" in out
          and "Fixture GPU 24: 23.9 GiB" in out and "16.0 GiB" in out
          and "Fixture Corp GPU 24" in out and "USB" not in out)
    return ok, f"rc={rc} {out.strip().splitlines()[3:5]}"


def case_bare(b):
    setup(b, gpu=False)
    rc, out = b.cap("act", "system.hardware")
    ok = rc == 0 and "Fixture CPU 9000" in out and "gpu" not in out
    return ok, f"rc={rc}"


def case_status(b):
    setup(b)
    rc, out = b.cap("act", "system.status")
    ok = (rc == 0 and "1d 2h 3m" in out and "12.0 GiB used of 16.0 GiB" in out
          and "51 °C" in out and "cpu_fan 1800 rpm" in out and "balanced" in out
          and "21750 of 24463 MiB" in out)
    return ok, f"rc={rc}"


def case_battery(b):
    setup(b)
    rc, out = b.cap("act", "system.battery")
    ok = (rc == 0 and "64%" in out and "on battery" in out and "charges to 80%" in out
          and "12.5 W" in out and "90% of design" in out)
    return ok, f"rc={rc}"


def case_no_battery(b):
    setup(b, battery=False)
    rc, out = b.cap("act", "system.battery")
    return rc == 1 and "no battery" in out, f"rc={rc} {out.strip()[-60:]}"


def case_disks(b):
    setup(b)
    rc, out = b.cap("act", "system.disks")
    rows = [l for l in out.splitlines() if l.strip().startswith("/dev/")]
    ok = (rc == 0 and len(rows) == 2 and "/, /home, /var/log" in out
          and "698.5 GiB free" in out and "tmpfs" not in out)
    return ok, f"rc={rc} rows={len(rows)}"


def case_observe(b):
    setup(b)
    # Listing probes hyprctl for availability, so it runs before the tripwires.
    _, listing = b.cap("list", "--json")
    # Desktop tools that would show a side effect if anything reached for them.
    for name in ("hyprctl", "notify-send", "noctalia", "wtype"):
        (b.dir / "stubs" / name).write_text(f'#!/bin/sh\necho "$0 $*" >> "{b.dir}/touched.log"\n')
        (b.dir / "stubs" / name).chmod(0o755)
    rcs = [b.cap("act", f"system.{a}")[0] for a in ("hardware", "status", "battery", "disks")]
    decl = {a["action"]: a for a in json.loads(listing) if a["action"].startswith("system.")}
    ok = (rcs == [0, 0, 0, 0] and len(decl) == 4
          and all(a.get("consequence") == "observe" and not a.get("mutating") for a in decl.values())
          and not (b.dir / "touched.log").exists())
    return ok, f"rcs={rcs} declared={sorted(decl)}"


def main():
    print("system actions:")
    with Box() as b:
        check("1 hardware: cores per core, VRAM read", *case_hardware(b))
    with Box() as b:
        check("2 without nvidia-smi or lspci, the rest is answered", *case_bare(b))
    with Box() as b:
        check("3 status from its sources", *case_status(b))
    with Box() as b:
        check("4 battery: charge, source, limit, draw, health", *case_battery(b))
    with Box() as b:
        check("5 no battery: refused as unavailable", *case_no_battery(b))
    with Box() as b:
        check("6 disks: one line per filesystem, tmpfs left out", *case_disks(b))
    with Box() as b:
        check("7 all observe, and no desktop tool touched", *case_observe(b))

    print("negative controls:")
    with Box() as b:
        patch(b.cap_path, '            cores.add((phys, v))', '            cores.add((phys, v, threads))')
        ok, d = case_hardware(b)
        check("1n threads counted as cores -> assertion 1 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '    return (True, None) if _battery_dir() else (False, "this machine has no battery")',
              '    return True, None')
        try:
            ok, d = case_no_battery(b)
        except Exception as exc:          # a crash is also the guard failing
            ok, d = False, repr(exc)[:60]
        check("5n battery requirement removed -> assertion 5 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '        fs.setdefault(src, {', '        fs.setdefault(target, {')
        ok, d = case_disks(b)
        check("6n grouped by mount, not filesystem -> assertion 6 fails", not ok, d)
    with Box() as b:
        patch(b.cap_path, '    _show(lines)\n    plan = plan_status()',
              '    _show(lines)\n    subprocess.run(["notify-send", "status"])\n    plan = plan_status()')
        ok, d = case_observe(b)
        check("7n a status that notifies -> assertion 7 fails", not ok, d)

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} assertions passed")
    if failed:
        print("FAILED: " + ", ".join(failed))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
