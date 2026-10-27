// SPDX-License-Identifier: GPL-2.0
/* F.CSM302 / Project 3: real task snapshot, linear listing and iterative DFS.
 * Target: Ubuntu 24.04 GA kernel 6.8. Rebuild for the running kernel.
 * Never traverses children/sibling without tasklist_lock: the mutable tree is
 * reconstructed from scalar parent IDs copied while holding the RCU read lock.
 */
#include <linux/module.h>
#include <linux/init_task.h>
#include <linux/sched/signal.h>
#include <linux/rcupdate.h>
#include <linux/proc_fs.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/hashtable.h>
#include <linux/ktime.h>

#define TG_NAME "taskgraph"
#define TG_MAX 16384U
static unsigned int max_tasks = 4096;
module_param(max_tasks, uint, 0444);
MODULE_PARM_DESC(max_tasks, "Maximum rows including PID 0 (16..16384)");
static bool log_on_load = true;
module_param(log_on_load, bool, 0444);
MODULE_PARM_DESC(log_on_load, "Print both textbook traversals at module init");

struct tg_row {
	pid_t pid, ppid, tgid, parent;
	char state, comm[TASK_COMM_LEN];
	int first, last, next, prev;
	unsigned int dfs, depth;
	bool thread, orphan, visited;
	struct hlist_node index;
};
struct tg_snapshot {
	struct tg_row *rows;
	unsigned int *stack;
	unsigned int count;
	bool truncated;
	u64 start_ns, duration_ns;
	DECLARE_HASHTABLE(index, 10);
};
static struct proc_dir_entry *tg_entry;

static struct tg_row *tg_lookup(struct tg_snapshot *s, pid_t pid)
{
	struct tg_row *r;
	hash_for_each_possible(s->index, r, index, (unsigned int)pid)
		if (r->pid == pid)
			return r;
	return NULL;
}

/* Called only under rcu_read_lock(); buffers were allocated beforehand. */
static bool tg_copy(struct tg_snapshot *s, struct task_struct *task)
{
	struct tg_row *r;
	struct task_struct *parent;
	if (s->count == max_tasks) {
		s->truncated = true;
		return false;
	}
	r = &s->rows[s->count++];
	r->pid = task_pid_nr(task);
	r->tgid = task_tgid_nr(task);
	parent = rcu_dereference(task->real_parent);
	r->ppid = task_tgid_nr(parent);
	r->thread = r->pid != r->tgid;
	/* Thread edges mean membership, process edges mean parenthood. */
	r->parent = r->thread ? r->tgid : r->ppid;
	r->state = task_state_to_char(task);
	get_task_comm(r->comm, task);
	r->first = r->last = r->next = r->prev = -1;
	hash_add(s->index, &r->index, (unsigned int)r->pid);
	return true;
}

static void tg_free(struct tg_snapshot *s)
{
	if (!s)
		return;
	kvfree(s->rows);
	kvfree(s->stack);
	kvfree(s);
}

static void tg_tree(struct tg_snapshot *s)
{
	unsigned int i, serial = 0, top;
	struct tg_row *r, *p;
	int child;
	for (i = 1; i < s->count; i++) {
		r = &s->rows[i];
		p = tg_lookup(s, r->parent);
		if (!p || p == r) {
			p = &s->rows[0];
			r->orphan = true;
		}
		if (p->last >= 0) {
			s->rows[p->last].next = i;
			r->prev = p->last;
		} else {
			p->first = i;
		}
		p->last = i;
	}
	/* Iterative, bounded stack: no recursive use of the small kernel stack.
	 * The extra outer pass retains components disconnected by process churn. */
	for (i = 0; i < s->count; i++) {
		if (s->rows[i].visited)
			continue;
		top = 0;
		s->stack[top++] = i;
		while (top) {
			r = &s->rows[s->stack[--top]];
			if (r->visited)
				continue;
			r->visited = true;
			r->dfs = serial++;
			for (child = r->last; child >= 0;
			     child = s->rows[child].prev) {
				if (!s->rows[child].visited && top < max_tasks) {
					s->rows[child].depth = r->depth + 1;
					s->stack[top++] = child;
				}
			}
		}
	}
}

static struct tg_snapshot *tg_capture(void)
{
	struct tg_snapshot *s;
	struct task_struct *leader, *thread;
	s = kvzalloc(sizeof(*s), GFP_KERNEL);
	if (!s)
		return NULL;
	s->rows = kvcalloc(max_tasks, sizeof(*s->rows), GFP_KERNEL);
	s->stack = kvcalloc(max_tasks, sizeof(*s->stack), GFP_KERNEL);
	if (!s->rows || !s->stack) {
		tg_free(s);
		return NULL;
	}
	hash_init(s->index);
	s->start_ns = ktime_get_boottime_ns();
	rcu_read_lock();
	tg_copy(s, &init_task);
	for_each_process(leader) {
		if (!tg_copy(s, leader))
			goto unlock;
		for_each_thread(leader, thread) {
			if (thread != leader && !tg_copy(s, thread))
				goto unlock;
		}
	}
unlock:
	rcu_read_unlock();
	tg_tree(s);
	s->duration_ns = ktime_get_boottime_ns() - s->start_ns;
	return s;
}

/* Single-open retains the same snapshot across short reads and seq retries. */
static int tg_show(struct seq_file *m, void *v)
{
	struct tg_snapshot *s = m->private;
	struct tg_row *r;
	unsigned int i, j;
	seq_printf(m, "# taskgraph version=1 source=kernel count=%u cap=%u truncated=%u boot_ns=%llu duration_ns=%llu\n",
		   s->count, max_tasks, s->truncated,
		   (unsigned long long)s->start_ns,
		   (unsigned long long)s->duration_ns);
	seq_puts(m, "pid\tppid\ttgid\tparent\tstate\tkind\tlinear\tdfs\tdepth\torphan\tcomm\n");
	for (i = 0; i < s->count; i++) {
		r = &s->rows[i];
		seq_printf(m, "%d\t%d\t%d\t%d\t%c\t%s\t%u\t%u\t%u\t%u\t",
			   r->pid, r->ppid, r->tgid, r->parent, r->state,
			   i == 0 ? "root" : (r->thread ? "thread" : "process"),
			   i, r->dfs, r->depth, r->orphan);
		/* Escape delimiter/control bytes in an arbitrary task command name. */
		for (j = 0; j < TASK_COMM_LEN && r->comm[j]; j++) {
			unsigned char c = r->comm[j];
			if (c < 32 || c >= 127 || c == '\\')
				seq_printf(m, "\\x%02x", c);
			else
				seq_putc(m, c);
		}
		seq_putc(m, '\n');
	}
	return 0;
}

static int tg_open(struct inode *inode, struct file *file)
{
	struct tg_snapshot *s = tg_capture();
	int ret;
	if (!s)
		return -ENOMEM;
	ret = single_open(file, tg_show, s);
	if (ret)
		tg_free(s);
	return ret;
}

static int tg_release(struct inode *inode, struct file *file)
{
	struct seq_file *m = file->private_data;
	tg_free(m->private);
	return single_release(inode, file);
}

static const struct proc_ops tg_ops = {
	.proc_open = tg_open,
	.proc_read = seq_read,
	.proc_lseek = seq_lseek,
	.proc_release = tg_release,
};

static int __init tg_init(void)
{
	struct tg_snapshot *s;
	struct tg_row *r;
	unsigned int i;
	if (max_tasks < 16 || max_tasks > TG_MAX)
		return -EINVAL;
	/* Make the capture even if logging is disabled: detect allocation errors. */
	s = tg_capture();
	if (!s)
		return -ENOMEM;
	tg_entry = proc_create(TG_NAME, 0444, NULL, &tg_ops);
	if (!tg_entry) {
		tg_free(s);
		return -ENOMEM;
	}
	if (log_on_load) {
		for (i = 1; i < s->count; i++) {
			r = &s->rows[i];
			if (!r->thread)
				pr_info("taskgraph LINEAR pid=%d state=%c comm=%s\n",
					r->pid, r->state, r->comm);
		}
		/* Invert DFS ranks using the already allocated work array. */
		for (i = 0; i < s->count; i++)
			s->stack[s->rows[i].dfs] = i;
		for (i = 0; i < s->count; i++) {
			r = &s->rows[s->stack[i]];
			pr_info("taskgraph DFS order=%u depth=%u pid=%d ppid=%d state=%c comm=%s\n",
				r->dfs, r->depth, r->pid, r->ppid, r->state, r->comm);
		}
	}
	pr_info("taskgraph loaded count=%u truncated=%u; read /proc/taskgraph\n",
		s->count, s->truncated);
	tg_free(s);
	return 0;
}

static void __exit tg_exit(void)
{
	proc_remove(tg_entry);
	pr_info("taskgraph unloaded\n");
}
module_init(tg_init);
module_exit(tg_exit);
MODULE_LICENSE("GPL");
MODULE_AUTHOR("F.CSM302 Project 3 team");
MODULE_DESCRIPTION("Task listing and real process graph snapshot");
MODULE_VERSION("1.0");
