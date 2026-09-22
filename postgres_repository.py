from typing import Optional

import psycopg
from psycopg.rows import dict_row

from repository import TaskRepository


def _row_to_task(row: dict) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


class PostgresTaskRepository(TaskRepository):
    """Same interface as SQLiteTaskRepository — main.py never knows which
    one it's talking to. Table creation/seeding lives in db/init.sql,
    run once by Postgres itself on first container startup (not here),
    matching the assignment's "one SQL file" requirement."""

    def __init__(self, database_url: str):
        self.database_url = database_url

    def _get_connection(self):
        return psycopg.connect(self.database_url, row_factory=dict_row)

    def list_tasks(self) -> list[dict]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
            return [_row_to_task(r) for r in rows]

    def get_task(self, task_id: int) -> Optional[dict]:
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM tasks WHERE id = %s", (task_id,)
            ).fetchone()
            return _row_to_task(row) if row else None

    def create_task(self, title: str, done: bool) -> dict:
        with self._get_connection() as conn:
            row = conn.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING *",
                (title, done),
            ).fetchone()
            return _row_to_task(row)

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        with self._get_connection() as conn:
            row = conn.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING *",
                (title, done, task_id),
            ).fetchone()
            return _row_to_task(row) if row else None

    def delete_task(self, task_id: int) -> bool:
        with self._get_connection() as conn:
            cur = conn.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0
