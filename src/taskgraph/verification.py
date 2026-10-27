"""Compare independent procps output with kernel snapshots and init logs."""
import re


def parse_ps(text, threads=False):
    """Parse headerless `ps -e[L] -o ...` output, retaining comm spaces."""
    result = {}
    columns = 5 if threads else 4
    for line in text.splitlines():
        if not line.strip():
            continue
        fields = line.split(None, columns - 1)
        if len(fields) != columns:
            raise ValueError("Incomplete ps row: " + line)
        if threads:
            tid, tgid, ppid, state, comm = fields
        else:
            tid, ppid, state, comm = fields
            tgid = tid
        tid = int(tid)
        if tid in result:
            raise ValueError("Duplicate ps task ID")
        result[tid] = dict(pid=tid, tgid=int(tgid), ppid=int(ppid),
                           state=state, comm=comm)
    if not result:
        raise ValueError("ps returned no tasks")
    return result


def raw_ps_ids(text, threads=False):
    """Extract IDs from the textbook's unmodified ps -el / ps -eLf."""
    lines = [line.split() for line in text.splitlines() if line.strip()]
    key = "LWP" if threads else "PID"
    column = lines[0].index(key)
    return {int(row[column]) for row in lines[1:]}


def dfs_errors(snapshot):
    """A true preorder keeps each subtree contiguous, not just parent-first."""
    stack, errors = [], []
    for t in sorted(snapshot.tasks, key=lambda t: t.dfs):
        if t.pid == 0:
            if t.dfs != 0 or t.depth != 0:
                errors.append("root rank/depth")
            stack = [0]
            continue
        while stack and stack[-1] != t.parent:
            stack.pop()
        if not stack or t.depth != len(stack):
            errors.append(f"PID {t.pid}: non-contiguous subtree or bad depth")
        stack.append(t.pid)
    return errors


def compare_ps(snapshot, process_text, thread_text, raw_el, raw_elf,
               stable_pids=(), kernel_log=None):
    processes = parse_ps(process_text)
    threads = parse_ps(thread_text, threads=True)
    raw_processes = raw_ps_ids(raw_el)
    raw_threads = raw_ps_ids(raw_elf, threads=True)
    stable_pids = set(stable_pids)
    module = {t.pid: t for t in snapshot.tasks if t.pid != 0}
    result = dict(snapshot_tasks=len(snapshot.tasks),
                  ps_el_tasks=len(raw_processes), ps_eLf_tasks=len(raw_threads),
                  dfs_errors=dfs_errors(snapshot), workload=[], comparisons=[])
    for label, expected, actual in [
        ("LINEAR / ps -el", {p: t for p, t in module.items() if t.kind == "process"}, processes),
        ("DFS / ps -eLf", module, threads),
    ]:
        common = expected.keys() & actual.keys()
        result["comparisons"].append(dict(
            name=label, module_count=len(expected), ps_count=len(actual), common=len(common),
            name_matches=sum(expected[p].comm == actual[p]["comm"] for p in common),
            state_matches=sum(expected[p].state == actual[p]["state"] for p in common),
            parent_matches=sum(expected[p].ppid == actual[p]["ppid"] for p in common),
            tgid_matches=sum(expected[p].tgid == actual[p]["tgid"] for p in common),
            name_differences=[dict(pid=p, module=expected[p].comm, ps=actual[p]["comm"])
                              for p in sorted(common) if expected[p].comm != actual[p]["comm"]],
            state_differences=[dict(pid=p, module=expected[p].state, ps=actual[p]["state"])
                               for p in sorted(common) if expected[p].state != actual[p]["state"]],
            only_module=[dict(pid=p, comm=expected[p].comm) for p in sorted(expected.keys() - actual.keys())],
            only_ps=[actual[p] for p in sorted(actual.keys() - expected.keys())]))
    log_linear = set()
    log_dfs = set()
    if kernel_log is not None:
        log_linear = {int(p) for p in re.findall(r"taskgraph LINEAR pid=(\d+)", kernel_log)}
        log_dfs = {int(p) for p in re.findall(r"taskgraph DFS .*?pid=(\d+)", kernel_log)}
        result["init_log"] = dict(linear_tasks=len(log_linear), dfs_tasks=len(log_dfs),
                                  linear_common=len(log_linear & raw_processes),
                                  dfs_common=len((log_dfs - {0}) & raw_threads))
    for pid in sorted(stable_pids):
        task = module.get(pid)
        actual = threads.get(pid)
        ok = task is not None and actual is not None and pid in raw_threads
        if ok:
            ok = (task.comm, task.ppid, task.tgid, task.state) == (
                actual["comm"], actual["ppid"], actual["tgid"], actual["state"])
            if task.kind == "process":
                ok = ok and pid in raw_processes and pid in processes
            if kernel_log is not None:
                ok = ok and pid in log_dfs and (task.kind != "process" or pid in log_linear)
        result["workload"].append(dict(pid=pid, comm=task.comm if task else "missing",
            kind=task.kind if task else "missing", ppid=task.ppid if task else None,
            tgid=task.tgid if task else None, module_state=task.state if task else None,
            ps_state=actual["state"] if actual else None, passed=bool(ok)))
    result["passed"] = (bool(stable_pids) and not result["dfs_errors"]
                        and all(row["passed"] for row in result["workload"]))
    return result
