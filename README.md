# TaskGraph - Linux Kernel Module for Listing Tasks

F.CSM302 Үйлдлийн систем / Бие даалт 1 / **IV-2-3** / Chapter 3, Project 3.

Гүйцэтгэсэн: **А.Тэмүүлэн /B242270063/**. Багийн бүрэлдэхүүн: `docs/TEAM.md`.

Repository: https://github.com/Temka0511/FCSA_302-IV-2-3-LINUX-Kernel-Module-For-Task-Information

## Зорилго

C kernel module нь Linux-ийн бодит task-уудын PID, PPID, TGID, төлөв, нэрийг
уншина. Модуль ачаалагдахдаа LINEAR ба DFS жагсаалтыг kernel log-д гаргаж,
шинэ snapshot бүрийг `/proc/taskgraph`-аар өгнө. Python/Tkinter програм нь
тэдгээрийг parent-child граф, хүснэгт, traversal алхмуудаар харуулна.

## Quick Start - Windows дээр зөвхөн UI турших

Python 3 (Tcl/Tk-тэй ердийн Windows installer) суулгасан байхад repository-г
clone хийгээд **run.bat**-ийг нээнэ. VirtualBox болон Ubuntu энэ горимд хэрэггүй.
GitHub-д байршуулсны дараа өөрсдийн repository-г clone хийх команд:

```bat
git clone https://github.com/Temka0511/FCSA_302-IV-2-3-LINUX-Kernel-Module-For-Task-Information.git taskgraph
cd taskgraph
run.bat
```

Одоогийн ZIP-ийг задалсан бол `taskgraph/run.bat`-ийг double-click хийнэ.
Автомат тестээ Windows дээр `test.bat`-аар ажиллуулна (Linux procfs-ийн нэг
тест Windows дээр SKIP, үлдсэн 22 нь ажиллана).
Модуль олдоогүй үед UI нь **SOURCE: FIXTURE** гэсэн бэлэн сургалтын модтой
нээгдэнэ. Root PID=10, thread filter, LINEAR/DFS, playback, reset, export/import
удирдлагуудыг туршиж болно. Linux module ачаалсан бол энгийн launcher нь kernel
өгөгдөл сонгоно. `--kernel` гэж илт сонгосон үед sample руу шилжихгүй.

`Файл нээх` товчоор `docs/evidence/created.tsv`, `stopped.tsv`, `after.tsv`-г
нээж QEMU kernel-ээс өмнө авсан бодит snapshot-уудыг харьцуулна. Эдгээр файлыг
Windows дээр харах нь Windows-ийн бодит процессуудыг Linux module-оор уншиж
байгаа гэсэн үг биш. Бодит цагийн Linux туршилтад доорх Ubuntu орчныг ашиглана.

Linux дээр UI-г дангаар турших: `bash run.sh`. `python3-tk` хэрэгтэй.

## Quick Start - бодит Linux kernel / Ubuntu VM

Windows хэрэглэвэл VirtualBox дотор Ubuntu Desktop **24.04 LTS** суулгана.
Санал болгох VM: 2 CPU, 4 GB RAM, 40 GB dynamic disk, NAT network.
VM-ийн EFI/Secure Boot тохиргоо unsigned module ачаалахыг зөвшөөрсөн байна.
Ubuntu-ийн 6.8 GA kernel үндсэн зорилтот орчин. Өөр kernel дээр өөрийнх нь
headers-тай дахин build хийж туршина.

```bash
sudo apt update
sudo apt install -y build-essential linux-headers-$(uname -r) python3 python3-tk git
```

ZIP-ийг задалж `taskgraph` хавтсанд Terminal нээнэ:

```bash
bash scripts/check_env.sh
make -C src/kernel
sudo insmod src/kernel/taskgraph.ko max_tasks=4096 log_on_load=1
bash run.sh --kernel
```

UI-г **энгийн хэрэглэгчээр** ажиллуулна. Модуль ачаалах/буулгахад л sudo хэрэгтэй.
Эх үүсвэр `kernel` үед `/proc/taskgraph` байхгүй бол тодорхой алдаа харуулна;
өөр эх үүсвэр рүү автоматаар шилжихгүй.

Ажлаа дуусгаад:

```bash
sudo rmmod taskgraph
```

## Үндсэн туршилт

```bash
sudo dmesg | grep 'taskgraph LINEAR' | head
sudo dmesg | grep 'taskgraph DFS' | head
ps -el
ps -eLf
cat /proc/taskgraph
```

`ps -el` нь process leader-уудтай, `ps -eLf` нь thread-үүдтэй харьцуулахад хэрэглэнэ.
Хоёр хэмжилтийн хооронд шинэ/дууссан task болон төлөвийн зөрүү гарах боломжтой.
PID 0 нь модулийн нэмсэн жинхэнэ `init_task`; энгийн ps-д харагдахгүй.

Өөр Terminal-д:

```bash
export PYTHONPATH="$PWD/src"
python3 -m taskgraph.workload --depth 2 --fanout 2 --seconds 45
```

Эхний мөрийн root PID-г UI-ийн `Root PID` талбарт оруулж `Хэрэглэх` дарна.
Нийт 7 process бүхий мод харагдана. `Авто шинэчлэлт` асаагаад workload дуусахад
шинэчилсэн snapshot-оос процессууд алга болохыг ажиглана. Сонгосон root өөрөө
дуусвал "PID ... алга" гэсэн мэдээлэл гарна; Root PID-г цэвэрлэж дахин хэрэглэнэ.

## Тест

```bash
bash scripts/test.sh
export PYTHONPATH="$PWD/src"
python3 scripts/verify_live.py
```

Эхний команд parser, DFS, subtree, boundary/error, export/import болон бодит
procfs уншилтын 23 тест ажиллуулна. Хоёр дахь команд нь ачаалагдсан kernel
module шаардсан 6 интеграцийн шалгалт хийж `evidence/` хавтсанд үр дүнг хадгална.
Хүлээгдэж буй үр дүнг PASS болсон мэтээр тайлагнадаггүй: гарсан JSON-ыг уншина.

Бэлтгэх үед 23/23 автомат тест, Linux 6.8.0-31 дээр QEMU TCG-ийн 12/12
бодит kernel шалгалт тэнцсэн. Бүтэн нотолгоо: `docs/evidence/kernel_results.json`,
`docs/evidence/qemu-serial.log`, `docs/unit-tests.log`. QEMU туршилт нь initramfs
орчин; Desktop VM дээр UI-г шууд `/proc/taskgraph`-тай ажиллуулан давтахыг
хэрэглэгчийн гарын авлагад заасан. Тайлангийн kernel UI зураг нь энэ QEMU-аас
авсан бодит snapshot-ийг импортолсон дэлгэц юм.

QEMU шалгалтыг дахин хийх бол нэмэлт орчин:

```bash
sudo apt install -y qemu-system-x86 busybox-static
PYTHONPATH=src python3 scripts/qemu_smoke.py --kernel /boot/vmlinuz-$(uname -r)
```

Энэ нь тухайн kernel-тэй таарсан `src/kernel/taskgraph.ko`-г build хийсэн байхыг
шаардана. Зарим системд `/boot/vmlinuz-*` зөвхөн root-д уншигдана; тухайн
kernel image-ийн уншиж болох хуулбарыг `--kernel`-д өгнө. Энгийн хэрэглэгчийн
гол Quick Start-д QEMU суулгах шаардлагагүй.

CLI:

```bash
PYTHONPATH=src python3 -m taskgraph.cli --source /proc/taskgraph --mode DFS --limit 40
PYTHONPATH=src python3 -m taskgraph.cli --source /proc/taskgraph --export evidence.tsv
```

Модульгүйгээр зөвхөн UI/өгөгдлийн боловсруулалтыг шалгах хоёр тусдаа горим:

```bash
bash run.sh --source examples/small_tree.tsv
bash run.sh --procfs
```

Эхнийх нь **FIXTURE / зохиомол тест**, хоёр дахь нь **PROCFS оношилгоо**.
Эдгээр нь kernel module ачаалагдсан гэдгийн нотолгоо биш. Бүрэн хамгаалалтыг
`kernel` эх үүсвэртэй Ubuntu VM дээр хийнэ. pip/npm/JDK/Graphviz хэрэггүй.

## UI

- `Шинэчлэх`: эх үүсвэрийг дахин нээж шинэ snapshot авна.
- `Авто шинэчлэлт`: 500..10000 ms интервал; алдаа гарвал зогсоно.
- `DFS / LINEAR`: нэг snapshot дээр kernel-ээс ирсэн дарааллыг сонгоно.
- `Root PID`: тухайн task-ийн дэд мод; хоосон бол бүгд.
- `Зангилааны хязгаар`: 1..2000; энэ нь харагдах хэмжээг л өөрчилнө.
- `Threads`: thread-үүдийг харуулах/нуух.
- `Өмнөх / Дараах / Тоглуулах`: snapshot дотор traversal үзүүлнэ.
- `Reset`: тухайн snapshot-ийн view тохиргоог сэргээнэ; OS процессыг устгахгүй.
- `Snapshot хадгалах / Файл нээх`: бүтэн TSV-г экспорт/импорт хийнэ.
- Graph scroll болон дунд товчоор чирэх боломжтой; click хийвэл дэлгэрэнгүй гарна.

Ногоон R, цэнхэр S, шар T/D, ягаан Z. Тасралтгүй сум нь process parenthood,
тасархай сум нь thread group membership. PPID (бодит parent process) ба graph
parent (thread-ийн хувьд TGID) нь зориуд тусдаа багана.

## Зохиомж ба хязгаарлалт

`task_struct` -> RCU хамгаалсан scalar snapshot -> parent индекс -> iterative DFS
-> `/proc/taskgraph` (seq_file) -> shared parser -> Tkinter graph/table.

- RCU нь task бүтцийн амьдралыг хамгаална; snapshot нь бүх системийн нэг агшны
  атомик зураг биш. Fork/exit/reparent үед missing parent-г root-д холбоно.
- Номын `children/sibling` жагсаалтын утгыг parent ID-уудаас сэргээнэ. Mutable
  children жагсаалтыг түгжээгүй дагаж kernel stack дээр рекурс хийдэггүй.
- LINEAR log нь process leader-ууд, DFS нь root+process+thread-үүдийг харуулна.
- `max_tasks=16..16384`, default 4096. Хүрсэн бол `truncated=1` ил тод гарна.
- Нэр нь Linux `TASK_COMM_LEN`-ээр хязгаарлагдана; бүтэн command line биш.
- PID-ууд init namespace-ийнх. Host task-уудыг харуулах учраас тусдаа Ubuntu VM
  зориулсан; container-уудын тусгаарлалтад ашиглах хэрэгсэл биш.
- Том графыг scroll/subtree/limit-ээр судална; 2000 хүртэл зангилаанд layout
  гүйцэтгэл дэлгэцийн хэмжээнээс хамаарна.
- Модулийг build хийсэн kernel-тэй тааруулж ачаална. Invalid module format бол
  одоо ажиллаж буй kernel-ийн headers-тай `make clean` дараа дахин build хийнэ.

## Repository бүтэц

```text
src/kernel/             C module + Kbuild Makefile
src/taskgraph/          shared model, GUI, CLI, workload
tests/                  23 automated checks
examples/               explicit fixture data
scripts/                environment and live verification
docs/                   report, manual, evidence and team metadata
```

## Баримт бичиг ба илгээлт

- `docs/TaskGraph_BD1_Report.pdf`: үндсэн тайлан.
- `docs/TaskGraph_Manual.pdf`: хэрэглэгчийн болон operational заавар.
- `docs/latex/`: өгсөн ШУТИС-ийн нүүр, лого, тайлан/Manual-ийн LaTeX эх.
- PDF-ийг дахин үүсгэх: `python3 docs/generate_documents.py` (XeLaTeX хэрэгтэй).

GitHub repository-д эх код, тест, баримт бичиг, нотолгооны файлуудыг хамт
байршуулна. Нийтэлсэн хувилбарт `v1.0-bd1` tag тавина. Багийн нэг Teams постод
тайлан, Manual болон GitHub холбоос хавсаргана. Багшийн нэр болон бусад гишүүний нэрийг баталгаажуулсны дараа `docs/latex/Titlepage.tex`-д нөхнө.
Оноогдсон багийн Review.pdf нь тусдаа илгээлт байна.

## Эх сурвалж ба AI

- Silberschatz, Galvin, Gagne. Operating System Concepts, 10th ed. (2018),
  Chapter 3, Programming Projects, Project 3, P-17..P-19 (PDF 209..211).
- Linux 6.8: https://docs.kernel.org/6.8/RCU/listRCU.html
- seq_file: https://docs.kernel.org/6.8/filesystems/seq_file.html
- Kbuild: https://docs.kernel.org/6.8/kbuild/modules.html
- Python standard library: tkinter, dataclasses, unittest, subprocess.
- Багшийн OS_BD1_Guide.pdf; II-4-13 багийн report/manual-ийг баримт бичгийн
  бүтцийн жишээ болгож ашигласан. Тэдний Banker алгоритм энэ сэдэвт хамаарахгүй.
- Код, тест, баримт бичгийг боловсруулахад ChatGPT/Codex-ийн туслалцаа ашигласан.

Kernel source: SPDX GPL-2.0; бусад төслийн эх код мөн GPL-2.0-only.
