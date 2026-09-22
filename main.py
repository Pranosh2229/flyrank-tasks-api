from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from db import init_db

app = FastAPI(title="Tasks API")

# SQLite database is created and seeded on startup, but the endpoints below
# still read/write the in-memory list for now — Stage 1 switches them over.
init_db()

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


def find_task(task_id: int) -> dict:
    task = next((t for t in tasks if t["id"] == task_id), None)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.get("/tasks")
def list_tasks():
    return tasks


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    return find_task(task_id)


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    global next_id
    task = {"id": next_id, "title": payload.title, "done": bool(payload.done)}
    tasks.append(task)
    next_id += 1
    return task


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
