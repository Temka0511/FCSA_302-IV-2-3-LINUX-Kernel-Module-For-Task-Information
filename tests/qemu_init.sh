#!/bin/sh
mount -t devtmpfs devtmpfs /dev
exec >/dev/console 2>&1
mount -t proc proc /proc
mount -t sysfs sysfs /sys
export PATH=/bin
echo ENV_KERNEL=$(uname -r)
insmod /taskgraph.ko max_tasks=4096 log_on_load=1
echo 'RESULT LOAD=' $?
echo BEGIN_SNAPSHOT_BEFORE
cat /proc/taskgraph
echo END_SNAPSHOT_BEFORE
/guest_workload &
ROOT=$!
echo WORKLOAD_ROOT=$ROOT
sleep 1
# Reload while the stable workload exists: entry-point logs must contain it.
rmmod taskgraph
dmesg -c >/dev/null
insmod /taskgraph.ko max_tasks=4096 log_on_load=1
echo BEGIN_COMPARISON_LOG
dmesg | grep taskgraph
echo END_COMPARISON_LOG
echo BEGIN_SNAPSHOT_CREATED
cat /proc/taskgraph
echo END_SNAPSHOT_CREATED
export LC_ALL=C COLUMNS=4096
echo BEGIN_PS_VERSION
/bin/ps --version
echo END_PS_VERSION
echo BEGIN_PS_EL
/bin/ps -el
echo END_PS_EL
echo BEGIN_PS_ELF
/bin/ps -eLf
echo END_PS_ELF
echo BEGIN_PS_PROCESS_COLUMNS
/bin/ps -e -o pid=,ppid=,state=,comm=
echo END_PS_PROCESS_COLUMNS
echo BEGIN_PS_THREAD_COLUMNS
/bin/ps -eL -o lwp=,pid=,ppid=,state=,comm=
echo END_PS_THREAD_COLUMNS
kill -STOP $ROOT
sleep 1
echo BEGIN_SNAPSHOT_STOPPED
cat /proc/taskgraph
echo END_SNAPSHOT_STOPPED
kill -CONT $ROOT
kill -TERM $ROOT
wait $ROOT
sleep 1
echo BEGIN_SNAPSHOT_AFTER
cat /proc/taskgraph
echo END_SNAPSHOT_AFTER
/guest_workload --thread-fork &
THREAD_ROOT=$!
echo THREAD_FORK_ROOT=$THREAD_ROOT
sleep 1
echo BEGIN_SNAPSHOT_THREAD_FORK
cat /proc/taskgraph
echo END_SNAPSHOT_THREAD_FORK
kill -TERM $THREAD_ROOT
wait $THREAD_ROOT
CHURN=0
i=0
while test "$i" -lt 10; do
  /guest_workload &
  CHILD=$!
  cat /proc/taskgraph >/dev/null || CHURN=1
  kill -TERM $CHILD
  wait $CHILD
  i=$((i + 1))
done
echo RESULT CHURN=$CHURN
echo BEGIN_MODULE_LOG
dmesg | grep taskgraph
echo END_MODULE_LOG
rmmod taskgraph
echo 'RESULT UNLOAD=' $?
if test -e /proc/taskgraph; then echo RESULT ENDPOINT_REMOVED=1; else echo RESULT ENDPOINT_REMOVED=0; fi
insmod /taskgraph.ko max_tasks=1
echo 'RESULT INVALID_CAP=' $?
insmod /taskgraph.ko max_tasks=16 log_on_load=0
echo 'RESULT SMALL_CAP_LOAD=' $?
echo BEGIN_SNAPSHOT_CAPPED
cat /proc/taskgraph
echo END_SNAPSHOT_CAPPED
rmmod taskgraph
echo 'RESULT FINAL_UNLOAD=' $?
echo SMOKE_DONE
poweroff -f
