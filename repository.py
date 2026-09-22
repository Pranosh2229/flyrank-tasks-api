from abc import ABC, abstractmethod
from typing import Optional


class TaskRepository(ABC):
    """Storage-agnostic interface. Routes in main.py depend only on this —
    swapping backends (SQLite, Postgres, ...) means swapping which
    implementation get_repository() returns, nothing in main.py changes."""

    @abstractmethod
    def list_tasks(self) -> list[dict]:
        ...

    @abstractmethod
    def get_task(self, task_id: int) -> Optional[dict]:
        ...

    @abstractmethod
    def create_task(self, title: str, done: bool) -> dict:
        ...

    @abstractmethod
    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        ...

    @abstractmethod
    def delete_task(self, task_id: int) -> bool:
        ...
