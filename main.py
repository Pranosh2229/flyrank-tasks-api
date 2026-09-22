from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db import get_connection, init_db

app = FastAPI(title="Tasks API")

init_db()

# PUT/DELETE still use this in-memory list — Stage 3 switches them over to
# SQL. GET (Stage 1) and POST (Stage 2) already use tasks.db.
tasks: list[dict] = [
    {"id": 1, "title": "Buy milk", "done": False},
    {"id": 2, "title": "Write README", "done": False},
    {"id": 3, "title": "Push to GitHub", "done": False},
]
next_id = 4


class TaskIn(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = False


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


def row_to_task(row) -> dict:
    return {"id": row["id"], "title": row["title"], "done": bool(row["done"])}


def find_task(task_id: int) -> dict:
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks")
def list_tasks():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM tasks").fetchall()
    conn.close()
    return [row_to_task(r) for r in rows]


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return row_to_task(row)


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO tasks (title, done) VALUES (?, ?)",
        (payload.title, int(bool(payload.done))),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)
    ).fetchone()
    conn.close()
    return row_to_task(row)


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn):
    task = find_task(task_id)
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    task["title"] = payload.title
    task["done"] = bool(payload.done)
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    task = find_task(task_id)
    tasks.remove(task)
    return None
