"""python3 -m taskgraph.cli [--procfs | --source /proc/taskgraph]"""
import argparse
from pathlib import Path
from .model import capture_procfs, read_snapshot, write_json


def main():
    p = argparse.ArgumentParser(description="TaskGraph snapshot / listing")
    p.add_argument("--source", default="/proc/taskgraph")
    p.add_argument("--procfs", action="store_true", help="Explicit diagnostic mode")
    p.add_argument("--mode", choices=["DFS", "LINEAR"], default="DFS")
    p.add_argument("--root", type=int)
    p.add_argument("--limit", type=int, default=300)
    p.add_argument("--no-threads", action="store_true")
    p.add_argument("--export", type=Path)
    p.add_argument("--json", type=Path)
    a = p.parse_args()
    try:
        s = capture_procfs() if a.procfs else read_snapshot(a.source)
        rows, total = s.view(a.mode, a.root, a.limit, not a.no_threads)
        if a.export:
            a.export.write_text(s.dump(), encoding="utf-8")
        if a.json:
            write_json(a.json, s)
        print("SOURCE:", s.meta.get("source"), "SHOWN:", len(rows), "/", total,
              "TRUNCATED:", s.meta.get("truncated"))
        print("PID\tPPID\tTGID\tSTATE\tKIND\tDFS\tCOMM")
        for t in rows:
            print(f"{t.pid}\t{t.ppid}\t{t.tgid}\t{t.state}\t{t.kind}\t{t.dfs}\t{t.comm!r}")
    except (OSError, ValueError) as exc:
        p.exit(1, f"TaskGraph: {exc}\n")


if __name__ == "__main__":
    main()
