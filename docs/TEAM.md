# Багийн бүрэлдэхүүн

Багийн код: IV-2-3  
Хичээл: F.CSM302 Үйлдлийн систем  
Төсөл: Linux Kernel Module for Listing Tasks  
Сурах бичиг: Chapter 3 / Programming Project 3  
Үндсэн дүрслэл: Task graph

| Оюутны код | Нэр |
|---|---|
| B242270063 | А.Тэмүүлэн |
| B232270142 | Ч.Балгандамба |
| B241940101 | Д.Азмаа |
| B231910009 | Н.Билэгт-Очир |
| B190910820 | Т.Түвшинтөр |
| B210930901 | Б.Өсөхбаяр |

Шалгасан багш: Г.Ганбат.

Repository: https://github.com/Temka0511/FCSA_302-IV-2-3-LINUX-Kernel-Module-For-Task-Information

## Ажлын хуваарилалт

| Гишүүн | Хариуцах ажил | Холбогдох файл |
|---|---|---|
| А.Тэмүүлэн /B242270063/ | Kernel module, LINEAR, children/sibling DFS | `src/kernel/taskgraph.c`, `src/kernel/Makefile` |
| Ч.Балгандамба /B232270142/ | Snapshot формат, parser, оролтын шалгалт, нэгж тест | `src/taskgraph/model.py`, `tests/test_model.py` |
| Д.Азмаа /B241940101/ | Процессын граф, хүснэгт, UI удирдлага, шүүлт | `src/taskgraph/gui.py`, `src/taskgraph/cli.py` |
| Н.Билэгт-Очир /B231910009/ | Workload, STOP/CONT, ps харьцуулалт | `tests/guest_workload.c`, `scripts/verify_live.py` |
| Т.Түвшинтөр /B190910820/ | Орчин, build/run, QEMU, boundary/error шалгалт | `scripts/check_env.sh`, `scripts/qemu_smoke.py` |
| Б.Өсөхбаяр /B210930901/ | Тайлан, гарын авлага, нотолгоог нэгтгэх | `docs/latex/report.tex`, `docs/latex/manual.tex` |
