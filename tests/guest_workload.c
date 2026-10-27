/* SPDX-License-Identifier: GPL-2.0 */
/* QEMU-only workload: five processes and two extra pthreads = seven tasks. */
#define _GNU_SOURCE
#include <pthread.h>
#include <signal.h>
#include <sys/prctl.h>
#include <sys/wait.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>

static volatile sig_atomic_t done;
static int thread_fork;
static void stop(int sig) { (void)sig; done = 1; }
static void *worker(void *arg)
{
    pid_t owned = -1;
    prctl(PR_SET_NAME, "tg-worker", 0, 0, 0);
    if (thread_fork && arg) {
        owned = fork();
        if (!owned) {
            prctl(PR_SET_NAME, "tg-thread-child", 0, 0, 0);
            while (!done) usleep(20000);
            _exit(0);
        }
    }
    while (!done) usleep(20000);
    if (owned > 0) {
        kill(owned, SIGTERM);
        waitpid(owned, NULL, 0);
    }
    return NULL;
}
static void child(void)
{
    pid_t leaf;
    prctl(PR_SET_NAME, "tg-child", 0, 0, 0);
    leaf = fork();
    if (leaf < 0) _exit(2);
    if (!leaf) {
        prctl(PR_SET_NAME, "tg-leaf", 0, 0, 0);
        while (!done) usleep(20000);
        _exit(0);
    }
    while (!done) usleep(20000);
    kill(leaf, SIGTERM);
    waitpid(leaf, NULL, 0);
    _exit(0);
}
int main(int argc, char **argv)
{
    pid_t kids[2];
    pthread_t threads[2];
    int i;
    signal(SIGTERM, stop);
    signal(SIGINT, stop);
    thread_fork = argc > 1 && !strcmp(argv[1], "--thread-fork");
    prctl(PR_SET_NAME, "tg-root", 0, 0, 0);
    for (i = 0; i < 2; i++) {
        kids[i] = fork();
        if (kids[i] < 0) return 2;
        if (!kids[i]) child();
    }
    for (i = 0; i < 2; i++)
        if (pthread_create(&threads[i], NULL, worker, (void *)(long)(i == 0))) return 3;
    while (!done) usleep(20000);
    for (i = 0; i < 2; i++) kill(kids[i], SIGTERM);
    for (i = 0; i < 2; i++) waitpid(kids[i], NULL, 0);
    for (i = 0; i < 2; i++) pthread_join(threads[i], NULL);
    return 0;
}
