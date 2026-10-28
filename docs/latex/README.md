# Тайлангийн LaTeX эх

ШУТИС-ийн өгсөн Titlepage.tex загвар болон MUST_logo.png логог ашиглав.

- report.tex: үндсэн тайлан.
- manual.tex: хэрэглэгчийн болон operational гарын авлага.
- Titlepage.tex: нийтлэг нүүр; нэр, оюутны кодыг энд засна.
- preamble.tex: фонт, хуудас, хүснэгтийн тохиргоо.
- figures/MUST_logo.png: өгсөн лого.
- figures/architecture.pdf: цөм ба хэрэглэгчийн орон зайн архитектур.
- figures/snapshot_lifecycle.pdf: snapshot унших дуудлагын дараалал.
- figures/task_tree.pdf: бодит kernel snapshot-ийн процесс/thread мод.
- ../images/: UI-ийн нотолгооны зургууд.

XeLaTeX ашиглан хоёр удаа compile хийнэ. Төслийн үндсэн хавтсаас:

```bash
python3 docs/generate_documents.py
```

TeX Live эсвэл MiKTeX шаардлагатай. Програмын UI-г ажиллуулахад LaTeX хэрэггүй.
Фонт Times New Roman байвал түүнийг, байхгүй бол DejaVu Serif ашиглана.
Тайлангийн зураг, эх код, test log-ийг хамт хадгална.

Схемүүд вектор PDF тул томруулж харах, хэвлэхэд чанараа алдахгүй.
Эдгээр PDF нь repository-д байгаа учир тайлан хөрвүүлэхэд Python-ийн нэмэлт
сан шаардахгүй. Схемийг өөрчлөх бол `reportlab`, DejaVu Sans фонтуудтай орчинд:

```bash
python3 docs/generate_diagrams.py
python3 docs/generate_documents.py
```

Модны PID, нэр, DFS дарааллыг `docs/evidence/created.tsv` нотолгооноос уншдаг.
