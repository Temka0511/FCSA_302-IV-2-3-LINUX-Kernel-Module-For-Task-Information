import unittest
from dataclasses import replace

from taskgraph.model import Snapshot, Task
from taskgraph.verification import compare_ps, dfs_errors, parse_ps, raw_ps_ids


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.snapshot = Snapshot([
            Task(0, 0, 0, 0, "R", "root", 0, 0, 0, 0, "swapper/0"),
            Task(10, 1, 10, 0, "S", "process", 1, 1, 1, 0, "example root"),
            Task(11, 1, 10, 10, "S", "thread", 2, 2, 2, 0, "worker"),
        ], {})
        self.processes = "10 1 S example root\n20 1 R ps\n"
        self.threads = "10 10 1 S example root\n11 10 1 S worker\n21 21 1 R ps\n"
        self.el = "F S UID PID PPID CMD\n0 S 0 10 1 /example\n0 R 0 18 1 ps\n"
        self.elf = "UID PID PPID LWP C CMD\n0 10 1 10 0 /example\n0 10 1 11 0 /example\n0 19 1 19 0 ps\n"

    def compare(self, **kwargs):
        return compare_ps(kwargs.get("snapshot", self.snapshot), self.processes,
            kwargs.get("threads", self.threads), self.el, self.elf, [10, 11])

    def test_ps_spaces_and_thread_ids(self):
        records = parse_ps(self.threads, threads=True)
        self.assertEqual(records[10]["comm"], "example root")
        self.assertEqual(records[11]["tgid"], 10)
        self.assertEqual(raw_ps_ids(self.elf, threads=True), {10, 11, 19})

    def test_transient_ps_process_is_reported_not_hidden(self):
        result = self.compare()
        self.assertTrue(result["passed"])
        self.assertEqual(result["comparisons"][1]["only_ps"][0]["pid"], 21)

    def test_wrong_state_fails_workload_comparison(self):
        self.assertFalse(self.compare(threads=self.threads.replace("11 10 1 S", "11 10 1 T"))["passed"])

    def test_parent_first_is_not_enough_for_dfs(self):
        # 0 -> {1, 2}, 1 -> 3: 0,1,2,3 is parent-first but not DFS.
        tasks = [Task(0, 0, 0, 0, "R", "root", 0, 0, 0, 0, "root")]
        for rank, pid, parent, depth in [(1, 1, 0, 1), (2, 2, 0, 1), (3, 3, 1, 2)]:
            tasks.append(Task(pid, parent, pid, parent, "S", "process", rank, rank, depth, 0, str(pid)))
        self.assertTrue(dfs_errors(Snapshot(tasks, {})))
        tasks[2] = replace(tasks[2], dfs=3)
        tasks[3] = replace(tasks[3], dfs=2)
        self.assertEqual(dfs_errors(Snapshot(tasks, {})), [])

    def test_missing_thread_in_init_log_fails(self):
        log = "taskgraph LINEAR pid=10 state=S comm=example root\n" \
              "taskgraph DFS order=0 depth=0 pid=0 ppid=0 state=R comm=swapper/0\n" \
              "taskgraph DFS order=1 depth=1 pid=10 ppid=1 state=S comm=example root\n"
        result = compare_ps(self.snapshot, self.processes, self.threads, self.el,
                            self.elf, [10, 11], kernel_log=log)
        self.assertFalse(result["passed"])


if __name__ == "__main__":
    unittest.main()
