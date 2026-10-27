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
echo BEGIN_SNAPSHOT_CREATED
cat /proc/taskgraph
echo END_SNAPSHOT_CREATED
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
echo BEGIN_PS
ps -el
ps -T
echo END_PS
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
