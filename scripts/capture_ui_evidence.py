"""Capture the actual Tk UI using saved snapshots from the QEMU kernel test.

Run with a graphical display and Pillow installed:
    PYTHONPATH=src python3 scripts/capture_ui_evidence.py
"""
from pathlib import Path
import tkinter as tk

from PIL import ImageGrab

from taskgraph.gui import App


ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "docs" / "images"


def capture(source, mode, filename):
    root = tk.Tk()
    try:
        root.geometry("1280x850+20+20")
        app = App(root, str(ROOT / "docs" / "evidence" / source))
        app.root_pid.set("90")
        app.mode.set(mode)
        app.apply()
        root.update()
        assert app.snapshot.meta["source"] == "kernel"
        assert len(app.rows) == 7
        assert app.canvas.bbox("all")[2] <= app.canvas.winfo_width(), "Graph is clipped horizontally"
        if source == "stopped.tsv":
            assert next(t.state for t in app.rows if t.pid == 90) in ("T", "t")
        x, y = root.winfo_rootx(), root.winfo_rooty()
        ImageGrab.grab(bbox=(x, y, x + 1280, y + 850)).save(IMAGES / filename)
        print(filename, mode, source, "tasks=7")
    finally:
        root.destroy()


def main():
    IMAGES.mkdir(exist_ok=True)
    capture("created.tsv", "DFS", "kernel_created_ui.png")
    capture("created.tsv", "LINEAR", "kernel_linear_ui.png")
    capture("stopped.tsv", "DFS", "kernel_stopped_ui.png")


if __name__ == "__main__":
    main()
