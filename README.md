# Tasks API

A tiny CRUD API for managing a to-do list. FlyRank Backend Engineering Internship — Assignment A1 (in-memory), Assignment A2 (SQLite), Assignment A3/BE-04 (containerized, Postgres).

## Run it — Docker (Postgres, the real stack)

```bash
cp .env.example .env
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

| Method | Path          | Behaviour                                  |
|--------|---------------|---------------------------------------------|
| GET    | `/tasks`      | List all tasks                              |
| GET    | `/tasks/{id}` | Get one task, `404` if it doesn't exist     |
| POST   | `/tasks`      | Create a task, `400` if `title` is missing  |
| PUT    | `/tasks/{id}` | Update a task, `404`/`400` as above         |
| DELETE | `/tasks/{id}` | Delete a task, `404` if it doesn't exist    |

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
