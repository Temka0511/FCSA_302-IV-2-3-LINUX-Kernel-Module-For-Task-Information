"""Regenerate the report's vector diagrams: python3 docs/generate_diagrams.py.

Requires reportlab and DejaVu Sans fonts (fonts-dejavu-core on Ubuntu).
The task-tree labels and DFS order are read from the recorded kernel evidence.
"""
from pathlib import Path
import math
import sys

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, Color

DOCS = Path(__file__).resolve().parent
sys.path.insert(0, str(DOCS.parent / "src"))
from taskgraph.model import parse

OUT = DOCS / "latex" / "figures"
NAVY, BLUE, TEAL = "#193F64", "#356C9B", "#167D83"
INK, MUTED, LINE = "#23374A", "#526B7E", "#AABFCC"
PALE, GREEN = "#EDF4FA", "#EBF6F5"


def setup(name, width, height):
    OUT.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(OUT / name), pagesize=(width, height))
    c.setTitle(name.removesuffix(".pdf").replace("_", " "))
    c.setAuthor("TaskGraph / IV-2-3")
    return c


def text(c, x, y, value, size=10, color=INK, bold=False, align="center"):
    c.setFillColor(HexColor(color))
    c.setFont("DVB" if bold else "DV", size)
    getattr(c, {"left": "drawString", "center": "drawCentredString",
                "right": "drawRightString"}[align])(x, y, value)


def box(c, x, y, w, h, title, subtitle="", fill=PALE, color=BLUE, size=11):
    c.setFillColor(HexColor(fill))
    c.setStrokeColor(HexColor(color))
    c.setLineWidth(1)
    c.roundRect(x, y, w, h, 7, stroke=1, fill=1)
    text(c, x+w/2, y+h/2+(3 if subtitle else -4), title, size, color, True)
    if subtitle:
        text(c, x+w/2, y+h/2-13, subtitle, 8.6, MUTED)


def arrow(c, points, color=BLUE, dashed=False):
    c.setStrokeColor(HexColor(color))
    c.setFillColor(HexColor(color))
    c.setLineWidth(1.15)
    c.setDash(4, 3) if dashed else c.setDash()
    path = c.beginPath()
    path.moveTo(*points[0])
    for p in points[1:]:
        path.lineTo(*p)
    c.drawPath(path)
    c.setDash()
    x, y = points[-1]
    px, py = points[-2]
    a = math.atan2(y-py, x-px)
    head = c.beginPath()
    head.moveTo(x, y)
    head.lineTo(x-6*math.cos(a-.42), y-6*math.sin(a-.42))
    head.lineTo(x-6*math.cos(a+.42), y-6*math.sin(a+.42))
    head.close()
    c.drawPath(head, fill=1, stroke=0)


def architecture():
    c = setup("architecture.pdf", 480, 358)
    # Two visibly separated execution domains; arrows carry actual data.
    for y, h, fill in [(188, 160, PALE), (8, 168, GREEN)]:
        c.setFillColor(HexColor(fill))
        c.roundRect(3, y, 474, h, 9, stroke=0, fill=1)
    text(c, 18, 328, "LINUX ЦӨМ", 9, NAVY, True, "left")
    text(c, 18, 156, "ХЭРЭГЛЭГЧИЙН ОРОН ЗАЙ", 9, TEAL, True, "left")
    box(c, 18, 255, 150, 53, "task_struct", "PID · PPID · TGID · state")
    box(c, 215, 255, 244, 53, "taskgraph.c", "LINEAR + children/sibling DFS")
    arrow(c, [(168, 282), (215, 282)])
    box(c, 215, 199, 244, 38, "/proc/taskgraph", "snapshot / TSV", size=10)
    arrow(c, [(337, 255), (337, 237)])
    arrow(c, [(337, 199), (337, 129), (301, 129)])
    text(c, 347, 181, "open / read", 8, BLUE, align="left")
    box(c, 18, 200, 150, 38, "Kernel log", "ачаалах үеийн LINEAR / DFS", size=10)
    arrow(c, [(215, 267), (190, 267), (190, 219), (168, 219)])
    box(c, 18, 108, 109, 39, "Хадгалсан TSV", "импорт / экспорт", fill="#FFFFFF", color=TEAL, size=9)
    box(c, 165, 105, 136, 48, "model.py", "parse() → Snapshot", fill="#FFFFFF", color=TEAL)
    arrow(c, [(127, 129), (165, 129)], TEAL)
    arrow(c, [(193, 105), (193, 82), (73, 82), (73, 108)], TEAL, True)
    text(c, 105, 87, "dump()", 8, TEAL)
    box(c, 165, 20, 136, 46, "gui.py", "граф + хүснэгт", fill="#FFFFFF", color=TEAL)
    box(c, 341, 20, 118, 46, "cli.py", "Terminal гаралт", fill="#FFFFFF", color=TEAL)
    arrow(c, [(233, 105), (233, 66)], TEAL)
    arrow(c, [(301, 116), (400, 116), (400, 66)], TEAL)
    c.save()


def lifecycle():
    c = setup("snapshot_lifecycle.pdf", 480, 260)
    actors = [(51, "UI / model.py"), (178, "proc / seq_file"), (316, "taskgraph.c"), (430, "Linux task")]
    for x, label in actors:
        box(c, x-47, 226, 94, 28, label, size=8.3)
        c.setStrokeColor(HexColor(LINE)); c.setDash(2, 3)
        c.line(x, 24, x, 226); c.setDash()
    def msg(x1, x2, y, label, dashed=False):
        text(c, (x1+x2)/2, y+6, label, 8.2, TEAL if dashed else BLUE)
        arrow(c, [(x1,y), (x2,y)], TEAL if dashed else BLUE, dashed)
    msg(51,178,206,"Шинэчлэх: open()")
    msg(178,316,180,"tg_open() / tg_capture()")
    # The shaded band denotes the bounded capture only, not the read lifetime.
    c.setFillColor(Color(.92,.96,.96)); c.rect(289,105,174,62,stroke=0,fill=1)
    text(c, 376, 154, "stop_machine() + RCU", 8.4, TEAL, True)
    msg(316,430,132,"хуулбарлах + DFS")
    msg(430,316,112,"rows / order / depth",True)
    msg(316,178,86,"single_open(snapshot)",True)
    msg(51,178,61,"read() / seq_read()")
    msg(178,51,36,"TSV → parse() → дүрслэл",True)
    text(c, 240, 4, "close(): tg_release() санах ойг чөлөөлнө. Дараагийн open() шинэ snapshot авна.", 8.4, MUTED)
    c.save()


def traversal():
    c = setup("task_tree.pdf", 480, 255)
    snapshot = parse((DOCS / "evidence" / "created.tsv").read_text())
    tasks = {t.pid:t for t in snapshot.tasks if 90 <= t.pid <= 96}
    positions = {90:(240,208), 95:(55,125), 96:(175,125), 91:(300,125),
                 92:(420,125), 93:(300,43), 94:(420,43)}
    for pid, t in tasks.items():
        if pid == 90:
            continue
        px, py = positions[t.parent]; x,y = positions[pid]
        arrow(c, [(px,py-22), (x,y+22)], TEAL if t.kind=="thread" else BLUE, t.kind=="thread")
    for pid,(x,y) in positions.items():
        t = tasks[pid]
        box(c,x-48,y-22,96,44,f"PID {pid}",t.comm,
            GREEN if t.kind=="thread" else PALE,
            TEAL if t.kind=="thread" else BLUE,10)
    arrow(c,[(9,63),(40,63)],BLUE)
    text(c,47,60,"process: эцэг → хүүхэд",8.4,MUTED,align="left")
    arrow(c,[(9,43),(40,43)],TEAL,True)
    text(c,47,40,"thread: бүлгийн гишүүн",8.4,MUTED,align="left")
    order = ", ".join(str(t.pid) for t in sorted(tasks.values(),key=lambda t:t.dfs))
    text(c,240,6,"Бичигдсэн DFS дараалал: " + order,9,NAVY,True)
    c.save()


def main():
    font_dir = Path("/usr/share/fonts/truetype/dejavu")
    for name, filename in [("DV","DejaVuSans.ttf"),("DVB","DejaVuSans-Bold.ttf")]:
        pdfmetrics.registerFont(TTFont(name,str(font_dir / filename)))
    architecture(); lifecycle(); traversal()
    print("Created architecture.pdf, snapshot_lifecycle.pdf, task_tree.pdf")


if __name__ == "__main__":
    main()
