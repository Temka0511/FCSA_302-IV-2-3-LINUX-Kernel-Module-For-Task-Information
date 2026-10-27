"""Bounded reproducible process tree, cleanup only the children we created."""
import argparse
import os
import signal
import subprocess
import sys
import time


def spawn_tree(depth, fanout, seconds):
    children = []
    def stop(_signum, _frame):
        raise SystemExit(0)
    signal.signal(signal.SIGTERM, stop)
    try:
        if depth:
            for _ in range(fanout):
                children.append(subprocess.Popen([sys.executable, "-m", "taskgraph.workload",
                    "--depth", str(depth - 1), "--fanout", str(fanout), "--seconds", str(seconds), "--child"]))
        print(f"PID={os.getpid()} PPID={os.getppid()} depth={depth}", flush=True)
        time.sleep(seconds)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


def main():
    parser = argparse.ArgumentParser(description="Create bounded live process tree")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--fanout", type=int, default=2)
    parser.add_argument("--seconds", type=int, default=45)
    parser.add_argument("--child", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not (0 <= args.depth <= 3 and 1 <= args.fanout <= 3 and 2 <= args.seconds <= 300):
        parser.error("depth=0..3, fanout=1..3, seconds=2..300")
    if not args.child:
        print(f"ROOT_PID={os.getpid()}", flush=True)
    spawn_tree(args.depth, args.fanout, args.seconds)


if __name__ == "__main__":
    main()
