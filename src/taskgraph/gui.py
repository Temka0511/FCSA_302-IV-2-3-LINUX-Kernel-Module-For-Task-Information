"""Native Tk interface: real snapshot, graph, table and traversal controls."""
import argparse
from collections import Counter
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from .model import capture_procfs, read_snapshot

COLORS = {"R": "#b9ead7", "S": "#cbdff6", "I": "#e0e6ef", "D": "#f8d9aa",
          "T": "#f8d9aa", "t": "#f8d9aa", "Z": "#f6c1c9", "X": "#f6c1c9"}


class App:
    def __init__(self, root, source="/proc/taskgraph", procfs=False):
        self.root = root
        self.snapshot = None
        self.rows = []
        self.step = -1
        self.playing = False
        self.autorefresh = tk.BooleanVar(value=False)
        self.threads = tk.BooleanVar(value=True)
        self.source_kind = tk.StringVar(value="procfs" if procfs else
                                       ("kernel" if source == "/proc/taskgraph" else "file"))
        self.source_path = source
        self.mode = tk.StringVar(value="DFS")
        self.root_pid = tk.StringVar()
        self.limit = tk.StringVar(value="150")
        self.interval = tk.StringVar(value="1500")
        self.status = tk.StringVar(value="TaskGraph")
        self.summary = tk.StringVar()
        self.detail = tk.StringVar(value="Зангилаа сонгож дэлгэрэнгүйг харна.")
        root.title("F.CSM302 | TaskGraph - Linux Tasks")
        root.geometry("1280x850")
        root.minsize(1040, 700)
        root.configure(background="#f1f5fa")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f1f5fa")
        style.configure("TLabel", background="#f1f5fa", font=("DejaVu Sans", 10))
        style.configure("Title.TLabel", font=("DejaVu Sans", 20, "bold"), foreground="#173250")
        style.configure("TButton", padding=(9, 6))
        style.configure("Treeview", rowheight=25, font=("DejaVu Sans", 9))
        outer = ttk.Frame(root, padding=16)
        outer.pack(fill="both", expand=True)
        title = ttk.Frame(outer)
        title.pack(fill="x")
        ttk.Label(title, text="TaskGraph", style="Title.TLabel").pack(side="left")
        ttk.Label(title, text="  Linux Kernel Module for Listing Tasks  /  Project 3").pack(side="left", padx=14)
        top = ttk.Frame(outer)
        top.pack(fill="x", pady=(12, 6))
        ttk.Label(top, text="Эх үүсвэр:").pack(side="left")
        sourcebox = ttk.Combobox(top, textvariable=self.source_kind,
            values=("kernel", "procfs", "file"), state="readonly", width=9)
        sourcebox.pack(side="left", padx=5)
        sourcebox.bind("<<ComboboxSelected>>", self.change_source)
        ttk.Button(top, text="Файл нээх", command=self.open_file).pack(side="left", padx=3)
        ttk.Button(top, text="Шинэчлэх", command=self.refresh).pack(side="left", padx=3)
        ttk.Checkbutton(top, text="Авто шинэчлэлт", variable=self.autorefresh).pack(side="left", padx=10)
        ttk.Label(top, text="ms:").pack(side="left")
        ttk.Spinbox(top, from_=500, to=10000, increment=500,
                    textvariable=self.interval, width=6).pack(side="left", padx=4)
        ttk.Button(top, text="Snapshot хадгалах", command=self.export).pack(side="right")
        config = ttk.Frame(outer)
        config.pack(fill="x", pady=5)
        ttk.Label(config, text="Дараалал:").pack(side="left")
        box = ttk.Combobox(config, textvariable=self.mode, values=("DFS", "LINEAR"),
                           state="readonly", width=9)
        box.pack(side="left", padx=5)
        box.bind("<<ComboboxSelected>>", lambda _: self.apply())
        ttk.Label(config, text="Root PID (хоосон = бүгд):").pack(side="left", padx=(12, 4))
        ttk.Entry(config, textvariable=self.root_pid, width=8).pack(side="left")
        ttk.Label(config, text="  Зангилааны хязгаар:").pack(side="left")
        ttk.Spinbox(config, from_=1, to=2000, textvariable=self.limit, width=6).pack(side="left", padx=4)
        ttk.Checkbutton(config, text="Threads", variable=self.threads,
                        command=self.apply).pack(side="left", padx=8)
        ttk.Button(config, text="Хэрэглэх", command=self.apply).pack(side="left", padx=3)
        ttk.Button(config, text="Reset", command=self.reset).pack(side="left", padx=3)
        ttk.Label(outer, textvariable=self.summary, foreground="#24617a").pack(anchor="w", pady=7)
        panes = ttk.Panedwindow(outer, orient="horizontal")
        panes.pack(fill="both", expand=True)
        graphframe = ttk.Frame(panes)
        tableframe = ttk.Frame(panes)
        panes.add(graphframe, weight=3)
        panes.add(tableframe, weight=2)
        ttk.Label(graphframe, text="TASK GRAPH   |   сум: parent -> child; тасархай: process -> thread").pack(anchor="w", pady=4)
        viewport = ttk.Frame(graphframe)
        viewport.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(viewport, background="#ffffff", highlightthickness=1,
                                highlightbackground="#d4deea")
        ys = ttk.Scrollbar(viewport, orient="vertical", command=self.canvas.yview)
        xs = ttk.Scrollbar(viewport, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        ys.grid(row=0, column=1, sticky="ns")
        xs.grid(row=1, column=0, sticky="ew")
        viewport.rowconfigure(0, weight=1)
        viewport.columnconfigure(0, weight=1)
        self.canvas.bind("<ButtonPress-2>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B2-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))
        self.canvas.bind("<MouseWheel>", lambda e: self.canvas.yview_scroll(-int(e.delta / 120), "units"))
        ttk.Label(tableframe, text="SNAPSHOT TABLE   |   сонгосон traversal-ийн дараалал").pack(anchor="w", padx=8, pady=4)
        tableview = ttk.Frame(tableframe)
        tableview.pack(fill="both", expand=True, padx=(8, 0))
        cols = ("pid", "ppid", "state", "kind", "comm")
        self.table = ttk.Treeview(tableview, columns=cols, show="headings", selectmode="browse")
        for col, width in zip(cols, (64, 64, 47, 70, 150)):
            self.table.heading(col, text=col.upper())
            self.table.column(col, width=width, minwidth=45)
        ts = ttk.Scrollbar(tableview, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=ts.set)
        self.table.pack(side="left", fill="both", expand=True)
        ts.pack(side="right", fill="y")
        self.table.bind("<<TreeviewSelect>>", self.select_table)
        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(10, 4))
        ttk.Button(controls, text="Өмнөх", command=lambda: self.advance(-1)).pack(side="left")
        ttk.Button(controls, text="Дараах", command=lambda: self.advance(1)).pack(side="left", padx=4)
        self.play_button = ttk.Button(controls, text="Тоглуулах", command=self.play)
        self.play_button.pack(side="left", padx=4)
        ttk.Label(controls, text="  Ногоон R | Цэнхэр S | Шар T/D | Ягаан Z | Улбар хүрээ = сонгосон",
                  font=("DejaVu Sans", 9)).pack(side="left", padx=8)
        ttk.Label(outer, textvariable=self.detail, wraplength=1210).pack(anchor="w", pady=5)
        self.status_label = ttk.Label(outer, textvariable=self.status, foreground="#2f526b", wraplength=1210)
        self.status_label.pack(anchor="w")
        root.bind("<Return>", lambda _: self.apply())
        self.refresh()
        root.after(500, self.tick)

    def interval_value(self):
        try:
            value = int(self.interval.get())
            if not 500 <= value <= 10000:
                raise ValueError()
            return value
        except ValueError as exc:
            raise ValueError("Шинэчлэх интервал 500..10000 ms байна.") from exc

    def change_source(self, _=None):
        self.autorefresh.set(False)
        if self.source_kind.get() == "file":
            self.open_file()
        else:
            self.source_path = "/proc/taskgraph"
            self.refresh()

    def open_file(self):
        path = filedialog.askopenfilename(filetypes=[("TaskGraph snapshot", "*.tsv"), ("All", "*")])
        if path:
            self.source_kind.set("file")
            self.source_path = path
            self.autorefresh.set(False)
            self.refresh()

    def refresh(self):
        try:
            self.interval_value()
            snapshot = (capture_procfs() if self.source_kind.get() == "procfs"
                        else read_snapshot(self.source_path))
            self.snapshot = snapshot
            self.playing = False
            self.play_button.config(text="Тоглуулах")
            self.step = -1
            self.apply()
        except (OSError, ValueError) as exc:
            self.autorefresh.set(False)
            self.status_label.config(foreground="#a72c47")
            self.status.set(f"Унших алдаа: {exc}. Kernel горимд эхлээд make, sudo insmod хийнэ. "
                            "Өмнөх snapshot байвал дэлгэцэд хэвээр байна.")

    def apply(self):
        if self.snapshot is None:
            return
        try:
            self.interval_value()
            root = int(self.root_pid.get()) if self.root_pid.get().strip() else None
            if root is not None and root < 0:
                raise ValueError("PID сөрөг байж болохгүй.")
            self.rows, total = self.snapshot.view(self.mode.get(), root,
                int(self.limit.get()), self.threads.get())
            self.step = min(self.step, len(self.rows) - 1)
            counts = Counter(t.state for t in self.snapshot.tasks)
            source = self.snapshot.meta.get("source", "unknown")
            self.summary.set(f"SOURCE: {source.upper()}  |  Snapshot: {len(self.snapshot.tasks)} tasks  |  "
                             f"Харагдаж буй: {len(self.rows)}/{total}  |  " +
                             "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
            self.status_label.config(foreground="#2f526b")
            text = {"kernel": "Kernel модуль -> /proc/taskgraph -> бодит task snapshot.",
                    "procfs": "PROCFS оношилгооны горим: бодит /proc өгөгдөл; kernel модулийн тест биш.",
                    "fixture": "FIXTURE: зохиомол тестийн өгөгдөл; бодит kernel snapshot биш."}.get(source,
                        "Импортолсон snapshot: source мэдээллийг файлаас уншсан.")
            if self.source_kind.get() == "file":
                text = "FILE: " + Path(self.source_path).name + " | " + text
            if self.snapshot.meta.get("truncated") == "1":
                text += " АНХААР: capture cap хүрсэн, snapshot дутуу. max_tasks-ийг өсгөж дахин ачаална."
            elif len(self.rows) < total:
                text += " Графын хязгаараас зарим зангилаа харагдахгүй; snapshot бүтэн."
            self.status.set(text)
            self.draw()
        except ValueError as exc:
            self.autorefresh.set(False)
            self.status_label.config(foreground="#a72c47")
            self.status.set(f"Оролтын алдаа: {exc}")

    def draw(self):
        self.canvas.delete("all")
        self.table.delete(*self.table.get_children())
        by_pid = {t.pid: t for t in self.rows}
        # Indentation is relative to visible roots, cycle-safe and iterative.
        depths = {}
        for t in self.rows:
            chain, seen, cur = [], set(), t
            while cur.pid not in depths and cur.pid not in seen:
                seen.add(cur.pid)
                chain.append(cur.pid)
                if cur.parent not in by_pid or cur.parent == cur.pid:
                    break
                cur = by_pid[cur.parent]
            depth = depths.get(cur.pid, -1)
            for pid in reversed(chain):
                depth += 1
                depths[pid] = depth
        positions = {t.pid: (30 + depths[t.pid] * 55, 28 + i * 63)
                     for i, t in enumerate(self.rows)}
        for t in self.rows:
            if t.parent in positions and t.parent != t.pid:
                x, y = positions[t.pid]
                px, py = positions[t.parent]
                self.canvas.create_line(px + 12, py + 36, px + 12, y + 18,
                    x, y + 18, fill="#8ba4bb", width=2, arrow="last",
                    dash=(4, 3) if t.kind == "thread" else ())
        for i, t in enumerate(self.rows):
            x, y = positions[t.pid]
            tag = f"pid_{t.pid}"
            self.canvas.create_rectangle(x, y, x + 258, y + 42, fill=COLORS.get(t.state, "#e4eaf1"),
                outline="#e68b21" if i == self.step else "#9ab0c6",
                width=3 if i == self.step else 1, tags=tag)
            self.canvas.create_text(x + 10, y + 12, anchor="w", text=f"{t.pid}  {t.comm[:22]}",
                font=("DejaVu Sans", 10, "bold"), fill="#15324d", tags=tag)
            self.canvas.create_text(x + 10, y + 30, anchor="w",
                text=f"{t.state}  |  {t.kind}  |  PPID {t.ppid}  |  DFS {t.dfs}",
                font=("DejaVu Sans", 8), fill="#36556f", tags=tag)
            self.canvas.tag_bind(tag, "<Button-1>", lambda _, idx=i: self.select(idx))
            self.table.insert("", "end", iid=str(t.pid), values=(t.pid, t.ppid, t.state, t.kind, t.comm))
        bounds = self.canvas.bbox("all")
        self.canvas.configure(scrollregion=(0, 0, max(600, bounds[2] + 30) if bounds else 600,
                                            max(500, bounds[3] + 30) if bounds else 500))
        if 0 <= self.step < len(self.rows):
            self.table.selection_set(str(self.rows[self.step].pid))

    def select(self, idx):
        if not 0 <= idx < len(self.rows):
            return
        self.step = idx
        t = self.rows[idx]
        self.detail.set(f"Алхам {idx + 1}/{len(self.rows)}: PID={t.pid}, PPID={t.ppid}, TGID={t.tgid}, "
                        f"graph parent={t.parent}, state={t.state}, type={t.kind}, "
                        f"linear={t.linear}, DFS={t.dfs}, depth={t.depth}, comm={t.comm!r}")
        self.draw()
        self.table.see(str(t.pid))

    def select_table(self, _):
        selected = self.table.selection()
        if selected and 0 <= self.step < len(self.rows) and int(selected[0]) == self.rows[self.step].pid:
            return
        if selected:
            for i, t in enumerate(self.rows):
                if t.pid == int(selected[0]):
                    self.select(i)
                    break

    def advance(self, delta):
        self.playing = False
        self.play_button.config(text="Тоглуулах")
        if self.rows:
            self.select(max(0, min(len(self.rows) - 1, self.step + delta)))

    def play(self):
        self.autorefresh.set(False)
        self.playing = not self.playing
        self.play_button.config(text="Зогсоох" if self.playing else "Тоглуулах")
        if self.playing:
            if self.step >= len(self.rows) - 1:
                self.step = -1
            self.play_step()

    def play_step(self):
        if not self.playing:
            return
        if self.step + 1 < len(self.rows):
            self.select(self.step + 1)
            self.root.after(650, self.play_step)
        else:
            self.playing = False
            self.play_button.config(text="Тоглуулах")

    def reset(self):
        self.playing = False
        self.play_button.config(text="Тоглуулах")
        self.root_pid.set("")
        self.limit.set("150")
        self.mode.set("DFS")
        self.threads.set(True)
        self.autorefresh.set(False)
        self.step = -1
        self.detail.set("Reset: тухайн snapshot-ийн шүүлт болон traversal эхэллээ.")
        self.apply()
        self.canvas.yview_moveto(0)
        self.canvas.xview_moveto(0)

    def export(self):
        if self.snapshot is None:
            messagebox.showinfo("TaskGraph", "Эхлээд snapshot уншина.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".tsv", initialfile="snapshot.tsv")
        if path:
            try:
                Path(path).write_text(self.snapshot.dump(), encoding="utf-8")
                self.status.set("Бүтэн snapshot хадгаллаа: " + path)
            except OSError as exc:
                self.status.set("Хадгалах алдаа: " + str(exc))

    def tick(self):
        try:
            delay = self.interval_value()
        except ValueError:
            delay = 1500
            if self.autorefresh.get():
                self.apply()
        if self.autorefresh.get():
            self.refresh()
        self.root.after(delay, self.tick)


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source", help="Import a saved snapshot")
    group.add_argument("--procfs", action="store_true")
    group.add_argument("--kernel", action="store_true", help="Require the real Linux kernel module")
    args = parser.parse_args()
    from .launch import startup_source
    source, procfs = startup_source(args.source, args.kernel, args.procfs)
    root = tk.Tk()
    app = App(root, source, procfs)
    root.mainloop()


if __name__ == "__main__":
    main()
