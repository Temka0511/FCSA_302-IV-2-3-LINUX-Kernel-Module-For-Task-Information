#!/usr/bin/env bash
set -u
printf 'OS: '; uname -sr
printf 'Python: '; python3 --version
printf 'Compiler: '; gcc --version | head -1
printf 'Build: '; make --version | head -1
if test -d "/lib/modules/$(uname -r)/build"; then
  echo 'Matching kernel headers: OK'
else
  echo 'Matching kernel headers: MISSING'
fi
python3 -c 'import tkinter; print("Tkinter:", tkinter.TkVersion)' || true
if test -r /proc/taskgraph; then
  echo 'Kernel module endpoint: OK'
else
  echo 'Kernel module endpoint: NOT LOADED'
fi
printf 'DISPLAY: %s\n' "${DISPLAY:-unset (CLI only)}"
