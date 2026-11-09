"""Check the displayed traversal and graph edges without a display server."""
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

from taskgraph.cli import main as cli_main
from taskgraph.gui import App
from taskgraph.model import read_snapshot


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "small_tree.tsv"
CREATED = Path(__file__).resolve().parents[1] / "docs" / "evidence" / "created.tsv"


class DisplayContractTests(TestCase):
    def test_linear_cli_shows_linear_ranks(self):
        output = StringIO()
        with patch("sys.argv", ["taskgraph.cli", "--source", str(EXAMPLE),
                                "--mode", "LINEAR"]), redirect_stdout(output):
            cli_main()
        lines = output.getvalue().splitlines()
        self.assertEqual(lines[1].split("\t")[5], "LINEAR")
        self.assertEqual([(int(row[0]), int(row[5])) for row in
                          (line.split("\t") for line in lines[2:])],
                         [(0, 0), (1, 1), (2, 2), (10, 3), (11, 4), (20, 5), (21, 6)])

    def test_linear_graph_keeps_true_parent_edges_clear_of_boxes(self):
        snapshot = read_snapshot(EXAMPLE)
        rows, _ = snapshot.view("LINEAR")
        app = App.__new__(App)
        app.rows = rows
        app.step = 2  # PID 2 in LINEAR, which is last on the physical tree.
        app.mode = Mock(get=lambda: "LINEAR")
        app.canvas = Mock()
        app.canvas.bbox.return_value = (0, 0, 1500, 800)
        app.table = Mock()
        app.table.get_children.return_value = []
        app.draw()

        tree_rows = sorted(rows, key=lambda task: task.dfs)
        boxes = {task.pid: call.args for task, call in
                 zip(tree_rows, app.canvas.create_rectangle.call_args_list)}
        outlines = {task.pid: call.kwargs["outline"] for task, call in
                    zip(tree_rows, app.canvas.create_rectangle.call_args_list)}
        fills = {task.pid: call.kwargs["fill"] for task, call in
                 zip(tree_rows, app.canvas.create_rectangle.call_args_list)}
        self.assertEqual(outlines[2], "#563b8c")
        self.assertNotEqual(outlines[2], fills[21])  # T-state's orange fill.
        edges = [call.args for call in app.canvas.create_line.call_args_list]
        expected_children = [task for task in tree_rows
                             if task.parent in boxes and task.parent != task.pid]
        self.assertEqual(len(edges), len(expected_children))
        for task, edge in zip(expected_children, edges):
            parent, child = boxes[task.parent], boxes[task.pid]
            self.assertEqual(edge[0:2], (parent[2], parent[1] + 21))
            self.assertEqual(edge[-2:], (child[0], child[1] + 21))
            # Vertical connectors live entirely in the gap between columns.
            connector_x = edge[2]
            low_y, high_y = sorted((edge[3], edge[5]))
            for pid, box in boxes.items():
                if pid not in (task.parent, task.pid):
                    self.assertFalse(box[0] <= connector_x <= box[2] and
                                     low_y <= box[3] and high_y >= box[1],
                                     f"edge to {task.pid} overlaps PID {pid}")
        labels = [call.kwargs["text"] for call in app.canvas.create_text.call_args_list
                  if "PPID" in call.kwargs["text"]]
        self.assertTrue(all("LINEAR " in label and "DFS " not in label for label in labels))
        self.assertEqual([call.kwargs["values"][0] for call in
                          app.table.insert.call_args_list], [task.pid for task in rows])

    def test_seven_task_kernel_tree_fits_default_graph_viewport(self):
        rows, count = read_snapshot(CREATED).view("LINEAR", root=90, limit=20)
        self.assertEqual(count, 7)
        app = App.__new__(App)
        app.rows, app.step = rows, -1
        app.mode = Mock(get=lambda: "LINEAR")
        app.canvas, app.table = Mock(), Mock()
        app.canvas.bbox.return_value = (0, 0, 700, 600)
        app.table.get_children.return_value = []
        app.draw()
        self.assertLessEqual(max(call.args[2] for call in
                                 app.canvas.create_rectangle.call_args_list), 650)
