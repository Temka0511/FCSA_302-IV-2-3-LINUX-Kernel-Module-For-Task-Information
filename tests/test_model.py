import unittest
from pathlib import Path
from taskgraph.model import (Task, Snapshot, parse, read_snapshot, rank_records,
                             capture_procfs, encode_comm, decode_comm)

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "small_tree.tsv"


class SnapshotTests(unittest.TestCase):
    def setUp(self):
        self.s = read_snapshot(EXAMPLE)

    def test_01_fixture_fields(self):
        self.assertEqual(len(self.s.tasks), 7)
        self.assertEqual(self.s.meta["source"], "fixture")
        self.assertEqual(self.s.tasks[0].pid, 0)

    def test_02_dfs_order(self):
        rows, _ = self.s.view()
        self.assertEqual([t.pid for t in rows], [0, 1, 10, 11, 20, 21, 2])

    def test_03_linear_order(self):
        rows, _ = self.s.view("LINEAR")
        self.assertEqual([t.pid for t in rows], [0, 1, 2, 10, 11, 20, 21])

    def test_04_subtree(self):
        rows, total = self.s.view(root=10)
        self.assertEqual([t.pid for t in rows], [10, 11, 20, 21])
        self.assertEqual(total, 4)

    def test_05_hide_threads(self):
        rows, total = self.s.view(threads=False)
        self.assertEqual(total, 6)
        self.assertNotIn(11, [t.pid for t in rows])

    def test_06_display_limit_preserves_total(self):
        rows, total = self.s.view(limit=2)
        self.assertEqual((len(rows), total), (2, 7))

    def test_07_bad_root(self):
        with self.assertRaisesRegex(ValueError, "999"):
            self.s.view(root=999)

    def test_08_bad_limits(self):
        for value in [0, -1, 2001]:
            with self.assertRaises(ValueError):
                self.s.view(limit=value)

    def test_09_bad_version(self):
        with self.assertRaisesRegex(ValueError, "version"):
            parse(self.s.dump().replace("version=1", "version=9"))

    def test_10_duplicate_pid(self):
        text = self.s.dump()
        lines = text.splitlines()
        lines[-1] = "\t".join(["0"] + lines[-1].split("\t")[1:])
        with self.assertRaisesRegex(ValueError, "PID"):
            parse("\n".join(lines))

    def test_11_invalid_count(self):
        with self.assertRaisesRegex(ValueError, "count"):
            parse(self.s.dump().replace("count=7", "count=8"))

    def test_12_invalid_state(self):
        with self.assertRaises(ValueError):
            parse(self.s.dump().replace("\tS\t", "\t?\t", 1))

    def test_13_control_and_unicode_name_roundtrip(self):
        value = "test\tline\n\\Монгол"
        self.assertEqual(decode_comm(encode_comm(value)), value)

    def test_14_snapshot_roundtrip(self):
        self.assertEqual(parse(self.s.dump()).tasks, self.s.tasks)

    def test_15_truncated_flag(self):
        text = self.s.dump().replace("truncated=0", "truncated=1")
        self.assertEqual(parse(text).meta["truncated"], "1")

    def test_16_missing_parent_retained(self):
        rows = [dict(pid=7, parent=999), dict(pid=8, parent=7)]
        rank_records(rows)
        self.assertEqual([(r["dfs"], r["depth"]) for r in rows], [(0, 0), (1, 1)])

    def test_17_cycle_does_not_loop(self):
        rows = [dict(pid=7, parent=8), dict(pid=8, parent=7)]
        rank_records(rows)
        self.assertEqual(sorted(r["dfs"] for r in rows), [0, 1])

    def test_18_deep_tree_without_recursion(self):
        rows = [dict(pid=i, parent=max(0, i-1)) for i in range(5000)]
        rank_records(rows)
        self.assertEqual(rows[-1]["depth"], 4999)

    def test_19_parent_after_child(self):
        rows = [dict(pid=1, parent=20), dict(pid=20, parent=999)]
        rank_records(rows)
        self.assertEqual([r["dfs"] for r in rows], [1, 0])

    def test_20_bad_dfs_rank(self):
        lines = self.s.dump().splitlines()
        vals = lines[-1].split("\t")
        vals[7] = "0"
        lines[-1] = "\t".join(vals)
        with self.assertRaisesRegex(ValueError, "dfs"):
            parse("\n".join(lines))

    def test_21_bad_column_count(self):
        with self.assertRaises(ValueError):
            parse(self.s.dump() + "broken\n")

    def test_22_bad_escape(self):
        with self.assertRaises(ValueError):
            decode_comm("bad\\q")

    @unittest.skipUnless(Path("/proc/self/stat").exists(), "Linux procfs required")
    def test_23_live_procfs(self):
        snap = capture_procfs()
        self.assertEqual(snap.meta["source"], "procfs")
        # Use the PID visible in this procfs mount (test runner may be namespaced).
        visible_pid = int(Path("/proc/self/stat").read_text().split()[0])
        self.assertIn(visible_pid, [t.pid for t in snap.tasks])
        self.assertEqual(parse(snap.dump()).tasks, snap.tasks)


if __name__ == "__main__":
    unittest.main()
