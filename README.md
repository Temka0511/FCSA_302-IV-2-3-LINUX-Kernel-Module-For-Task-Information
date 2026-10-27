# TaskGraph - Linux Kernel Module for Listing Tasks

F.CSM302 Үйлдлийн систем / Бие даалт 1 / **IV-2-3** / Chapter 3, Project 3.

Хувилбар: **v1.1.1-bd1**. Тайлан, гарын авлага: [docs/](docs/).

Багийн бүрэлдэхүүн: [docs/TEAM.md](docs/TEAM.md). Шалгасан багш: **Г.Ганбат**.

Repository: https://github.com/Temka0511/FCSA_302-IV-2-3-LINUX-Kernel-Module-For-Task-Information

## Зорилго

C kernel module нь Linux-ийн бодит task-уудын PID, PPID, TGID, төлөв, нэрийг
уншина. Модуль ачаалагдахдаа LINEAR ба DFS жагсаалтыг kernel log-д гаргаж,
шинэ snapshot бүрийг `/proc/taskgraph`-аар өгнө. Python/Tkinter програм нь
тэдгээрийг parent-child граф, хүснэгт, traversal алхмуудаар харуулна.

## Ubuntu дээр суулгах

Ubuntu Desktop 24.04 LTS орчинд ажиллана. Туршсан kernel: Linux 6.8.0-31.
Өөр kernel ашиглавал тухайн kernel-ийн headers-тай хөрвүүлнэ.
VirtualBox ашиглавал 2 CPU, 4 GB RAM, 40 GB диск тохиромжтой.

```bash
sudo apt update
sudo apt install -y build-essential linux-headers-$(uname -r) python3 python3-tk git procps
git clone https://github.com/Temka0511/FCSA_302-IV-2-3-LINUX-Kernel-Module-For-Task-Information.git taskgraph
cd taskgraph
```

Дараагийн командуудыг `taskgraph` хавтас дотроос ажиллуулна.
Хавтас өмнө нь байгаа бол дахин clone хийхгүй: `cd ~/taskgraph` гэж ороод
`git pull --ff-only` командаар шинэчилнэ.

## Ажиллуулах

```bash
bash scripts/check_env.sh
make -C src/kernel
sudo insmod src/kernel/taskgraph.ko max_tasks=4096 log_on_load=1
bash run.sh --kernel
```

`make` нь kernel module-ийг хөрвүүлнэ. `insmod` нь модулийг ачаалж,
`/proc/taskgraph` мэдээллийн файлыг үүсгэнэ. Сүүлийн команд график интерфэйсийг
нээж бодит task-уудыг харуулна. Дэлгэцийн эх үүсвэр `KERNEL` байна.
UI-г энгийн хэрэглэгчээр ажиллуулна; модуль ачаалах, буулгахад sudo хэрэглэнэ.

Цонхыг хаасны дараа модулийг буулгана:

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
python3 -m taskgraph.workload --depth 2 --fanout 2 --seconds 300 &
ROOT_PID=$!
echo "ROOT_PID=$ROOT_PID"
```

Эхний мөрийн root PID-г UI-ийн `Root PID` талбарт оруулж `Хэрэглэх` дарна.
Нийт 7 process бүхий мод харагдана. `Авто шинэчлэлт` асаагаад workload дуусахад
шинэчилсэн snapshot-оос процессууд алга болохыг ажиглана. Сонгосон root өөрөө
дуусвал "PID ... алга" гэсэн мэдээлэл гарна; Root PID-г цэвэрлэж дахин хэрэглэнэ.


### Төлөвийн өөрчлөлт шалгах

Workload-ийг эхлүүлсэн тэр Terminal-д дараах командыг ажиллуулна.
`"$ROOT_PID"` хувьсагч процессын дугаарыг автоматаар ашиглана:

```bash
kill -STOP "$ROOT_PID"
```

UI-д `Шинэчлэх` дарахад root-ийн төлөв `T` болж шарлана. Дараа нь:

```bash
kill -CONT "$ROOT_PID"
```

Дахин шинэчлэхэд root үргэлжлүүлэн ажиллана. Дээрх workload зөвхөн process
үүсгэдэг тул thread шүүлтийг шалгахад олон thread-тэй task эсвэл хадгалсан
`docs/evidence/created.tsv` snapshot ашиглана.

### Интерфэйсийн шалгалт

| Үйлдэл | Хүлээгдэх үр дүн |
|---|---|
| DFS сонгоод Дараах / Тоглуулах дарах | Эцэг task хүүхдийнхээ өмнө, дэд модоор дараалан сонгогдоно. |
| LINEAR сонгох | Жагсаалт kernel-ийн шугаман дарааллаар харагдана. |
| Threads чагтыг авах | Нэмэлт thread-үүд нуугдаж, process leader-ууд үлдэнэ. |
| Snapshot хадгалах, дараа нь Файл нээх | Хадгалсан task-уудын PID, холбоос, төлөв дахин харагдана. |
| Root PID-д `abc` оруулах | Буруу оролтын мэдээлэл гарч програм үргэлжлэн ажиллана. |
| Reset дарах | Шүүлт, дараалал, playback анхны байдалд орно. |

Файл нээсний дараа бодит хэмжилтэд буцах бол UI-г хааж `bash run.sh --kernel`
командаар дахин нээнэ. Хадгалсан файл өөрөө амьд task-уудыг шинэчлэхгүй.

## Тест

```bash
bash scripts/test.sh
export PYTHONPATH="$PWD/src"
python3 scripts/verify_live.py
```

Эхний команд parser, DFS, subtree, boundary/error, export/import болон бодит
procfs уншилтын 28 тест ажиллуулна. Хоёр дахь команд нь ачаалагдсан kernel
module шаардсан 8 интеграцийн шалгалт хийж `evidence/` хавтсанд үр дүнг хадгална.
Үр дүнг үүссэн JSON болон log файлаас харна.

Бэлтгэх үед 28/28 автомат тест, Linux 6.8.0-31 дээр QEMU TCG-ийн 17/17
бодит kernel шалгалт тэнцсэн. Бүтэн нотолгоо: `docs/evidence/kernel_results.json`,
`docs/evidence/qemu-serial.log`, `docs/unit-tests.log`. QEMU туршилт нь initramfs
орчин; Desktop VM дээр UI-г шууд `/proc/taskgraph`-тай ажиллуулан давтахыг
хэрэглэгчийн гарын авлагад заасан. Тайлангийн kernel UI зураг нь энэ QEMU-аас
авсан бодит snapshot-ийг импортолсон дэлгэц юм.


### `ps`-тэй тулгасан нотолгоо

Linux 6.8.0-31, procps-ng 4.0.4 дээр модулийн entry log болон snapshot-ийг
`ps -el`, `ps -eLf`-тэй тулгасан. Туршилтын 5 process + 2 thread-ийн 7 task-ийн
PID, PPID, TGID, нэр, төлөв таарсан. Бүх системийн нийтлэг 69 process,
71 task-ийн PPID/TGID мөн таарсан. PID 0 нь ps-д харагдахгүй; түр cat/ps/insmod
процессууд, kernel thread-ийн урт нэр болон хэмжилтийн хооронд өөрчлөгдсөн
төлөвийг зөрүүний жагсаалтад тайлбарласан.

- `docs/evidence/ps-el.txt`, `ps-eLf.txt`: номын командуудын бодит гаралт.
- `docs/evidence/ps_processes.txt`, `ps_threads.txt`: талбаруудын нэмэлт гаралт.
- `docs/evidence/comparison-kernel.log`: workload ажиллаж байх үеийн entry log.
- `docs/evidence/ps_comparison.json`: харьцуулалтын тоо, зөрүү, task бүрийн дүн.
- `python3 scripts/verify_live.py`: өөр Ubuntu дээр нотолгоог дахин үүсгэнэ
  (төслийн хавтас, `PYTHONPATH=src`, ачаалсан module шаардлагатай).

QEMU шалгалтыг дахин хийх бол нэмэлт орчин:

```bash
sudo apt install -y qemu-system-x86 busybox-static procps
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
Эдгээр нь kernel module ачаалагдсан гэдгийн нотолгоо биш. Бодит task-уудыг
`kernel` эх үүсвэртэй Ubuntu орчинд харна. pip/npm/JDK/Graphviz хэрэггүй.

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

`task_struct` -> stop_machine + RCU -> for_each_process + children/sibling DFS
-> `/proc/taskgraph` (seq_file) -> shared parser -> Tkinter graph/table.

- `init_task`-аас `children/sibling` холбоосоор шууд DFS хийнэ. Стек дээр
  iterator хадгалдаг тул kernel stack дээр рекурс ашиглахгүй. Thread бүрийн
  children жагсаалтыг шалгаж, thread-ээс үүсгэсэн хүүхдийг мөн хамруулна.
- `tasklist_lock` module-д export хийгдээгүй тул `stop_machine()` ашиглан
  жагсаалт өөрчлөгдөхгүй үед хуулна. Санах ойг урьдчилан хуваарилна;
  callback дотор allocation, sleep, log хийхгүй. Snapshot бүр CPU-уудыг түр
  саатуулдаг учраас сургалтын VM-д зориулагдсан.
- Snapshot хооронд task-ууд өөрчлөгдөнө. Хязгаараас болж parent багтаагүй бол
  root-д холбож `orphan=1` гэж тэмдэглэнэ.
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
tests/                  28 automated checks
examples/               explicit fixture data
scripts/                environment and live verification
docs/                   report, manual, evidence and team metadata
```

## Эх сурвалж

- Silberschatz, Galvin, Gagne. Operating System Concepts, 10th ed. (2018),
  Chapter 3, Programming Projects, Project 3, P-17..P-19
- Linux 6.8: https://docs.kernel.org/6.8/RCU/listRCU.html
- seq_file: https://docs.kernel.org/6.8/filesystems/seq_file.html
- Kbuild: https://docs.kernel.org/6.8/kbuild/modules.html
- Python standard library: tkinter, dataclasses, unittest, subprocess.

Kernel source: SPDX GPL-2.0; бусад төслийн эх код мөн GPL-2.0-only.

Код, тест, баримт бичгийг боловсруулахад ChatGPT/Codex-ийн туслалцаа ашигласан.
