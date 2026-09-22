import sqlite3
from pathlib import Path
from typing import Optional

from repository import TaskRepository

DB_PATH = Path(__file__).parent / "tasks.db"

SEED_TASKS = [
    ("Buy milk", 0),
    ("Write README", 0),
    ("Push to GitHub", 0),
]


def _row_to_task(row: sqlite3.Row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


class SQLiteTaskRepository(TaskRepository):
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done BOOLEAN NOT NULL DEFAULT 0
            )
            """
        )
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS
            )
            conn.commit()
        conn.close()

    def list_tasks(self) -> list[dict]:
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM tasks").fetchall()
        conn.close()
        return [_row_to_task(r) for r in rows]

    def get_task(self, task_id: int) -> Optional[dict]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return _row_to_task(row) if row else None

    def create_task(self, title: str, done: bool) -> dict:
        conn = self._get_connection()
        cur = conn.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)", (title, int(done))
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        conn.close()
        return _row_to_task(row)

    def update_task(self, task_id: int, title: str, done: bool) -> Optional[dict]:
        conn = self._get_connection()
        existing = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if existing is None:
            conn.close()
            return None
        conn.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (title, int(done), task_id),
        )
        conn.commit()
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        conn.close()
        return _row_to_task(row)

    def delete_task(self, task_id: int) -> bool:
        conn = self._get_connection()
        existing = conn.execute(
            "SELECT * FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if existing is None:
            conn.close()
            return False
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        return True
