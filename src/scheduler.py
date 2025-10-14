from dataclasses import dataclass
from typing import Dict, List, Optional

# ----- Hardcoded Menu -----
REQUIRED_MENU: Dict[str, int] = {
    "americano": 2,
    "latte": 3,
    "cappuccino": 3,
    "mocha": 4,
    "tea": 1,
    "macchiato": 2,
    "hot_chocolate": 4,
}


# ----- Task -----
@dataclass
class Task:
    task_id: str
    remaining: int


# ----- Simple FIFO Queue -----
class QueueRR:
    """A simple FIFO queue with capacity limit."""

    def __init__(self, queue_id: str, capacity: int) -> None:
        self.queue_id = queue_id
        self.capacity = capacity
        self.data: List[Task] = []

    def enqueue(self, task: Task) -> bool:
        if len(self.data) >= self.capacity:
            return False
        self.data.append(task)
        return True

    def dequeue(self) -> Optional[Task]:
        if not self.data:
            return None
        return self.data.pop(0)

    def __len__(self) -> int:
        return len(self.data)

    def peek(self) -> Optional[Task]:
        return self.data[0] if self.data else None

    def __iter__(self):
        return iter(self.data)


# ----- Scheduler -----
class Scheduler:
    def __init__(self) -> None:
        self.time = 0
        self.queues: Dict[str, QueueRR] = {}
        self.queue_order: List[str] = []
        self.id_counter: Dict[str, int] = {}
        self.skip_flags: Dict[str, bool] = {}
        self.rr_index = 0
        self._menu = REQUIRED_MENU.copy()

    # ----- Helpers -----
    def menu(self) -> Dict[str, int]:
        return self._menu.copy()

    def next_queue(self) -> Optional[str]:
        if not self.queue_order:
            return None
        return self.queue_order[self.rr_index % len(self.queue_order)]

    # ----- Queue creation -----
    def create_queue(self, queue_id: str, capacity: int) -> List[str]:
        logs = []
        if queue_id not in self.queues:
            self.queues[queue_id] = QueueRR(queue_id, capacity)
            self.queue_order.append(queue_id)
            self.id_counter[queue_id] = 0
            self.skip_flags[queue_id] = False
            logs.append(f"time={self.time} event=create queue={queue_id}")
        return logs

    # ----- Enqueue -----
    def enqueue(self, queue_id: str, item_name: str) -> List[str]:
        logs = []
        if queue_id not in self.queues:
            return logs  # unknown queue - silently ignore for this simple version

        q = self.queues[queue_id]
        self.id_counter[queue_id] += 1
        task_id = f"{queue_id}-{self.id_counter[queue_id]:03d}"

        # Item not on menu
        if item_name not in self._menu:
            print("Sorry, we don't serve that.")
            logs.append(
                f"time={self.time} event=reject queue={queue_id} task={task_id} reason=unknown_item"
            )
            return logs

        # Queue full
        burst = self._menu[item_name]
        task = Task(task_id, burst)
        if not q.enqueue(task):
            print("Sorry, we're at capacity.")
            logs.append(
                f"time={self.time} event=reject queue={queue_id} task={task_id} reason=full"
            )
            return logs

        # Success
        logs.append(
            f"time={self.time} event=enqueue queue={queue_id} task={task_id} remaining={burst}"
        )
        return logs

    # ----- Mark Skip -----
    def mark_skip(self, queue_id: str) -> List[str]:
        logs = []
        if queue_id in self.skip_flags:
            self.skip_flags[queue_id] = True
            logs.append(f"time={self.time} event=skip queue={queue_id}")
        return logs

    # ----- Run -----
    def run(self, quantum: int, steps: Optional[int]) -> List[str]:
        logs = []

        n_queues = len(self.queue_order)
        if n_queues == 0:
            return logs

        # Step validation
        if steps is not None:
            if steps < 1 or steps > n_queues:
                logs.append(f"time={self.time} event=error reason=invalid_steps")
                return logs
            turns = steps
        else:
            # run until all queues empty and no skips pending
            turns = n_queues * 100  # safety loop limit (enough to drain)
        turns_done = 0

        while turns_done < turns:
            if n_queues == 0:
                break

            qid = self.queue_order[self.rr_index]
            q = self.queues[qid]

            logs.append(f"time={self.time} event=run queue={qid}")

            # Handle skip
            if self.skip_flags[qid]:
                self.skip_flags[qid] = False
                # no time advance
            else:
                # If queue has task
                if len(q) > 0:
                    task = q.dequeue()
                    work_time = min(task.remaining, quantum)
                    task.remaining -= work_time
                    self.time += work_time

                    if task.remaining > 0:
                        q.enqueue(task)
                        logs.append(
                            f"time={self.time} event=work queue={qid} task={task.task_id} remaining={task.remaining}"
                        )
                    else:
                        logs.append(
                            f"time={self.time} event=finish queue={qid} task={task.task_id}"
                        )
                # else: empty queue -> do nothing

            # After each run turn, move RR pointer and produce display
            self.rr_index = (self.rr_index + 1) % n_queues
            logs.extend(self.display())
            turns_done += 1

            # stop if run until empty mode (no steps) and all empty+no skip
            if steps is None:
                all_empty = all(len(qx) == 0 for qx in self.queues.values())
                no_skips = not any(self.skip_flags.values())
                if all_empty and no_skips:
                    break

        return logs

    # ----- Display -----
    def display(self) -> List[str]:
        lines = []
        next_qid = self.next_queue() or "none"

        lines.append(f"display time={self.time} next={next_qid}")
        # sorted menu
        menu_items = ",".join(
            f"{name}:{mins}" for name, mins in sorted(self._menu.items())
        )
        lines.append(f"display menu=[{menu_items}]")

        # queues
        for qid in self.queue_order:
            q = self.queues[qid]
            skip_tag = " [ skip]" if self.skip_flags[qid] else ""
            tasks_str = ",".join(
                f"{t.task_id}:{t.remaining}" for t in q.data
            )
            lines.append(
                f"display {qid} [{len(q)}/{q.capacity}]{skip_tag} -> [{tasks_str}]"
            )

        return lines