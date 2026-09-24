# Tasks API

A tiny CRUD API for managing a to-do list. FlyRank Backend Engineering Internship — Assignment A1 (in-memory), Assignment A2 (SQLite), Assignment A3/BE-04 (containerized, Postgres), BE-03/A4 (Supabase Auth — sign up, log in, log out, protected routes), BE-05/A9 (a separate polite scraper — see [`scraper/README.md`](scraper/README.md)).

## Setup — environment variables

```bash
cp .env.example .env
```

Then fill in `.env` with your own values (never commit this file — it's git-ignored):

| Variable | Where to get it |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Pick anything — used only by the local Docker Postgres container |
| `DATABASE_URL` | Set automatically for Docker (`db` is the compose service name); leave unset to fall back to SQLite locally |
| `SUPABASE_URL` | Your Supabase project → **Project Settings → API Keys** → Project URL |
| `SUPABASE_KEY` | Same page → **Publishable key** (never the **Secret key** — that bypasses all security) |
| `PORT` | `8000` for local FastAPI dev |

One-time Supabase dashboard setting for local testing: **Authentication → Sign In / Providers → Email → turn off "Confirm email"**, so a fresh signup can log in immediately (leave this on in a real production project).

## Run it — Docker (Postgres, the real stack)

```bash
docker compose up -d --build
curl http://localhost:8000/tasks
```

That's the whole stack: Postgres with a persistent volume, and the API, started with one command. `docker compose down` stops both containers but keeps the volume, so data survives; add `-v` only if you actually want to wipe it.

## Run it — locally without Docker (SQLite, for quick local dev)

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

With no `DATABASE_URL` set, the app falls back to the SQLite repository from Assignment A2 — same routes, same behaviour, different storage. That fallback is what "the architecture proves itself" actually means here: `get_repository.py` is the *only* file that decides which backend to use; `main.py`'s routes never change either way.

## Endpoints

| Method | Path | Auth required? | Behaviour |
|--------|------|:---:|---|
| POST | `/auth/signup` | No | Create a Supabase user, `201` on success, `400` if `email`/`password` missing |
| POST | `/auth/login` | No | Log in via Supabase, `200` + `access_token`/`refresh_token`, `401` on bad credentials |
| POST | `/auth/logout` | **Yes** | Revoke the caller's Supabase session, `204` on success |
| GET | `/public/info` | No | `200`, no auth needed |
| GET | `/protected/profile` | **Yes** | `200` with `id`/`email`/`created_at`, `401` if the bearer token is missing/invalid/expired |
| GET | `/protected/dashboard` | **Yes** | Same guard as `/protected/profile`, proves the auth middleware is reusable |
| GET | `/tasks` | No | List all tasks |
| GET | `/tasks/{id}` | No | Get one task, `404` if it doesn't exist |
| POST | `/tasks` | No | Create a task, `400` if `title` is missing |
| PUT | `/tasks/{id}` | No | Update a task, `404`/`400` as above |
| DELETE | `/tasks/{id}` | No | Delete a task, `404` if it doesn't exist |

Protected routes expect `Authorization: Bearer <access_token>` from `/auth/login`.

## Authentication (BE-03)

Supabase Auth is the Identity Provider — this app never hashes a password or signs a token itself; it only sends credentials to Supabase and verifies the tokens Supabase hands back (`supabase_client.py`).

- **`get_current_user`** (`main.py`) is the single reusable FastAPI dependency — every protected route just adds `Depends(get_current_user)`. It's registered against FastAPI's `HTTPBearer` security scheme, which is what makes the "Authorize" padlock appear on the right routes in Swagger and gives FastAPI's own `Bearer <token>` parsing instead of hand-rolled header slicing.
- **Logout** calls Supabase Auth's `/auth/v1/logout` REST endpoint directly with the caller's own token, rather than the SDK's `sign_out()` — that method acts on the *shared client's own* cached session, and this API is stateless (one client instance, many users), so it would silently no-op. Hitting the REST endpoint with the caller's token revokes that specific session, still using only the publishable key.
- **Swagger UI** at `/docs` shows a lock icon on every protected route; click **Authorize**, paste an `access_token` from `/auth/login`, and "Try it out" works directly from the browser:

![Swagger UI with bearer auth](swagger-auth-screenshot.png)

## Architecture (BE-04)

```
main.py  →  TaskRepository (interface, repository.py)
                  ├── SQLiteTaskRepository    (used when DATABASE_URL is unset)
                  └── PostgresTaskRepository  (used when DATABASE_URL is set — Docker sets it)
```

`get_repository.py` is the single switch. Every route in `main.py` calls `repo.list_tasks()`, `repo.create_task(...)`, etc. — it has no idea which database is behind that call. Swapping SQLite for Postgres was a matter of adding `postgres_repository.py` and never touching a single route.

## Database

**SQLite (A2, local dev):** `tasks.db`, created automatically next to `main.py`, git-ignored. Zero setup — the whole database is one file, and the file is the backup.

**Postgres (A3/BE-04, the real stack):** runs in Docker with a named volume (`pgdata`), so data survives `docker compose down` and even the container being deleted and recreated. Table + seed data come from `db/init.sql`, which Postgres runs automatically — and only once ever — the first time it starts against an empty volume (that's Postgres's own `docker-entrypoint-initdb.d` mechanism, not custom code).

**Why Postgres over just staying on SQLite:** SQLite is one file on one machine — fine for a solo dev loop, wrong for anything with concurrent writers or that needs to run as a separate service other things connect to. Docker + Postgres is what makes this look like a real deployable stack instead of a demo, and every later week's work (jobs, caching, RAG) assumes this local stack exists.

**Connection string:** lives in `.env` (git-ignored), copied from the committed `.env.example`. `docker-compose.yml` passes it into the `app` container as `DATABASE_URL`; the `db` container gets `POSTGRES_USER`/`PASSWORD`/`DB` from the same file.

### Persistence proof (BE-04 requirement)

Verified directly, not assumed:

1. `docker compose up -d --build` — both containers start, `db` passes its healthcheck before `app` starts (via `depends_on: condition: service_healthy`).
2. `GET /tasks` → the 3 seeded rows, read live from Postgres.
3. `POST /tasks` a new row, `PUT` it to `done: true`.
4. `docker compose down` — **both containers are stopped and removed entirely** (not just the app).
5. `docker compose up -d` — fresh containers, same named volume.
6. `GET /tasks` → all 4 rows still there, including the one created and updated in step 3, with `done: true` intact.

That's a full container teardown, not a soft restart — the volume is what survived, which is the actual point of Assignment A2 → A3: the interface never changed, only which repository sits behind it.

## SQL explored by hand (Stage 4)

Ran directly against `tasks.db` with the server live, no restart, and confirmed through the running API:

```sql
UPDATE tasks SET done = 1 WHERE id = 2;
```

Before: `GET /tasks/2` → `{"id":2,"title":"Write README","done":false}`
Ran that `UPDATE` directly against the database file (same thing DB Browser does).
After, same running server, no restart: `GET /tasks/2` → `{"id":2,"title":"Write README","done":true}` — the API reflected the change instantly, because it and the database viewer read the exact same file.

Also confirmed in [DB Browser for SQLite](https://sqlitebrowser.org/) directly — `SELECT * FROM tasks WHERE done = 1;` against the freshly seeded database correctly returns 0 rows, since none of the three seed tasks start out done:

![DB Browser screenshot](db-browser.png)
