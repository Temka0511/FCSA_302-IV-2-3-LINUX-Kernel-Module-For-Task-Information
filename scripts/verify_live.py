"""Run after insmod on the Ubuntu VM; evidence is generated, never hard-coded."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from taskgraph.model import read_snapshot


def main():
    out = Path("evidence")
    out.mkdir(exist_ok=True)
    results = []
    def check(name, passed, detail):
        results.append(dict(test=name, passed=bool(passed), detail=detail))
    first = read_snapshot("/proc/taskgraph")
    (out / "before.tsv").write_text(first.dump(), encoding="utf-8")
    check("L1 source and init_task", first.meta.get("source") == "kernel" and
          0 in {t.pid for t in first.tasks}, "source=kernel, PID 0 included")
    ranks = sorted(t.dfs for t in first.tasks)
    check("L2 DFS permutation", ranks == list(range(len(first.tasks))), str(len(ranks)))
    child = subprocess.Popen([sys.executable, "-m", "taskgraph.workload", "--depth", "2",
        "--fanout", "2", "--seconds", "30"], stdout=subprocess.DEVNULL)
    try:
        time.sleep(1)
        current = read_snapshot("/proc/taskgraph")
        rows, total = current.view(root=child.pid, limit=100)
        check("L3 tree creation", total == 7, f"root={child.pid}, subtree={total}, expected=7")
        (out / "created.tsv").write_text(current.dump(), encoding="utf-8")
        os.kill(child.pid, signal.SIGSTOP)
        time.sleep(.15)
        stopped = read_snapshot("/proc/taskgraph")
        states = {t.pid: t.state for t in stopped.tasks}
        check("L4 stopped state", states.get(child.pid) in ("T", "t"), str(states.get(child.pid)))
        (out / "stopped.tsv").write_text(stopped.dump(), encoding="utf-8")
        os.kill(child.pid, signal.SIGCONT)
        proc_pids = {int(p.name) for p in Path("/proc").iterdir() if p.name.isdigit()}
        module_pids = {t.pid for t in stopped.tasks if t.kind == "process"}
        overlap = len(proc_pids & module_pids) / max(1, len(proc_pids))
        check("L5 process comparison", overlap >= .95, f"overlap={overlap:.3f}; dynamic samples")
    finally:
        if child.poll() is None:
            os.kill(child.pid, signal.SIGCONT)
            child.terminate()
            child.wait(timeout=10)
    after = read_snapshot("/proc/taskgraph")
    check("L6 process exit", child.pid not in {t.pid for t in after.tasks}, f"PID {child.pid} removed")
    (out / "after.tsv").write_text(after.dump(), encoding="utf-8")
    (out / "live_results.json").write_text(json.dumps(results, ensure_ascii=False, indent=2))
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0 if all(r["passed"] for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
