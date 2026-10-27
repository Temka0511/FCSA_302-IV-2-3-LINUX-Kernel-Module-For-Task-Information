// SPDX-License-Identifier: GPL-2.0
/* F.CSM302 / Project 3: for_each_process and direct children/sibling DFS.
 * Target: Ubuntu 24.04 GA kernel 6.8. Rebuild for the running kernel.
 * tasklist_lock is not exported to modules. stop_machine() quiesces all CPUs
 * for the bounded, allocation-free capture and direct process-tree walk.
 * Intended for an educational VM, not latency-sensitive production systems.
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
#include <linux/stop_machine.h>
#include <linux/err.h>

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
	unsigned int dfs, depth;
	bool thread, orphan, visited;
	struct hlist_node index;
};
struct tg_frame {
	struct task_struct *leader, *owner;
	struct list_head *next_child;
	unsigned int depth;
};
struct tg_snapshot {
	struct tg_row *rows;
	struct tg_frame *stack;
	unsigned int *order;
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

/* Called only inside stop_machine + RCU; buffers allocated beforehand. */
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
	hash_add(s->index, &r->index, (unsigned int)r->pid);
	return true;
}

static void tg_free(struct tg_snapshot *s)
{
	if (!s)
		return;
	kvfree(s->rows);
	kvfree(s->stack);
	kvfree(s->order);
	kvfree(s);
}

/* Enter a process, then its thread members. Child processes are visited by
 * following each member's real children/sibling lists, including children
 * forked by a non-leader thread. No parent-ID reconstruction is used. */
static bool tg_enter(struct tg_snapshot *s, struct task_struct *leader,
		     unsigned int depth, unsigned int *serial)
{
	struct task_struct *thread;
	struct tg_row *r = tg_lookup(s, task_pid_nr(leader));
	if (!r || r->visited)
		return false;
	r->visited = true;
	r->dfs = (*serial)++;
	r->depth = depth;
	for_each_thread(leader, thread) {
		if (thread == leader)
			continue;
		r = tg_lookup(s, task_pid_nr(thread));
		if (r && !r->visited) {
			r->visited = true;
			r->dfs = (*serial)++;
			r->depth = depth + 1;
		}
	}
	return true;
}

static void tg_walk(struct tg_snapshot *s, struct task_struct *leader,
		    unsigned int depth, unsigned int *serial)
{
	struct tg_frame *f;
	struct task_struct *child;
	struct list_head *link;
	unsigned int top = 0;
	if (!tg_enter(s, leader, depth, serial))
		return;
	s->stack[top++] = (struct tg_frame) {
		leader, leader, leader->children.next, depth
	};
	while (top) {
		f = &s->stack[top - 1];
		if (f->next_child == &f->owner->children) {
			f->owner = next_thread(f->owner);
			if (f->owner == f->leader) {
				top--;
				continue;
			}
			f->next_child = f->owner->children.next;
			continue;
		}
		link = f->next_child;
		f->next_child = link->next;
		child = list_entry(link, struct task_struct, sibling)->group_leader;
		depth = f->depth + 1;
		if (top < max_tasks && tg_enter(s, child, depth, serial))
			s->stack[top++] = (struct tg_frame) {
				child, child, child->children.next, depth
			};
	}
}

/* stop_machine callback: never allocate, sleep, print or call user space. */
static int tg_capture_stopped(void *data)
{
	struct tg_snapshot *s = data;
	struct task_struct *leader, *thread;
	struct tg_row *r;
	unsigned int i, serial = 0;
	s->start_ns = ktime_get_boottime_ns();
	rcu_read_lock();
	tg_copy(s, &init_task);
	for_each_process(leader) {
		if (!tg_copy(s, leader))
			goto captured;
		for_each_thread(leader, thread) {
			if (thread != leader && !tg_copy(s, thread))
				goto captured;
		}
	}
captured:
	for (i = 1; i < s->count; i++) {
		r = &s->rows[i];
		if (!tg_lookup(s, r->parent)) {
			r->parent = 0;
			r->orphan = true;
		}
	}
	tg_walk(s, &init_task, 0, &serial);
	/* A capped capture may omit an ancestor of a retained task. Preserve
	 * those rows, mark the missing edge, and walk their actual child lists. */
	for_each_process(leader) {
		r = tg_lookup(s, task_pid_nr(leader));
		if (r && !r->visited)
			tg_walk(s, leader, 1, &serial);
	}
	for (i = 0; i < s->count; i++) {
		r = &s->rows[i];
		if (!r->visited) {
			r->visited = true;
			r->orphan = true;
			r->parent = 0;
			r->depth = 1;
			r->dfs = serial++;
		}
		s->order[r->dfs] = i;
	}
	rcu_read_unlock();
	s->duration_ns = ktime_get_boottime_ns() - s->start_ns;
	return 0;
}

static struct tg_snapshot *tg_capture(void)
{
	struct tg_snapshot *s;
	int ret;
	s = kvzalloc(sizeof(*s), GFP_KERNEL);
	if (!s)
		return ERR_PTR(-ENOMEM);
	s->rows = kvcalloc(max_tasks, sizeof(*s->rows), GFP_KERNEL);
	s->stack = kvcalloc(max_tasks, sizeof(*s->stack), GFP_KERNEL);
	s->order = kvcalloc(max_tasks, sizeof(*s->order), GFP_KERNEL);
	if (!s->rows || !s->stack || !s->order) {
		tg_free(s);
		return ERR_PTR(-ENOMEM);
	}
	hash_init(s->index);
	ret = stop_machine(tg_capture_stopped, s, NULL);
	if (ret) {
		tg_free(s);
		return ERR_PTR(ret);
	}
	return s;
}

/* Single-open retains the same snapshot across short reads and seq retries. */
static int tg_show(struct seq_file *m, void *v)
{
	struct tg_snapshot *s = m->private;
	struct tg_row *r;
	unsigned int i, j;
	seq_printf(m, "# taskgraph version=1 source=kernel count=%u cap=%u truncated=%u boot_ns=%llu duration_ns=%llu traversal=children_sibling synchronization=stop_machine\n",
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
	if (IS_ERR(s))
		return PTR_ERR(s);
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
	if (IS_ERR(s))
		return PTR_ERR(s);
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
		for (i = 0; i < s->count; i++) {
			r = &s->rows[s->order[i]];
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
MODULE_VERSION("1.1");
