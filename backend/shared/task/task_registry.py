from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class TaskRegistry:
    busy_tasks: set[str] = field(default_factory=set)
    stopped_tasks: set[str] = field(default_factory=set)
    lock: Lock = field(default_factory=Lock)

    def start_task(self, name: str) -> bool:
        with self.lock:
            if name in self.busy_tasks:
                return False
            self.busy_tasks.add(name)
            self.stopped_tasks.discard(name)
            return True

    def finish_task(self, name: str) -> None:
        with self.lock:
            self.busy_tasks.discard(name)
            self.stopped_tasks.discard(name)

    def request_stop(self, name: str) -> bool:
        with self.lock:
            if name not in self.busy_tasks:
                return False
            self.stopped_tasks.add(name)
            return True

    def is_stop_requested(self, name: str) -> bool:
        with self.lock:
            return name in self.stopped_tasks

    def is_running(self, name: str) -> bool:
        with self.lock:
            return name in self.busy_tasks
