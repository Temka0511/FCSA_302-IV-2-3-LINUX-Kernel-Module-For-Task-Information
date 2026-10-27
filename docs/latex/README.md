# Тайлангийн LaTeX эх

ШУТИС-ийн өгсөн Titlepage.tex загвар болон MUST_logo.png логог ашиглав.

- report.tex: үндсэн тайлан.
- manual.tex: хэрэглэгчийн болон operational гарын авлага.
- Titlepage.tex: нийтлэг нүүр; нэр, оюутны кодыг энд засна.
- preamble.tex: фонт, хуудас, хүснэгтийн тохиргоо.
- figures/MUST_logo.png: өгсөн лого.
- ../images/: UI-ийн нотолгооны зургууд.

XeLaTeX ашиглан хоёр удаа compile хийнэ. Төслийн үндсэн хавтсаас:

```bash
python3 docs/generate_documents.py
```

TeX Live эсвэл MiKTeX шаардлагатай. Програмын UI-г ажиллуулахад LaTeX хэрэггүй.
Фонт Times New Roman байвал түүнийг, байхгүй бол DejaVu Serif ашиглана.
Тайлангийн зураг, эх код, test log-ийг хамт хадгална.
