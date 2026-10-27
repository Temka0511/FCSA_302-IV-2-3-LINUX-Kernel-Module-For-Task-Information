"""Shared snapshot parser and nonrecursive traversal used by CLI and GUI."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
import time

MAX_ROWS = 16384
MAX_BYTES = 8 * 1024 * 1024
FIELDS = "pid ppid tgid parent state kind linear dfs depth orphan comm".split()


@dataclass(frozen=True)
class Task:
    pid: int
    ppid: int
    tgid: int
    parent: int
    state: str
    kind: str
    linear: int
    dfs: int
    depth: int
    orphan: int
    comm: str


@dataclass
class Snapshot:
    tasks: list[Task]
    meta: dict[str, str]

    def view(self, mode="DFS", root=None, limit=300, threads=True):
        if mode not in ("DFS", "LINEAR"):
            raise ValueError("Горим DFS эсвэл LINEAR байна.")
        if not 1 <= limit <= 2000:
            raise ValueError("Харагдах зангилааны тоо 1..2000 байна.")
        all_tasks = {t.pid: t for t in self.tasks}
        if root is not None and root not in all_tasks:
            raise ValueError(f"PID {root} энэ snapshot-д алга.")
        children = {}
        for t in self.tasks:
            if t.parent != t.pid:
                children.setdefault(t.parent, []).append(t.pid)
        allowed = set(all_tasks)
        if root is not None:
            allowed = set()
            stack = [root]
            while stack:
                pid = stack.pop()
                if pid in allowed:
                    continue
                allowed.add(pid)
                stack.extend(children.get(pid, []))
        chosen = [t for t in self.tasks if t.pid in allowed
                  and (threads or t.kind != "thread")]
        chosen.sort(key=lambda t: t.dfs if mode == "DFS" else t.linear)
        return chosen[:limit], len(chosen)

    def dump(self):
        meta = " ".join(f"{k}={v}" for k, v in self.meta.items())
        lines = ["# taskgraph " + meta, "\t".join(FIELDS)]
        for t in self.tasks:
            vals = [getattr(t, f) for f in FIELDS]
            vals[-1] = encode_comm(t.comm)
            lines.append("\t".join(map(str, vals)))
        return "\n".join(lines) + "\n"


def decode_comm(value):
    raw = bytearray()
    i = 0
    while i < len(value):
        if value[i] == "\\":
            if not re.fullmatch(r"\\x[0-9a-fA-F]{2}", value[i:i + 4]):
                raise ValueError("comm escape нь \\xNN хэлбэртэй байна.")
            raw.append(int(value[i + 2:i + 4], 16))
            i += 4
        else:
            raw.extend(value[i].encode("utf-8"))
            i += 1
    return raw.decode("utf-8", errors="replace")


def encode_comm(value):
    return "".join(chr(b) if 32 <= b < 127 and b != 92 else f"\\x{b:02x}"
                   for b in value.encode("utf-8"))


def parse(text):
    if len(text.encode("utf-8")) > MAX_BYTES:
        raise ValueError("Snapshot 8 MiB хэмжээнээс хэтэрсэн.")
    lines = text.splitlines()
    if len(lines) < 2 or not lines[0].startswith("# taskgraph "):
        raise ValueError("TaskGraph header олдсонгүй.")
    meta = dict(re.findall(r"(\w+)=([^\s]+)", lines[0]))
    if meta.get("version") != "1":
        raise ValueError("Зөвхөн snapshot version=1 дэмжинэ.")
    if lines[1].split("\t") != FIELDS:
        raise ValueError("Snapshot баганын бүтэц буруу.")
    tasks = []
    pids = set()
    for line_no, line in enumerate(lines[2:], 3):
        if len(tasks) >= MAX_ROWS:
            raise ValueError("Snapshot мөрийн тоо 16384-өөс хэтэрсэн.")
        vals = line.split("\t")
        if len(vals) != len(FIELDS):
            raise ValueError(f"{line_no}-р мөрийн баганын тоо буруу.")
        data = dict(zip(FIELDS, vals))
        try:
            for f in ("pid", "ppid", "tgid", "parent", "linear", "dfs", "depth", "orphan"):
                data[f] = int(data[f])
                if data[f] < 0:
                    raise ValueError()
            if data["orphan"] not in (0, 1):
                raise ValueError()
            if data["state"] not in list("RSDTtXZPIWK"):
                raise ValueError()
            if data["kind"] not in ("root", "thread", "process"):
                raise ValueError()
            data["comm"] = decode_comm(data["comm"])
        except (ValueError, TypeError) as exc:
            raise ValueError(f"{line_no}-р мөрийн утга буруу: {exc}") from exc
        if data["pid"] in pids:
            raise ValueError(f"Давхардсан PID: {data['pid']}")
        pids.add(data["pid"])
        tasks.append(Task(**data))
    try:
        if int(meta.get("count", "-1")) != len(tasks):
            raise ValueError()
        if meta.get("truncated") not in ("0", "1"):
            raise ValueError()
    except ValueError as exc:
        raise ValueError("Snapshot count/truncated мэдээлэл буруу.") from exc
    for key in ("linear", "dfs"):
        if sorted(getattr(t, key) for t in tasks) != list(range(len(tasks))):
            raise ValueError(f"{key} дараалал давхардсан эсвэл тасарсан.")
    return Snapshot(tasks, meta)


def read_snapshot(path):
    with Path(path).open(encoding="utf-8") as stream:
        text = stream.read(MAX_BYTES + 1)
    return parse(text)


def rank_records(records):
    """Attach DFS ranks to scalar records, never recursively following parents."""
    by_pid = {r["pid"]: r for r in records}
    children = {}
    for r in records:
        if r["pid"] != r["parent"]:
            children.setdefault(r["parent"], []).append(r["pid"])
    visited = set()
    roots = [r for r in records if r["parent"] not in by_pid or r["parent"] == r["pid"]]
    for start in roots + records:
        if start["pid"] in visited:
            continue
        stack = [(start["pid"], 0)]
        while stack:
            pid, depth = stack.pop()
            if pid in visited:
                continue
            r = by_pid[pid]
            r["dfs"] = len(visited)
            r["depth"] = depth
            visited.add(pid)
            stack.extend((c, depth + 1) for c in reversed(children.get(pid, [])))
    return records


def capture_procfs(proc=Path("/proc")):
    """Explicit diagnostic source. Does NOT pretend to be a loaded module."""
    records = []
    seen = set()
    for process in sorted(proc.iterdir(), key=lambda p: (not p.name.isdigit(),
                           int(p.name) if p.name.isdigit() else 0)):
        if not process.name.isdigit():
            continue
        try:
            candidates = sorted((process / "task").iterdir(), key=lambda p: int(p.name))
        except (OSError, ValueError):
            continue
        for task in candidates:
            try:
                text = (task / "stat").read_text()
                end = text.rindex(")")
                pid = int(text[:text.index(" ")])
                comm = text[text.index("(") + 1:end]
                rest = text[end + 2:].split()
                state, ppid = rest[0], int(rest[1])
                tgid = int(process.name)
                if pid in seen:
                    continue
                seen.add(pid)
                records.append(dict(pid=pid, ppid=ppid, tgid=tgid,
                    parent=tgid if pid != tgid else ppid, state=state,
                    kind="thread" if pid != tgid else "process",
                    linear=len(records), dfs=0, depth=0, orphan=0, comm=comm))
            except (OSError, ValueError, IndexError):
                continue  # Process exited while the directory was being read.
    if not records:
        raise ValueError("/proc-оос task уншигдсангүй.")
    if len(records) > MAX_ROWS:
        records = records[:MAX_ROWS]
        truncated = "1"
    else:
        truncated = "0"
    known = {r["pid"] for r in records}
    for r in records:
        r["orphan"] = int(r["parent"] not in known)
    rank_records(records)
    return Snapshot([Task(**r) for r in records], dict(version="1", source="procfs",
                    count=str(len(records)), cap=str(MAX_ROWS), truncated=truncated,
                    wall_ns=str(time.time_ns())))


def write_json(path, snapshot):
    from dataclasses import asdict
    Path(path).write_text(json.dumps({"meta": snapshot.meta,
        "tasks": [asdict(t) for t in snapshot.tasks]}, ensure_ascii=False, indent=2),
        encoding="utf-8")
