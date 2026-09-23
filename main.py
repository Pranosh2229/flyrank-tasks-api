from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError

from get_repository import get_repository
from supabase_client import supabase

app = FastAPI(title="Tasks API")

repo = get_repository()


@app.on_event("startup")
async def startup_event():
    # supabase_client already built the client at import time (Stage 0);
    # this just confirms it's the object this process is holding.
    assert supabase is not None
    print("Server running and connected to Supabase")


class TaskIn(BaseModel):
    title: Optional[str] = None
    done: Optional[bool] = False


class AuthIn(BaseModel):
    email: Optional[str] = None
    password: Optional[str] = None


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.post("/auth/signup", status_code=201)
def signup(payload: AuthIn):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_up(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError as exc:
        raise HTTPException(status_code=400, detail=exc.message)
    return result.user.model_dump(mode="json")


@app.post("/auth/login")
def login(payload: AuthIn):
    if not payload.email or not payload.password:
        raise HTTPException(status_code=400, detail="email and password are required")
    try:
        result = supabase.auth.sign_in_with_password(
            {"email": payload.email, "password": payload.password}
        )
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid login credentials")
    return {
        "access_token": result.session.access_token,
        "refresh_token": result.session.refresh_token,
    }


def _extract_bearer_token(authorization: Optional[str]) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Access token required")
    token = authorization[len("Bearer ") :].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Access token required")
    return token


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(authorization: Optional[str] = Header(None)):
    # Stage 2: only checks a token was presented. Stage 3 verifies it with Supabase.
    _extract_bearer_token(authorization)
    return {"message": "token received, not yet verified"}


@app.get("/tasks")
def list_tasks():
    return repo.list_tasks()


@app.get("/tasks/{task_id}")
def get_task(task_id: int):
    task = repo.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.post("/tasks", status_code=201)
def create_task(payload: TaskIn):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    return repo.create_task(payload.title, bool(payload.done))


@app.put("/tasks/{task_id}")
def update_task(task_id: int, payload: TaskIn):
    if not payload.title or not payload.title.strip():
        raise HTTPException(status_code=400, detail="title is required")
    task = repo.update_task(task_id, payload.title, bool(payload.done))
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@app.delete("/tasks/{task_id}", status_code=204)
def delete_task(task_id: int):
    deleted = repo.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Task not found")
    return None
