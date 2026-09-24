import os
from typing import Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from supabase_auth.errors import AuthApiError

from get_repository import get_repository
from supabase_client import supabase, SUPABASE_KEY, SUPABASE_URL
from llm.schema import EnrichInput, EnrichOutput, STUB_OUTPUT

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


# BE-07 Stage 1: a wrong type, missing field, or over-length value must be a
# 400 naming the field -- not FastAPI's default 422 -- so a caller can tell
# immediately what to fix, before any model call is ever made.
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        field = ".".join(str(p) for p in errors[0]["loc"] if p != "body")
        message = f"{field}: {errors[0]['msg']}"
    else:
        message = "Invalid request"
    return JSONResponse(status_code=400, content={"error": message})


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


# Stage 5: registering this as a security scheme (rather than reading the
# Authorization header manually) is what makes Swagger's "Authorize"
# padlock appear on every route that depends on it, and lets FastAPI parse
# the "Bearer <token>" prefix itself instead of hand-rolled string slicing.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """Reusable auth guard (FastAPI dependency). Verifies the bearer token
    with Supabase; every protected route just depends on this instead of
    repeating the check. Returns the user plus the raw token, since
    /auth/logout needs the token itself, not just the user it names."""
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="Access token required")
    token = credentials.credentials
    try:
        result = supabase.auth.get_user(token)
    except AuthApiError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    if result is None or result.user is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return {"user": result.user, "token": token}


@app.get("/public/info")
def public_info():
    return {"message": "Welcome stranger! This info is public."}


@app.get("/protected/profile")
def protected_profile(auth=Depends(get_current_user)):
    return auth["user"].model_dump(mode="json", include={"id", "email", "created_at"})


@app.get("/protected/dashboard")
def protected_dashboard(auth=Depends(get_current_user)):
    return {"message": f"welcome to your dashboard, {auth['user'].email}"}


@app.post("/auth/logout", status_code=204)
def logout(auth=Depends(get_current_user)):
    # supabase.auth.sign_out() acts on the shared client's own cached
    # session — this API is stateless and never populates one, so that
    # call would silently no-op. Hitting Supabase Auth's REST endpoint
    # directly with the caller's own token actually revokes that session,
    # using only the anon key.
    httpx.post(
        f"{SUPABASE_URL}/auth/v1/logout",
        params={"scope": "global"},
        headers={"Authorization": f"Bearer {auth['token']}", "apikey": SUPABASE_KEY},
    )
    return None


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


# BE-07: POST /enrich -- judge a scraped book record's audience, write an
# inferred blurb, flag quality concerns. Input validation happens via
# EnrichInput's Pydantic model before any model call, so a malformed
# request never spends a call. Stage 1: stub mode only, no model wired yet.
@app.post("/enrich", response_model=EnrichOutput)
def enrich(payload: EnrichInput):
    if os.environ.get("LLM_STUB") == "1":
        return STUB_OUTPUT
    raise HTTPException(status_code=501, detail="model call not implemented yet (Stage 2)")
