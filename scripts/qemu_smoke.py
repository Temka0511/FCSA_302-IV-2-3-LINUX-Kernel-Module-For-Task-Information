"""Optional real-kernel checks in QEMU; no root or mounted disk required.

Usage (after installing qemu-system-x86 busybox-static and matching headers/image):
PYTHONPATH=src python3 scripts/qemu_smoke.py --kernel /boot/vmlinuz-VERSION
"""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from taskgraph.model import parse
from taskgraph.verification import compare_ps, dfs_errors

PROJECT = Path(__file__).resolve().parents[1]


def newc_entry(name, data=b"", mode=0o100755, ino=1):
    name = name.encode() + b"\0"
    fields = [ino, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(name), 0]
    header = b"070701" + b"".join(f"{v:08x}".encode() for v in fields)
    prefix = header + name
    return prefix + b"\0" * (-len(prefix) % 4) + data + b"\0" * (-len(data) % 4)


def inspect(log, out):
    log = log.replace("\r", "")
    snapshots = {}
    for name in ["BEFORE", "CREATED", "STOPPED", "AFTER", "CAPPED", "THREAD_FORK"]:
        match = re.search(rf"BEGIN_SNAPSHOT_{name}\n(.*?)END_SNAPSHOT_{name}", log, re.S)
        if not match:
            raise ValueError("Missing snapshot " + name)
        # Serial kernel messages can interleave: retain only protocol lines.
        lines = [line for line in match[1].splitlines()
                 if line.startswith("# taskgraph ") or line.startswith("pid\t")
                 or re.match(r"^\d+\t", line)]
        text = "\n".join(lines) + "\n"
        snapshots[name] = parse(text)
        (out / (name.lower() + ".tsv")).write_text(text, encoding="utf-8")
    root = int(re.search(r"WORKLOAD_ROOT=(\d+)", log).group(1))
    created = snapshots["CREATED"]
    subtree, count = created.view(root=root)
    result = []
    def check(name, passed, detail):
        result.append(dict(test=name, passed=bool(passed), detail=detail))
    check("K1 module load", "RESULT LOAD= 0" in log, "insmod exit=0")
    before = snapshots["BEFORE"]
    check("K2 real kernel protocol", before.meta["source"] == "kernel" and
          before.tasks[0].pid == 0, f"rows={len(before.tasks)}; init_task PID=0")
    check("K3 linear and DFS init logs", "taskgraph LINEAR pid=" in log and
          "taskgraph DFS order=" in log, "Both log streams emitted")
    ranks = {t.pid: t.dfs for t in created.tasks}
    valid = not dfs_errors(created)
    check("K4 DFS ranks and parents", valid, f"Unique contiguous ranks: {len(ranks)}")
    check("K5 process tree creation", count == 7, f"root={root}; tasks={count}; expected=7")
    threads = [t for t in subtree if t.kind == "thread"]
    check("K6 pthread membership", len(threads) == 2 and all(t.parent == root for t in threads),
          f"thread PIDs={[t.pid for t in threads]}; TGID={root}")
    stopped = next(t for t in snapshots["STOPPED"].tasks if t.pid == root)
    check("K7 stop state", stopped.state in ("T", "t"), "state=" + stopped.state)
    left = [t.pid for t in snapshots["AFTER"].tasks if t.comm.startswith("tg-")]
    check("K8 exit and cleanup", not left, f"remaining workload tasks={left}")
    check("K9 module unload", "RESULT UNLOAD= 0" in log and "RESULT ENDPOINT_REMOVED=0" in log,
          "rmmod=0; /proc/taskgraph removed")
    check("K10 invalid cap rejected", bool(re.search(r"RESULT INVALID_CAP= [1-9]", log)),
          "max_tasks=1 rejected")
    capped = snapshots["CAPPED"]
    check("K11 bounded snapshot", len(capped.tasks) == 16 and capped.meta["truncated"] == "1",
          f"rows={len(capped.tasks)}; truncated={capped.meta['truncated']}")
    check("K12 reload and final unload", "RESULT SMALL_CAP_LOAD= 0" in log and
          "RESULT FINAL_UNLOAD= 0" in log and "SMOKE_DONE" in log, "Clean end")
    def section(name, filename):
        value = re.search(rf"BEGIN_{name}\n(.*?)END_{name}", log, re.S)
        if not value:
            raise ValueError("Missing evidence: " + name)
        text = value.group(1)
        (out / filename).write_text(text, encoding="utf-8")
        return text
    comparison = compare_ps(created,
        section("PS_PROCESS_COLUMNS", "ps_processes.txt"),
        section("PS_THREAD_COLUMNS", "ps_threads.txt"),
        section("PS_EL", "ps-el.txt"), section("PS_ELF", "ps-eLf.txt"),
        stable_pids=[t.pid for t in subtree],
        kernel_log=section("COMPARISON_LOG", "comparison-kernel.log"))
    (out / "ps_comparison.json").write_text(json.dumps(comparison, ensure_ascii=False, indent=2))
    check("K13 textbook children/sibling traversal", created.meta.get("traversal") == "children_sibling",
          "Direct kernel list traversal with stop_machine protection")
    check("K14 ps -el and ps -eLf comparison", comparison["passed"],
          f"{sum(r['passed'] for r in comparison['workload'])}/{count} stable task fields match")
    check("K15 repeated snapshots under churn", "RESULT CHURN=0" in log,
          "10 captures during concurrent process creation/exit; no read failure")
    check("K16 no kernel faults", not re.search(r"BUG:|Oops:|WARNING:|soft lockup", log),
          "No BUG/Oops/WARNING/lockup in serial log")
    threaded = snapshots["THREAD_FORK"]
    threaded_root = int(re.search(r"THREAD_FORK_ROOT=(\d+)", log).group(1))
    thread_rows, thread_count = threaded.view(root=threaded_root)
    special = [t for t in thread_rows if t.comm == "tg-thread-child"]
    check("K17 child forked by non-leader thread", thread_count == 8 and len(special) == 1
          and special[0].parent == threaded_root and not dfs_errors(threaded),
          f"root={threaded_root}; tasks={thread_count}; thread-owned child retained")
    (out / "kernel_results.json").write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return all(x["passed"] for x in result)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--kernel", required=True, type=Path)
    p.add_argument("--module", type=Path, default=PROJECT / "src/kernel/taskgraph.ko")
    p.add_argument("--busybox", type=Path, default=Path("/usr/bin/busybox"))
    p.add_argument("--ps", type=Path, default=Path("/usr/bin/ps"), help="procps ps, not BusyBox ps")
    p.add_argument("--qemu", default="qemu-system-x86_64")
    p.add_argument("--bios", type=Path)
    p.add_argument("--data-dir", type=Path)
    p.add_argument("--out", type=Path, default=PROJECT / "docs/evidence")
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as temp:
        temp = Path(temp)
        workload = temp / "guest_workload"
        subprocess.run(["gcc", "-static", "-pthread", "-O2", "-Wall", "-Wextra", "-o", str(workload),
                        str(PROJECT / "tests/guest_workload.c")], check=True)
        data = bytearray()
        for i, d in enumerate(["bin", "dev", "proc", "sys", "tmp", "lib", "lib64", "lib/x86_64-linux-gnu"]):
            data.extend(newc_entry(d, mode=0o040755, ino=i + 1))
        data.extend(newc_entry("bin/busybox", a.busybox.read_bytes()))
        for x in ["sh", "mount", "cat", "echo", "sleep", "insmod", "rmmod", "dmesg",
                  "grep", "kill", "poweroff", "uname", "test"]:
            data.extend(newc_entry("bin/" + x, b"busybox", mode=0o120777))
        data.extend(newc_entry("bin/ps", a.ps.read_bytes()))
        # Copy the selected, trusted local procps executable's loader/libraries.
        dependencies = subprocess.check_output(["ldd", str(a.ps)], text=True)
        if "not found" in dependencies:
            raise RuntimeError("procps shared library missing: " + dependencies)
        for lib in sorted(set(re.findall(r"(/[^\s()]+)", dependencies))):
            data.extend(newc_entry(lib.lstrip("/"), Path(lib).read_bytes()))
        data.extend(newc_entry("taskgraph.ko", a.module.read_bytes()))
        data.extend(newc_entry("guest_workload", workload.read_bytes()))
        data.extend(newc_entry("init", (PROJECT / "tests/qemu_init.sh").read_bytes()))
        data.extend(newc_entry("TRAILER!!!", mode=0))
        initrd = temp / "initramfs.cpio"
        initrd.write_bytes(data)
        cmd = [a.qemu, "-machine", "pc,accel=tcg", "-m", "512", "-smp", "2", "-kernel",
               str(a.kernel.resolve()), "-initrd", str(initrd), "-append",
               "console=ttyS0 rdinit=/init panic=-1", "-nographic", "-vga", "none", "-no-reboot", "-nic", "none"]
        if a.bios:
            cmd += ["-bios", str(a.bios.resolve())]
        if a.data_dir:
            cmd += ["-L", str(a.data_dir.resolve())]
        with (a.out / "qemu-serial.log").open("w") as output:
            subprocess.run(cmd, stdout=output, stderr=subprocess.STDOUT, check=True, timeout=90)
    log_path = a.out / "qemu-serial.log"
    normalized = "\n".join(line.rstrip() for line in log_path.read_text(errors="replace").splitlines()) + "\n"
    log_path.write_text(normalized, encoding="utf-8")
    return 0 if inspect(normalized, a.out) else 1


if __name__ == "__main__":
    raise SystemExit(main())
